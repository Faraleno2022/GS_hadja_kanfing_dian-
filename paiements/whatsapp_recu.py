"""
Module d'envoi de reçus de paiement via WhatsApp
Génère un message avec les détails du paiement et un lien vers le PDF du reçu
"""

import logging
import urllib.parse
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.contrib.auth.decorators import login_required
from django.urls import reverse

from .models import Paiement

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
        
        # Générer l'URL du PDF du reçu
        pdf_url = None
        try:
            base_url = request.build_absolute_uri('/')[:-1]
            pdf_path = reverse('paiements:generer_recu_pdf', args=[paiement.id])
            pdf_url = f"{base_url}{pdf_path}"
        except Exception as e:
            logger.warning(f"Impossible de générer l'URL du PDF: {e}")
        
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
