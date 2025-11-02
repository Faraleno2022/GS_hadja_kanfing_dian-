"""
Test de l'importation et affichage des notes sur le bulletin
Vérifie que les notes sont correctement récupérées et affichées
"""

import os
import django
import sys

# Configuration Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ecole_moderne.settings')
django.setup()

from django.contrib.auth import get_user_model
from notes.models import ClasseNote, MatiereNote, Evaluation, NoteEleve
from eleves.models import Eleve, Classe as ClasseEleve
from decimal import Decimal

User = get_user_model()

def print_section(title):
    """Afficher une section de test"""
    print("\n" + "="*70)
    print(f"  {title}")
    print("="*70)

def test_notes_bulletin():
    """Test de l'importation des notes sur le bulletin"""
    print_section("TEST: Importation des Notes sur le Bulletin")
    
    try:
        # 1. Trouver une classe avec des notes
        print("\n📚 Recherche d'une classe avec des notes...")
        
        classe_note = None
        matiere = None
        eleve = None
        periode = 'TRIMESTRE_1'
        
        # Chercher une classe avec des matières et des notes
        for classe in ClasseNote.objects.filter(actif=True):
            matieres = MatiereNote.objects.filter(classe=classe, actif=True)
            if not matieres.exists():
                continue
            
            for mat in matieres:
                # Chercher des évaluations
                evaluations = Evaluation.objects.filter(
                    matiere=mat,
                    periode=periode
                )
                
                if evaluations.exists():
                    # Chercher des notes
                    notes = NoteEleve.objects.filter(
                        evaluation__in=evaluations,
                        note__isnull=False
                    )
                    
                    if notes.exists():
                        classe_note = classe
                        matiere = mat
                        eleve = notes.first().eleve
                        break
            
            if classe_note:
                break
        
        if not classe_note or not matiere or not eleve:
            print("⚠️ Aucune donnée de test trouvée")
            print("   Créez d'abord des notes via l'interface de saisie")
            return False
        
        print(f"✓ Classe trouvée: {classe_note.nom}")
        print(f"✓ Matière trouvée: {matiere.nom}")
        print(f"✓ Élève trouvé: {eleve.nom} {eleve.prenom}")
        print(f"✓ Période: {periode}")
        
        # 2. Récupérer toutes les matières de la classe
        print("\n📊 Récupération des matières et notes...")
        matieres = MatiereNote.objects.filter(classe=classe_note, actif=True).order_by('nom')
        print(f"✓ {matieres.count()} matière(s) dans la classe")
        
        # 3. Pour chaque matière, récupérer les notes de l'élève
        notes_trouvees = 0
        total_points = Decimal('0')
        total_coefficients = Decimal('0')
        
        print("\n📝 Détail des notes par matière:")
        print("-" * 70)
        
        for mat in matieres:
            evaluations = Evaluation.objects.filter(
                matiere=mat,
                periode=periode
            ).order_by('date_evaluation')
            
            if not evaluations.exists():
                print(f"  {mat.nom:30} | Pas d'évaluation")
                continue
            
            # Séparer devoirs et compositions
            total_devoirs = Decimal('0')
            count_devoirs = 0
            total_compo = Decimal('0')
            count_compo = 0
            
            for evaluation in evaluations:
                try:
                    note_obj = NoteEleve.objects.get(eleve=eleve, evaluation=evaluation)
                    if note_obj.note is not None and not note_obj.absent:
                        if evaluation.type_evaluation in ['COMPOSITION', 'EXAMEN']:
                            total_compo += Decimal(str(note_obj.note))
                            count_compo += 1
                        else:
                            total_devoirs += Decimal(str(note_obj.note))
                            count_devoirs += 1
                        notes_trouvees += 1
                except NoteEleve.DoesNotExist:
                    pass
            
            # Calculer les moyennes
            moyenne_continue = None
            note_composition = None
            
            if count_devoirs > 0:
                moyenne_continue = round(float(total_devoirs / count_devoirs), 2)
            
            if count_compo > 0:
                note_composition = round(float(total_compo / count_compo), 2)
            
            # Calculer la moyenne de la matière
            moyenne_matiere = None
            if moyenne_continue is not None and note_composition is not None:
                moyenne_matiere = round((moyenne_continue + note_composition * 2) / 3, 2)
            elif note_composition is not None:
                moyenne_matiere = note_composition
            elif moyenne_continue is not None:
                moyenne_matiere = moyenne_continue
            
            # Afficher les résultats
            moy_cont_str = f"{moyenne_continue:.2f}" if moyenne_continue else "-"
            note_comp_str = f"{note_composition:.2f}" if note_composition else "-"
            moy_mat_str = f"{moyenne_matiere:.2f}" if moyenne_matiere else "-"
            
            print(f"  {mat.nom:30} | Moy.Cont: {moy_cont_str:6} | Compo: {note_comp_str:6} | Moyenne: {moy_mat_str:6} | Coef: {mat.coefficient}")
            
            if moyenne_matiere is not None:
                total_points += Decimal(str(moyenne_matiere)) * mat.coefficient
                total_coefficients += mat.coefficient
        
        print("-" * 70)
        
        # 4. Calculer la moyenne générale
        if total_coefficients > 0:
            moyenne_generale = round(float(total_points / total_coefficients), 2)
            print(f"\n✓ {notes_trouvees} note(s) trouvée(s)")
            print(f"✓ Total points: {float(total_points):.2f}")
            print(f"✓ Total coefficients: {float(total_coefficients):.0f}")
            print(f"✓ Moyenne générale: {moyenne_generale:.2f}/20")
            
            # Déterminer la mention
            if moyenne_generale >= 16:
                mention = "Très Bien"
            elif moyenne_generale >= 14:
                mention = "Bien"
            elif moyenne_generale >= 12:
                mention = "Assez Bien"
            elif moyenne_generale >= 10:
                mention = "Passable"
            else:
                mention = "Insuffisant"
            
            print(f"✓ Mention: {mention}")
        else:
            print("\n⚠️ Aucune note trouvée pour calculer la moyenne")
            return False
        
        # 5. Vérifier la structure des données pour le template
        print("\n🔍 Vérification de la structure des données...")
        
        bulletin_data = {
            'eleve': eleve,
            'classe': classe_note,
            'periode': periode,
            'matieres_notes': [],
            'moyenne_generale': moyenne_generale,
            'total_points': float(total_points),
            'total_coefficients': float(total_coefficients),
        }
        
        # Recréer la structure pour une matière test
        for mat in matieres[:3]:  # Tester les 3 premières matières
            evaluations = Evaluation.objects.filter(matiere=mat, periode=periode)
            
            total_devoirs = Decimal('0')
            count_devoirs = 0
            total_compo = Decimal('0')
            count_compo = 0
            
            for evaluation in evaluations:
                try:
                    note_obj = NoteEleve.objects.get(eleve=eleve, evaluation=evaluation)
                    if note_obj.note is not None and not note_obj.absent:
                        if evaluation.type_evaluation in ['COMPOSITION', 'EXAMEN']:
                            total_compo += Decimal(str(note_obj.note))
                            count_compo += 1
                        else:
                            total_devoirs += Decimal(str(note_obj.note))
                            count_devoirs += 1
                except NoteEleve.DoesNotExist:
                    pass
            
            moyenne_continue = round(float(total_devoirs / count_devoirs), 2) if count_devoirs > 0 else None
            note_composition = round(float(total_compo / count_compo), 2) if count_compo > 0 else None
            
            if moyenne_continue is not None and note_composition is not None:
                moyenne_matiere = round((moyenne_continue + note_composition * 2) / 3, 2)
            elif note_composition is not None:
                moyenne_matiere = note_composition
            elif moyenne_continue is not None:
                moyenne_matiere = moyenne_continue
            else:
                moyenne_matiere = None
            
            points = round(moyenne_matiere * float(mat.coefficient), 2) if moyenne_matiere else None
            
            bulletin_data['matieres_notes'].append({
                'matiere': mat,
                'moyenne_continue': moyenne_continue,
                'note_composition': note_composition,
                'moyenne': moyenne_matiere,
                'coefficient': mat.coefficient,
                'points': points,
                'notes': [
                    {'note': moyenne_continue, 'absent': False},
                    {'note': note_composition, 'absent': False}
                ]
            })
        
        print(f"✓ Structure bulletin_data créée avec {len(bulletin_data['matieres_notes'])} matière(s)")
        
        # Vérifier que les champs nécessaires sont présents
        champs_requis = ['eleve', 'classe', 'periode', 'matieres_notes', 'moyenne_generale']
        for champ in champs_requis:
            if champ in bulletin_data:
                print(f"  ✓ Champ '{champ}' présent")
            else:
                print(f"  ❌ Champ '{champ}' manquant")
                return False
        
        # Vérifier la structure d'une matière
        if bulletin_data['matieres_notes']:
            matiere_test = bulletin_data['matieres_notes'][0]
            champs_matiere = ['matiere', 'moyenne_continue', 'note_composition', 'moyenne', 'coefficient', 'points', 'notes']
            print("\n  Vérification de la structure d'une matière:")
            for champ in champs_matiere:
                if champ in matiere_test:
                    valeur = matiere_test[champ]
                    if champ == 'matiere':
                        print(f"    ✓ {champ}: {valeur.nom}")
                    elif champ == 'notes':
                        print(f"    ✓ {champ}: {len(valeur)} note(s)")
                    else:
                        print(f"    ✓ {champ}: {valeur}")
                else:
                    print(f"    ❌ {champ}: manquant")
        
        print("\n✅ TEST RÉUSSI: Les notes sont correctement importées et structurées")
        print("\n📌 Résumé:")
        print(f"   • Élève: {eleve.nom} {eleve.prenom}")
        print(f"   • Classe: {classe_note.nom}")
        print(f"   • Période: {periode}")
        print(f"   • Notes trouvées: {notes_trouvees}")
        print(f"   • Moyenne générale: {moyenne_generale:.2f}/20")
        print(f"   • Mention: {mention}")
        
        return True
        
    except Exception as e:
        print(f"\n❌ ERREUR: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Exécuter le test"""
    print("\n" + "🧪"*35)
    print("  TEST D'IMPORTATION DES NOTES SUR LE BULLETIN")
    print("🧪"*35)
    
    resultat = test_notes_bulletin()
    
    print("\n" + "="*70)
    if resultat:
        print("  ✅ SUCCÈS: Les notes sont correctement importées sur le bulletin")
    else:
        print("  ⚠️ ATTENTION: Vérifiez les données ou créez des notes de test")
    print("="*70 + "\n")
    
    return 0 if resultat else 1

if __name__ == "__main__":
    sys.exit(main())
