"""Script de diagnostic pour consulter_notes"""
import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ecole_moderne.settings')
django.setup()

from notes.models import NoteMensuelle, CompositionNote, MatiereNote, ClasseNote
from eleves.models import Eleve, Classe as ClasseEleve

# Classe ID 6
classe_note = ClasseNote.objects.get(id=6)
print(f"ClasseNote: {classe_note.nom}")
print(f"Année scolaire: {classe_note.annee_scolaire}")
print(f"Ecole: {classe_note.ecole}")

# Matières de cette classe
matieres = MatiereNote.objects.filter(classe=classe_note, actif=True)
print(f"\nMatières ({matieres.count()}):")
for m in matieres:
    print(f"  - ID={m.id}: {m.nom} (coef={m.coefficient})")

# Chercher la classe élève correspondante
classe_eleve = ClasseEleve.objects.filter(
    nom=classe_note.nom,
    annee_scolaire=classe_note.annee_scolaire
).first()
print(f"\nClasseEleve trouvée: {classe_eleve}")

if classe_eleve:
    eleves = Eleve.objects.filter(classe=classe_eleve, statut='ACTIF')
    print(f"Élèves actifs: {eleves.count()}")
    
    # Vérifier les notes mensuelles
    print("\n--- Notes Mensuelles ---")
    for matiere in matieres[:2]:
        notes = NoteMensuelle.objects.filter(
            matiere=matiere,
            annee_scolaire=classe_note.annee_scolaire
        )
        print(f"Matière {matiere.nom}: {notes.count()} notes")
        if notes.exists():
            for n in notes[:3]:
                print(f"  - Eleve ID={n.eleve_id}, mois={n.mois}, note={n.note}")
    
    # Vérifier les notes de composition
    print("\n--- Notes Composition ---")
    for matiere in matieres[:2]:
        notes = CompositionNote.objects.filter(
            matiere=matiere,
            annee_scolaire=classe_note.annee_scolaire
        )
        print(f"Matière {matiere.nom}: {notes.count()} notes")
        if notes.exists():
            for n in notes[:3]:
                print(f"  - Eleve ID={n.eleve_id}, periode={n.periode}, note={n.note}")

# Vérifier toutes les notes mensuelles pour cette classe
print("\n--- Toutes les NoteMensuelle pour cette classe ---")
all_notes = NoteMensuelle.objects.filter(matiere__classe=classe_note)
print(f"Total: {all_notes.count()}")
mois_distincts = all_notes.values_list('mois', flat=True).distinct()
print(f"Mois distincts: {list(mois_distincts)}")

# Vérifier toutes les notes de composition pour cette classe
print("\n--- Toutes les CompositionNote pour cette classe ---")
all_compo = CompositionNote.objects.filter(matiere__classe=classe_note)
print(f"Total: {all_compo.count()}")
periodes_distinctes = all_compo.values_list('periode', flat=True).distinct()
print(f"Périodes distinctes: {list(periodes_distinctes)}")
