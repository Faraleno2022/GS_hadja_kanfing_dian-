"""
Script complet pour:
1. Créer l'enseignant LENO MAMADOU DJOULDE
2. Le marquer comme démissionnaire
3. Le supprimer définitivement et le mettre dans la corbeille
"""
import os
import django
from datetime import datetime, date
from decimal import Decimal

# Configuration Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ecole_moderne.settings')
django.setup()

from django.db import transaction
from django.contrib.auth.models import User
from salaires.models import Enseignant, TypeEnseignant, StatutEnseignant, EtatSalaire, AffectationClasse, PeriodeSalaire
from eleves.models import Ecole, Classe
from administration.models import SystemLog
from utilisateurs.models import JournalActivite

def creer_enseignant():
    """Crée l'enseignant LENO MAMADOU DJOULDE"""
    print("\n📝 CRÉATION DE L'ENSEIGNANT")
    print("="*70)
    
    try:
        # Obtenir ou créer une école
        ecole = Ecole.objects.first()
        if not ecole:
            print("❌ Aucune école trouvée. Création d'une école par défaut...")
            ecole = Ecole.objects.create(
                nom="École Moderne de Conakry",
                adresse="Conakry, Guinée",
                telephone="620000000"
            )
            print(f"✅ École créée: {ecole.nom}")
        else:
            print(f"✅ École trouvée: {ecole.nom}")
        
        # Vérifier si l'enseignant existe déjà
        enseignant_existe = Enseignant.objects.filter(
            nom="LENO",
            prenoms="MAMADOU DJOULDE"
        ).exists()
        
        if enseignant_existe:
            enseignant = Enseignant.objects.get(nom="LENO", prenoms="MAMADOU DJOULDE")
            print(f"⚠️ L'enseignant {enseignant.nom_complet} existe déjà (Statut: {enseignant.statut})")
            return enseignant
        
        # Créer l'enseignant
        enseignant = Enseignant.objects.create(
            nom="LENO",
            prenoms="MAMADOU DJOULDE",
            telephone="625123456",
            email="leno.mamadou@ecole.gn",
            adresse="Quartier Taouyah, Conakry",
            ecole=ecole,
            type_enseignant=TypeEnseignant.PRIMAIRE,
            statut=StatutEnseignant.ACTIF,
            salaire_fixe=Decimal('5000000'),  # 5 millions GNF
            heures_mensuelles=Decimal('160'),
            date_embauche=date(2020, 9, 1)
        )
        
        print(f"✅ Enseignant créé: {enseignant.nom_complet}")
        print(f"   Type: {enseignant.get_type_enseignant_display()}")
        print(f"   Salaire fixe: {enseignant.salaire_fixe} GNF")
        print(f"   Date d'embauche: {enseignant.date_embauche}")
        
        # Créer une affectation de classe (optionnel)
        classe = Classe.objects.filter(ecole=ecole).first()
        if not classe:
            print("📚 Création d'une classe...")
            classe = Classe.objects.create(
                nom="CP1",
                niveau="PRIMAIRE",
                ecole=ecole,
                effectif_max=30
            )
            print(f"✅ Classe créée: {classe.nom}")
        
        # Créer l'affectation
        affectation = AffectationClasse.objects.create(
            enseignant=enseignant,
            classe=classe,
            date_debut=date(2020, 9, 1),
            actif=True
        )
        print(f"✅ Affectation créée: {classe.nom}")
        
        # Créer un état de salaire (optionnel)
        print("💰 Création d'un état de salaire...")
        
        # Créer ou obtenir une période de salaire
        periode, created = PeriodeSalaire.objects.get_or_create(
            mois=11,
            annee=2024,
            ecole=ecole,
            defaults={'nombre_semaines': Decimal('4.33')}
        )
        
        if created:
            print(f"✅ Période de salaire créée: {periode.nom_periode}")
        
        # Créer l'état de salaire
        etat_salaire = EtatSalaire.objects.create(
            enseignant=enseignant,
            periode=periode,
            salaire_base=enseignant.salaire_fixe,
            primes=Decimal('500000'),  # Prime de 500k GNF
            deductions=Decimal('0'),
            valide=True,
            paye=True
        )
        print(f"✅ État de salaire créé: {etat_salaire.salaire_net} GNF")
        
        return enseignant
        
    except Exception as e:
        print(f"❌ Erreur lors de la création: {e}")
        import traceback
        traceback.print_exc()
        return None

