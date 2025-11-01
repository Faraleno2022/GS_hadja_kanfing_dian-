#!/usr/bin/env python
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ecole_moderne.settings')
django.setup()

from notes.models import ClasseNote, MatiereNote, NoteMensuelle, CompositionNote
from eleves.models import Eleve

print("=" * 80)
print("RECHERCHE ÉLÈVE AVEC NOTES")
print("=" * 80)

# Chercher un élève qui a des notes mensuelles
print("\n1. ÉLÈVES AVEC NOTES MENSUELLES")
eleves_avec_notes = []
for eleve in Eleve.objects.all()[:100]:  # Tester les 100 premiers
    nb_notes = NoteMensuelle.objects.filter(eleve=eleve).count()
    if nb_notes > 0:
        eleves_avec_notes.append((eleve, nb_notes))

print(f"   Trouvés: {len(eleves_avec_notes)}")
if eleves_avec_notes:
    for eleve, nb in eleves_avec_notes[:10]:
        print(f"   - {eleve.nom} {eleve.prenom}: {nb} notes mensuelles")

# Chercher un élève qui a des notes de composition
print("\n2. ÉLÈVES AVEC NOTES DE COMPOSITION")
eleves_avec_compo = []
for eleve in Eleve.objects.all()[:100]:
    nb_compo = CompositionNote.objects.filter(eleve=eleve).count()
    if nb_compo > 0:
        eleves_avec_compo.append((eleve, nb_compo))

print(f"   Trouvés: {len(eleves_avec_compo)}")
if eleves_avec_compo:
    for eleve, nb in eleves_avec_compo[:10]:
        print(f"   - {eleve.nom} {eleve.prenom}: {nb} notes composition")

# Tester avec un élève qui a des notes
print("\n3. TEST AVEC UN ÉLÈVE QUI A DES NOTES")
if eleves_avec_notes:
    eleve = eleves_avec_notes[0][0]
    print(f"   Élève: {eleve.nom} {eleve.prenom}")
    print(f"   Classe: {eleve.classe.nom}")
    print(f"   Année: {eleve.classe.annee_scolaire}")
    
    # Chercher ClasseNote
    print(f"\n   Recherche ClasseNote...")
    classes_note = ClasseNote.objects.all()
    print(f"   ClasseNote disponibles:")
    for cn in classes_note[:10]:
        print(f"     - {cn.nom} ({cn.annee_scolaire})")
    
    # Essayer de trouver la correspondance
    classe_note = None
    # Essai 1: nom exact + année
    try:
        classe_note = ClasseNote.objects.get(
            nom=eleve.classe.nom,
            annee_scolaire=eleve.classe.annee_scolaire
        )
        print(f"   ✓ Trouvée (exact): {classe_note.nom}")
    except:
        pass
    
    # Essai 2: nom exact seulement
    if not classe_note:
        try:
            classe_note = ClasseNote.objects.filter(nom=eleve.classe.nom).first()
            if classe_note:
                print(f"   ✓ Trouvée (nom): {classe_note.nom}")
        except:
            pass
    
    # Essai 3: nom case-insensitive
    if not classe_note:
        try:
            classe_note = ClasseNote.objects.filter(nom__iexact=eleve.classe.nom).first()
            if classe_note:
                print(f"   ✓ Trouvée (iexact): {classe_note.nom}")
        except:
            pass
    
    if not classe_note:
        print(f"   ✗ ClasseNote NON trouvée pour '{eleve.classe.nom}'")
    
    # Afficher les notes
    notes_mois = NoteMensuelle.objects.filter(eleve=eleve)
    print(f"\n   Notes mensuelles: {notes_mois.count()}")
    for note in notes_mois[:5]:
        print(f"     - {note.matiere.nom}: {note.note}/20 ({note.mois})")
    
    notes_compo = CompositionNote.objects.filter(eleve=eleve)
    print(f"\n   Notes composition: {notes_compo.count()}")
    for note in notes_compo[:5]:
        print(f"     - {note.matiere.nom}: {note.note}/20 ({note.periode})")

print("\n" + "=" * 80)
