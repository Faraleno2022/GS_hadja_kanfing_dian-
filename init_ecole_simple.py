"""
Script simplifie d'initialisation de l'ecole Hadja Kanfing Diane
avec eleves, matieres et notes pour octobre
"""
import os
import sys
import django
from decimal import Decimal

# Configuration Django
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ecole_moderne.settings')
django.setup()

from eleves.models import Ecole, Eleve, Classe as ClasseEleve, Responsable
from notes.models import ClasseNote, MatiereNote, Evaluation, NoteEleve

print("=" * 80)
print("INITIALISATION ECOLE HADJA KANFING DIANE")
print("=" * 80)

# 1. Ecole
print("\nETAPE 1 : Ecole")
print("-" * 80)

ecole = Ecole.objects.filter(nom__icontains="HADJA KANFING").first()
if not ecole:
    ecole = Ecole.objects.create(
        nom="GROUPE SCOLAIRE HADJA KANFING DIANE",
        adresse='SONFONIA, CONAKRY',
        telephone='+224620643009',
        email='gshkd2025@gmail.com',
        directeur='Directeur GSHKD',
        ire='IRE RATOMA',
        dpe='DPE RATOMA',
        desee='DESEE CONAKRY',
        etat='VALIDE',
    )
    print(f"Ecole creee : {ecole.nom}")
else:
    print(f"Ecole existante : {ecole.nom} (ID: {ecole.id})")

# 2. Classe
print("\nETAPE 2 : Classe 12 SERIE SCIENTIFIQUE")
print("-" * 80)

classe_eleve, created = ClasseEleve.objects.get_or_create(
    nom="12 SERIE SCIENTIFIQUE",
    ecole=ecole,
    annee_scolaire="2025-2026",
    defaults={
        'niveau': 'LYCEE_12',
        'capacite_max': 50,
        'code_matricule': 'L12SC',
    }
)
print(f"{'Creee' if created else 'Existante'} : {classe_eleve.nom}")

classe_note, created = ClasseNote.objects.get_or_create(
    nom="12 SERIE SCIENTIFIQUE",
    ecole=ecole,
    defaults={'niveau': 'SECONDAIRE'}
)
print(f"ClasseNote {'creee' if created else 'existante'} : {classe_note.nom}")

# 3. Matieres
print("\nETAPE 3 : Matieres")
print("-" * 80)

matieres_data = [
    ('Anglais', 'ANG', 2.0),
    ('Biologie', 'BIO', 2.0),
    ('Chimie', 'CHI', 3.0),
    ('Economie', 'ECOPO', 2.0),
    ('Francais', 'FR', 2.0),
    ('Geographie', 'GEO', 2.0),
    ('Histoire', 'HIST', 2.0),
    ('Mathematique', 'MATH', 4.0),
    ('Philosophie', 'PHILO', 2.0),
    ('Physique', 'PHY', 3.0),
]

matieres = {}
for nom, code, coef in matieres_data:
    matiere, created = MatiereNote.objects.get_or_create(
        nom=nom,
        classe=classe_note,
        defaults={
            'code': code,
            'coefficient': Decimal(str(coef)),
        }
    )
    matieres[code] = matiere
    print(f"  {'Creee' if created else 'OK'} : {nom} ({code}) - Coef: {coef}")

print(f"\nTotal : {len(matieres)} matieres")

# 4. Responsable par defaut
print("\nETAPE 4 : Responsable par defaut")
print("-" * 80)

responsable = Responsable.objects.filter(nom="RESPONSABLE").first()
if not responsable:
    responsable = Responsable.objects.create(
        nom="RESPONSABLE",
        prenom="TEST",
        telephone='+224620000000',
        relation='PERE',
    )
    print(f"Responsable cree : {responsable.prenom} {responsable.nom}")
else:
    print(f"Responsable existant : {responsable.prenom} {responsable.nom}")

# 5. Eleves
print("\nETAPE 5 : Eleves")
print("-" * 80)

