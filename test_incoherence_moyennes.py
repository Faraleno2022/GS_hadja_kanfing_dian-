"""
Test pour vérifier s'il y a des incohérences entre les moyennes calculées
par différentes méthodes dans le système
"""

import os
import django
from decimal import Decimal

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ecole_moderne.settings')
django.setup()

from notes.models import ClasseNote, MatiereNote, Evaluation, NoteEleve
from eleves.models import Eleve
from notes.calculs_moyennes import calculer_moyenne_generale_eleve

def calculer_moyenne_export_classement(eleve, matieres, periode):
    """Simule le calcul dans export_classement.py (lignes 433-514)"""
    total_notes = Decimal('0')
    total_coefficients = Decimal('0')
    
    for matiere in matieres:
        coefficient = matiere.coefficient or Decimal('1')
        note_value = None
        
        evaluations = Evaluation.objects.filter(matiere=matiere, periode=periode)
        
        if evaluations.exists():
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
                note_value = total_pondere / total_coef_eval
        
        if note_value is None:
            note_value = Decimal('0')
        total_notes += note_value * coefficient
        total_coefficients += coefficient
    
    if total_coefficients > 0:
        return float(total_notes / total_coefficients)
    return None


def comparer_methodes():
    """Compare les résultats des différentes méthodes de calcul"""
    print("\n" + "="*80)
    print("TEST D'INCOHÉRENCE DES MOYENNES")
    print("="*80 + "\n")
    
    # Trouver une classe avec des notes
    classe = ClasseNote.objects.filter(nom__icontains="12").filter(nom__icontains="SCIENTIFIQUE").first()
    
    if not classe:
        classe = ClasseNote.objects.first()
    
    if not classe:
        print("❌ Aucune classe trouvée")
        return
    
    print(f"📚 Classe testée: {classe.nom}")
    
    # Trouver la classe élève correspondante
    from eleves.models import Classe as ClasseEleve
    
    # Essayer plusieurs méthodes de recherche
    classe_eleve = ClasseEleve.objects.filter(
        nom__icontains="12",
        annee_scolaire=classe.annee_scolaire
    ).filter(nom__icontains="SCIENTIFIQUE").first()
    
    if not classe_eleve:
        # Essayer avec "12" seulement
        classe_eleve = ClasseEleve.objects.filter(
            nom__icontains="12",
            annee_scolaire=classe.annee_scolaire
        ).first()
    
    if not classe_eleve:
        # Prendre une classe avec des élèves
        for ce in ClasseEleve.objects.filter(annee_scolaire=classe.annee_scolaire):
            if Eleve.objects.filter(classe=ce, statut='ACTIF').exists():
                classe_eleve = ce
                break
    
    if not classe_eleve:
        print("❌ Classe élève introuvable")
        return
    
    # Récupérer les élèves et matières
    eleves = Eleve.objects.filter(classe=classe_eleve, statut='ACTIF')[:5]  # Tester 5 élèves
    matieres = MatiereNote.objects.filter(classe=classe, actif=True)
    
    print(f"👥 Élèves testés: {eleves.count()}")
    print(f"📖 Matières: {matieres.count()}\n")
    
    periode = 'OCTOBRE'
    
    # Comparer les méthodes
    print(f"{'Élève':<30} {'Module centralisé':<18} {'Export classement':<18} {'Différence'}")
    print("-" * 84)
    
    incoherences = 0
    
    for eleve in eleves:
        # Méthode 1: Module centralisé (la référence)
        result_centralise = calculer_moyenne_generale_eleve(eleve, matieres, periode, 'mensuel')
        moy_centralise = result_centralise['moyenne_generale']
        
        # Méthode 2: Export classement
        moy_export = calculer_moyenne_export_classement(eleve, matieres, periode)
        
        # Comparer
        nom_complet = f"{eleve.prenom} {eleve.nom}"[:28]
        
        if moy_centralise is not None and moy_export is not None:
            diff = abs(moy_centralise - moy_export)
            
            moy_c_str = f"{moy_centralise:.2f}"
            moy_e_str = f"{moy_export:.2f}"
            
            if diff < 0.01:
                status = "✅ OK"
            else:
                status = f"❌ {diff:.2f}"
                incoherences += 1
            
            print(f"{nom_complet:<30} {moy_c_str:<18} {moy_e_str:<18} {status}")
        else:
            moy_c_str = "-" if moy_centralise is None else f"{moy_centralise:.2f}"
            moy_e_str = "-" if moy_export is None else f"{moy_export:.2f}"
            print(f"{nom_complet:<30} {moy_c_str:<18} {moy_e_str:<18} ⚠️")
    
    print("-" * 84)
    
    if incoherences > 0:
        print(f"\n❌ INCOHÉRENCE DÉTECTÉE: {incoherences} différence(s)")
        print("   → Les méthodes de calcul ne donnent PAS les mêmes résultats")
        print("   → Il faut unifier les calculs avec le module centralisé")
    else:
        print(f"\n✅ COHÉRENCE VALIDÉE: Les méthodes donnent les mêmes résultats")
        print("   → Même si le code est différent, les calculs sont cohérents")
        print("   → Recommandation: Unifier quand même pour faciliter la maintenance")
    
    print("="*80 + "\n")


if __name__ == "__main__":
    comparer_methodes()
