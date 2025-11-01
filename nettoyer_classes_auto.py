"""
Script automatique pour nettoyer les classes incohérentes et les doublons
Version sans confirmation
"""

import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ecole_moderne.settings')
django.setup()

from eleves.models import Classe, Eleve
from notes.models import ClasseNote
from collections import defaultdict

print("\n" + "=" * 70)
print("NETTOYAGE AUTOMATIQUE DES CLASSES")
print("=" * 70)

# 1. Supprimer les classes incohérentes (sans élèves)
print("\n1. Suppression des classes incohérentes...")
patterns_incoherents = [
    ('1ère année', 'COLLEGE'),
    ('2ème année', 'COLLEGE'),
    ('3ème année', 'COLLEGE'),
    ('7ème année', 'COLLEGE'),
    ('garderie', 'COLLEGE'),
    ('petite section', 'COLLEGE'),
]

supprimees_incoherentes = 0
for classe in Classe.objects.all():
    nom_lower = classe.nom.lower()
    niveau_upper = classe.niveau.upper() if classe.niveau else ''
    
    for pattern_nom, pattern_niveau in patterns_incoherents:
        if pattern_nom in nom_lower and pattern_niveau in niveau_upper:
            nb_eleves = Eleve.objects.filter(classe=classe).count()
            if nb_eleves == 0:
                print(f"   ✅ Supprimée: {classe.nom} - {classe.niveau}")
                classe.delete()
                supprimees_incoherentes += 1
            else:
                print(f"   ⚠️  Conservée (a {nb_eleves} élève(s)): {classe.nom}")
            break

print(f"✅ {supprimees_incoherentes} classe(s) incohérente(s) supprimée(s)")

# 2. Supprimer les doublons
print("\n2. Suppression des doublons...")
classes_par_cle = defaultdict(list)

for classe in Classe.objects.all():
    cle = (classe.nom, classe.annee_scolaire)
    classes_par_cle[cle].append(classe)

supprimees_doublons = 0
for (nom, annee), classes in classes_par_cle.items():
    if len(classes) > 1:
        # Trier par nombre d'élèves
        classes_avec_eleves = []
        for classe in classes:
            nb_eleves = Eleve.objects.filter(classe=classe).count()
            classes_avec_eleves.append((classe, nb_eleves))
        
        classes_avec_eleves.sort(key=lambda x: x[1], reverse=True)
        
        # Garder la première
        a_garder = classes_avec_eleves[0][0]
        
        print(f"\n   Doublon: {nom} ({annee})")
        print(f"      ✅ GARDÉE: ID={a_garder.id}, Élèves={classes_avec_eleves[0][1]}")
        
        for classe, nb_eleves in classes_avec_eleves[1:]:
            if nb_eleves > 0:
                # Déplacer les élèves
                print(f"      ⚠️  Déplacement de {nb_eleves} élève(s)")
                Eleve.objects.filter(classe=classe).update(classe=a_garder)
            
            print(f"      ✅ Supprimée: ID={classe.id}")
            classe.delete()
            supprimees_doublons += 1

print(f"\n✅ {supprimees_doublons} doublon(s) supprimé(s)")

# 3. Nettoyer ClasseNote
print("\n3. Nettoyage des ClasseNote...")
classes_note_par_cle = defaultdict(list)

for classe in ClasseNote.objects.all():
    cle = (classe.nom, classe.annee_scolaire)
    classes_note_par_cle[cle].append(classe)

supprimees_notes = 0
for (nom, annee), classes in classes_note_par_cle.items():
    if len(classes) > 1:
        # Garder le premier, supprimer les autres
        for classe in classes[1:]:
            print(f"   ✅ ClasseNote supprimée: {classe.nom} (ID={classe.id})")
            classe.delete()
            supprimees_notes += 1

print(f"✅ {supprimees_notes} doublon(s) ClasseNote supprimé(s)")

# Statistiques finales
print("\n" + "=" * 70)
print("STATISTIQUES FINALES")
print("=" * 70)
print(f"📊 Classes (Eleves): {Classe.objects.count()}")
print(f"📊 Classes (Notes): {ClasseNote.objects.count()}")
print(f"📊 Élèves: {Eleve.objects.count()}")

# Vérifier les doublons restants
classes_par_cle = defaultdict(list)
for classe in Classe.objects.all():
    cle = (classe.nom, classe.annee_scolaire)
    classes_par_cle[cle].append(classe)

doublons_restants = sum(1 for classes in classes_par_cle.values() if len(classes) > 1)

if doublons_restants > 0:
    print(f"\n⚠️  {doublons_restants} doublon(s) restant(s)")
else:
    print(f"\n✅ Aucun doublon restant")

print("\n" + "=" * 70)
print("✅ NETTOYAGE TERMINÉ !")
print("=" * 70)