eleves_data = [
    ('L12SC-009', 'ABOUBACAR MOHAMED', 'HAIDARA', 'M'),
    ('L12SC-011', 'LANCINET', 'KANDE', 'M'),
    ('L12SC-020', 'ZARATOULAYE', 'DIALLO', 'F'),
    ('L12SC-010', 'FATOUMATA DJARAYE', 'BALDE', 'F'),
    ('L12SC-015', "N'FALY", 'KONATE', 'M'),
    ('L12SC-017', 'CLARA JEANNETTE', 'KOIBA', 'F'),
    ('L12SC-021', 'TOUPOU ANGELINE', 'KPOGHOMOU', 'F'),
    ('L12SC-019', 'AMINATA', 'BANGOURA', 'F'),
    ('L12SC-022', 'ALPHA OUSMANE', 'DIALLO', 'M'),
    ('L12SC-012', 'JEAN DAVID', 'LOUAMMOU', 'M'),
    ('L12SC-018', 'RICHARD', 'MAMY', 'M'),
    ('L12SC-023', 'FATOUMATA KANNY', 'SYSAVANE', 'F'),
    ('L12SC-007', 'MADINA', 'TOURE', 'F'),
    ('L12SC-016', 'MOHAMED', "M'MAHAWA", 'M'),
    ('L12SC-008', 'NESTOR', 'GAMY', 'M'),
    ('L12SC-006', 'FATOUMATA', 'CAMARA', 'F'),
    ('L12SC-013', 'HASSANATOU', 'DIA', 'F'),
    ('L12SC-014', 'HOUSSAINATOU', 'DIA', 'F'),
]

eleves = {}
for matricule, prenom, nom, sexe in eleves_data:
    eleve, created = Eleve.objects.get_or_create(
        matricule=matricule,
        defaults={
            'prenom': prenom,
            'nom': nom,
            'sexe': sexe,
            'classe': classe_eleve,
            'responsable_principal': responsable,
            'statut': 'ACTIF',
            'date_naissance': '2007-01-01',
            'date_inscription': '2025-10-01',
            'lieu_naissance': 'CONAKRY',
        }
    )
    eleves[matricule] = eleve
    print(f"  {'OK' if created else '  '} {matricule}: {prenom} {nom}")

print(f"\nTotal : {len(eleves)} eleves")

# 6. Evaluations
print("\nETAPE 6 : Evaluations OCTOBRE")
print("-" * 80)

evaluations = {}
for code, matiere in matieres.items():
    eval_obj, created = Evaluation.objects.get_or_create(
        titre=f"Notes Octobre - {matiere.nom}",
        matiere=matiere,
        periode='OCTOBRE',
        defaults={
            'type_evaluation': 'DEVOIR',
            'note_sur': Decimal('20'),
            'date_evaluation': '2025-10-15',
        }
    )
    evaluations[code] = eval_obj
    print(f"  {'Creee' if created else 'OK'} : {matiere.nom}")

print(f"\nTotal : {len(evaluations)} evaluations")

# 7. Notes
print("\nETAPE 7 : Notes")
print("-" * 80)

