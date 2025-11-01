"""
Script de test pour générer des notes pour une classe complète
Usage: python manage.py shell < test_bulletin_classe.py
"""

import os
import django
import random
from decimal import Decimal

# Configuration Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'gestion_scolaire.settings')
django.setup()

from notes.models import ClasseNote, MatiereNote, NoteMensuelle, CompositionNote
from eleves.models import Eleve, Classe as ClasseEleve
from django.contrib.auth.models import User

print("=" * 80)
print("🧪 SCRIPT DE TEST - GÉNÉRATION DE NOTES POUR UNE CLASSE")
print("=" * 80)

# Configuration
CLASSE_NOM = "1ère année"  # Modifier selon votre classe
ANNEE_SCOLAIRE = "2024-2025"
TRIMESTRE = "TRIMESTRE_1"
MOIS_TRIMESTRE_1 = ['OCTOBRE', 'NOVEMBRE', 'DECEMBRE']

print(f"\n📋 Configuration:")
print(f"   - Classe: {CLASSE_NOM}")
print(f"   - Année scolaire: {ANNEE_SCOLAIRE}")
print(f"   - Période: {TRIMESTRE}")
print(f"   - Mois: {', '.join(MOIS_TRIMESTRE_1)}")

# Récupérer ou créer un utilisateur pour les notes
try:
    user = User.objects.filter(is_staff=True).first()
    if not user:
        user = User.objects.create_user(
            username='admin_test',
            password='admin123',
            is_staff=True,
            is_superuser=True
        )
        print(f"\n✅ Utilisateur créé: {user.username}")
    else:
        print(f"\n✅ Utilisateur trouvé: {user.username}")
except Exception as e:
    print(f"\n❌ Erreur utilisateur: {e}")
    exit(1)

# Récupérer la classe de notes
try:
    classe_note = ClasseNote.objects.get(
        nom__icontains=CLASSE_NOM,
        annee_scolaire=ANNEE_SCOLAIRE
    )
    print(f"\n✅ Classe de notes trouvée: {classe_note.nom}")
except ClasseNote.DoesNotExist:
    print(f"\n❌ Classe de notes '{CLASSE_NOM}' non trouvée!")
    print("\n📝 Classes disponibles:")
    for c in ClasseNote.objects.filter(annee_scolaire=ANNEE_SCOLAIRE):
        print(f"   - {c.nom}")
    exit(1)

# Récupérer la classe d'élèves
try:
    classe_eleve = ClasseEleve.objects.get(
        nom__icontains=CLASSE_NOM,
        annee_scolaire=ANNEE_SCOLAIRE
    )
    print(f"✅ Classe d'élèves trouvée: {classe_eleve.nom}")
except ClasseEleve.DoesNotExist:
    print(f"\n❌ Classe d'élèves '{CLASSE_NOM}' non trouvée!")
    exit(1)

# Récupérer les élèves
eleves = Eleve.objects.filter(classe=classe_eleve, statut='ACTIF')
print(f"✅ {eleves.count()} élève(s) trouvé(s)")

if eleves.count() == 0:
    print("\n❌ Aucun élève dans cette classe!")
    exit(1)

# Récupérer les matières
matieres = MatiereNote.objects.filter(classe=classe_note, actif=True)
print(f"✅ {matieres.count()} matière(s) trouvée(s)")

if matieres.count() == 0:
    print("\n❌ Aucune matière pour cette classe!")
    exit(1)

print("\n" + "=" * 80)
print("📚 MATIÈRES DE LA CLASSE")
print("=" * 80)
for matiere in matieres:
    print(f"   - {matiere.nom} (Coefficient: {matiere.coefficient})")

# Fonction pour générer une note aléatoire
def generer_note():
    """Génère une note entre 8 et 18 avec une tendance vers 12-14"""
    # 70% de chances d'avoir une note entre 10 et 16
    if random.random() < 0.7:
        return round(random.uniform(10, 16), 2)
    else:
        return round(random.uniform(8, 18), 2)

# Compteurs
notes_mensuelles_creees = 0
compositions_creees = 0
notes_existantes = 0

print("\n" + "=" * 80)
print("🎯 GÉNÉRATION DES NOTES")
print("=" * 80)

