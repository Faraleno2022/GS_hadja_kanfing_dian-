import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ecole_moderne.settings')
django.setup()

from notes.models import MatiereClasse, Evaluation, Note
print(f"Matières: {MatiereClasse.objects.count()}")
print(f"Évaluations: {Evaluation.objects.count()}")
print(f"Notes: {Note.objects.count()}")
print("✅ Données prêtes pour tester les interfaces modernes!")
print("🌐 Accédez au dashboard: http://127.0.0.1:8001/notes/")
