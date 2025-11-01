"""
Script pour ajouter des notes exemple pour toutes les classes
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

def ajouter_notes_classe(classe_note, periode='TRIMESTRE_1', user=None):
    """Ajouter des notes pour une classe"""
    
    print(f"\n{'='*70}")
    print(f"Classe: {classe_note.nom} - {classe_note.niveau_enseignement}")
    print(f"{'='*70}")
    
    # Vérifier les matières
    matieres = MatiereNote.objects.filter(classe=classe_note)
    if matieres.count() == 0:
        print(f"   ⚠️  Aucune matière configurée - IGNORÉE")
        return False
    
    print(f"   ✅ {matieres.count()} matière(s) configurée(s)")
    
    # Trouver les élèves
    try:
        classe_eleve = ClasseEleve.objects.get(
            nom=classe_note.nom,
            annee_scolaire=classe_note.annee_scolaire
        )
    except ClasseEleve.DoesNotExist:
        print(f"   ⚠️  Classe élève non trouvée - IGNORÉE")
        return False
    except ClasseEleve.MultipleObjectsReturned:
        classe_eleve = ClasseEleve.objects.filter(
            nom=classe_note.nom,
            annee_scolaire=classe_note.annee_scolaire
        ).first()
    
    eleves = Eleve.objects.filter(classe=classe_eleve, statut='ACTIF')
    if eleves.count() == 0:
        print(f"   ⚠️  Aucun élève trouvé - IGNORÉE")
        return False
    
    print(f"   ✅ {eleves.count()} élève(s) trouvé(s)")
    
    # Vérifier si des notes existent déjà
    notes_existantes = NoteMensuelle.objects.filter(
        matiere__classe=classe_note,
        periode=periode
    ).count()
    
    if notes_existantes > 0:
        print(f"   ℹ️  {notes_existantes} note(s) déjà saisie(s) - IGNORÉE")
        return False
    
    # Ajouter les notes
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
    return True

def main():
    """Fonction principale"""
    
    print("\n" + "="*70)
    print("AJOUT DE NOTES POUR TOUTES LES CLASSES")
    print("="*70)
    
    # Récupérer un utilisateur pour l'enregistrement
    user = User.objects.filter(is_superuser=True).first()
    if not user:
        user = User.objects.first()
    
    if not user:
        print("\n❌ Aucun utilisateur trouvé!")
        return
    
    print(f"\n👤 Utilisateur: {user.username}")
    
    # Récupérer toutes les classes
    classes = ClasseNote.objects.filter(actif=True).order_by('niveau_enseignement', 'nom')
    print(f"\n📚 Classes actives: {classes.count()}")
    
    # Demander confirmation
    print("\n" + "="*70)
    print("⚠️  ATTENTION")
    print("="*70)
    print("Ce script va ajouter des notes ALÉATOIRES pour toutes les classes")
    print("qui n'ont pas encore de notes pour le Trimestre 1.")
    print("\nLes notes seront comprises entre 8/20 et 18/20.")
    print("\n" + "="*70)
    
    reponse = input("\nContinuer? (oui/non): ")
    
    if reponse.lower() not in ['oui', 'o', 'yes', 'y']:
        print("\n❌ Opération annulée")
        return
    
    # Traiter chaque classe
    classes_traitees = 0
    classes_ignorees = 0
    
    for classe in classes:
        if ajouter_notes_classe(classe, periode='TRIMESTRE_1', user=user):
            classes_traitees += 1
        else:
            classes_ignorees += 1
    
    # Résumé
    print("\n" + "="*70)
    print("RÉSUMÉ")
    print("="*70)
    print(f"\n✅ Classes traitées: {classes_traitees}")
    print(f"ℹ️  Classes ignorées: {classes_ignorees}")
    print(f"📊 Total classes: {classes.count()}")
    
    if classes_traitees > 0:
        print("\n" + "="*70)
        print("✅ NOTES AJOUTÉES AVEC SUCCÈS!")
        print("="*70)
        print("\n📝 Prochaines étapes:")
        print("   1. Vérifier les notes: http://127.0.0.1:8000/notes/consulter/")
        print("   2. Générer les bulletins: http://127.0.0.1:8000/notes/bulletins/")
        print("   3. Modifier les notes si nécessaire")
    else:
        print("\n" + "="*70)
        print("ℹ️  AUCUNE NOTE AJOUTÉE")
        print("="*70)
        print("\nRaisons possibles:")
        print("   - Toutes les classes ont déjà des notes")
        print("   - Aucune matière configurée")
        print("   - Aucun élève dans les classes")

if __name__ == '__main__':
    main()
