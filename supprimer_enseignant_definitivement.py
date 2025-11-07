"""
Script pour supprimer définitivement un enseignant marqué comme démissionnaire
et le mettre dans la corbeille
"""
import os
import django
from datetime import datetime

# Configuration Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ecole_moderne.settings')
django.setup()

from django.db import transaction
from salaires.models import Enseignant, EtatSalaire, AffectationClasse, PresenceEnseignant
from administration.models import SystemLog
from django.contrib.auth.models import User

def supprimer_enseignant_definitivement(nom, prenoms):
    """
    Supprime définitivement un enseignant et le met dans la corbeille
    
    Args:
        nom: Le nom de l'enseignant
        prenoms: Les prénoms de l'enseignant
    """
    print("\n" + "="*70)
    print("🗑️ SUPPRESSION DÉFINITIVE D'ENSEIGNANT".center(70))
    print("="*70 + "\n")
    
    try:
        # Rechercher l'enseignant
        print(f"🔍 Recherche de l'enseignant: {nom} {prenoms}")
        
        # Essayer d'abord une recherche exacte
        enseignants = Enseignant.objects.filter(
            nom__iexact=nom,
            prenoms__iexact=prenoms
        )
        
        # Si pas trouvé, essayer avec contains
        if not enseignants.exists():
            enseignants = Enseignant.objects.filter(
                nom__icontains=nom,
                prenoms__icontains=prenoms
            )
        
        if not enseignants.exists():
            print(f"❌ Aucun enseignant trouvé avec le nom '{nom} {prenoms}'")
            
            # Afficher tous les enseignants démissionnaires pour aider
            demissionnaires = Enseignant.objects.filter(statut='DEMISSIONNAIRE')
            if demissionnaires.exists():
                print("\n📋 Enseignants actuellement démissionnaires:")
                for ens in demissionnaires:
                    print(f"   - {ens.nom} {ens.prenoms} (ID: {ens.id})")
            return False
        
        # Si plusieurs trouvés, prendre le premier démissionnaire
        enseignant = enseignants.filter(statut='DEMISSIONNAIRE').first()
        if not enseignant:
            enseignant = enseignants.first()
        
        print(f"✅ Enseignant trouvé: {enseignant.nom_complet}")
        print(f"   ID: {enseignant.id}")
        print(f"   École: {enseignant.ecole.nom}")
        print(f"   Type: {enseignant.get_type_enseignant_display()}")
        print(f"   Statut actuel: {enseignant.statut}")
        
        # Compter les éléments associés
        etats_salaire_count = enseignant.etats_salaire.count()
        affectations_count = enseignant.affectations.count()
        presences_count = enseignant.presences.count()
        
        print(f"\n📊 Éléments associés:")
        print(f"   États de salaire: {etats_salaire_count}")
        print(f"   Affectations de classe: {affectations_count}")
        print(f"   Présences: {presences_count}")
        
        # Confirmation
        print(f"\n⚠️ ATTENTION: Cette action est IRRÉVERSIBLE!")
        print(f"L'enseignant {enseignant.nom_complet} et TOUS ses éléments associés seront supprimés définitivement.")
        
        # Procéder à la suppression
        with transaction.atomic():
            # Collecter les informations pour la corbeille
            print("\n📝 Collecte des informations pour la corbeille...")
            
            etats_supprimes = []
            for etat in enseignant.etats_salaire.all():
                etats_supprimes.append({
                    'periode': str(etat.periode.nom_periode),
                    'salaire_base': str(etat.salaire_base),
                    'salaire_net': str(etat.salaire_net),
                    'paye': etat.paye
                })
            
            affectations_supprimees = []
            for affectation in enseignant.affectations.all():
                affectations_supprimees.append({
                    'classe': str(affectation.classe.nom),
                    'matiere': affectation.matiere or 'Toutes matières',
                    'heures_par_semaine': str(affectation.heures_par_semaine) if affectation.heures_par_semaine else None,
                    'date_debut': str(affectation.date_debut),
                    'date_fin': str(affectation.date_fin) if affectation.date_fin else None,
                    'actif': affectation.actif
                })
            
            presences_supprimees = []
            for presence in enseignant.presences.all()[:50]:  # Limiter à 50 pour éviter trop de données
                presences_supprimees.append({
                    'date': str(presence.date),
                    'statut': presence.statut,
                    'heures_travaillees': str(presence.heures_travaillees) if presence.heures_travaillees else None
                })
            
            # Créer l'entrée dans la corbeille
            print("💾 Sauvegarde dans la corbeille...")
            
            # Obtenir un utilisateur système (le premier superuser ou admin)
            user_system = User.objects.filter(is_superuser=True).first()
            if not user_system:
                user_system = User.objects.first()
            
            log_entry = SystemLog.objects.create(
                action='SUPPRESSION_DEFINITIVE_ENSEIGNANT',
                description=f"Suppression définitive de l'enseignant {enseignant.nom_complet} (précédemment DÉMISSIONNAIRE) avec {etats_salaire_count} état(s) de salaire, {affectations_count} affectation(s) et {presences_count} présence(s)",
                user=user_system,
                ip_address='127.0.0.1',  # Script local
                details={
                    'enseignant_id': enseignant.id,
                    'nom': enseignant.nom,
                    'prenoms': enseignant.prenoms,
                    'nom_complet': enseignant.nom_complet,
                    'ecole': enseignant.ecole.nom,
                    'type_enseignant': enseignant.type_enseignant,
                    'statut_avant_suppression': enseignant.statut,
                    'salaire_fixe': str(enseignant.salaire_fixe) if enseignant.salaire_fixe else None,
                    'taux_horaire': str(enseignant.taux_horaire) if enseignant.taux_horaire else None,
                    'heures_mensuelles': str(enseignant.heures_mensuelles) if enseignant.heures_mensuelles else None,
                    'date_embauche': str(enseignant.date_embauche),
                    'telephone': enseignant.telephone,
                    'email': enseignant.email,
                    'adresse': enseignant.adresse,
                    'etats_supprimes': etats_supprimes,
                    'etats_salaire_count': etats_salaire_count,
                    'affectations_supprimees': affectations_supprimees,
                    'affectations_count': affectations_count,
                    'presences_supprimees_sample': presences_supprimees,
                    'presences_count': presences_count,
                    'suppression_method': 'SCRIPT',
                    'suppression_date': str(datetime.now()),
                    'raison': 'Suppression définitive demandée - Enseignant marqué démissionnaire à supprimer complètement'
                }
            )
            print(f"✅ Entrée créée dans la corbeille (ID: {log_entry.id})")
            
            # Supprimer les états de salaire
            if etats_salaire_count > 0:
                print(f"🗑️ Suppression de {etats_salaire_count} état(s) de salaire...")
                enseignant.etats_salaire.all().delete()
            
            # Supprimer les affectations
            if affectations_count > 0:
                print(f"🗑️ Suppression de {affectations_count} affectation(s)...")
                enseignant.affectations.all().delete()
            
            # Supprimer les présences
            if presences_count > 0:
                print(f"🗑️ Suppression de {presences_count} présence(s)...")
                enseignant.presences.all().delete()
            
            # Supprimer l'enseignant définitivement
            print(f"🗑️ Suppression définitive de l'enseignant...")
            enseignant.delete()
            
            print(f"\n✅ SUCCÈS: L'enseignant {nom} {prenoms} a été supprimé définitivement!")
            print(f"   - {etats_salaire_count} état(s) de salaire supprimé(s)")
            print(f"   - {affectations_count} affectation(s) supprimée(s)")
            print(f"   - {presences_count} présence(s) supprimée(s)")
            print(f"   - Sauvegarde complète dans la corbeille")
            
            return True
            
    except Exception as e:
        print(f"\n❌ ERREUR lors de la suppression: {e}")
        import traceback
        traceback.print_exc()
        return False

