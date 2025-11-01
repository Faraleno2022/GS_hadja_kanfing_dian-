import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ecole_moderne.settings')
django.setup()

from notes.models import ClasseNote, MatiereNote, Evaluation, NoteEleve
from eleves.models import Eleve

print("=" * 60)
print("📊 RÉSUMÉ DES DONNÉES DE TEST GÉNÉRÉES")
print("=" * 60)

print(f"\n✅ Classes (Notes): {ClasseNote.objects.count()}")
for classe in ClasseNote.objects.all():
    print(f"   - {classe.nom}")

print(f"\n✅ Matières: {MatiereNote.objects.count()}")

print(f"\n✅ Évaluations: {Evaluation.objects.count()}")
print(f"   - Trimestre 1: {Evaluation.objects.filter(periode='TRIMESTRE_1').count()}")
print(f"   - Trimestre 2: {Evaluation.objects.filter(periode='TRIMESTRE_2').count()}")
print(f"   - Trimestre 3: {Evaluation.objects.filter(periode='TRIMESTRE_3').count()}")

print(f"\n✅ Notes d'élèves: {NoteEleve.objects.count()}")

eleves_avec_notes = Eleve.objects.filter(notes_evaluations__isnull=False).distinct()
print(f"\n✅ Élèves avec notes: {eleves_avec_notes.count()}")
for eleve in eleves_avec_notes:
    nb_notes = NoteEleve.objects.filter(eleve=eleve).count()
    print(f"   - {eleve.nom} {eleve.prenom}: {nb_notes} notes")

print("\n" + "=" * 60)
print("✅ Données de test prêtes!")
print("=" * 60)
