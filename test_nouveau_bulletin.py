"""
Script de test rapide pour le nouveau bulletin
Usage: python manage.py shell < test_nouveau_bulletin.py
"""

import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'gestion_scolaire.settings')
django.setup()

from notes.models import ClasseNote, MatiereNote, NoteMensuelle, CompositionNote
from eleves.models import Eleve, Classe as ClasseEleve

print("=" * 80)
print("🧪 TEST DU NOUVEAU BULLETIN")
print("=" * 80)

# Vérifier les classes disponibles
print("\n📚 Classes disponibles:")
classes = ClasseNote.objects.filter(annee_scolaire="2024-2025")
for i, classe in enumerate(classes[:10], 1):
    print(f"   {i}. {classe.nom} (ID: {classe.id})")

# Vérifier une classe spécifique
if classes.exists():
    classe_test = classes.first()
    print(f"\n🎯 Test avec la classe: {classe_test.nom} (ID: {classe_test.id})")
    
    # Vérifier les élèves
    try:
        classe_eleve = ClasseEleve.objects.get(
            nom__icontains=classe_test.nom.split()[0],
            annee_scolaire="2024-2025"
        )
        eleves = Eleve.objects.filter(classe=classe_eleve, statut='ACTIF')
        print(f"   ✅ {eleves.count()} élève(s) trouvé(s)")
        
        if eleves.exists():
            eleve_test = eleves.first()
            print(f"   👤 Élève test: {eleve_test.nom} {eleve_test.prenom} (ID: {eleve_test.id})")
            
            # Vérifier les matières
            matieres = MatiereNote.objects.filter(classe=classe_test, actif=True)
            print(f"   📖 {matieres.count()} matière(s)")
            
            # Vérifier les notes
            notes_oct = NoteMensuelle.objects.filter(
                eleve=eleve_test,
                mois='OCTOBRE',
                annee_scolaire="2024-2025"
            ).count()
            
            notes_comp = CompositionNote.objects.filter(
                eleve=eleve_test,
                periode='TRIMESTRE_1',
                annee_scolaire="2024-2025"
            ).count()
            
            print(f"   📝 Notes Octobre: {notes_oct}")
            print(f"   📝 Compositions T1: {notes_comp}")
            
            # URL de test
            print("\n" + "=" * 80)
            print("🌐 URL DE TEST")
            print("=" * 80)
            print(f"\n✅ Accéder au bulletin:")
            print(f"   http://127.0.0.1:8000/notes/bulletins/")
            print(f"\n✅ Paramètres à sélectionner:")
            print(f"   - Classe: {classe_test.nom} (ID: {classe_test.id})")
            print(f"   - Système: Trimestre")
            print(f"   - Période: 1er Trimestre")
            print(f"   - Élève: {eleve_test.nom} {eleve_test.prenom} (ID: {eleve_test.id})")
            
            print(f"\n✅ URL directe:")
            print(f"   http://127.0.0.1:8000/notes/bulletins/?classe_id={classe_test.id}&system_type=trimestre&periode=TRIMESTRE_1&eleve_id={eleve_test.id}")
            
            if notes_oct > 0 and notes_comp > 0:
                print(f"\n✅ NOTES DISPONIBLES - Le bulletin devrait s'afficher correctement!")
            else:
                print(f"\n⚠️  PAS ASSEZ DE NOTES - Exécutez d'abord: python manage.py shell < test_bulletin_classe.py")
        else:
            print("   ❌ Aucun élève dans cette classe")
    except ClasseEleve.DoesNotExist:
        print("   ❌ Classe d'élèves non trouvée")
else:
    print("\n❌ Aucune classe trouvée pour 2024-2025")

print("\n" + "=" * 80)
print("✅ TEST TERMINÉ")
print("=" * 80)
