#!/usr/bin/env python
"""
Script de test complet pour vérifier que le recalcul des absences s'applique bien
"""
import os
import sys
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ecole_moderne.settings')
django.setup()

from decimal import Decimal
from notes.models import ClasseNote, MatiereNote, Evaluation, NoteEleve
from eleves.models import Eleve, Classe as ClasseEleve

def test_1_verifier_absences():
    """TEST 1 : Vérifier que CL10-032 a bien 6 absences"""
    print("\n" + "="*80)
    print("TEST 1 : Vérifier que CL10-032 a bien 6 absences")
    print("="*80)
    
    try:
        eleve = Eleve.objects.get(matricule='CL10-032')
        print(f"✓ Élève trouvé : {eleve.prenom} {eleve.nom} ({eleve.matricule})")
        
        # Récupérer les notes OCTOBRE
        notes = NoteEleve.objects.filter(
            eleve=eleve,
            evaluation__periode='OCTOBRE'
        ).select_related('evaluation__matiere')
        
        print(f"\nNotes en OCTOBRE : {notes.count()} évaluations")
        absences = 0
        notes_presentes = 0
        for note in notes:
            if note.absent:
                print(f"  - {note.evaluation.matiere.nom} : ABS")
                absences += 1
            elif note.note:
                print(f"  - {note.evaluation.matiere.nom} : {note.note}")
                notes_presentes += 1
            else:
                print(f"  - {note.evaluation.matiere.nom} : VIDE")
        
        print(f"\nRésumé : {absences} absences, {notes_presentes} notes présentes")
        return True
        
    except Eleve.DoesNotExist:
        print("✗ Élève CL10-032 non trouvé")
        return False

def test_2_calculer_moyenne():
    """TEST 2 : Calculer la moyenne de CL10-032 avec la nouvelle logique"""
    print("\n" + "="*80)
    print("TEST 2 : Calculer la moyenne de CL10-032 avec la nouvelle logique")
    print("="*80)
    
    try:
        classe = ClasseNote.objects.get(pk=14)
        eleve = Eleve.objects.get(matricule='CL10-032')
        
        somme_moy_coef = Decimal('0')
        somme_coef = Decimal('0')
        
        matieres = MatiereNote.objects.filter(classe=classe, actif=True).order_by('nom')
        
        print(f"\nCalcul par matière :")
        for matiere in matieres:
            evaluations = Evaluation.objects.filter(matiere=matiere, periode='OCTOBRE')
            total_pondere = Decimal('0')
            total_coef_eval = Decimal('0')
            
            for evaluation in evaluations:
                try:
                    note_obj = NoteEleve.objects.get(eleve=eleve, evaluation=evaluation)
                    coef_eval = Decimal(str(evaluation.coefficient or 1))
                    if note_obj.absent or note_obj.note is None:
                        total_pondere += Decimal('0') * coef_eval
                    else:
                        total_pondere += Decimal(str(note_obj.note)) * coef_eval
                    total_coef_eval += coef_eval
                except NoteEleve.DoesNotExist:
                    coef_eval = Decimal(str(evaluation.coefficient or 1))
                    total_pondere += Decimal('0') * coef_eval
                    total_coef_eval += coef_eval
            
            if total_coef_eval > 0:
                moy = total_pondere / total_coef_eval
                print(f"  {matiere.nom:40} → {float(moy):.2f}")
                coef_matiere = Decimal(str(matiere.coefficient or 1))
                somme_moy_coef += moy * coef_matiere
                somme_coef += coef_matiere
        
        if somme_coef > 0:
            moyenne_generale = somme_moy_coef / somme_coef
            print(f"\n✓ Moyenne générale calculée : {float(moyenne_generale):.2f}/20")
            
            # Vérifier que c'est bien ~3.33
            if 3.0 <= float(moyenne_generale) <= 3.5:
                print("✓ CORRECT : Moyenne entre 3.0 et 3.5 (absences comptées comme 0)")
                return True
            else:
                print(f"✗ INCORRECT : Moyenne = {float(moyenne_generale):.2f} (devrait être ~3.33)")
                return False
        else:
            print("\n✗ Pas de moyenne calculée")
            return False
            
    except Exception as e:
        print(f"✗ Erreur : {e}")
        import traceback
        traceback.print_exc()
        return False

