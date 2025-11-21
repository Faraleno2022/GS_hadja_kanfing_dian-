"""
Test spécifique pour la classe 12 SÉRIE SCIENTIFIQUE
Vérifie la cohérence bulletin-classement pour les matières sans notes
"""

import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ecole_moderne.settings')
django.setup()

from notes.models import ClasseNote, MatiereNote, Evaluation, NoteEleve
from eleves.models import Eleve, Classe as ClasseEleve
from decimal import Decimal

def test_12_serie_scientifique():
    """
    Test pour la classe 12 SÉRIE SCIENTIFIQUE
    """
    print("\n" + "="*80)
    print("TEST: 12 SÉRIE SCIENTIFIQUE - Cohérence bulletin-classement")
    print("="*80 + "\n")
    
    # Trouver la classe 12 SÉRIE SCIENTIFIQUE
    classe_note = ClasseNote.objects.filter(nom__icontains="12").filter(nom__icontains="SCIENTIFIQUE").first()
    
    if not classe_note:
        print("❌ Classe '12 SÉRIE SCIENTIFIQUE' introuvable")
        print("\n📋 Classes disponibles:")
        for c in ClasseNote.objects.all()[:10]:
            print(f"   - {c.nom}")
        return
    
    print(f"✅ Classe trouvée: {classe_note.nom}")
    print(f"📅 Année scolaire: {classe_note.annee_scolaire}\n")
    
    # Trouver la classe élève correspondante
    # Essayer plusieurs variantes
    classe_eleve = ClasseEleve.objects.filter(
        nom__icontains="12",
        annee_scolaire=classe_note.annee_scolaire
    ).filter(nom__icontains="scientifique").first()
    
    if not classe_eleve:
        # Essayer avec "série"
        classe_eleve = ClasseEleve.objects.filter(
            nom__icontains="12",
            annee_scolaire=classe_note.annee_scolaire
        ).filter(nom__icontains="série").first()
    
    if not classe_eleve:
        # Essayer juste "12"
        classe_eleve = ClasseEleve.objects.filter(
            nom__icontains="12",
            annee_scolaire=classe_note.annee_scolaire
        ).first()
    
    if not classe_eleve:
        print("❌ Classe élève correspondante introuvable")
        print("\n📋 Classes élèves disponibles:")
        for c in ClasseEleve.objects.filter(annee_scolaire=classe_note.annee_scolaire):
            print(f"   - {c.nom}")
        print("\n💡 Essayez de créer la classe élève correspondante ou utilisez une autre classe")
        return
    
    print(f"✅ Classe élève: {classe_eleve.nom}")
    
    # Récupérer les élèves actifs
    eleves = Eleve.objects.filter(classe=classe_eleve, statut='ACTIF').order_by('prenom', 'nom')
    print(f"👥 Nombre d'élèves actifs: {eleves.count()}\n")
    
    if not eleves.exists():
        print("❌ Aucun élève actif trouvé")
        return
    
    # Récupérer les matières
    matieres = MatiereNote.objects.filter(classe=classe_note, actif=True).order_by('nom')
    print(f"📖 Matières actives: {matieres.count()}")
    for mat in matieres:
        print(f"   - {mat.nom} (Coef: {mat.coefficient})")
    print()
    
    periode = 'OCTOBRE'
    print(f"📅 Période testée: {periode}\n")
    
    # Tester chaque élève
    print("="*80)
    print(f"{'Élève':<35} {'Moy Bulletin':<15} {'Moy Classement':<15} {'Status'}")
    print("="*80)
    
    incoherences = 0
    eleves_testes = 0
    
    for eleve in eleves:
        # Calculer moyenne BULLETIN (nouvelle méthode)
        total_points_bulletin = Decimal('0')
        total_coef_bulletin = Decimal('0')
        matieres_sans_notes = 0
        
        for matiere in matieres:
            evaluations = Evaluation.objects.filter(
                matiere=matiere,
                periode=periode
            )
            
            total = Decimal('0')
            count = 0
            
            for evaluation in evaluations:
                try:
                    note_obj = NoteEleve.objects.get(eleve=eleve, evaluation=evaluation)
                    if note_obj.note is not None and not note_obj.absent:
                        total += Decimal(str(note_obj.note))
                        count += 1
                except NoteEleve.DoesNotExist:
                    pass
            
            if count > 0:
                moyenne = total / count
            else:
                moyenne = Decimal('0')
                matieres_sans_notes += 1
            
            # NOUVELLE RÈGLE: Toutes les matières comptent
            total_points_bulletin += moyenne * matiere.coefficient
            total_coef_bulletin += matiere.coefficient
        
        moyenne_bulletin = None
        if total_coef_bulletin > 0:
            moyenne_bulletin = total_points_bulletin / total_coef_bulletin
        
        # Calculer moyenne CLASSEMENT (méthode export_classement.py)
        total_points_classement = Decimal('0')
        total_coef_classement = Decimal('0')
        
        for matiere in matieres:
            evaluations = Evaluation.objects.filter(
                matiere=matiere,
                periode=periode
            )
            
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
            else:
                note_value = Decimal('0')
            
            total_points_classement += note_value * matiere.coefficient
            total_coef_classement += matiere.coefficient
        
        moyenne_classement = None
        if total_coef_classement > 0:
            moyenne_classement = total_points_classement / total_coef_classement
        
        # Comparer
        nom_complet = f"{eleve.prenom} {eleve.nom}"[:33]
        
        if moyenne_bulletin is not None and moyenne_classement is not None:
            diff = abs(float(moyenne_bulletin - moyenne_classement))
            
            if diff < 0.01:  # Tolérance pour les arrondis
                status = "✅ OK"
                if matieres_sans_notes > 0:
                    status += f" ({matieres_sans_notes} mat. sans notes)"
            else:
                status = f"❌ DIFF: {diff:.2f}"
                incoherences += 1
            
            moy_b = f"{float(moyenne_bulletin):.2f}"
            moy_c = f"{float(moyenne_classement):.2f}"
            print(f"{nom_complet:<35} {moy_b:<15} {moy_c:<15} {status}")
            eleves_testes += 1
        else:
            print(f"{nom_complet:<35} {'N/A':<15} {'N/A':<15} ⚠️  Pas de notes")
    
    print("="*80)
    print(f"\n📊 RÉSULTATS:")
    print(f"   Élèves testés: {eleves_testes}")
    print(f"   Incohérences détectées: {incoherences}")
    
    if incoherences == 0 and eleves_testes > 0:
        print(f"\n✅ ✅ ✅ SUCCÈS TOTAL! ✅ ✅ ✅")
        print(f"   Cohérence à 100% entre bulletin et classement")
        print(f"   Toutes les matières sont correctement comptées")
    elif eleves_testes == 0:
        print(f"\n⚠️  AUCUN ÉLÈVE TESTÉ")
        print(f"   Vérifiez qu'il y a des notes pour la période {periode}")
    else:
        print(f"\n❌ ÉCHEC: {incoherences} incohérence(s) détectée(s)")
        print(f"   Le code nécessite une correction supplémentaire")
    
    print("="*80 + "\n")


if __name__ == "__main__":
    test_12_serie_scientifique()
