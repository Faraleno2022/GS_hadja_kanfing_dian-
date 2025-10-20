#!/usr/bin/env python
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ecole_moderne.settings')
django.setup()

from notes.models import MatiereClasse, Evaluation, Note
from eleves.models import Classe, Eleve
from django.db.models import Avg

print("📊 VÉRIFICATION DES DONNÉES")
print("=" * 30)

# Classes
classes = Classe.objects.all()
print(f"📚 Classes: {classes.count()}")
for classe in classes[:3]:
    print(f"   • {classe.nom}")

# Matières
matieres = MatiereClasse.objects.all()
print(f"\n📖 Matières: {matieres.count()}")
for matiere in matieres[:5]:
    print(f"   • {matiere.nom} - {matiere.classe.nom} (coeff. {matiere.coefficient})")

# Évaluations
evaluations = Evaluation.objects.all()
print(f"\n📝 Évaluations: {evaluations.count()}")
for evaluation in evaluations[:5]:
    print(f"   • {evaluation.titre}")

# Notes
notes = Note.objects.all()
print(f"\n🎯 Notes: {notes.count()}")
if notes.count() > 0:
    moyenne = notes.aggregate(avg=Avg('note'))['avg']
    print(f"📊 Moyenne générale: {moyenne:.2f}/20")
    
    # Quelques exemples
    for note in notes[:5]:
        print(f"   • {note.eleve.nom} {note.eleve.prenom}: {note.note}/20 ({note.evaluation.titre})")

# Élèves
eleves = Eleve.objects.filter(statut='ACTIF')
print(f"\n👥 Élèves actifs: {eleves.count()}")

print(f"\n🎉 Données prêtes pour les tests!")
print("Accédez au dashboard: http://127.0.0.1:8001/notes/")
