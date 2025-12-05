"""
Module pour le téléchargement public de bulletins PDF via un lien sécurisé.
Permet aux parents de télécharger le bulletin sans se connecter au site.
"""

import hashlib
import hmac
from datetime import datetime, timedelta
from django.conf import settings
from django.http import HttpResponse, Http404
from django.shortcuts import get_object_or_404
from django.utils import timezone
import logging

from eleves.models import Eleve
from .models import ClasseNote

logger = logging.getLogger(__name__)

# Clé secrète pour signer les tokens (utiliser SECRET_KEY de Django)
def get_secret_key():
    return getattr(settings, 'SECRET_KEY', 'default-secret-key')


def generer_token_bulletin(eleve_id, classe_note_id, periode, duree_validite_jours=30):
    """
    Génère un token sécurisé pour accéder au bulletin sans authentification.
    
    Le token est valide pendant `duree_validite_jours` jours.
    Format: {timestamp}_{signature}
    """
    # Timestamp d'expiration
    expiration = datetime.now() + timedelta(days=duree_validite_jours)
    timestamp = int(expiration.timestamp())
    
    # Données à signer
    data = f"{eleve_id}:{classe_note_id}:{periode}:{timestamp}"
    
    # Signature HMAC
    signature = hmac.new(
        get_secret_key().encode(),
        data.encode(),
        hashlib.sha256
    ).hexdigest()[:32]  # Prendre les 32 premiers caractères
    
    return f"{timestamp}_{signature}"


def verifier_token_bulletin(eleve_id, classe_note_id, periode, token):
    """
    Vérifie si le token est valide pour accéder au bulletin.
    
    Returns:
        bool: True si le token est valide, False sinon
    """
    try:
        parts = token.split('_')
        if len(parts) != 2:
            return False
        
        timestamp_str, signature_fournie = parts
        timestamp = int(timestamp_str)
        
        # Vérifier si le token n'a pas expiré
        if datetime.now().timestamp() > timestamp:
            logger.warning(f"Token expiré pour bulletin eleve={eleve_id}")
            return False
        
        # Recalculer la signature
        data = f"{eleve_id}:{classe_note_id}:{periode}:{timestamp}"
        signature_attendue = hmac.new(
            get_secret_key().encode(),
            data.encode(),
            hashlib.sha256
        ).hexdigest()[:32]
        
        # Comparer les signatures de manière sécurisée
        return hmac.compare_digest(signature_fournie, signature_attendue)
        
    except Exception as e:
        logger.error(f"Erreur vérification token: {e}")
        return False


def generer_url_bulletin_public(request, eleve_id, classe_note_id, periode):
    """
    Génère l'URL publique complète pour télécharger le bulletin.
    """
    token = generer_token_bulletin(eleve_id, classe_note_id, periode)
    
    # Construire l'URL absolue
    base_url = request.build_absolute_uri('/')[:-1]  # Enlever le / final
    url = f"{base_url}/notes/bulletin-public/{eleve_id}/{classe_note_id}/{periode}/?token={token}"
    
    return url


