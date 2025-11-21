"""
Test simple pour vérifier le rang affiché sur le bulletin PDF
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ecole_moderne.settings')
django.setup()

from eleves.models import Eleve, Classe

print("=" * 80)
print("VÉRIFICATION DU RANG SUR LE BULLETIN PDF")
print("=" * 80)

# Trouver la classe 12ème Sciences
try:
    classe = Classe.objects.get(nom__icontains="12ÈME SCIENCES")
    print(f"\n✅ Classe trouvée : {classe.nom}")
    print(f"   ID: {classe.id}")
except Classe.DoesNotExist:
    print("\n❌ Classe 12ème Sciences non trouvée")
    exit(1)
except Classe.MultipleObjectsReturned:
    classes = Classe.objects.filter(nom__icontains="12ÈME SCIENCES")
    print(f"\n⚠️  Plusieurs classes trouvées:")
    for c in classes:
        print(f"   - {c.nom} (ID: {c.id})")
    classe = classes.first()
    print(f"\n✅ Utilisation de : {classe.nom} (ID: {c.id})")

# Trouver l'élève DIALLO Alpha Ousmane
try:
    eleve = Eleve.objects.get(
        classe=classe,
        nom__icontains="DIALLO",
        prenom__icontains="ALPHA"
    )
    print(f"\n✅ Élève trouvé : {eleve.prenom} {eleve.nom}")
    print(f"   Matricule: {eleve.matricule}")
    print(f"   ID: {eleve.id}")
except Eleve.DoesNotExist:
    print("\n❌ Élève DIALLO Alpha Ousmane non trouvé dans cette classe")
    print("\nÉlèves de la classe:")
    for e in Eleve.objects.filter(classe=classe)[:10]:
        print(f"   - {e.prenom} {e.nom}")
    exit(1)

print("\n" + "=" * 80)
print("INSTRUCTIONS POUR TESTER")
print("=" * 80)
print(f"\n1. Accéder à l'URL du bulletin PDF:")
print(f"   http://127.0.0.1:8000/notes/bulletin-pdf/{classe.id}/{eleve.id}/T1/")
print(f"\n2. Vérifier que le rang affiché est: 9ème/18")
print(f"\n3. Si le rang est toujours 10ème, cela signifie que:")
print(f"   - Le serveur n'a pas été redémarré")
print(f"   - Le cache du navigateur n'a pas été vidé")
print(f"   - Les modifications n'ont pas été déployées")
print("\n" + "=" * 80)
