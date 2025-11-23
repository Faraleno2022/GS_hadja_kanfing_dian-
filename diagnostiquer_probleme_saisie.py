#!/usr/bin/env python
"""
Diagnostiquer le problème d'affichage des élèves dans la saisie de notes
"""
import os
import sys
import django

# Configuration Django
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ecole_moderne.settings')
django.setup()

from notes.models import ClasseNote, MatiereNote, Evaluation, NoteEleve
from eleves.models import Classe as ClasseEleve, Eleve

def diagnostiquer_probleme_saisie():
    """Diagnostiquer pourquoi les élèves ne s'affichent pas"""
    print("🔍 DIAGNOSTIC PROBLÈME SAISIE NOTES")
    print("=" * 40)
    
    # 1. Vérifier la classe 59
    classe_note = ClasseNote.objects.get(pk=59)
    print(f"✅ ClasseNote 59: {classe_note.nom}")
    
    # 2. Vérifier la matière 134 (Anglais)
    try:
        matiere = MatiereNote.objects.get(pk=134)
        print(f"✅ Matière 134: {matiere.nom} (classe: {matiere.classe.nom})")
    except MatiereNote.DoesNotExist:
        print("❌ Matière 134 n'existe pas")
        return
    
    # 3. Vérifier la ClasseEleve correspondante
    mapping_classes = {59: 8}
    classe_eleve_id = mapping_classes.get(59)
    
    if classe_eleve_id:
        classe_eleve = ClasseEleve.objects.get(pk=classe_eleve_id)
        print(f"✅ ClasseEleve {classe_eleve_id}: {classe_eleve.nom}")
    else:
        print("❌ Pas de mapping pour la classe 59")
        return
    
    # 4. Vérifier les élèves
    eleves = Eleve.objects.filter(classe=classe_eleve, statut='ACTIF')
    print(f"👥 Élèves actifs dans ClasseEleve {classe_eleve_id}: {eleves.count()}")
    
    for eleve in eleves[:5]:
        print(f"   - {eleve.matricule}: {eleve.prenom} {eleve.nom}")
    
    # 5. Vérifier les évaluations OCTOBRE pour cette matière
    evaluations = Evaluation.objects.filter(
        matiere=matiere,
        periode='OCTOBRE'
    )
    print(f"📝 Évaluations OCTOBRE pour {matiere.nom}: {evaluations.count()}")
    
    for eval in evaluations:
        print(f"   - {eval.titre} (ID: {eval.id})")
    
    # 6. Vérifier les notes existantes
    notes_existantes = NoteEleve.objects.filter(
        evaluation__matiere=matiere,
        evaluation__periode='OCTOBRE'
    )
    print(f"📊 Notes existantes: {notes_existantes.count()}")
    
    # 7. Analyser les notes par élève
    print(f"\n🔍 ANALYSE DES NOTES PAR ÉLÈVE:")
    eleves_avec_notes = set()
    
    for note in notes_existantes:
        eleve = note.eleve
        eleves_avec_notes.add(eleve.id)
        print(f"   - Note ID {note.id}: Élève {eleve.id} ({eleve.prenom} {eleve.nom}) - Classe {eleve.classe.id}")
    
    print(f"\n📊 RÉSUMÉ:")
    print(f"   - Élèves dans ClasseEleve {classe_eleve_id}: {eleves.count()}")
    print(f"   - Élèves avec des notes: {len(eleves_avec_notes)}")
    print(f"   - Notes totales: {notes_existantes.count()}")
    
    # 8. Vérifier si les élèves avec notes sont dans la bonne classe
    print(f"\n🔍 VÉRIFICATION COHÉRENCE:")
    
    problemes = []
    for note in notes_existantes[:5]:  # Vérifier les 5 premières
        eleve = note.eleve
        if eleve.classe.id != classe_eleve_id:
            problemes.append(f"Élève {eleve.prenom} {eleve.nom} est dans classe {eleve.classe.id} au lieu de {classe_eleve_id}")
    
    if problemes:
        print("❌ PROBLÈMES DÉTECTÉS:")
        for probleme in problemes:
            print(f"   - {probleme}")
    else:
        print("✅ Cohérence OK")
    
    # 9. Simuler la logique de la vue saisir_notes
    print(f"\n🧪 SIMULATION VUE SAISIR_NOTES:")
    
    # Récupérer les élèves comme le fait la vue
    eleves_vue = Eleve.objects.filter(
        classe__classenote=classe_note,  # Utilise la relation inverse
        statut='ACTIF'
    ).order_by('prenom', 'nom')
    
    print(f"👥 Élèves trouvés par la vue: {eleves_vue.count()}")
    
    if eleves_vue.count() == 0:
        print("❌ PROBLÈME: La vue ne trouve aucun élève")
        print("   Cause probable: Pas de relation ClasseEleve -> ClasseNote")
        
        # Vérifier la relation inverse
        try:
            classe_note_from_eleve = classe_eleve.classenote
            print(f"   ClasseNote liée à ClasseEleve {classe_eleve_id}: {classe_note_from_eleve}")
        except:
            print(f"   ❌ Aucune ClasseNote liée à ClasseEleve {classe_eleve_id}")
            print(f"   💡 SOLUTION: Créer la relation ou modifier la logique de la vue")
    else:
        print("✅ La vue trouve les élèves correctement")

def proposer_solution():
    """Proposer une solution au problème"""
    print(f"\n💡 SOLUTIONS POSSIBLES:")
    print("=" * 25)
    
    print("1️⃣ SOLUTION RAPIDE - Modifier la vue saisir_notes")
    print("   Remplacer la logique de récupération des élèves")
    print("   Au lieu de: classe__classenote=classe_note")
    print("   Utiliser le mapping comme dans consulter_notes")
    
    print("\n2️⃣ SOLUTION PROPRE - Créer la relation manquante")
    print("   Ajouter un champ classe_eleve dans ClasseNote")
    print("   Ou utiliser le mapping existant")
    
    print("\n3️⃣ SOLUTION IMMÉDIATE - Corriger les données")
    print("   Réassigner les élèves à la bonne classe")
    print("   Ou créer les relations manquantes")

if __name__ == "__main__":
    try:
        diagnostiquer_probleme_saisie()
        proposer_solution()
    except Exception as e:
        print(f"❌ Erreur: {e}")
        import traceback
        traceback.print_exc()
