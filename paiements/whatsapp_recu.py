"""
Module d'envoi de reçus de paiement et notes de rappel via WhatsApp
Génère un message avec les détails et un lien vers le PDF
"""

import logging
import urllib.parse
from decimal import Decimal
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.contrib.auth.decorators import login_required
from django.urls import reverse
from django.db.models import Sum

from .models import Paiement
from eleves.models import Eleve

logger = logging.getLogger(__name__)


class WhatsAppRecuSender:
    """Classe pour gérer l'envoi de reçus via WhatsApp"""
    
    def _get_telephone_parent(self, eleve):
        """Récupère le numéro de téléphone du parent"""
        if eleve.responsable_principal and eleve.responsable_principal.telephone:
            return eleve.responsable_principal.telephone
        elif hasattr(eleve, 'responsable_secondaire') and eleve.responsable_secondaire and eleve.responsable_secondaire.telephone:
            return eleve.responsable_secondaire.telephone
        return None
    
    def _formater_numero_whatsapp(self, telephone):
        """Formate le numéro pour WhatsApp (format international)"""
        if not telephone:
            return None
        
        # Nettoyer le numéro
        clean_number = telephone.replace(' ', '').replace('-', '').replace('.', '')
        
        # Ajouter le code pays si nécessaire
        if not clean_number.startswith('+'):
            if clean_number.startswith('00'):
                clean_number = '+' + clean_number[2:]
            elif clean_number.startswith('224'):
                clean_number = '+' + clean_number
            else:
                clean_number = '+224' + clean_number
        
        return clean_number
    
    def _generer_message_recu(self, paiement, pdf_url=None):
        """Génère le message WhatsApp pour le reçu de paiement"""
        eleve = paiement.eleve
        ecole = eleve.classe.ecole if eleve.classe else None
        nom_ecole = ecole.nom if ecole else "École"
        tel_ecole = ecole.telephone if ecole else ""
        email_ecole = ecole.email if ecole else ""
        
        # Formater le montant avec séparateur de milliers
        montant_formate = f"{paiement.montant:,.0f}".replace(",", " ")
        
        message = f"""🏫 *{nom_ecole} - Reçu de Paiement*

Bonjour Cher Parent,

Nous accusons réception de votre paiement pour *{eleve.prenom} {eleve.nom}*.

💰 *Détails du paiement:*
• Numéro de reçu: *{paiement.numero_recu}*
• Montant: *{montant_formate} GNF*
• Type: {paiement.type_paiement.nom}
• Mode: {paiement.mode_paiement.nom}
• Date: {paiement.date_paiement.strftime('%d/%m/%Y')}
• Statut: *{paiement.get_statut_display()}*"""

        # Ajouter le lien vers le PDF si disponible
        if pdf_url:
            message += f"""

📄 *Télécharger le reçu PDF:*
{pdf_url}"""

        message += """

Merci pour votre confiance.

📞 Pour toute question, n'hésitez pas à nous contacter."""

        if tel_ecole:
            message += f"""
📱 Tél: {tel_ecole}"""
        if email_ecole:
            message += f"""
📧 Email: {email_ecole}"""

        message += """

Cordialement,
🏫 La Direction"""

        return message


# Instance globale
whatsapp_recu_sender = WhatsAppRecuSender()


