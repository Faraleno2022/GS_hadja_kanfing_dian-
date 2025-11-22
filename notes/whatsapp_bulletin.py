"""
Module pour l'envoi de bulletins PDF par WhatsApp aux parents
"""

import os
import tempfile
import logging
from django.conf import settings
from django.http import JsonResponse, HttpResponse
from django.shortcuts import get_object_or_404
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
from django.template.loader import render_to_string
from django.contrib import messages
from django.shortcuts import redirect
from django.utils import timezone
from decimal import Decimal

from eleves.models import Eleve, Classe as ClasseEleve
from .models import MatiereNote, Note, Evaluation
from .calculs_moyennes import calculer_moyenne_generale_eleve, calculer_classement_classe
from paiements.models import Relance

logger = logging.getLogger(__name__)

class WhatsAppBulletinSender:
    """Gestionnaire pour l'envoi de bulletins par WhatsApp"""
    
    def __init__(self):
        self.temp_files = []  # Pour nettoyer les fichiers temporaires
    
    def generer_bulletin_pdf(self, eleve_id, classe_id, periode, system_type='trimestre'):
        """
        Génère le PDF du bulletin pour un élève
        
        Returns:
            tuple: (file_path, filename) ou (None, None) si erreur
        """
        try:
            # Récupérer l'élève et la classe
            eleve = get_object_or_404(Eleve, id=eleve_id)
            classe_eleve = get_object_or_404(ClasseEleve, id=classe_id)
            
            # Récupérer les matières et notes
            matieres = MatiereNote.objects.filter(classe=classe_eleve, actif=True)
            
            if not matieres.exists():
                logger.error(f"Aucune matière trouvée pour la classe {classe_eleve.nom}")
                return None, None
            
            # Calculer les données du bulletin
            result_centralized = calculer_moyenne_generale_eleve(eleve, matieres, periode, system_type)
            
            # Calculer le classement
            eleves = Eleve.objects.filter(classe=classe_eleve, actif=True)
            classement_complet = calculer_classement_classe(eleves, matieres, periode, system_type)
            
            # Trouver le rang de l'élève
            rang_eleve = "N/A"
            for rang_data in classement_complet:
                if rang_data['eleve'].id == eleve.id:
                    rang_eleve = rang_data['rang']
                    break
            
            # Préparer les données pour le template
            bulletin_data = {
                'eleve': eleve,
                'moyenne_generale': result_centralized['moyenne_generale'],
                'details_matieres': result_centralized['details_matieres'],
                'rang': rang_eleve,
                'mention': result_centralized.get('mention', 'N/A'),
                'appreciation': result_centralized.get('appreciation', 'Bon travail. Continuez vos efforts.'),
                'effectif': eleves.count(),
                'titre_periode': self._get_titre_periode(periode, system_type)
            }
            
            # Récupérer l'école
            user_profil = getattr(eleve.classe.ecole, 'profil', None) if eleve.classe else None
            ecole = eleve.classe.ecole if eleve.classe else None
            
            # Préparer le contexte pour le template
            context = {
                'bulletin_data': bulletin_data,
                'classe_selectionnee': classe_eleve,
                'periode_selectionnee': periode,
                'system_type': system_type,
                'ecole': ecole,
                'annee_scolaire': classe_eleve.annee_scolaire if classe_eleve else timezone.now().year,
            }
            
            # Générer le HTML
            html_string = render_to_string('notes/bulletin_dynamique.html', context)
            
            # Générer le PDF
            try:
                from weasyprint import HTML, CSS
                from weasyprint.text.fonts import FontConfiguration
                
                # Configuration des polices
                font_config = FontConfiguration()
                
                # CSS pour le PDF
                css_string = """
                @page { size: A4; margin: 0.5cm; }
                body { font-family: 'DejaVu Sans', sans-serif; font-size: 10px; }
                .no-print { display: none !important; }
                .bulletin-container { margin: 0; padding: 0; }
                """
                
                # Créer un fichier temporaire
                with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf', prefix='bulletin_') as temp_file:
                    temp_path = temp_file.name
                    
                    # Générer le PDF
                    HTML(string=html_string).write_pdf(
                        temp_path,
                        stylesheets=[CSS(string=css_string)],
                        font_config=font_config
                    )
                    
                    self.temp_files.append(temp_path)
                    
                    # Nom du fichier
                    filename = f"bulletin_{eleve.prenom}_{eleve.nom}_{periode}.pdf"
                    filename = filename.replace(' ', '_').replace('/', '_')
                    
                    return temp_path, filename
                    
            except ImportError:
                logger.error("WeasyPrint non disponible pour la génération PDF")
                return None, None
                
        except Exception as e:
            logger.error(f"Erreur lors de la génération du bulletin PDF: {e}")
            return None, None
    
    def _get_titre_periode(self, periode, system_type):
        """Retourne le titre formaté de la période"""
        periodes_map = {
            'mensuel': {
                'OCTOBRE': 'Octobre', 'NOVEMBRE': 'Novembre', 'DECEMBRE': 'Décembre',
                'JANVIER': 'Janvier', 'FEVRIER': 'Février', 'MARS': 'Mars',
                'AVRIL': 'Avril', 'MAI': 'Mai'
            },
            'trimestre': {
                'TRIMESTRE_1': '1er Trimestre', 'TRIMESTRE_2': '2ème Trimestre', 'TRIMESTRE_3': '3ème Trimestre'
            },
            'semestre': {
                'SEMESTRE_1': '1er Semestre', 'SEMESTRE_2': '2ème Semestre'
            },
            'annuel': {
                'ANNUEL': 'Année Complète'
            }
        }
        
        return periodes_map.get(system_type, {}).get(periode, periode)
    
    def envoyer_whatsapp_bulletin(self, eleve_id, classe_id, periode, system_type, utilisateur=None):
        """
        Envoie le bulletin par WhatsApp au parent
        
        Returns:
            dict: Résultat de l'envoi avec succès/erreur
        """
        try:
            # Récupérer l'élève
            eleve = get_object_or_404(Eleve, id=eleve_id)
            
            # Vérifier si l'élève a un numéro WhatsApp
            telephone_parent = self._get_telephone_parent(eleve)
            if not telephone_parent:
                return {
                    'success': False,
                    'error': 'Aucun numéro de téléphone trouvé pour les parents'
                }
            
            # Générer le PDF du bulletin
            pdf_path, filename = self.generer_bulletin_pdf(eleve_id, classe_id, periode, system_type)
            
            if not pdf_path:
                return {
                    'success': False,
                    'error': 'Impossible de générer le bulletin PDF'
                }
            
            # Préparer le message WhatsApp
            message = self._generer_message_whatsapp(eleve, periode, system_type)
            
            # Simuler l'envoi WhatsApp (à remplacer par l'API réelle)
            envoi_reussi = self._simuler_envoi_whatsapp(telephone_parent, message, pdf_path)
            
            if envoi_reussi:
                # Enregistrer dans l'historique des relances
                self._enregistrer_relance(eleve, message, utilisateur)
                
                return {
                    'success': True,
                    'message': f'Bulletin envoyé avec succès au {telephone_parent}',
                    'telephone': telephone_parent
                }
            else:
                return {
                    'success': False,
                    'error': 'Échec de l\'envoi WhatsApp'
                }
                
        except Exception as e:
            logger.error(f"Erreur lors de l'envoi WhatsApp: {e}")
            return {
                'success': False,
                'error': f'Erreur technique: {str(e)}'
            }
        finally:
            # Nettoyer les fichiers temporaires
            self._cleanup_temp_files()
    
    def _get_telephone_parent(self, eleve):
        """Récupère le numéro de téléphone du parent"""
        # Priorité : Responsable principal > Responsable secondaire
        if eleve.responsable_principal and eleve.responsable_principal.telephone:
            return eleve.responsable_principal.telephone
        elif hasattr(eleve, 'responsable_secondaire') and eleve.responsable_secondaire and eleve.responsable_secondaire.telephone:
            return eleve.responsable_secondaire.telephone
        else:
            return None
    
    def _generer_message_whatsapp(self, eleve, periode, system_type):
        """Génère le message WhatsApp personnalisé"""
        titre_periode = self._get_titre_periode(periode, system_type)
        
        message = f"""🏫 *École Moderne - Bulletin de Notes*

Bonjour,

Nous avons le plaisir de vous transmettre le bulletin de notes de votre enfant *{eleve.prenom} {eleve.nom}* pour la période *{titre_periode}*.

📋 Le bulletin est joint à ce message en format PDF.

📞 Pour toute question, n'hésitez pas à nous contacter.

🏫 Direction de l'École
📧 Contact: direction@ecole.com
📱 Tél: +224 XXX XX XX XX

_Message automatique - Ne pas répondre_"""

        return message
    
    def _simuler_envoi_whatsapp(self, telephone, message, pdf_path):
        """
        Simule l'envoi WhatsApp (à remplacer par l'API réelle)
        
        Pour l'implémentation réelle, utiliser:
        - WhatsApp Business API
        - Twilio WhatsApp API
        - Ou autre service
        """
        try:
            # Simulation : toujours réussi pour les tests
            logger.info(f"Simulation envoi WhatsApp vers {telephone}")
            logger.info(f"Message: {message[:100]}...")
            logger.info(f"Fichier PDF: {pdf_path}")
            
            # TODO: Remplacer par l'API réelle
            # Exemple avec Twilio:
            # from twilio.rest import Client
            # client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
            # 
            # # Uploader le fichier
            # with open(pdf_path, 'rb') as f:
            #     media = client.media.create(content_type='application/pdf', body=f.read())
            # 
            # # Envoyer le message avec le fichier
            # message = client.messages.create(
            #     body=message,
            #     from_='whatsapp:+14155238886',  # Numéro Twilio WhatsApp
            #     to=f'whatsapp:{telephone}',
            #     media_url=[media.uri]
            # )
            
            return True  # Simulation réussie
            
        except Exception as e:
            logger.error(f"Erreur simulation WhatsApp: {e}")
            return False
    
    def _enregistrer_relance(self, eleve, message, utilisateur):
        """Enregistre l'envoi dans l'historique des relances"""
        try:
            Relance.objects.create(
                eleve=eleve,
                canal='WHATSAPP',
                message=message,
                statut='ENVOYEE',
                solde_estime=Decimal('0'),  # Bulletin, pas de paiement
                cree_par=utilisateur,
                date_envoi=timezone.now()
            )
        except Exception as e:
            logger.error(f"Erreur enregistrement relance: {e}")
    
    def _cleanup_temp_files(self):
        """Nettoie les fichiers temporaires"""
        for temp_file in self.temp_files:
            try:
                if os.path.exists(temp_file):
                    os.unlink(temp_file)
            except Exception as e:
                logger.error(f"Erreur suppression fichier temporaire {temp_file}: {e}")
        self.temp_files.clear()

