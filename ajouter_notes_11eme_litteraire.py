#!/usr/bin/env python
"""
Script pour ajouter des notes à la classe 11ème série littéraire 2024-2025
"""
import os
import sys
import django
import random
from decimal import Decimal

# Configuration Django
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ecole_moderne.settings')
django.setup()

from notes.models import ClasseNote, MatiereNote, Evaluation, NoteEleve
from eleves.models import Classe as ClasseEleve, Eleve, Ecole

def identifier_classe_11eme_litteraire():
    """Identifier la classe 11ème série littéraire"""
    print("🔍 IDENTIFICATION CLASSE 11ÈME SÉRIE LITTÉRAIRE")
    print("=" * 50)
    
    # Chercher dans ClasseNote
    classes_notes = ClasseNote.objects.filter(
        nom__icontains="11",
        annee_scolaire="2024-2025"
    ).filter(nom__icontains="littéraire")
    
    print(f"📚 Classes Notes trouvées: {classes_notes.count()}")
    for classe in classes_notes:
        print(f"   - ID {classe.id}: {classe.nom} ({classe.annee_scolaire}) - {classe.ecole}")
    
    # Chercher dans ClasseEleve
    classes_eleves = ClasseEleve.objects.filter(
        nom__icontains="11",
        annee_scolaire="2024-2025"
    ).filter(nom__icontains="littéraire")
    
    print(f"👥 Classes Élèves trouvées: {classes_eleves.count()}")
    for classe in classes_eleves:
        print(f"   - ID {classe.id}: {classe.nom} ({classe.annee_scolaire}) - {classe.ecole}")
    
    # Chercher aussi avec "LETTRES"
    classes_eleves_lettres = ClasseEleve.objects.filter(
        nom__icontains="11",
        annee_scolaire="2024-2025"
    ).filter(nom__icontains="LETTRES")
    
    print(f"📖 Classes Lettres trouvées: {classes_eleves_lettres.count()}")
    for classe in classes_eleves_lettres:
        print(f"   - ID {classe.id}: {classe.nom} ({classe.annee_scolaire}) - {classe.ecole}")
    
    return classes_notes, classes_eleves, classes_eleves_lettres

def creer_ou_completer_classe_note(classe_eleve):
    """Créer ou compléter la ClasseNote correspondante"""
    print(f"\n🏫 CRÉATION/VÉRIFICATION CLASSE NOTE")
    print("-" * 40)
    
    # Chercher une ClasseNote correspondante
    classe_note = ClasseNote.objects.filter(
        nom__icontains="11",
        annee_scolaire=classe_eleve.annee_scolaire,
        ecole=classe_eleve.ecole
    ).filter(nom__icontains="littéraire").first()
    
    if not classe_note:
        # Créer une nouvelle ClasseNote
        classe_note = ClasseNote.objects.create(
            nom="11ème série littéraire",
            niveau=classe_eleve.niveau,
            annee_scolaire=classe_eleve.annee_scolaire,
            ecole=classe_eleve.ecole,
            niveau_enseignement='SECONDAIRE',
            actif=True,
            description=f"Classe créée automatiquement pour {classe_eleve.nom}"
        )
        print(f"✅ ClasseNote créée: {classe_note.nom} (ID: {classe_note.id})")
    else:
        print(f"✅ ClasseNote existante: {classe_note.nom} (ID: {classe_note.id})")
    
    return classe_note

def creer_matieres_litteraires(classe_note):
    """Créer les matières typiques d'une série littéraire"""
    print(f"\n📚 CRÉATION MATIÈRES LITTÉRAIRES")
    print("-" * 35)
    
    matieres_litteraires = [
        ('Français', 'FR', 5),
        ('Philosophie', 'PHILO', 4),
        ('Histoire-Géographie', 'HG', 4),
        ('Anglais', 'ANG', 3),
        ('Mathématiques', 'MATH', 2),
        ('Sciences Physiques', 'SP', 2),
        ('SVT', 'SVT', 2),
        ('Éducation Civique', 'EC', 1),
        ('EPS', 'EPS', 1),
    ]
    
    matieres_creees = []
    for nom, code, coef in matieres_litteraires:
        matiere, created = MatiereNote.objects.get_or_create(
            classe=classe_note,
            nom=nom,
            defaults={
                'code': code,
                'coefficient': coef,
                'actif': True,
                'description': f'Matière de série littéraire'
            }
        )
        matieres_creees.append(matiere)
        if created:
            print(f"   ✅ {nom} (coef: {coef})")
        else:
            print(f"   ↻ {nom} (existe déjà)")
    
    return matieres_creees