def bulletin_public_pdf(request, eleve_id, classe_note_id, periode):
    """
    Vue publique pour télécharger le bulletin PDF sans authentification.
    Nécessite un token valide dans les paramètres GET.
    """
    # Récupérer le token
    token = request.GET.get('token', '')
    
    if not token:
        logger.warning(f"Tentative d'accès bulletin public sans token: eleve={eleve_id}")
        raise Http404("Lien invalide ou expiré. Veuillez demander un nouveau lien.")
    
    # Vérifier le token
    if not verifier_token_bulletin(eleve_id, classe_note_id, periode, token):
        logger.warning(f"Token invalide pour bulletin: eleve={eleve_id}, token={token[:20]}...")
        raise Http404("Lien invalide ou expiré. Veuillez demander un nouveau lien à l'école.")
    
    # Token valide - générer le PDF
    try:
        from .bulletin_intelligent import (
            CalculateurBulletinIntelligent, 
            generer_pdf_avec_filigrane
        )
        
        eleve = get_object_or_404(Eleve, id=eleve_id)
        classe_note = get_object_or_404(ClasseNote, id=classe_note_id)
        
        # Déterminer le système et le type de système pour l'affichage
        systeme = 'SEMESTRE' if 'SEMESTRE' in periode else 'TRIMESTRE'
        system_type = 'mensuel'
        
        if 'ANNUEL_TRIM' in periode:
            system_type = 'annuel_trimestriel'
            systeme = 'TRIMESTRE'
        elif 'ANNUEL_SEM' in periode:
            system_type = 'annuel_semestriel'
            systeme = 'SEMESTRE'
        elif 'TRIMESTRE' in periode:
            system_type = 'trimestriel'
        elif 'SEMESTRE' in periode:
            system_type = 'semestriel'
        
        # Calculer le bulletin
        calculateur = CalculateurBulletinIntelligent(eleve, classe_note, periode, systeme)
        bulletin_data = calculateur.generer_bulletin()
        
        # Ajouter le system_type et la période
        bulletin_data['system_type'] = system_type
        bulletin_data['periode'] = periode
        
        # Enrichir avec les données détaillées selon le type de système
        from notes.calculs_moyennes import calculer_bulletin_intelligent
        
        matieres_enrichies = []
        for mat_data in bulletin_data.get('matieres', []):
            mat_obj = mat_data.get('matiere')
            if mat_obj:
                try:
                    # Utiliser la fonction centralisée intelligente
                    result = calculer_bulletin_intelligent(eleve, mat_obj, periode, system_type)
                    mat_data['moyennes_mensuelles'] = result.get('moyennes_mensuelles', [])
                    mat_data['note_composition'] = result.get('note_composition')
                    mat_data['moyenne_continue'] = result.get('moyenne_continue')
                    mat_data['moyenne'] = result.get('moyenne')
                    mat_data['points'] = result.get('points')
                except:
                    pass
            matieres_enrichies.append(mat_data)
        
        bulletin_data['matieres'] = matieres_enrichies
        
        # ===== RECALCULER LA MOYENNE GÉNÉRALE ET LE RANG POUR BULLETINS ANNUELS =====
        # IMPORTANT: Utiliser UNE SEULE SOURCE pour garantir la cohérence moyenne/rang
        if system_type in ['annuel_trimestriel', 'annuel_semestriel']:
            from notes.calculs_moyennes import (
                calculer_classement_classe, 
                detecter_niveau_scolaire,
                obtenir_mention_intelligente
            )
            from notes.models import MatiereNote
            from notes.bulletin_intelligent import formater_rang_intelligent
            from eleves.models import Classe as ClasseEleve
            
            # Récupérer les matières de la classe
            matieres = MatiereNote.objects.filter(classe=classe_note)
            
            # Récupérer tous les élèves de la classe
            classe_eleve = ClasseEleve.objects.filter(
                nom=classe_note.nom,
                annee_scolaire=classe_note.annee_scolaire,
                ecole=classe_note.ecole
            ).first()
            
            if classe_eleve:
                from eleves.models import Eleve as EleveModel
                eleves_classe = list(EleveModel.objects.filter(classe=classe_eleve, statut='ACTIF'))
                total_eleves = len(eleves_classe)
                bulletin_data['total_eleves'] = total_eleves
                
                # CALCUL UNIQUE: Le classement calcule les moyennes ET les rangs avec la même source
                classement_result = calculer_classement_classe(eleves_classe, matieres, periode, system_type)
                rang_map = classement_result.get('rang_map', {})
                details_map = classement_result.get('details_par_eleve', {})
                
                # Récupérer les données de l'élève depuis le classement (MÊME SOURCE)
                if eleve.id in details_map:
                    details_eleve = details_map[eleve.id]
                    bulletin_data['moyenne_generale'] = details_eleve.get('moyenne_generale')
                    bulletin_data['total_points'] = details_eleve.get('total_points', 0)
                    bulletin_data['total_coefficients'] = details_eleve.get('total_coefficients', 0)
                
                # Récupérer le rang de l'élève (MÊME SOURCE que la moyenne)
                rang_brut = rang_map.get(eleve.id, '-')
                if rang_brut and rang_brut != '-':
                    sexe = getattr(eleve, 'sexe', 'M')
                    bulletin_data['rang'] = formater_rang_intelligent(rang_brut, sexe, total_eleves)
                else:
                    bulletin_data['rang'] = '-'
            
            # Calculer la mention basée sur la moyenne (cohérente)
            niveau = detecter_niveau_scolaire(classe_note.nom)
            if bulletin_data.get('moyenne_generale'):
                bulletin_data['mention'] = obtenir_mention_intelligente(bulletin_data['moyenne_generale'], niveau)
        
        # Chemin du logo
        ecole = eleve.classe.ecole if eleve.classe else None
        logo_path = None
        if ecole and hasattr(ecole, 'logo') and ecole.logo:
            logo_path = ecole.logo.path
        
        # Ajouter le matricule aux données du bulletin
        bulletin_data['matricule'] = eleve.matricule
        
        # Générer le PDF avec l'école
        pdf_buffer = generer_pdf_avec_filigrane(bulletin_data, logo_path, ecole)
        
        # Réponse HTTP
        response = HttpResponse(pdf_buffer, content_type='application/pdf')
        filename = f"bulletin_{eleve.nom}_{eleve.prenom}_{periode}.pdf"
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        
        logger.info(f"Bulletin téléchargé via lien public: eleve={eleve_id}, periode={periode}")
        
        return response
        
    except Exception as e:
        logger.error(f"Erreur génération bulletin public: {e}")
        raise Http404("Erreur lors de la génération du bulletin. Veuillez réessayer.")
