"""
Guide pour saisir les notes de la classe 1ère année
"""

import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ecole_moderne.settings')
django.setup()

from notes.models import ClasseNote, MatiereNote
from eleves.models import Eleve

print("\n" + "=" * 70)
print("GUIDE DE SAISIE DES NOTES - 1ÈRE ANNÉE")
print("=" * 70)

# Trouver la classe
classes = ClasseNote.objects.filter(nom__icontains='1ère')
print(f"\n📚 Classes trouvées contenant '1ère année':")
for c in classes:
    print(f"   ID: {c.id} - {c.nom} - {c.niveau_enseignement} ({c.annee_scolaire})")

if classes.exists():
    classe = classes.first()
    print(f"\n✅ Classe sélectionnée: {classe.nom} (ID: {classe.id})")
    
    # Vérifier les matières
    matieres = MatiereNote.objects.filter(classe=classe)
    print(f"\n📖 Matières configurées: {matieres.count()}")
    for m in matieres:
        print(f"   - {m.nom} (Coef: {m.coefficient})")
    
    if matieres.count() == 0:
        print("\n⚠️  AUCUNE MATIÈRE CONFIGURÉE!")
        print("\n📝 Pour configurer les matières:")
        print(f"   1. Aller sur: http://127.0.0.1:8000/notes/matieres/?classe_id={classe.id}")
        print("   2. Cliquer sur 'Charger matières par défaut'")
        print("   3. Ou ajouter manuellement les matières")
    
    # Vérifier les élèves
    from eleves.models import Classe as ClasseEleve
    try:
        classe_eleve = ClasseEleve.objects.get(nom=classe.nom, annee_scolaire=classe.annee_scolaire)
        eleves = Eleve.objects.filter(classe=classe_eleve, statut='ACTIF')
        print(f"\n👥 Élèves dans la classe: {eleves.count()}")
        for e in eleves[:5]:
            print(f"   - {e.matricule} - {e.nom_complet}")
        if eleves.count() > 5:
            print(f"   ... et {eleves.count() - 5} autres")
    except:
        print("\n⚠️  Classe élève non trouvée")
    
    print("\n" + "=" * 70)
    print("ÉTAPES POUR SAISIR LES NOTES")
    print("=" * 70)
    
    print("\n1️⃣  CONFIGURER LES MATIÈRES (si pas encore fait)")
    print(f"   URL: http://127.0.0.1:8000/notes/matieres/?classe_id={classe.id}")
    print("   → Cliquer sur 'Charger matières par défaut'")
    
    print("\n2️⃣  SAISIR LES NOTES")
    print(f"   URL: http://127.0.0.1:8000/notes/saisir/?classe_id={classe.id}")
    print("   → Choisir la période (Trimestre 1)")
    print("   → Saisir les notes pour chaque élève")
    
    print("\n3️⃣  GÉNÉRER LES BULLETINS")
    print(f"   URL: http://127.0.0.1:8000/notes/bulletins/?classe_id={classe.id}")
    print("   → Choisir la période")
    print("   → Télécharger les bulletins")
    
    print("\n" + "=" * 70)
    print("EXEMPLE DE NOTES À SAISIR")
    print("=" * 70)
    
    if matieres.exists():
        print("\nPour chaque élève, saisir:")
        for m in matieres:
            print(f"   {m.nom}:")
            print(f"      - Note mensuelle: /20")
            print(f"      - Composition: /20")
    else:
        print("\n⚠️  Configurez d'abord les matières!")
    
else:
    print("\n❌ Aucune classe trouvée!")
    print("\n📝 Classes disponibles:")
    for c in ClasseNote.objects.all()[:10]:
        print(f"   ID: {c.id} - {c.nom}")

print("\n" + "=" * 70)