@login_required
def apercu_message_whatsapp_recu(request):
    """Aperçu du message WhatsApp pour un reçu de paiement"""
    try:
        paiement_id = request.GET.get('paiement_id')
        
        if not paiement_id:
            return JsonResponse({
                'success': False,
                'error': 'ID paiement manquant'
            })
        
        paiement = get_object_or_404(Paiement, id=paiement_id)
        eleve = paiement.eleve
        telephone = whatsapp_recu_sender._get_telephone_parent(eleve)
        
        # Générer l'URL PUBLIQUE du PDF du reçu (sans authentification requise)
        pdf_url = None
        try:
            from .recu_public import generer_url_recu_public
            pdf_url = generer_url_recu_public(request, paiement.id)
        except Exception as e:
            logger.warning(f"Impossible de générer l'URL publique du PDF: {e}")
        
        # Générer le message
        message = whatsapp_recu_sender._generer_message_recu(paiement, pdf_url)
        
        # Formater le numéro pour WhatsApp
        whatsapp_number = whatsapp_recu_sender._formater_numero_whatsapp(telephone)
        
        # Générer le lien WhatsApp
        whatsapp_link = None
        if whatsapp_number:
            encoded_message = urllib.parse.quote(message)
            whatsapp_link = f"https://wa.me/{whatsapp_number.replace('+', '')}?text={encoded_message}"
        
        # Formater le montant pour l'affichage
        montant_formate = f"{paiement.montant:,.0f}".replace(",", " ")
        
        return JsonResponse({
            'success': True,
            'message': message,
            'telephone': telephone,
            'whatsapp_number': whatsapp_number,
            'whatsapp_link': whatsapp_link,
            'pdf_url': pdf_url,
            'eleve_nom': f"{eleve.prenom} {eleve.nom}",
            'numero_recu': paiement.numero_recu,
            'montant': montant_formate,
            'type_paiement': paiement.type_paiement.nom,
            'date_paiement': paiement.date_paiement.strftime('%d/%m/%Y'),
            'statut': paiement.get_statut_display()
        })
        
    except Exception as e:
        logger.error(f"Erreur aperçu message WhatsApp reçu: {e}")
        return JsonResponse({
            'success': False,
            'error': 'Erreur lors de la génération de l\'aperçu'
        })


class WhatsAppNoteRappelSender:
    """Classe pour gérer l'envoi de notes de rappel via WhatsApp"""
    
    def _get_telephone_parent(self, eleve):
        """Récupère le numéro de téléphone du parent"""
        if eleve.responsable_principal and eleve.responsable_principal.telephone:
            return eleve.responsable_principal.telephone
        elif hasattr(eleve, 'responsable_secondaire') and eleve.responsable_secondaire and eleve.responsable_secondaire.telephone:
            return eleve.responsable_secondaire.telephone
        return None
    
    def _formater_numero_whatsapp(self, telephone):
        """Formate le numéro pour WhatsApp (format international)"""
        if not telephone:
            return None
        
        clean_number = telephone.replace(' ', '').replace('-', '').replace('.', '')
        
        if not clean_number.startswith('+'):
            if clean_number.startswith('00'):
                clean_number = '+' + clean_number[2:]
            elif clean_number.startswith('224'):
                clean_number = '+' + clean_number
            else:
                clean_number = '+224' + clean_number
        
        return clean_number
    
    def _calculer_solde_eleve(self, eleve):
        """Calcule le solde de l'élève (montant dû - montant payé)"""
        from .models import Paiement
        
        # Récupérer les frais de scolarité de la classe
        montant_total = Decimal('0')
        if eleve.classe and hasattr(eleve.classe, 'frais_scolarite'):
            montant_total = eleve.classe.frais_scolarite or Decimal('0')
        
        # Calculer le total payé (paiements validés)
        montant_paye = Paiement.objects.filter(
            eleve=eleve,
            statut='VALIDE'
        ).aggregate(total=Sum('montant'))['total'] or Decimal('0')
        
        reste_a_payer = montant_total - montant_paye
        
        return {
            'montant_total': montant_total,
            'montant_paye': montant_paye,
            'reste_a_payer': max(reste_a_payer, Decimal('0'))
        }
    
    def _generer_message_note_rappel(self, eleve, solde_info, pdf_url=None):
        """Génère le message WhatsApp pour la note de rappel"""
        ecole = eleve.classe.ecole if eleve.classe else None
        nom_ecole = ecole.nom if ecole else "École"
        tel_ecole = ecole.telephone if ecole else ""
        email_ecole = ecole.email if ecole else ""
        
        # Formater les montants
        montant_total = f"{solde_info['montant_total']:,.0f}".replace(",", " ")
        montant_paye = f"{solde_info['montant_paye']:,.0f}".replace(",", " ")
        reste_a_payer = f"{solde_info['reste_a_payer']:,.0f}".replace(",", " ")
        
        message = f"""🏫 *{nom_ecole} - Note de Rappel de Paiement*

Bonjour Cher Parent,

Nous vous rappelons que le règlement des frais de scolarité de votre enfant *{eleve.prenom} {eleve.nom}* n'est pas encore complet.

📋 *Situation financière:*
• Classe: {eleve.classe.nom if eleve.classe else 'N/A'}
• Frais de scolarité: *{montant_total} GNF*
• Montant payé: *{montant_paye} GNF*
• ⚠️ Reste à payer: *{reste_a_payer} GNF*"""

        if pdf_url:
            message += f"""

📄 *Télécharger la note de rappel:*
{pdf_url}"""

        message += """

Nous vous prions de bien vouloir régulariser cette situation dans les meilleurs délais.

📞 Pour toute question ou arrangement de paiement, contactez-nous."""

        if tel_ecole:
            message += f"""
📱 Tél: {tel_ecole}"""
        if email_ecole:
            message += f"""
📧 Email: {email_ecole}"""

        message += """

Cordialement,
🏫 La Direction"""

        return message


