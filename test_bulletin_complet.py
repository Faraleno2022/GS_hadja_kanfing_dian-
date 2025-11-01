#!/usr/bin/env python
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ecole_moderne.settings')
django.setup()

from notes.models import ClasseNote, MatiereNote, NoteMensuelle, CompositionNote
from eleves.models import Eleve, Classe, Ecole

print("=" * 80)
print("TEST COMPLET DU BULLETIN")
print("=" * 80)

# 1. Vérifier les écoles
print("\n1. ÉCOLES")
ecoles = Ecole.objects.all()
print(f"   Nombre: {ecoles.count()}")
if ecoles.exists():
    ecole = ecoles.first()
    print(f"   Première: {ecole.nom}")

# 2. Vérifier les ClasseNote
print("\n2. CLASSENOTE")
classes_note = ClasseNote.objects.filter(actif=True)
print(f"   Nombre actives: {classes_note.count()}")
if classes_note.exists():
    classe_note = classes_note.first()
    print(f"   Première: {classe_note.nom} (ID: {classe_note.id})")

# 3. Vérifier les Classe (eleves.models)
print("\n3. CLASSE (eleves.models)")
classes = Classe.objects.all()
print(f"   Nombre: {classes.count()}")
if classes.exists():
    classe = classes.first()
    print(f"   Première: {classe.nom}")

# 4. Vérifier les élèves
print("\n4. ÉLÈVES")
eleves = Eleve.objects.all()
print(f"   Nombre total: {eleves.count()}")
if eleves.exists():
    eleve = eleves.first()
    print(f"   Premier: {eleve.nom} {eleve.prenom}")
    print(f"   Classe: {eleve.classe}")
    print(f"   Classe nom: {eleve.classe.nom}")
    print(f"   Classe année: {eleve.classe.annee_scolaire}")

# 5. Trouver la ClasseNote correspondante
print("\n5. MAPPING CLASSE → CLASSENOTE")
if eleves.exists():
    eleve = eleves.first()
    print(f"   Élève: {eleve.nom} {eleve.prenom}")
    print(f"   Classe élève: {eleve.classe.nom}")
    
    # Chercher ClasseNote
    try:
        classe_note = ClasseNote.objects.get(
            nom=eleve.classe.nom,
            annee_scolaire=eleve.classe.annee_scolaire
        )
        print(f"   ✓ ClasseNote trouvée: {classe_note.nom} (ID: {classe_note.id})")
    except ClasseNote.DoesNotExist:
        print(f"   ✗ ClasseNote NON trouvée pour {eleve.classe.nom}")
        # Essayer juste par nom
        classe_note = ClasseNote.objects.filter(nom=eleve.classe.nom).first()
        if classe_note:
            print(f"   ✓ ClasseNote trouvée par nom: {classe_note.nom}")
        else:
            print(f"   ✗ Aucune ClasseNote avec ce nom")
            classe_note = None

# 6. Vérifier les matières
print("\n6. MATIÈRES")
if classe_note:
    matieres = MatiereNote.objects.filter(classe=classe_note)
    print(f"   Nombre pour {classe_note.nom}: {matieres.count()}")
    if matieres.exists():
        for mat in matieres[:5]:
            print(f"   - {mat.nom} (Coef: {mat.coefficient})")

# 7. Vérifier les notes mensuelles
print("\n7. NOTES MENSUELLES")
if eleves.exists():
    eleve = eleves.first()
    notes_mois = NoteMensuelle.objects.filter(eleve=eleve)
    print(f"   Nombre pour {eleve.nom}: {notes_mois.count()}")
    if notes_mois.exists():
        for note in notes_mois[:5]:
            print(f"   - {note.matiere.nom}: {note.note}/20 ({note.mois})")

# 8. Vérifier les notes de composition
print("\n8. NOTES DE COMPOSITION")
if eleves.exists():
    eleve = eleves.first()
    notes_compo = CompositionNote.objects.filter(eleve=eleve)
    print(f"   Nombre pour {eleve.nom}: {notes_compo.count()}")
    if notes_compo.exists():
        for note in notes_compo[:5]:
            print(f"   - {note.matiere.nom}: {note.note}/20 ({note.periode})")

# 9. Test complet de génération
print("\n9. TEST GÉNÉRATION BULLETIN")
if eleves.exists() and classe_note:
    eleve = eleves.first()
    periode = 'SEMESTRE_1'
    system_type = 'semestre'
    
    print(f"   Élève: {eleve.nom} {eleve.prenom}")
    print(f"   Période: {periode}")
    print(f"   Système: {system_type}")
    
    # Chercher ClasseNote
    try:
        classe_note_test = ClasseNote.objects.get(
            nom=eleve.classe.nom,
            annee_scolaire=eleve.classe.annee_scolaire
        )
        print(f"   ✓ ClasseNote: {classe_note_test.nom}")
        
        # Chercher matières
        matieres_test = MatiereNote.objects.filter(classe=classe_note_test)
        print(f"   ✓ Matières: {matieres_test.count()}")
        
        # Pour chaque matière, vérifier les notes
        mois = ['OCTOBRE', 'NOVEMBRE', 'DECEMBRE', 'JANVIER', 'FEVRIER']
        for matiere in matieres_test[:3]:
            print(f"\n   Matière: {matiere.nom}")
            
            # Notes mensuelles
            notes_mois = NoteMensuelle.objects.filter(
                eleve=eleve,
                matiere=matiere,
                mois__in=mois
            )
            print(f"     - Notes mensuelles: {notes_mois.count()}")
            if notes_mois.exists():
                somme = sum(n.note for n in notes_mois)
                moyenne = somme / notes_mois.count()
                print(f"     - Moyenne: {moyenne:.2f}")
            
            # Note de composition
            try:
                compo = CompositionNote.objects.get(
                    eleve=eleve,
                    matiere=matiere,
                    periode='SEMESTRE_1'
                )
                print(f"     - Composition: {compo.note}/20")
            except CompositionNote.DoesNotExist:
                print(f"     - Composition: Non trouvée")
        
    except ClasseNote.DoesNotExist:
        print(f"   ✗ ClasseNote non trouvée")

print("\n" + "=" * 80)
print("RÉSUMÉ")
print("=" * 80)
print(f"Écoles: {ecoles.count()}")
print(f"ClasseNote: {classes_note.count()}")
print(f"Classe: {classes.count()}")
print(f"Élèves: {eleves.count()}")
if eleves.exists():
    eleve = eleves.first()
    notes_mois = NoteMensuelle.objects.filter(eleve=eleve)
    notes_compo = CompositionNote.objects.filter(eleve=eleve)
    print(f"Notes mensuelles (1er élève): {notes_mois.count()}")
    print(f"Notes composition (1er élève): {notes_compo.count()}")
print("=" * 80)