# Instance globale
whatsapp_sender = WhatsAppBulletinSender()

@login_required
@require_POST
def envoyer_bulletin_whatsapp(request):
    """Vue pour envoyer le bulletin par WhatsApp"""
    try:
        eleve_id = request.POST.get('eleve_id')
        classe_id = request.POST.get('classe_id')
        periode = request.POST.get('periode')
        system_type = request.POST.get('system_type', 'trimestre')
        
        if not all([eleve_id, classe_id, periode]):
            return JsonResponse({
                'success': False,
                'error': 'Paramètres manquants'
            })
        
        # Envoyer le bulletin
        result = whatsapp_sender.envoyer_whatsapp_bulletin(
            eleve_id, classe_id, periode, system_type, request.user
        )
        
        return JsonResponse(result)
        
    except Exception as e:
        logger.error(f"Erreur vue envoyer_bulletin_whatsapp: {e}")
        return JsonResponse({
            'success': False,
            'error': 'Erreur technique lors de l\'envoi'
        })

@login_required
def apercu_message_whatsapp(request):
    """Aperçu du message WhatsApp avant envoi"""
    try:
        eleve_id = request.GET.get('eleve_id')
        periode = request.GET.get('periode')
        system_type = request.GET.get('system_type', 'trimestre')
        
        if not eleve_id:
            return JsonResponse({
                'success': False,
                'error': 'ID élève manquant'
            })
        
        eleve = get_object_or_404(Eleve, id=eleve_id)
        telephone = whatsapp_sender._get_telephone_parent(eleve)
        message = whatsapp_sender._generer_message_whatsapp(eleve, periode, system_type)
        
        return JsonResponse({
            'success': True,
            'message': message,
            'telephone': telephone,
            'eleve_nom': f"{eleve.prenom} {eleve.nom}"
        })
        
    except Exception as e:
        logger.error(f"Erreur aperçu message WhatsApp: {e}")
        return JsonResponse({
            'success': False,
            'error': 'Erreur lors de la génération de l\'aperçu'
        })
