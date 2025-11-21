"""
Script d'initialisation complète de l'école Hadja Kanfing Diané
avec élèves, matières et notes pour octobre
"""
import os
import sys
import django
from decimal import Decimal

# Configuration Django
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ecole_moderne.settings')
django.setup()

from django.contrib.auth.models import User
from eleves.models import Ecole, Eleve, Classe as ClasseEleve
from notes.models import ClasseNote, MatiereNote, Evaluation, NoteEleve

print("=" * 80)
print("INITIALISATION DE L'ÉCOLE HADJA KANFING DIANÉ")
print("=" * 80)

# 1. Créer ou récupérer l'école
print("\nETAPE 1 : Creation de l'ecole")
print("-" * 80)

ecole, created = Ecole.objects.get_or_create(
    nom="GROUPE SCOLAIRE HADJA KANFING DIANE",
    defaults={
        'adresse': 'SONFONIA, CONAKRY',
        'telephone': '+224620643009',
        'email': 'gshkd2025@gmail.com',
        'directeur': 'Directeur GSHKD',
        'ire': 'IRE RATOMA',
        'dpe': 'DPE RATOMA',
        'desee': 'DESEE CONAKRY',
        'etat': 'VALIDE',
    }
)

if created:
    print(f"✅ École créée : {ecole.nom}")
else:
    print(f"✅ École existante : {ecole.nom} (ID: {ecole.id})")

# 2. Pas de modèle AnneeScolaire - on utilise directement l'année courante
print("\n📅 ÉTAPE 2 : Année scolaire")
print("-" * 80)
print(f"✅ Année scolaire : 2025-2026 (gérée automatiquement)")

# 3. Créer la classe 12 SÉRIE SCIENTIFIQUE
print("\n🎓 ÉTAPE 3 : Création de la classe")
print("-" * 80)

classe_eleve, created = ClasseEleve.objects.get_or_create(
    nom="12 SÉRIE SCIENTIFIQUE",
    ecole=ecole,
    annee_scolaire="2025-2026",
    defaults={
        'niveau': 'LYCEE_12',
        'capacite_max': 50,
        'code_matricule': 'L12SC',
    }
)

if created:
    print(f"✅ Classe créée : {classe_eleve.nom}")
else:
    print(f"✅ Classe existante : {classe_eleve.nom} (ID: {classe_eleve.id})")

# 4. Créer la ClasseNote correspondante
classe_note, created = ClasseNote.objects.get_or_create(
    nom="12 SÉRIE SCIENTIFIQUE",
    ecole=ecole,
    defaults={
        'niveau': 'SECONDAIRE',
    }
)

if created:
    print(f"✅ ClasseNote créée : {classe_note.nom}")
else:
    print(f"✅ ClasseNote existante : {classe_note.nom} (ID: {classe_note.id})")

# 5. Créer les matières
print("\n📖 ÉTAPE 4 : Création des matières")
print("-" * 80)

matieres_data = [
    ('Anglais', 'ANG', 2.0),
    ('Biologie', 'BIO', 2.0),
    ('Chimie', 'CHI', 3.0),
    ('Economie', 'ECOPO', 2.0),
    ('Français', 'FR', 2.0),
    ('Géographie', 'GEO', 2.0),
    ('Histoire', 'HIST', 2.0),
    ('Mathématique', 'MATH', 4.0),
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
            'ecole': ecole,
        }
    )
    matieres[code] = matiere
    status = "✅ Créée" if created else "✓ Existante"
    print(f"  {status} : {nom} ({code}) - Coef: {coef}")

print(f"\n✅ Total : {len(matieres)} matières créées/vérifiées")

# 6. Créer les élèves
print("\n👥 ÉTAPE 5 : Création des élèves")
print("-" * 80)

