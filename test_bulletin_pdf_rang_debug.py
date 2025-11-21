"""
Script de debug pour tester le calcul du rang dans bulletin_pdf
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ecole_moderne.settings')
django.setup()

from decimal import Decimal
from eleves.models import Eleve, Classe
from notes.models import NoteEleve, Evaluation, MatiereClasse

def test_calcul_rang_bulletin_pdf():
    """
    Simule le calcul du rang tel qu'il est fait dans bulletin_pdf
    """
    print("=" * 80)
    print("TEST DU CALCUL DU RANG DANS BULLETIN_PDF")
    print("=" * 80)
    
    # Trouver la classe 12ème Sciences
    try:
        classe = Classe.objects.get(nom__icontains="12ÈME SCIENCES")
        print(f"\n✅ Classe trouvée : {classe.nom}")
    except Classe.DoesNotExist:
        print("\n❌ Classe 12ème Sciences non trouvée")
        return
    except Classe.MultipleObjectsReturned:
        classe = Classe.objects.filter(nom__icontains="12ÈME SCIENCES").first()
        print(f"\n✅ Classe trouvée : {classe.nom}")
    
    # Trouver l'élève DIALLO Alpha Ousmane
    try:
        eleve = Eleve.objects.get(
            classe=classe,
            nom__icontains="DIALLO",
            prenom__icontains="ALPHA"
        )
        print(f"✅ Élève trouvé : {eleve.prenom} {eleve.nom}")
    except Eleve.DoesNotExist:
        print("❌ Élève DIALLO Alpha Ousmane non trouvé")
        return
    
    # Récupérer les matières
    matieres = MatiereClasse.objects.filter(classe=classe, ecole=classe.ecole, actif=True)
    print(f"✅ {matieres.count()} matières trouvées")
    
    # Trimestre (on suppose Octobre = T1 ou mensuel)
    trimestre = "T1"
    
    # Récupérer les évaluations
    evals_by_matiere = {}
    for mat in matieres:
        evals = Evaluation.objects.filter(classe=classe, matiere=mat, trimestre=trimestre)
        evals_by_matiere[mat.id] = list(evals)
    
    print(f"\n📊 Calcul des moyennes pour tous les élèves...")
    print("-" * 80)
    
    # Calculer la moyenne de tous les élèves (comme dans bulletin_pdf)
    eleves_classe = Eleve.objects.filter(classe=classe).only('id', 'prenom', 'nom', 'sexe')
    moyennes_generales = []
    
    for e in eleves_classe:
        notes_by_eval_e = {
            n.evaluation_id: n 
            for n in NoteEleve.objects.filter(
                eleve=e, 
                evaluation__classe=classe, 
                evaluation__trimestre=trimestre
            )
        }
        
        s_num = Decimal('0')
        s_den = Decimal('0')
        
        for mat in matieres:
            evals = evals_by_matiere.get(mat.id, [])
            num = Decimal('0')
            den = Decimal('0')
            
            for ev in evals:
                nn = notes_by_eval_e.get(ev.id)
                cc = Decimal(ev.coefficient or 1)
                
                if not nn or nn.note is None:
                    # Absence ou note manquante = 0
                    num += Decimal('0') * cc
                else:
                    num += Decimal(nn.note) * cc
                den += cc
            
            if den > 0:
                moy_mat_e = (num / den)
                s_num += moy_mat_e * Decimal(mat.coefficient or 1)
                s_den += Decimal(mat.coefficient or 1)
        
        if s_den > 0:
            mg = (s_num / s_den)
        else:
            mg = None
        
        if mg is not None:
            moyennes_generales.append((e.id, mg, e.prenom, e.nom, e.sexe))
    
    # Trier par moyenne décroissante
    moyennes_generales.sort(key=lambda t: t[1], reverse=True)
    total_eleves_ayant_moyenne = len(moyennes_generales)
    
    print(f"Total élèves avec moyenne : {total_eleves_ayant_moyenne}")
    print("\nClassement avec gestion des ex-aequo :")
    print("-" * 80)
    
    # Calculer le rang avec gestion des ex-aequo
    rang_actuel = 1
    prev_moy = None
    rang_diallo = None
    
    for idx, (eid, mg, prenom, nom, sexe) in enumerate(moyennes_generales, start=1):
        # Déterminer le rang de cet élève
        if prev_moy is not None and abs(mg - prev_moy) < Decimal('0.01'):
            # Ex-aequo : garde le même rang
            pass
        else:
            # Nouveau rang : utilise la position réelle
            rang_actuel = idx
        
        # Afficher les 15 premiers
        if idx <= 15:
            marker = " ⭐" if eid == eleve.id else ""
            ex_marker = " (ex-aequo)" if prev_moy and abs(mg - prev_moy) < Decimal('0.01') else ""
            print(f"  {rang_actuel}. {prenom} {nom} : {mg:.2f}/20{marker}{ex_marker}")
        
        # Vérifier si c'est notre élève
        if eid == eleve.id:
            rang_diallo = rang_actuel
        
        prev_moy = mg
    
    print("\n" + "=" * 80)
    print("RÉSULTAT")
    print("=" * 80)
    print(f"Élève : {eleve.prenom} {eleve.nom}")
    print(f"Rang calculé : {rang_diallo}ème/{total_eleves_ayant_moyenne}")
    
    if rang_diallo == 9:
        print("\n✅ TEST RÉUSSI : Le rang est correct (9ème)")
    else:
        print(f"\n❌ TEST ÉCHOUÉ : Rang attendu 9, obtenu {rang_diallo}")
    
    return rang_diallo == 9

if __name__ == "__main__":
    test_calcul_rang_bulletin_pdf()