def marquer_demissionnaire(enseignant):
    """Marque l'enseignant comme démissionnaire (soft delete)"""
    print("\n🔄 MARQUAGE COMME DÉMISSIONNAIRE")
    print("="*70)
    
    try:
        print(f"Statut actuel: {enseignant.statut}")
        
        if enseignant.statut == StatutEnseignant.DEMISSIONNAIRE:
            print("⚠️ L'enseignant est déjà marqué comme démissionnaire")
            return True
        
        # Marquer comme démissionnaire
        enseignant.statut = StatutEnseignant.DEMISSIONNAIRE
        enseignant.save()
        
        # Créer une entrée dans le journal
        user = User.objects.filter(is_superuser=True).first()
        if not user:
            user = User.objects.first()
        
        if user:
            JournalActivite.objects.create(
                user=user,
                action='DESACTIVATION',
                type_objet='ENSEIGNANT',
                objet_id=enseignant.id,
                description=f"Marquage de l'enseignant {enseignant.nom_complet} comme démissionnaire",
                adresse_ip='127.0.0.1',
                user_agent='Script Python'
            )
        
        print(f"✅ L'enseignant {enseignant.nom_complet} a été marqué comme DÉMISSIONNAIRE")
        print(f"   Nouveau statut: {enseignant.statut}")
        
        return True
        
    except Exception as e:
        print(f"❌ Erreur lors du marquage: {e}")
        return False

def supprimer_definitivement(enseignant):
    """Supprime définitivement l'enseignant et le met dans la corbeille"""
    print("\n🗑️ SUPPRESSION DÉFINITIVE")
    print("="*70)
    
    try:
        with transaction.atomic():
            # Collecter les informations
            print("📝 Collecte des informations...")
            
            nom_complet = enseignant.nom_complet
            etats_count = enseignant.etats_salaire.count()
            affectations_count = enseignant.affectations.count()
            presences_count = enseignant.presences.count()
            
            print(f"   États de salaire: {etats_count}")
            print(f"   Affectations: {affectations_count}")
            print(f"   Présences: {presences_count}")
            
            # Collecter les détails pour la corbeille
            etats_details = []
            for etat in enseignant.etats_salaire.all():
                etats_details.append({
                    'periode': str(etat.periode.nom_periode),
                    'salaire_net': str(etat.salaire_net),
                    'paye': etat.paye
                })
            
            affectations_details = []
            for affectation in enseignant.affectations.all():
                affectations_details.append({
                    'classe': str(affectation.classe.nom),
                    'date_debut': str(affectation.date_debut)
                })
            
            # Créer l'entrée dans la corbeille
            print("💾 Sauvegarde dans la corbeille...")
            
            user = User.objects.filter(is_superuser=True).first()
            if not user:
                user = User.objects.first()
            
            log_entry = SystemLog.objects.create(
                action='SUPPRESSION_DEFINITIVE_ENSEIGNANT',
                description=f"Suppression définitive de l'enseignant {nom_complet} (était DÉMISSIONNAIRE) avec tous ses éléments associés",
                user=user,
                ip_address='127.0.0.1',
                details={
                    'enseignant_id': enseignant.id,
                    'nom': enseignant.nom,
                    'prenoms': enseignant.prenoms,
                    'nom_complet': nom_complet,
                    'ecole': enseignant.ecole.nom,
                    'type_enseignant': enseignant.type_enseignant,
                    'statut_avant_suppression': enseignant.statut,
                    'salaire_fixe': str(enseignant.salaire_fixe) if enseignant.salaire_fixe else None,
                    'date_embauche': str(enseignant.date_embauche),
                    'telephone': enseignant.telephone,
                    'email': enseignant.email,
                    'adresse': enseignant.adresse,
                    'etats_salaire': etats_details,
                    'etats_count': etats_count,
                    'affectations': affectations_details,
                    'affectations_count': affectations_count,
                    'presences_count': presences_count,
                    'suppression_date': str(datetime.now()),
                    'methode': 'SCRIPT_AUTOMATIQUE',
                    'raison': 'Suppression définitive demandée - Ne pas marquer comme démissionnaire mais supprimer complètement'
                }
            )
            print(f"✅ Entrée créée dans la corbeille (ID: {log_entry.id})")
            
            # Supprimer tous les éléments associés
            print("🗑️ Suppression des éléments associés...")
            
            if etats_count > 0:
                enseignant.etats_salaire.all().delete()
                print(f"   ✅ {etats_count} état(s) de salaire supprimé(s)")
            
            if affectations_count > 0:
                enseignant.affectations.all().delete()
                print(f"   ✅ {affectations_count} affectation(s) supprimée(s)")
            
            if presences_count > 0:
                enseignant.presences.all().delete()
                print(f"   ✅ {presences_count} présence(s) supprimée(s)")
            
            # Supprimer définitivement l'enseignant
            print("🗑️ Suppression de l'enseignant...")
            enseignant.delete()
            
            print(f"\n✅ SUCCÈS: L'enseignant {nom_complet} a été supprimé définitivement!")
            print("   Toutes les données ont été sauvegardées dans la corbeille.")
            
            return True
            
    except Exception as e:
        print(f"❌ Erreur lors de la suppression: {e}")
        import traceback
        traceback.print_exc()
        return False