# Instance globale
whatsapp_note_rappel_sender = WhatsAppNoteRappelSender()


@login_required
def apercu_message_whatsapp_note_rappel(request):
    """Aperçu du message WhatsApp pour une note de rappel"""
    try:
        eleve_id = request.GET.get('eleve_id')
        
        if not eleve_id:
            return JsonResponse({
                'success': False,
                'error': 'ID élève manquant'
            })
        
        eleve = get_object_or_404(Eleve, id=eleve_id)
        telephone = whatsapp_note_rappel_sender._get_telephone_parent(eleve)
        
        # Calculer le solde
        solde_info = whatsapp_note_rappel_sender._calculer_solde_eleve(eleve)
        
        # Générer l'URL PUBLIQUE du PDF (sans authentification requise)
        pdf_url = None
        try:
            from .recu_public import generer_url_note_rappel_public
            pdf_url = generer_url_note_rappel_public(request, eleve.id)
        except Exception as e:
            logger.warning(f"Impossible de générer l'URL publique du PDF: {e}")
        
        # Générer le message
        message = whatsapp_note_rappel_sender._generer_message_note_rappel(eleve, solde_info, pdf_url)
        
        # Formater le numéro pour WhatsApp
        whatsapp_number = whatsapp_note_rappel_sender._formater_numero_whatsapp(telephone)
        
        # Générer le lien WhatsApp
        whatsapp_link = None
        if whatsapp_number:
            encoded_message = urllib.parse.quote(message)
            whatsapp_link = f"https://wa.me/{whatsapp_number.replace('+', '')}?text={encoded_message}"
        
        # Formater les montants pour l'affichage
        montant_total = f"{solde_info['montant_total']:,.0f}".replace(",", " ")
        montant_paye = f"{solde_info['montant_paye']:,.0f}".replace(",", " ")
        reste_a_payer = f"{solde_info['reste_a_payer']:,.0f}".replace(",", " ")
        
        return JsonResponse({
            'success': True,
            'message': message,
            'telephone': telephone,
            'whatsapp_number': whatsapp_number,
            'whatsapp_link': whatsapp_link,
            'pdf_url': pdf_url,
            'eleve_nom': f"{eleve.prenom} {eleve.nom}",
            'classe': eleve.classe.nom if eleve.classe else 'N/A',
            'montant_total': montant_total,
            'montant_paye': montant_paye,
            'reste_a_payer': reste_a_payer
        })
        
    except Exception as e:
        logger.error(f"Erreur aperçu message WhatsApp note de rappel: {e}")
        return JsonResponse({
            'success': False,
            'error': 'Erreur lors de la génération de l\'aperçu'
        })