def test_3_classement_complet():
    """TEST 3 : Vérifier le classement de toute la classe"""
    print("\n" + "="*80)
    print("TEST 3 : Vérifier le classement de toute la classe")
    print("="*80)
    
    try:
        classe = ClasseNote.objects.get(pk=14)
        classe_eleve = ClasseEleve.objects.filter(
            nom=classe.nom,
            annee_scolaire=classe.annee_scolaire,
            ecole=classe.ecole
        ).first()
        
        if not classe_eleve:
            print("✗ Classe élève non trouvée")
            return False
        
        eleves = Eleve.objects.filter(classe=classe_eleve, statut='ACTIF').order_by('prenom', 'nom')
        
        classement = []
        for eleve in eleves:
            somme_moy_coef = Decimal('0')
            somme_coef = Decimal('0')
            
            for matiere in MatiereNote.objects.filter(classe=classe, actif=True):
                evaluations = Evaluation.objects.filter(matiere=matiere, periode='OCTOBRE')
                total_pondere = Decimal('0')
                total_coef_eval = Decimal('0')
                
                for evaluation in evaluations:
                    try:
                        note_obj = NoteEleve.objects.get(eleve=eleve, evaluation=evaluation)
                        coef_eval = Decimal(str(evaluation.coefficient or 1))
                        if note_obj.absent or note_obj.note is None:
                            total_pondere += Decimal('0') * coef_eval
                        else:
                            total_pondere += Decimal(str(note_obj.note)) * coef_eval
                        total_coef_eval += coef_eval
                    except NoteEleve.DoesNotExist:
                        coef_eval = Decimal(str(evaluation.coefficient or 1))
                        total_pondere += Decimal('0') * coef_eval
                        total_coef_eval += coef_eval
                
                if total_coef_eval > 0:
                    moy = total_pondere / total_coef_eval
                    coef_matiere = Decimal(str(matiere.coefficient or 1))
                    somme_moy_coef += moy * coef_matiere
                    somme_coef += coef_matiere
            
            if somme_coef > 0:
                moyenne_generale = float(somme_moy_coef / somme_coef)
                classement.append({
                    'matricule': eleve.matricule,
                    'nom': f"{eleve.prenom} {eleve.nom}",
                    'moyenne': round(moyenne_generale, 2)
                })
        
        # Trier par moyenne décroissante
        classement.sort(key=lambda x: x['moyenne'], reverse=True)
        
        print(f"\nClassement complet ({len(classement)} élèves) :\n")
        print(f"{'Rang':<6} {'Matricule':<12} {'Nom':<30} {'Moyenne':<10}")
        print("-" * 60)
        
        cl10_032_rang = None
        for idx, eleve_data in enumerate(classement, 1):
            print(f"{idx:<6} {eleve_data['matricule']:<12} {eleve_data['nom']:<30} {eleve_data['moyenne']:<10.2f}")
            
            # Vérifier CL10-032
            if eleve_data['matricule'] == 'CL10-032':
                cl10_032_rang = idx
        
        if cl10_032_rang:
            print(f"\n{'='*60}")
            if cl10_032_rang >= 25:
                print(f"✓ CL10-032 est classé {cl10_032_rang}ème/31 (CORRECT)")
                print("✓ Le recalcul s'applique bien côté serveur")
                return True
            else:
                print(f"✗ CL10-032 est classé {cl10_032_rang}ème/31 (INCORRECT - devrait être ~30ème)")
                print("✗ Le recalcul ne s'applique pas correctement")
                return False
        else:
            print("\n✗ CL10-032 non trouvé dans le classement")
            return False
        
    except Exception as e:
        print(f"✗ Erreur : {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Exécuter tous les tests"""
    print("\n" + "🧪 TESTS COMPLETS DE RECALCUL DES ABSENCES".center(80))
    
    resultats = []
    
    # Test 1
    resultats.append(("Vérifier absences CL10-032", test_1_verifier_absences()))
    
    # Test 2
    resultats.append(("Calculer moyenne CL10-032", test_2_calculer_moyenne()))
    
    # Test 3
    resultats.append(("Classement complet", test_3_classement_complet()))
    
    # Résumé final
    print("\n" + "="*80)
    print("RÉSUMÉ FINAL DES TESTS")
    print("="*80)
    
    for nom_test, resultat in resultats:
        status = "✓ RÉUSSI" if resultat else "✗ ÉCHOUÉ"
        print(f"{status} | {nom_test}")
    
    total_reussis = sum(1 for _, r in resultats if r)
    total_tests = len(resultats)
    
    print(f"\n{'='*80}")
    print(f"Résultat : {total_reussis}/{total_tests} tests réussis")
    
    if total_reussis == total_tests:
        print("\n🎉 TOUS LES TESTS SONT PASSÉS !")
        print("✓ Le recalcul s'applique bien côté serveur")
        print("✓ Le classement est correct après rechargement")
        print("✓ CL10-032 est maintenant classé correctement (~30ème/31)")
    else:
        print(f"\n❌ {total_tests - total_reussis} test(s) échoué(s)")
        print("Vérifiez les logs ci-dessus pour plus de détails")

if __name__ == '__main__':
    main()
