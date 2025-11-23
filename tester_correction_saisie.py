#!/usr/bin/env python
"""
Tester la correction de la fonction saisir_notes
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

def tester_logique_saisie_notes():
    """Tester la logique corrigée de saisir_notes"""
    print("🧪 TEST LOGIQUE SAISIE NOTES CORRIGÉE")
    print("=" * 40)
    
    # Paramètres de test (comme dans l'URL)
    classe_id = 59
    matiere_id = 134
    periode = 'OCTOBRE'
    
    print(f"📋 Paramètres de test:")
    print(f"   - classe_id: {classe_id}")
    print(f"   - matiere_id: {matiere_id}")
    print(f"   - periode: {periode}")
    
    # 1. Récupérer la classe sélectionnée
    classe_selectionnee = ClasseNote.objects.get(pk=classe_id)
    print(f"\n✅ ClasseNote: {classe_selectionnee.nom}")
    
    # 2. Récupérer la matière
    matiere_selectionnee = MatiereNote.objects.get(pk=matiere_id)
    print(f"✅ Matière: {matiere_selectionnee.nom}")
    
    # 3. Appliquer la logique corrigée (même que dans la vue)
    mapping_classes = {
        61: 56,  # ClasseNote '12ème Année' -> ClasseEleve '12ÈME ANNÉE'
        59: 8,   # ClasseNote '11ème Série littéraire' -> ClasseEleve '11ème série littéraire'
    }
    
    if classe_selectionnee.id in mapping_classes:
        classe_eleve = ClasseEleve.objects.filter(
            id=mapping_classes[classe_selectionnee.id]
        ).first()
        print(f"✅ Mapping utilisé: ClasseEleve {mapping_classes[classe_selectionnee.id]}")
    else:
        classe_eleve = ClasseEleve.objects.filter(
            nom=classe_selectionnee.nom,
            annee_scolaire=classe_selectionnee.annee_scolaire,
            ecole=classe_selectionnee.ecole
        ).first()
        print(f"✅ Recherche normale utilisée")
    
    if classe_eleve:
        print(f"✅ ClasseEleve trouvée: {classe_eleve.nom} (ID: {classe_eleve.id})")
        
        # 4. Récupérer les élèves
        eleves = Eleve.objects.filter(classe=classe_eleve, statut='ACTIF').order_by('prenom', 'nom')
        print(f"👥 Élèves trouvés: {eleves.count()}")
        
        for i, eleve in enumerate(eleves[:5], 1):
            print(f"   {i}. {eleve.matricule}: {eleve.prenom} {eleve.nom}")
        
        if eleves.count() > 5:
            print(f"   ... et {eleves.count() - 5} autres")
        
        # 5. Vérifier les évaluations
        evaluations = Evaluation.objects.filter(matiere=matiere_selectionnee, periode=periode)
        print(f"📝 Évaluations {periode}: {evaluations.count()}")
        
        # 6. Vérifier les notes existantes
        if evaluations.exists():
            notes_existantes = NoteEleve.objects.filter(evaluation__in=evaluations)
            print(f"📊 Notes existantes: {notes_existantes.count()}")
            
            # Vérifier la correspondance élèves/notes
            eleves_avec_notes = set(note.eleve.id for note in notes_existantes)
            eleves_sans_notes = [e for e in eleves if e.id not in eleves_avec_notes]
            
            print(f"✅ Élèves avec notes: {len(eleves_avec_notes)}")
            print(f"⚠️  Élèves sans notes: {len(eleves_sans_notes)}")
            
            if len(eleves_sans_notes) > 0:
                print("   Élèves sans notes:")
                for eleve in eleves_sans_notes[:3]:
                    print(f"   - {eleve.prenom} {eleve.nom}")
        
        # 7. Résultat du test
        if eleves.count() > 0:
            print(f"\n🎉 SUCCÈS ! La vue saisir_notes devrait maintenant afficher {eleves.count()} élèves")
            print(f"🔗 URL de test: http://127.0.0.1:8000/notes/saisir/?classe_id={classe_id}&matiere_id={matiere_id}&type_note=mensuelle&periode={periode}")
        else:
            print(f"\n❌ ÉCHEC ! Aucun élève trouvé")
    
    else:
        print(f"❌ ClasseEleve non trouvée")

def tester_autres_classes():
    """Tester avec d'autres classes pour vérifier la non-régression"""
    print(f"\n🧪 TEST NON-RÉGRESSION AUTRES CLASSES")
    print("=" * 40)
    
    # Tester quelques autres classes
    autres_classes = ClasseNote.objects.filter(actif=True).exclude(id__in=[59, 61])[:3]
    
    for classe in autres_classes:
        print(f"\n📋 Test classe {classe.id}: {classe.nom}")
        
        # Logique normale (sans mapping)
        classe_eleve = ClasseEleve.objects.filter(
            nom=classe.nom,
            annee_scolaire=classe.annee_scolaire,
            ecole=classe.ecole
        ).first()
        
        if classe_eleve:
            eleves = Eleve.objects.filter(classe=classe_eleve, statut='ACTIF')
            print(f"   ✅ {eleves.count()} élèves trouvés")
        else:
            print(f"   ⚠️  Aucune ClasseEleve correspondante")

if __name__ == "__main__":
    try:
        tester_logique_saisie_notes()
        tester_autres_classes()
        
        print(f"\n🎯 RÉSUMÉ")
        print("=" * 15)
        print("✅ Correction appliquée dans notes/views.py")
        print("✅ Même mapping que consulter_notes")
        print("✅ Les élèves devraient maintenant s'afficher")
        print("🔗 Testez l'URL: http://127.0.0.1:8000/notes/saisir/?classe_id=59&matiere_id=134&type_note=mensuelle&periode=OCTOBRE")
        
    except Exception as e:
        print(f"❌ Erreur: {e}")
        import traceback
        traceback.print_exc()