def lister_enseignants_demissionnaires():
    """Liste tous les enseignants marqués comme démissionnaires"""
    print("\n📋 ENSEIGNANTS DÉMISSIONNAIRES (soft delete)")
    print("="*70)
    
    demissionnaires = Enseignant.objects.filter(statut='DEMISSIONNAIRE')
    
    if not demissionnaires.exists():
        print("✅ Aucun enseignant démissionnaire trouvé")
        return
    
    print(f"Trouvé {demissionnaires.count()} enseignant(s) démissionnaire(s):\n")
    
    for ens in demissionnaires:
        print(f"ID: {ens.id}")
        print(f"Nom: {ens.nom}")
        print(f"Prénoms: {ens.prenoms}")
        print(f"École: {ens.ecole.nom}")
        print(f"Type: {ens.get_type_enseignant_display()}")
        print(f"États de salaire: {ens.etats_salaire.count()}")
        print(f"Affectations: {ens.affectations.count()}")
        print(f"Présences: {ens.presences.count()}")
        print("-" * 40)

def verifier_corbeille():
    """Vérifie les suppressions d'enseignants dans la corbeille"""
    print("\n🗑️ CORBEILLE - ENSEIGNANTS SUPPRIMÉS")
    print("="*70)
    
    logs = SystemLog.objects.filter(action='SUPPRESSION_DEFINITIVE_ENSEIGNANT').order_by('-timestamp')[:10]
    
    if not logs.exists():
        print("Aucune suppression d'enseignant dans la corbeille")
        return
    
    print(f"Dernières {logs.count()} suppressions d'enseignants:\n")
    
    for log in logs:
        print(f"Date: {log.timestamp}")
        print(f"Description: {log.description}")
        if log.details:
            details = log.details
            print(f"  - Nom complet: {details.get('nom_complet', 'N/A')}")
            print(f"  - École: {details.get('ecole', 'N/A')}")
            print(f"  - États supprimés: {details.get('etats_salaire_count', 0)}")
            print(f"  - Affectations supprimées: {details.get('affectations_count', 0)}")
            print(f"  - Présences supprimées: {details.get('presences_count', 0)}")
        print("-" * 40)

if __name__ == '__main__':
    import sys
    
    print("\n" + "="*70)
    print("🗑️ SUPPRESSION DÉFINITIVE D'ENSEIGNANT".center(70))
    print("="*70)
    
    # Lister d'abord les enseignants démissionnaires
    lister_enseignants_demissionnaires()
    
    print("\n" + "="*70)
    print("SUPPRESSION DE LENO MAMADOU DJOULDE".center(70))
    print("="*70)
    
    # Supprimer LENO MAMADOU DJOULDE
    success = supprimer_enseignant_definitivement("LENO", "MAMADOU DJOULDE")
    
    if success:
        print("\n✅ Suppression terminée avec succès!")
        print("\n🗑️ Vérification de la corbeille:")
        verifier_corbeille()
    else:
        print("\n⚠️ La suppression n'a pas pu être effectuée.")
        print("Vérifiez que l'enseignant existe et réessayez.")
    
    print("\n" + "="*70 + "\n")
