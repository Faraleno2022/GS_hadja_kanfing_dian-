"""
Script automatique pour ajouter des notes exemple pour toutes les classes
Version sans confirmation
"""

import os
import django
import random

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ecole_moderne.settings')
django.setup()

from notes.models import ClasseNote, MatiereNote, NoteMensuelle, CompositionNote
from eleves.models import Eleve, Classe as ClasseEleve
from django.contrib.auth import get_user_model

User = get_user_model()

def generer_note_aleatoire(min_note=8, max_note=18):
    """Générer une note aléatoire entre min et max"""
    return round(random.uniform(min_note, max_note), 1)

print("\n" + "="*70)
print("AJOUT AUTOMATIQUE DE NOTES POUR TOUTES LES CLASSES")
print("="*70)

# Récupérer un utilisateur
user = User.objects.filter(is_superuser=True).first()
if not user:
    user = User.objects.first()

if not user:
    print("\n❌ Aucun utilisateur trouvé!")
    exit(1)

print(f"\n👤 Utilisateur: {user.username}")

# Récupérer toutes les classes
classes = ClasseNote.objects.filter(actif=True).order_by('niveau_enseignement', 'nom')
print(f"📚 Classes actives: {classes.count()}")

periode = 'TRIMESTRE_1'
classes_traitees = 0
classes_ignorees = 0
total_notes = 0

for classe in classes:
    print(f"\n{'─'*70}")
    print(f"📖 {classe.nom} - {classe.niveau_enseignement}")
    
    # Vérifier les matières
    matieres = MatiereNote.objects.filter(classe=classe)
    if matieres.count() == 0:
        print(f"   ⚠️  Aucune matière - IGNORÉE")
        classes_ignorees += 1
        continue
    
    # Trouver les élèves
    try:
        classe_eleve = ClasseEleve.objects.get(
            nom=classe.nom,
            annee_scolaire=classe.annee_scolaire
        )
    except ClasseEleve.DoesNotExist:
        print(f"   ⚠️  Classe élève non trouvée - IGNORÉE")
        classes_ignorees += 1
        continue
    except ClasseEleve.MultipleObjectsReturned:
        classe_eleve = ClasseEleve.objects.filter(
            nom=classe.nom,
            annee_scolaire=classe.annee_scolaire
        ).first()
    
    eleves = Eleve.objects.filter(classe=classe_eleve, statut='ACTIF')
    if eleves.count() == 0:
        print(f"   ⚠️  Aucun élève - IGNORÉE")
        classes_ignorees += 1
        continue
    
    # Vérifier si des notes existent déjà
    notes_existantes = NoteMensuelle.objects.filter(
        matiere__classe=classe,
        periode=periode
    ).count()
    
    if notes_existantes > 0:
        print(f"   ℹ️  Notes déjà saisies ({notes_existantes}) - IGNORÉE")
        classes_ignorees += 1
        continue
    
    # Ajouter les notes
    print(f"   📝 Ajout notes pour {eleves.count()} élève(s), {matieres.count()} matière(s)")
    notes_ajoutees = 0
    
    for eleve in eleves:
        for matiere in matieres:
            # Note mensuelle
            note_mensuelle = generer_note_aleatoire()
            NoteMensuelle.objects.create(
                eleve=eleve,
                matiere=matiere,
                periode=periode,
                note=note_mensuelle,
                enregistre_par=user
            )
            
            # Composition
            note_composition = generer_note_aleatoire()
            CompositionNote.objects.create(
                eleve=eleve,
                matiere=matiere,
                periode=periode,
                note=note_composition,
                enregistre_par=user
            )
            
            notes_ajoutees += 2
    
    print(f"   ✅ {notes_ajoutees} note(s) ajoutée(s)")
    classes_traitees += 1
    total_notes += notes_ajoutees

# Résumé
print("\n" + "="*70)
print("RÉSUMÉ FINAL")
print("="*70)
print(f"\n✅ Classes traitées: {classes_traitees}")
print(f"ℹ️  Classes ignorées: {classes_ignorees}")
print(f"📊 Total classes: {classes.count()}")
print(f"📝 Total notes ajoutées: {total_notes}")

if classes_traitees > 0:
    print("\n" + "="*70)
    print("✅ NOTES AJOUTÉES AVEC SUCCÈS!")
    print("="*70)
    print("\n📝 Accès rapides:")
    print("   Consulter: http://127.0.0.1:8000/notes/consulter/")
    print("   Bulletins: http://127.0.0.1:8000/notes/bulletins/")
else:
    print("\n" + "="*70)
    print("ℹ️  AUCUNE NOTE AJOUTÉE")
    print("="*70)

print("\n" + "="*70)