def creer_evaluations_periodes(matieres, classe_note):
    """Créer des évaluations pour différentes périodes"""
    print(f"\n📝 CRÉATION ÉVALUATIONS")
    print("-" * 25)
    
    periodes = [
        ('OCTOBRE', '2024-10-15'),
        ('NOVEMBRE', '2024-11-15'),
        ('DECEMBRE', '2024-12-15'),
        ('JANVIER', '2025-01-15'),
        ('FEVRIER', '2025-02-15'),
        ('MARS', '2025-03-15'),
    ]
    
    evaluations_creees = []
    
    for periode, date in periodes:
        print(f"\n   📅 Période {periode}:")
        
        for matiere in matieres:
            # Créer un devoir pour chaque matière et période
            evaluation, created = Evaluation.objects.get_or_create(
                matiere=matiere,
                titre=f"Devoir {periode} - {matiere.nom}",
                periode=periode,
                defaults={
                    'type_evaluation': 'DEVOIR',
                    'date_evaluation': date,
                    'note_sur': 20.0,
                    'coefficient': 1.0,
                    'description': f'Devoir de {matiere.nom} pour {periode}'
                }
            )
            evaluations_creees.append(evaluation)
            
            if created:
                print(f"      ✅ {matiere.nom}")
    
    print(f"\n📊 Total évaluations créées: {len([e for e in evaluations_creees if e])}")
    return evaluations_creees

def creer_eleves_test(classe_eleve):
    """Créer des élèves de test si nécessaire"""
    print(f"\n👥 VÉRIFICATION/CRÉATION ÉLÈVES")
    print("-" * 35)
    
    eleves_existants = Eleve.objects.filter(classe=classe_eleve, statut='ACTIF')
    print(f"📊 Élèves existants: {eleves_existants.count()}")
    
    if eleves_existants.count() > 0:
        print("✅ Des élèves existent déjà:")
        for eleve in eleves_existants[:5]:
            print(f"   - {eleve.prenom} {eleve.nom}")
        if eleves_existants.count() > 5:
            print(f"   ... et {eleves_existants.count() - 5} autres")
        return eleves_existants
    
    # Créer des élèves de test
    print("🆕 Création d'élèves de test...")
    
    eleves_test = [
        ('Aissatou', 'DIALLO', 'F'),
        ('Mamadou', 'BARRY', 'M'),
        ('Fatoumata', 'SOW', 'F'),
        ('Alpha', 'CONDE', 'M'),
        ('Mariama', 'CAMARA', 'F'),
        ('Ibrahima', 'TRAORE', 'M'),
        ('Kadiatou', 'BALDE', 'F'),
        ('Ousmane', 'DIAKITE', 'M'),
        ('Aminata', 'KEITA', 'F'),
        ('Sekou', 'TOURE', 'M'),
    ]
    
    eleves_crees = []
    
    # Créer un responsable de test d'abord
    from eleves.models import Responsable
    responsable, _ = Responsable.objects.get_or_create(
        nom='PARENT',
        prenom='Test',
        defaults={
            'telephone': '123456789',
            'profession': 'Test',
            'adresse': 'Adresse test'
        }
    )
    
    for i, (prenom, nom, sexe) in enumerate(eleves_test, 1):
        try:
            eleve, created = Eleve.objects.get_or_create(
                prenom=prenom,
                nom=nom,
                classe=classe_eleve,
                defaults={
                    'sexe': sexe,
                    'statut': 'ACTIF',
                    'date_naissance': '2006-01-01',
                    'lieu_naissance': 'Conakry',
                    'date_inscription': '2024-09-01',
                    'matricule': f'11L{i:03d}',
                    'responsable_principal': responsable,
                }
            )
            eleves_crees.append(eleve)
            if created:
                print(f"   ✅ {prenom} {nom}")
        except Exception as e:
            print(f"   ❌ Erreur pour {prenom} {nom}: {e}")
    
    return eleves_crees