# Pour chaque élève
for i, eleve in enumerate(eleves, 1):
    print(f"\n[{i}/{eleves.count()}] 👤 {eleve.nom} {eleve.prenom} ({eleve.matricule})")
    
    # Pour chaque matière
    for matiere in matieres:
        print(f"   📖 {matiere.nom}:")
        
        # Notes mensuelles
        for mois in MOIS_TRIMESTRE_1:
            try:
                # Vérifier si la note existe déjà
                note_existante = NoteMensuelle.objects.filter(
                    eleve=eleve,
                    matiere=matiere,
                    mois=mois,
                    annee_scolaire=ANNEE_SCOLAIRE
                ).first()
                
                if note_existante:
                    print(f"      ℹ️  {mois}: {note_existante.note} (existe déjà)")
                    notes_existantes += 1
                else:
                    # Créer la note
                    note_valeur = generer_note()
                    NoteMensuelle.objects.create(
                        eleve=eleve,
                        matiere=matiere,
                        mois=mois,
                        note=Decimal(str(note_valeur)),
                        absent=False,
                        annee_scolaire=ANNEE_SCOLAIRE,
                        cree_par=user
                    )
                    print(f"      ✅ {mois}: {note_valeur}")
                    notes_mensuelles_creees += 1
            except Exception as e:
                print(f"      ❌ Erreur {mois}: {e}")
        
        # Composition
        try:
            # Vérifier si la composition existe déjà
            comp_existante = CompositionNote.objects.filter(
                eleve=eleve,
                matiere=matiere,
                periode=TRIMESTRE,
                annee_scolaire=ANNEE_SCOLAIRE
            ).first()
            
            if comp_existante:
                print(f"      ℹ️  Composition: {comp_existante.note} (existe déjà)")
                notes_existantes += 1
            else:
                # Créer la composition
                note_comp = generer_note()
                CompositionNote.objects.create(
                    eleve=eleve,
                    matiere=matiere,
                    periode=TRIMESTRE,
                    note=Decimal(str(note_comp)),
                    absent=False,
                    annee_scolaire=ANNEE_SCOLAIRE,
                    cree_par=user
                )
                print(f"      ✅ Composition: {note_comp}")
                compositions_creees += 1
        except Exception as e:
            print(f"      ❌ Erreur Composition: {e}")

# Résumé
print("\n" + "=" * 80)
print("📊 RÉSUMÉ")
print("=" * 80)
print(f"✅ Notes mensuelles créées: {notes_mensuelles_creees}")
print(f"✅ Compositions créées: {compositions_creees}")
print(f"ℹ️  Notes déjà existantes: {notes_existantes}")
print(f"📝 Total: {notes_mensuelles_creees + compositions_creees + notes_existantes}")

# Calcul des moyennes pour vérification
print("\n" + "=" * 80)
print("📈 APERÇU DES MOYENNES")
print("=" * 80)

for eleve in eleves[:5]:  # Afficher les 5 premiers élèves
    total_points = 0
    total_coef = 0
    
    for matiere in matieres:
        # Récupérer les notes mensuelles
        notes_mois = []
        for mois in MOIS_TRIMESTRE_1:
            try:
                note = NoteMensuelle.objects.get(
                    eleve=eleve,
                    matiere=matiere,
                    mois=mois,
                    annee_scolaire=ANNEE_SCOLAIRE
                )
                if not note.absent:
                    notes_mois.append(float(note.note))
            except NoteMensuelle.DoesNotExist:
                pass
        
        # Moyenne mensuelle
        moy_mois = sum(notes_mois) / len(notes_mois) if notes_mois else 0
        
        # Composition
        note_comp = 0
        try:
            comp = CompositionNote.objects.get(
                eleve=eleve,
                matiere=matiere,
                periode=TRIMESTRE,
                annee_scolaire=ANNEE_SCOLAIRE
            )
            if not comp.absent:
                note_comp = float(comp.note)
        except CompositionNote.DoesNotExist:
            pass
        
        # Moyenne matière
        moy_matiere = (moy_mois + note_comp) / 2 if (moy_mois > 0 or note_comp > 0) else 0
        
        if moy_matiere > 0:
            total_points += moy_matiere * float(matiere.coefficient)
            total_coef += float(matiere.coefficient)
    
    # Moyenne générale
    moy_gen = total_points / total_coef if total_coef > 0 else 0
    
    print(f"   👤 {eleve.nom} {eleve.prenom}: {moy_gen:.2f}/20")

print("\n" + "=" * 80)
print("✅ GÉNÉRATION TERMINÉE !")
print("=" * 80)
print(f"\n🎓 Vous pouvez maintenant générer les bulletins pour la classe '{CLASSE_NOM}'")
print(f"📍 URL: http://127.0.0.1:8000/notes/bulletin-guineen/")
print(f"   1. Sélectionner: {CLASSE_NOM}")
print(f"   2. Période: 1er Trimestre")
print(f"   3. Choisir un élève")
print("\n" + "=" * 80)
