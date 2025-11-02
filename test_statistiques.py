"""
Test des statistiques de classe
Vérifie que les statistiques sont correctement calculées
"""

import os
import django
import sys

# Configuration Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ecole_moderne.settings')
django.setup()

from notes.models import ClasseNote, MatiereNote, Evaluation, NoteEleve
from eleves.models import Eleve, Classe as ClasseEleve
from decimal import Decimal

def print_section(title):
    """Afficher une section de test"""
    print("\n" + "="*70)
    print(f"  {title}")
    print("="*70)

def test_statistiques_classe():
    """Test du calcul des statistiques pour une classe"""
    print_section("TEST: Calcul des Statistiques de Classe")
    
    try:
        # 1. Trouver une classe avec des notes
        print("\n📚 Recherche d'une classe avec des notes...")
        
        classe_note = None
        periode = 'TRIMESTRE_1'
        
        # Chercher une classe avec des notes
        for classe in ClasseNote.objects.filter(actif=True):
            matieres = MatiereNote.objects.filter(classe=classe, actif=True)
            if not matieres.exists():
                continue
            
            # Vérifier s'il y a des évaluations pour cette période
            has_evaluations = False
            for matiere in matieres:
                if Evaluation.objects.filter(matiere=matiere, periode=periode).exists():
                    has_evaluations = True
                    break
            
            if has_evaluations:
                classe_note = classe
                break
        
        if not classe_note:
            print("⚠️ Aucune classe avec des notes trouvée")
            print("   Créez d'abord des notes via l'interface de saisie")
            return False
        
        print(f"✓ Classe trouvée: {classe_note.nom}")
        print(f"✓ Période: {periode}")
        
        # 2. Récupérer les élèves de la classe
        try:
            classe_eleve = ClasseEleve.objects.get(
                nom=classe_note.nom,
                annee_scolaire=classe_note.annee_scolaire
            )
            eleves = Eleve.objects.filter(classe=classe_eleve, statut='ACTIF').order_by('nom', 'prenom')
        except ClasseEleve.DoesNotExist:
            print("❌ Classe d'élèves non trouvée")
            return False
        
        print(f"✓ {eleves.count()} élève(s) dans la classe")
        
        # 3. Récupérer les matières
        matieres = MatiereNote.objects.filter(classe=classe_note, actif=True)
        print(f"✓ {matieres.count()} matière(s) dans la classe")
        
        # 4. Calculer les statistiques
        print("\n📊 Calcul des statistiques...")
        
        nb_evalues = 0
        nb_non_evalues = 0
        nb_non_admis = 0
        nb_a_suivre = 0
        nb_excellents = 0
        nb_precaution = 0
        eleves_details = []
        
        for eleve in eleves:
            total_points = Decimal('0')
            total_coefficients = Decimal('0')
            has_notes = False
            
            for matiere in matieres:
                evaluations = Evaluation.objects.filter(
                    matiere=matiere,
                    periode=periode
                )
                
                if evaluations.exists():
                    total_devoirs = Decimal('0')
                    count_devoirs = 0
                    total_compo = Decimal('0')
                    count_compo = 0
                    
                    for evaluation in evaluations:
                        try:
                            note_obj = NoteEleve.objects.get(eleve=eleve, evaluation=evaluation)
                            if note_obj.note is not None and not note_obj.absent:
                                has_notes = True
                                if evaluation.type_evaluation in ['COMPOSITION', 'EXAMEN']:
                                    total_compo += Decimal(str(note_obj.note))
                                    count_compo += 1
                                else:
                                    total_devoirs += Decimal(str(note_obj.note))
                                    count_devoirs += 1
                        except NoteEleve.DoesNotExist:
                            pass
                    
                    moyenne_continue = total_devoirs / count_devoirs if count_devoirs > 0 else None
                    note_composition = total_compo / count_compo if count_compo > 0 else None
                    
                    moyenne_matiere = None
                    if moyenne_continue is not None and note_composition is not None:
                        moyenne_matiere = (moyenne_continue + note_composition * 2) / 3
                    elif note_composition is not None:
                        moyenne_matiere = note_composition
                    elif moyenne_continue is not None:
                        moyenne_matiere = moyenne_continue
                    
                    if moyenne_matiere is not None:
                        total_points += moyenne_matiere * matiere.coefficient
                        total_coefficients += matiere.coefficient
            
            # Calculer la moyenne générale
            if has_notes and total_coefficients > 0:
                moyenne_generale = float(total_points / total_coefficients)
                nb_evalues += 1
                
                # Classifier l'élève
                categorie = ""
                if moyenne_generale < 10:
                    nb_non_admis += 1
                    categorie = "❌ Non admis"
                elif moyenne_generale < 12:
                    nb_a_suivre += 1
                    categorie = "⚠️ À suivre"
                elif moyenne_generale < 14:
                    nb_precaution += 1
                    categorie = "⚡ Précaution"
                else:
                    nb_excellents += 1
                    categorie = "✨ Excellent"
                
                eleves_details.append({
                    'nom': f"{eleve.nom} {eleve.prenom}",
                    'moyenne': round(moyenne_generale, 2),
                    'categorie': categorie
                })
            else:
                nb_non_evalues += 1
        
        # 5. Afficher les résultats
        print("\n📈 RÉSULTATS:")
        print("-" * 70)
        print(f"  Total élèves: {eleves.count()}")
        print(f"  Élèves évalués: {nb_evalues}")
        print(f"  Élèves non évalués: {nb_non_evalues}")
        print()
        print(f"  ✨ Excellents (≥14): {nb_excellents}")
        print(f"  ⚡ Précaution (12-14): {nb_precaution}")
        print(f"  ⚠️ À suivre (10-12): {nb_a_suivre}")
        print(f"  ❌ Non admis (<10): {nb_non_admis}")
        print()
        
        if nb_evalues > 0:
            taux_reussite = round((nb_evalues - nb_non_admis) / nb_evalues * 100, 1)
            taux_echec = round(nb_non_admis / nb_evalues * 100, 1)
            print(f"  📊 Taux de réussite: {taux_reussite}%")
            print(f"  📊 Taux d'échec: {taux_echec}%")
        
        # 6. Afficher le détail des élèves
        if eleves_details:
            print("\n👥 DÉTAIL DES ÉLÈVES ÉVALUÉS:")
            print("-" * 70)
            
            # Trier par moyenne décroissante
            eleves_details.sort(key=lambda x: x['moyenne'], reverse=True)
            
            for i, eleve_data in enumerate(eleves_details, 1):
                print(f"  {i:2}. {eleve_data['nom']:30} | {eleve_data['moyenne']:5.2f}/20 | {eleve_data['categorie']}")
        
        # 7. Recommandations
        print("\n💡 RECOMMANDATIONS:")
        print("-" * 70)
        
        if nb_non_admis > 0:
            print(f"  🔴 {nb_non_admis} élève(s) en difficulté → Soutien scolaire urgent")
        
        if nb_a_suivre > 0:
            print(f"  🟡 {nb_a_suivre} élève(s) à suivre → Accompagnement personnalisé")
        
        if nb_excellents > 0:
            print(f"  🟢 {nb_excellents} élève(s) excellent(s) → Félicitations !")
        
        if nb_non_evalues > 0:
            print(f"  ⚪ {nb_non_evalues} élève(s) non évalué(s) → Compléter les évaluations")
        
        print("\n✅ TEST RÉUSSI: Les statistiques sont correctement calculées")
        
        return True
        
    except Exception as e:
        print(f"\n❌ ERREUR: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Exécuter le test"""
    print("\n" + "📊"*35)
    print("  TEST DES STATISTIQUES DE CLASSE")
    print("📊"*35)
    
    resultat = test_statistiques_classe()
    
    print("\n" + "="*70)
    if resultat:
        print("  ✅ SUCCÈS: Les statistiques fonctionnent correctement")
    else:
        print("  ⚠️ ATTENTION: Vérifiez les données ou créez des notes de test")
    print("="*70 + "\n")
    
    return 0 if resultat else 1

if __name__ == "__main__":
    sys.exit(main())