def generer_notes_realistes(eleves, evaluations):
    """Générer des notes réalistes pour les élèves"""
    print(f"\n📊 GÉNÉRATION NOTES RÉALISTES")
    print("-" * 30)
    
    notes_creees = 0
    
    # Définir des profils d'élèves (excellent, bon, moyen, faible)
    profils = {
        'excellent': (15, 19),  # Notes entre 15 et 19
        'bon': (12, 16),        # Notes entre 12 et 16
        'moyen': (8, 14),       # Notes entre 8 et 14
        'faible': (5, 11),      # Notes entre 5 et 11
    }
    
    # Assigner un profil à chaque élève
    eleves_profils = {}
    profils_liste = list(profils.keys())
    
    for i, eleve in enumerate(eleves):
        # Distribution: 20% excellent, 30% bon, 35% moyen, 15% faible
        if i % 10 < 2:
            profil = 'excellent'
        elif i % 10 < 5:
            profil = 'bon'
        elif i % 10 < 8:
            profil = 'moyen'
        else:
            profil = 'faible'
        
        eleves_profils[eleve.id] = profil
    
    print(f"👥 Profils assignés:")
    for profil in profils_liste:
        count = list(eleves_profils.values()).count(profil)
        print(f"   - {profil.capitalize()}: {count} élèves")
    
    # Générer les notes
    for eleve in eleves:
        profil = eleves_profils[eleve.id]
        min_note, max_note = profils[profil]
        
        for evaluation in evaluations:
            # Variation selon la matière pour plus de réalisme
            matiere_nom = evaluation.matiere.nom.lower()
            
            # Ajustement selon la matière pour série littéraire
            if 'français' in matiere_nom or 'philosophie' in matiere_nom:
                # Matières principales: notes légèrement meilleures
                bonus = 1
            elif 'mathématiques' in matiere_nom or 'physiques' in matiere_nom:
                # Matières scientifiques: notes légèrement plus faibles
                bonus = -1
            else:
                bonus = 0
            
            # Générer la note avec variation
            note_base = random.uniform(min_note, max_note)
            note_finale = max(0, min(20, note_base + bonus + random.uniform(-1, 1)))
            note_finale = round(note_finale, 2)
            
            # Quelques absences aléatoirement (5% de chance)
            absent = random.random() < 0.05
            
            note_obj, created = NoteEleve.objects.get_or_create(
                eleve=eleve,
                evaluation=evaluation,
                defaults={
                    'note': None if absent else note_finale,
                    'absent': absent,
                }
            )
            
            if created:
                notes_creees += 1
    
    print(f"✅ {notes_creees} notes générées")
    return notes_creees

def ajouter_notes_11eme_litteraire():
    """Fonction principale pour ajouter les notes"""
    print("🎯 AJOUT NOTES 11ÈME SÉRIE LITTÉRAIRE 2024-2025")
    print("=" * 55)
    
    # 1. Identifier la classe
    classes_notes, classes_eleves, classes_lettres = identifier_classe_11eme_litteraire()
    
    # Utiliser la classe élève existante ou la première trouvée
    classe_eleve = None
    if classes_eleves.exists():
        classe_eleve = classes_eleves.first()
    elif classes_lettres.exists():
        classe_eleve = classes_lettres.first()
    
    if not classe_eleve:
        print("❌ Aucune classe 11ème littéraire trouvée")
        return
    
    print(f"\n🎯 Classe sélectionnée: {classe_eleve.nom} (ID: {classe_eleve.id})")
    
    # 2. Créer ou vérifier la ClasseNote
    classe_note = creer_ou_completer_classe_note(classe_eleve)
    
    # 3. Créer les matières
    matieres = creer_matieres_litteraires(classe_note)
    
    # 4. Créer les évaluations
    evaluations = creer_evaluations_periodes(matieres, classe_note)
    
    # 5. Créer/vérifier les élèves
    eleves = creer_eleves_test(classe_eleve)
    
    # 6. Générer les notes
    if eleves:
        notes_count = generer_notes_realistes(eleves, evaluations)
    else:
        notes_count = 0
    
    # 7. Résumé final
    print(f"\n📊 RÉSUMÉ FINAL")
    print("=" * 20)
    print(f"✅ ClasseNote: {classe_note.nom} (ID: {classe_note.id})")
    print(f"✅ ClasseEleve: {classe_eleve.nom} (ID: {classe_eleve.id})")
    print(f"✅ Matières: {len(matieres)}")
    print(f"✅ Évaluations: {len(evaluations)}")
    print(f"✅ Élèves: {len(eleves) if eleves else 0}")
    print(f"✅ Notes: {notes_count}")
    
    if notes_count > 0:
        print(f"\n🎉 SUCCÈS ! Notes ajoutées pour la 11ème série littéraire")
        print(f"🔗 URL de consultation: http://127.0.0.1:8000/notes/consulter/?classe_id={classe_note.id}&periode=OCTOBRE")
    else:
        print(f"\n⚠️  Problème lors de la création des notes")

if __name__ == "__main__":
    try:
        ajouter_notes_11eme_litteraire()
    except Exception as e:
        print(f"❌ Erreur: {e}")
        import traceback
        traceback.print_exc()