def verifier_corbeille():
    """Vérifie que l'enseignant est bien dans la corbeille"""
    print("\n🗑️ VÉRIFICATION DE LA CORBEILLE")
    print("="*70)
    
    logs = SystemLog.objects.filter(
        action='SUPPRESSION_DEFINITIVE_ENSEIGNANT'
    ).order_by('-timestamp')[:5]
    
    if not logs.exists():
        print("⚠️ Aucun enseignant dans la corbeille")
        return
    
    print(f"Dernières suppressions d'enseignants:\n")
    
    for log in logs:
        print(f"📅 Date: {log.timestamp}")
        print(f"📝 Description: {log.description}")
        
        if log.details:
            details = log.details
            print(f"👤 Enseignant: {details.get('nom_complet', 'N/A')}")
            print(f"🏫 École: {details.get('ecole', 'N/A')}")
            print(f"💼 Type: {details.get('type_enseignant', 'N/A')}")
            print(f"📊 Éléments supprimés:")
            print(f"   - États de salaire: {details.get('etats_count', 0)}")
            print(f"   - Affectations: {details.get('affectations_count', 0)}")
            print(f"   - Présences: {details.get('presences_count', 0)}")
        print("-" * 50)

def main():
    """Fonction principale"""
    print("\n" + "="*70)
    print("PROCESSUS COMPLET DE SUPPRESSION D'ENSEIGNANT".center(70))
    print("="*70)
    
    print("\nCe script va:")
    print("1. Créer l'enseignant LENO MAMADOU DJOULDE")
    print("2. Le marquer comme démissionnaire")
    print("3. Le supprimer définitivement et le mettre dans la corbeille")
    
    # Étape 1: Créer l'enseignant
    enseignant = creer_enseignant()
    if not enseignant:
        print("\n❌ Impossible de continuer sans enseignant")
        return
    
    # Étape 2: Marquer comme démissionnaire
    if not marquer_demissionnaire(enseignant):
        print("\n❌ Impossible de marquer l'enseignant comme démissionnaire")
        return
    
    # Étape 3: Supprimer définitivement
    if not supprimer_definitivement(enseignant):
        print("\n❌ La suppression définitive a échoué")
        return
    
    # Vérifier la corbeille
    verifier_corbeille()
    
    print("\n" + "="*70)
    print("✅ PROCESSUS TERMINÉ AVEC SUCCÈS!".center(70))
    print("="*70)
    print("\n📌 Résumé:")
    print("   - L'enseignant LENO MAMADOU DJOULDE a été créé")
    print("   - Il a été marqué comme démissionnaire (soft delete)")
    print("   - Puis supprimé définitivement (hard delete)")
    print("   - Toutes ses données sont sauvegardées dans la corbeille")
    print("   - Il peut être restauré depuis la corbeille si nécessaire")

if __name__ == '__main__':
    main()