notes_data = {
    'L12SC-009': {'ANG': 12, 'BIO': 12, 'CHI': 17, 'ECOPO': 17, 'FR': 15, 'GEO': 15, 'HIST': 14.5, 'MATH': 13.5, 'PHILO': 12, 'PHY': 17},
    'L12SC-011': {'ANG': 10, 'BIO': 19, 'CHI': 18, 'ECOPO': 11, 'FR': 13, 'GEO': 15.5, 'HIST': 17.75, 'MATH': 16, 'PHILO': 13, 'PHY': 13},
    'L12SC-020': {'ANG': 14, 'BIO': 18, 'CHI': 18.75, 'ECOPO': 13.5, 'FR': 12, 'GEO': 11, 'HIST': 17, 'MATH': 16, 'PHILO': 12, 'PHY': 10},
    'L12SC-010': {'ANG': 12, 'BIO': 16, 'CHI': 7, 'ECOPO': 10, 'FR': 11, 'GEO': 15, 'HIST': 16.5, 'MATH': 14.5, 'PHILO': 12, 'PHY': 17},
    'L12SC-015': {'ANG': 11, 'BIO': 13, 'CHI': 10, 'ECOPO': 8, 'FR': 11.5, 'GEO': 11, 'HIST': 14, 'MATH': 14.5, 'PHILO': 8, 'PHY': 4},
    'L12SC-017': {'ANG': 11, 'BIO': 10, 'CHI': 10, 'ECOPO': 11, 'FR': 7, 'GEO': 15, 'HIST': 16, 'MATH': 10, 'PHILO': 11, 'PHY': 4},
    'L12SC-021': {'ANG': 11, 'BIO': 12, 'CHI': 10, 'ECOPO': 8, 'FR': 12, 'GEO': 10, 'HIST': 12, 'MATH': 14, 'PHILO': 5, 'PHY': 4},
    'L12SC-019': {'ANG': 9, 'BIO': 10, 'CHI': 10, 'ECOPO': 8, 'FR': 6, 'GEO': 8, 'HIST': 14, 'MATH': 11.5, 'PHILO': 8, 'PHY': 8},
    'L12SC-022': {'ANG': 12, 'BIO': 11, 'CHI': 10, 'ECOPO': 6, 'FR': 8, 'GEO': 15, 'HIST': 9, 'MATH': 9.5, 'PHILO': 10, 'PHY': 5},
    'L12SC-012': {'ANG': 5, 'BIO': 12.5, 'CHI': 10, 'ECOPO': 10, 'FR': 5, 'GEO': 14, 'HIST': 11, 'MATH': 11.5, 'PHILO': 12, 'PHY': 3},
    'L12SC-018': {'ANG': 10, 'BIO': 9.5, 'CHI': 10, 'ECOPO': 10, 'FR': 11, 'GEO': 9, 'HIST': 12, 'MATH': 10, 'PHILO': 10, 'PHY': 2},
    'L12SC-023': {'ANG': 12, 'BIO': 8, 'CHI': 10, 'ECOPO': 12, 'FR': 12, 'GEO': 10, 'HIST': 12, 'MATH': 6, 'PHILO': 8, 'PHY': 5},
    'L12SC-007': {'ANG': 14, 'BIO': 8, 'CHI': 3, 'ECOPO': 8, 'FR': 10, 'GEO': 12, 'HIST': 12, 'MATH': 11.5, 'PHILO': 5, 'PHY': 4},
    'L12SC-016': {'ANG': 11, 'BIO': None, 'CHI': 14.5, 'ECOPO': 8, 'FR': 10, 'GEO': 16.75, 'HIST': 8, 'MATH': 16, 'PHILO': 6, 'PHY': None},
    'L12SC-008': {'ANG': 7, 'BIO': 12.5, 'CHI': 2, 'ECOPO': 8.5, 'FR': 8, 'GEO': 10, 'HIST': 11, 'MATH': 8, 'PHILO': 10, 'PHY': 2},
    'L12SC-006': {'ANG': 11, 'BIO': 12, 'CHI': 4, 'ECOPO': 7, 'FR': 8, 'GEO': 10, 'HIST': 13.5, 'MATH': 2, 'PHILO': 5, 'PHY': 2},
    'L12SC-013': {'ANG': 13, 'BIO': 4, 'CHI': 3.3, 'ECOPO': 6, 'FR': 8, 'GEO': 9, 'HIST': 9, 'MATH': 2, 'PHILO': 11, 'PHY': 2},
    'L12SC-014': {'ANG': 10, 'BIO': 4, 'CHI': 2, 'ECOPO': 6, 'FR': 5, 'GEO': 9, 'HIST': 7, 'MATH': 2, 'PHILO': 5, 'PHY': 2},
}

notes_creees = 0
for matricule, notes_matiere in notes_data.items():
    eleve = eleves[matricule]
    for code_matiere, note_value in notes_matiere.items():
        evaluation = evaluations[code_matiere]
        note_obj, created = NoteEleve.objects.get_or_create(
            eleve=eleve,
            evaluation=evaluation,
            defaults={
                'note': Decimal(str(note_value)) if note_value is not None else None,
                'absent': note_value is None,
            }
        )
        if created:
            notes_creees += 1

print(f"Notes creees : {notes_creees}")

# Resume
print("\n" + "=" * 80)
print("INITIALISATION TERMINEE !")
print("=" * 80)
print(f"""
Ecole : {ecole.nom}
Classe : {classe_eleve.nom}
Matieres : {len(matieres)}
Eleves : {len(eleves)}
Notes : {notes_creees}

PROCHAINES ETAPES :
1. python manage.py runserver
2. Testez : /notes/consulter/?classe_id={classe_note.id}&periode=OCTOBRE
3. python test_coherence_local.py
""")
print("=" * 80)