eleves_data = [
    ('L12SC-009', 'ABOUBACAR MOHAMED', 'HAÏDARA', 'M'),
    ('L12SC-011', 'LANCINET', 'KANDÉ', 'M'),
    ('L12SC-020', 'ZARATOULAYE', 'DIALLO', 'F'),
    ('L12SC-010', 'FATOUMATA DJARAYE', 'BALDÉ', 'F'),
    ('L12SC-015', "N'FALY", 'KONATÉ', 'M'),
    ('L12SC-017', 'CLARA JEANNETTE', 'KOÏBA', 'F'),
    ('L12SC-021', 'TOUPOU ANGELINE', 'KPOGHOMOU', 'F'),
    ('L12SC-019', 'AMINATA', 'BANGOURA', 'F'),
    ('L12SC-022', 'ALPHA OUSMANE', 'DIALLO', 'M'),
    ('L12SC-012', 'JEAN DAVID', 'LOUAMMOU', 'M'),
    ('L12SC-018', 'RICHARD', 'MAMY', 'M'),
    ('L12SC-023', 'FATOUMATA KANNY', 'SYSAVANÉ', 'F'),
    ('L12SC-007', 'MADINA', 'TOURÉ', 'F'),
    ('L12SC-016', 'MOHAMED', "M'MAHAWA", 'M'),
    ('L12SC-008', 'NESTOR', 'GAMY', 'M'),
    ('L12SC-006', 'FATOUMATA', 'CAMARA', 'F'),
    ('L12SC-013', 'HASSANATOU', 'DIA', 'F'),
    ('L12SC-014', 'HOUSSAÏNATOU', 'DIA', 'F'),
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
            'ecole': ecole,
            'statut': 'ACTIF',
            'date_naissance': '2007-01-01',
        }
    )
    eleves[matricule] = eleve
    status = "✅" if created else "✓"
    print(f"  {status} {matricule}: {prenom} {nom}")

print(f"\n✅ Total : {len(eleves)} élèves créés/vérifiés")

# 7. Créer les évaluations pour octobre
print("\n📝 ÉTAPE 6 : Création des évaluations pour OCTOBRE")
print("-" * 80)

evaluations = {}
for code, matiere in matieres.items():
    eval_obj, created = Evaluation.objects.get_or_create(
        titre=f"Notes Octobre - {matiere.nom}",
        matiere=matiere,
        periode='OCTOBRE',
        defaults={
            'type_evaluation': 'DEVOIR',
            'date': '2025-10-15',
            'note_sur': Decimal('20'),
            'ecole': ecole,
        }
    )
    evaluations[code] = eval_obj
    status = "✅" if created else "✓"
    print(f"  {status} {matiere.nom}")

print(f"\n✅ Total : {len(evaluations)} évaluations créées")

# 8. Créer les notes
print("\n📊 ÉTAPE 7 : Création des notes pour OCTOBRE")
print("-" * 80)

# Notes par élève et par matière
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
notes_existantes = 0

for matricule, notes_matiere in notes_data.items():
    eleve = eleves[matricule]
    
    for code_matiere, note_value in notes_matiere.items():
        evaluation = evaluations[code_matiere]
        
        if note_value is None:
            # Élève absent
            note_obj, created = NoteEleve.objects.get_or_create(
                eleve=eleve,
                evaluation=evaluation,
                defaults={
                    'note': None,
                    'absent': True,
                }
            )
        else:
            # Élève présent avec note
            note_obj, created = NoteEleve.objects.get_or_create(
                eleve=eleve,
                evaluation=evaluation,
                defaults={
                    'note': Decimal(str(note_value)),
                    'absent': False,
                }
            )
        
        if created:
            notes_creees += 1
        else:
            notes_existantes += 1

print(f"✅ Notes créées : {notes_creees}")
print(f"✓ Notes existantes : {notes_existantes}")
print(f"📊 Total : {notes_creees + notes_existantes} notes")

# 9. Résumé final
print("\n" + "=" * 80)
print("✅ INITIALISATION TERMINÉE AVEC SUCCÈS !")
print("=" * 80)

print(f"""
📚 École : {ecole.nom}
📅 Année scolaire : {annee.annee}
🎓 Classe : {classe_eleve.nom}
📖 Matières : {len(matieres)}
👥 Élèves : {len(eleves)}
📝 Évaluations : {len(evaluations)}
📊 Notes : {notes_creees + notes_existantes}

🎯 PROCHAINES ÉTAPES :
1. Lancez le serveur : python manage.py runserver
2. Testez le classement : /notes/consulter/?classe_id={classe_note.id}&periode=OCTOBRE
3. Exportez le PDF : Cliquez sur "Exporter Classement"
4. Générez les bulletins individuels

💡 Pour tester la cohérence des rangs :
   python test_coherence_local.py
""")

print("=" * 80)
