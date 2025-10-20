"""
Script ultra-simple pour créer un enseignant de test
À exécuter dans le shell Django: python manage.py shell < CREATION_ENSEIGNANT_SIMPLE.py
"""

print("🚀 CRÉATION SIMPLE D'ENSEIGNANT DE TEST")
print("=" * 40)

try:
    from salaires.models import Enseignant
    from eleves.models import Ecole
    from decimal import Decimal
    from django.utils import timezone
    
    # Vérifier l'école
    ecole = Ecole.objects.first()
    if not ecole:
        print("❌ Aucune école trouvée!")
        exit()
    
    print(f"✅ École: {ecole.nom}")
    
    # Vérifier si des enseignants existent déjà
    if Enseignant.objects.exists():
        count = Enseignant.objects.count()
        print(f"⚠️  {count} enseignant(s) déjà présent(s)")
        premier = Enseignant.objects.first()
        print(f"🔗 Testez: /salaires/enseignants/{premier.id}/")
    else:
        # Créer un enseignant simple
        enseignant = Enseignant.objects.create(
            ecole=ecole,
            nom='DIALLO',
            prenoms='Mamadou',
            email='mamadou.diallo@test.gn',
            telephone='622123456',
            type_enseignant='PRIMAIRE',
            salaire_fixe=Decimal('800000'),
            statut='ACTIF',
            date_embauche=timezone.now().date()
        )
        
        print(f"✅ Enseignant créé: {enseignant.nom} {enseignant.prenoms}")
        print(f"   • ID: {enseignant.id}")
        print(f"   • Type: {enseignant.type_enseignant}")
        print(f"   • Salaire: {enseignant.salaire_fixe:,.0f} GNF")
        print(f"🔗 Testez: /salaires/enseignants/{enseignant.id}/")

except Exception as e:
    print(f"❌ Erreur: {e}")
    print("💡 Vérifiez que les modèles sont bien migrés")

print("=" * 40)
print("✅ Script terminé!")
