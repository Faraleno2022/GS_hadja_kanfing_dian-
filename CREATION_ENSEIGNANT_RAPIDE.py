"""
Script à exécuter dans le shell Django pour créer rapidement un enseignant de test
Usage: python manage.py shell < CREATION_ENSEIGNANT_RAPIDE.py
"""

from salaires.models import Enseignant
from eleves.models import Ecole
from decimal import Decimal
from django.utils import timezone

print("🔧 CRÉATION RAPIDE D'ENSEIGNANT DE TEST")
print("=" * 50)

# Vérifier s'il y a une école
ecole = Ecole.objects.first()
if not ecole:
    print("❌ ERREUR: Aucune école trouvée dans la base de données!")
    print("   Créez d'abord une école avant de créer des enseignants.")
    exit()

print(f"✅ École trouvée: {ecole.nom}")

# Vérifier s'il y a déjà des enseignants
nb_enseignants = Enseignant.objects.count()
print(f"📊 Enseignants existants: {nb_enseignants}")

if nb_enseignants > 0:
    print("⚠️  Il y a déjà des enseignants. Voici les premiers:")
    for ens in Enseignant.objects.all()[:3]:
        print(f"   • ID {ens.id}: {ens.nom} {ens.prenoms}")
    
    premier = Enseignant.objects.first()
    print(f"\n🔗 Testez avec: /salaires/enseignants/{premier.id}/")
else:
    print("➕ Création d'un enseignant de test...")
    
    try:
        # Créer un enseignant de test
        enseignant = Enseignant.objects.create(
            ecole=ecole,
            nom='DIALLO',
            prenoms='Mamadou',
            email='mamadou.diallo@ecole.gn',
            telephone='622123456',
            type_enseignant='PRIMAIRE',
            salaire_fixe=Decimal('800000'),
            statut='ACTIF',
            date_embauche=timezone.now().date()
        )
        
        print(f"✅ Enseignant créé avec succès!")
        print(f"   • ID: {enseignant.id}")
        print(f"   • Nom: {enseignant.nom} {enseignant.prenoms}")
        print(f"   • Type: {enseignant.type_enseignant}")
        print(f"   • Salaire: {enseignant.salaire_fixe:,.0f} GNF")
        print(f"   • Statut: {enseignant.statut}")
        
        print(f"\n🔗 Testez maintenant: /salaires/enseignants/{enseignant.id}/")
        
    except Exception as e:
        print(f"❌ ERREUR lors de la création: {e}")
        print("\n🔍 Vérifiez les champs du modèle Enseignant:")
        print("   - Champs requis: nom, prenoms, ecole, type_enseignant, date_embauche")
        print("   - Champs optionnels: telephone, email, salaire_fixe, taux_horaire")

print("\n" + "=" * 50)
print("✅ Script terminé!")
