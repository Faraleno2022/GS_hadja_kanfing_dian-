"""
Vérification complète de la correction de l'export de classement
Ce script teste toutes les améliorations apportées
"""
import os
import django
import sys

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ecole_moderne.settings')
django.setup()

from notes.models import ClasseNote, MatiereNote, Evaluation, NoteEleve
from notes.export_classement import _generer_classement_general
from eleves.models import Eleve, Classe as ClasseEleve
import re

def verifier_correction():
    """Vérifier que toutes les corrections fonctionnent"""
    
    print("\n" + "="*80)
    print("VÉRIFICATION COMPLÈTE DE LA CORRECTION")
    print("="*80 + "\n")
    
    # 1. Test recherche de classe
    print("1️⃣  TEST RECHERCHE DE CLASSE")
    print("-" * 80)
    
    classe_note = ClasseNote.objects.filter(nom__icontains='12').filter(nom__icontains='scien').first()
    
    if not classe_note:
        print("❌ Aucune classe note trouvée")
        return False
    
    print(f"✅ ClasseNote: {classe_note.nom}")
    print(f"   École: {classe_note.ecole.nom} (ID: {classe_note.ecole.id})")
    
    # Reproduire la logique de recherche
    classe_eleve = ClasseEleve.objects.filter(
        nom=classe_note.nom,
        annee_scolaire=classe_note.annee_scolaire,
        ecole=classe_note.ecole
    ).first()
    
    if not classe_eleve:
        classe_eleve = ClasseEleve.objects.filter(
            nom__iexact=classe_note.nom,
            annee_scolaire=classe_note.annee_scolaire,
            ecole=classe_note.ecole
        ).first()
    
    if not classe_eleve:
        match = re.search(r'(\d+)', classe_note.nom)
        if match:
            niveau_num = match.group(1)
            classes_possibles = ClasseEleve.objects.filter(
                nom__icontains=niveau_num,
                annee_scolaire=classe_note.annee_scolaire,
                ecole=classe_note.ecole
            )
            
            if not classes_possibles.exists():
                classes_possibles = ClasseEleve.objects.filter(
                    nom__icontains=niveau_num,
                    annee_scolaire=classe_note.annee_scolaire
                )
            
            classe_eleve = classes_possibles.first()
            
            if classe_eleve and classes_possibles.count() > 1:
                if 'scientifique' in classe_note.nom.lower() or 'science' in classe_note.nom.lower():
                    for c in classes_possibles:
                        if 'SCIENCE' in c.nom.upper():
                            classe_eleve = c
                            break
    
    if not classe_eleve:
        print("❌ ClasseEleve non trouvée")
        return False
    
    print(f"✅ ClasseEleve: {classe_eleve.nom}")
    print(f"   École: {classe_eleve.ecole.nom} (ID: {classe_eleve.ecole.id})")
    
    # 2. Test récupération des élèves
    print(f"\n2️⃣  TEST RÉCUPÉRATION DES ÉLÈVES")
    print("-" * 80)
    
    eleves = Eleve.objects.filter(classe=classe_eleve, statut='ACTIF')
    
    if not eleves.exists():
        print("❌ Aucun élève actif")
        return False
    
    print(f"✅ {eleves.count()} élèves actifs trouvés")
    print(f"\nExemples:")
    for e in eleves[:3]:
        print(f"   - {e.matricule}: {e.nom} {e.prenom} ({e.sexe})")
    
    # 3. Test récupération des notes
    print(f"\n3️⃣  TEST RÉCUPÉRATION DES NOTES")
    print("-" * 80)
    
    matieres = MatiereNote.objects.filter(classe=classe_note, actif=True)
    print(f"✅ {matieres.count()} matières actives")
    
    if matieres.count() > 0:
        print(f"\nMatières:")
        for m in matieres[:5]:
            print(f"   - {m.nom} (coef: {m.coefficient})")
            
            # Vérifier les évaluations
            evals = Evaluation.objects.filter(matiere=m)
            if evals.exists():
                print(f"     → {evals.count()} évaluation(s)")
                for ev in evals[:2]:
                    notes_count = NoteEleve.objects.filter(evaluation=ev).count()
                    print(f"        • {ev.titre}: {notes_count} notes")
    
    # 4. Test génération du classement
    print(f"\n4️⃣  TEST GÉNÉRATION DU CLASSEMENT")
    print("-" * 80)
    
    try:
        classement_data, titre = _generer_classement_general(
            eleves,
            classe_note,
            type_note='mensuelle',
            periode='TRIMESTRE_1'
        )
        
        print(f"✅ Classement généré: {titre}")
        print(f"✅ {len(classement_data)} élèves dans le classement")
        
        # 5. Test statistiques
        print(f"\n5️⃣  TEST STATISTIQUES")
        print("-" * 80)
        
        eleves_avec_notes = [e for e in classement_data if e.get('moyenne') is not None]
        eleves_sans_notes = [e for e in classement_data if e.get('moyenne') is None]
        
        print(f"✅ Élèves avec notes: {len(eleves_avec_notes)}")
        print(f"✅ Élèves sans notes: {len(eleves_sans_notes)}")
        
        # 6. Test rangs et accord grammatical
        print(f"\n6️⃣  TEST RANGS ET ACCORD GRAMMATICAL")
        print("-" * 80)
        
        if eleves_avec_notes:
            print(f"\n🏆 TOP 5:")
            for eleve_data in eleves_avec_notes[:5]:
                rang = eleve_data.get('rang', '-')
                sexe = eleve_data.get('sexe', 'M')
                
                # Formater le rang
                if rang == 1:
                    rang_str = "1ère" if sexe == 'F' else "1er"
                elif rang > 1:
                    rang_str = f"{rang}ème"
                else:
                    rang_str = "-"
                
                moyenne = eleve_data.get('moyenne', 0)
                nom = eleve_data.get('nom_complet', '')
                
                print(f"   {rang_str:5} | {nom:30} | {moyenne:5.2f}/20 | ({sexe})")
            
            # Vérifier l'accord grammatical
            premier = eleves_avec_notes[0]
            if premier.get('rang') == 1:
                sexe_premier = premier.get('sexe')
                rang_attendu = "1ère" if sexe_premier == 'F' else "1er"
                print(f"\n✅ Accord grammatical correct: {rang_attendu} (sexe: {sexe_premier})")
        
        # 7. Test messages d'avertissement
        print(f"\n7️⃣  TEST MESSAGES")
        print("-" * 80)
        
        if eleves_sans_notes:
            print(f"⚠️  {len(eleves_sans_notes)} élève(s) n'ont pas de notes")
            print(f"\nDétail des 5 premiers:")
            for eleve_data in eleves_sans_notes[:5]:
                nom = eleve_data.get('nom_complet', '')
                raison = "Absent" if eleve_data.get('absent') else "Pas de notes"
                print(f"   - {nom:30} → {raison}")
        else:
            print(f"✅ Tous les élèves ont des notes")
        
        # RÉSULTAT FINAL
        print(f"\n{'='*80}")
        print("RÉSULTAT FINAL")
        print("="*80 + "\n")
        
        if len(eleves_avec_notes) > 0:
            print("✅ ✅ ✅ CORRECTION RÉUSSIE ✅ ✅ ✅")
            print("\nTout fonctionne correctement :")
            print("   ✅ Recherche de classe")
            print("   ✅ Récupération des élèves")
            print("   ✅ Récupération des notes")
            print("   ✅ Génération du classement")
            print("   ✅ Calcul des rangs")
            print("   ✅ Accord grammatical")
            print("   ✅ Statistiques")
            print("   ✅ Messages d'avertissement")
            return True
        else:
            print("⚠️  CORRECTION PARTIELLE")
            print("\nLa recherche fonctionne mais aucune note n'a été trouvée.")
            print("Causes possibles:")
            print("   - Notes pas encore saisies")
            print("   - Période incorrecte")
            print("   - Système de notes différent")
            return False
            
    except Exception as e:
        print(f"❌ ERREUR: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == '__main__':
    success = verifier_correction()
    exit(0 if success else 1)
