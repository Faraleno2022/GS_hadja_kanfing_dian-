import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ecole_moderne.settings')
django.setup()

from notes.models import MatiereClasse, Evaluation, Note
from django.db.models import Avg, Count

print("📊 STATISTIQUES FINALES DU MODULE NOTES")
print("=" * 45)

# Statistiques générales
total_matieres = MatiereClasse.objects.count()
total_evaluations = Evaluation.objects.count()
total_notes = Note.objects.count()

print(f"📖 Matières: {total_matieres}")
print(f"📝 Évaluations: {total_evaluations}")
print(f"🎯 Notes: {total_notes}")

if total_notes > 0:
    moyenne_generale = Note.objects.aggregate(avg=Avg('note'))['avg']
    print(f"📊 Moyenne générale: {moyenne_generale:.2f}/20")
    
    # Répartition par trimestre
    print(f"\n📅 RÉPARTITION PAR TRIMESTRE:")
    for trimestre in ['T1', 'T2', 'T3']:
        nb_eval = Evaluation.objects.filter(trimestre=trimestre).count()
        nb_notes = Note.objects.filter(evaluation__trimestre=trimestre).count()
        if nb_notes > 0:
            moy_trim = Note.objects.filter(evaluation__trimestre=trimestre).aggregate(avg=Avg('note'))['avg']
            print(f"   {trimestre}: {nb_eval} évaluations, {nb_notes} notes (moy: {moy_trim:.2f})")
    
    # Répartition par catégorie
    print(f"\n📋 RÉPARTITION PAR CATÉGORIE:")
    for categorie in ['COURS', 'COMPOSITION']:
        nb_eval = Evaluation.objects.filter(categorie=categorie).count()
        nb_notes = Note.objects.filter(evaluation__categorie=categorie).count()
        if nb_notes > 0:
            moy_cat = Note.objects.filter(evaluation__categorie=categorie).aggregate(avg=Avg('note'))['avg']
            print(f"   {categorie}: {nb_eval} évaluations, {nb_notes} notes (moy: {moy_cat:.2f})")

print(f"\n🎉 DONNÉES COMPLÈTES!")
print("🌐 Dashboard moderne: http://127.0.0.1:8001/notes/")
print("🔧 Interface de test disponible pour validation")
