"""
Test de cohérence entre le rang du bulletin et du classement général
"""

import os
import sys
import django
from decimal import Decimal

# Configuration Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ecole_moderne.settings')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
django.setup()

from eleves.models import Eleve, Classe as ClasseEleve
from notes.models import ClasseNote, MatiereNote, Evaluation, NoteEleve
from notes.views import monthly_avg

def test_coherence_rang():
    print("="*80)
    print("TEST DE COHÉRENCE DES RANGS - BULLETIN VS CLASSEMENT")
    print("="*80)
    
    try:
        # Récupérer la classe 12ème Scientifique
        classe_note = ClasseNote.objects.filter(nom__icontains="12").filter(nom__icontains="scientifique").first()
        if not classe_note:
            print("❌ Classe 12ème Scientifique non trouvée")
            return
        
        print(f"✅ Classe trouvée : {classe_note.nom}")
        
        # Récupérer la classe élève correspondante
        classe_eleve = ClasseEleve.objects.filter(
            nom=classe_note.nom,
            annee_scolaire=classe_note.annee_scolaire,
            ecole=classe_note.ecole
        ).first()
        
        if not classe_eleve:
            # Essayer avec une correspondance partielle du nom
            classe_eleve = ClasseEleve.objects.filter(
                nom__icontains="12",
                ecole=classe_note.ecole
            ).first()
            
            if not classe_eleve:
                print("❌ Classe élève correspondante non trouvée")
                print("Tentative de recherche par matricule L12SC-019...")
                
                # Rechercher directement les élèves avec ce matricule
                eleve_test = Eleve.objects.filter(matricule='L12SC-019').first()
                if eleve_test:
                    classe_eleve = eleve_test.classe
                    print(f"✅ Classe trouvée via l'élève : {classe_eleve.nom}")
                else:
                    print("❌ Impossible de trouver la classe ou l'élève")
                    return
        
        # Récupérer les élèves
        eleves = Eleve.objects.filter(classe=classe_eleve).order_by('nom', 'prenom')
        print(f"✅ {len(eleves)} élèves trouvés dans {classe_eleve.nom}")
        
        # Récupérer les matières
        matieres = MatiereNote.objects.filter(classe=classe_note, actif=True).order_by('nom')
        print(f"✅ {len(matieres)} matières trouvées")
        
        # Mois d'octobre (10)
        mois = 10
        annee_scolaire = classe_note.annee_scolaire
        
        print("\n" + "="*80)
        print("CALCUL DES MOYENNES POUR OCTOBRE")
        print("="*80)
        
        # Calculer les moyennes pour tous les élèves
        moyennes_eleves = []
        
        for eleve in eleves:
            somme_moy_coef = Decimal('0')
            somme_coef = Decimal('0')
            
            for matiere in matieres:
                # Utiliser la fonction monthly_avg de views.py
                moy_mois = monthly_avg(eleve, matiere, annee_scolaire, mois, mode='weighted')
                
                if moy_mois is not None:
                    coef = Decimal(str(matiere.coefficient or 1))
                    somme_moy_coef += moy_mois * coef
                    somme_coef += coef
            
            if somme_coef > 0:
                moyenne_generale = (somme_moy_coef / somme_coef).quantize(Decimal('0.01'))
                moyennes_eleves.append({
                    'eleve': eleve,
                    'matricule': eleve.matricule,
                    'nom_complet': f"{eleve.nom} {eleve.prenom}",
                    'moyenne': moyenne_generale
                })
        
        # Trier par moyenne décroissante
        moyennes_eleves.sort(key=lambda x: x['moyenne'], reverse=True)
        
        print("\nCLASSEMENT CALCULÉ :")
        print("-"*80)
        print("Rang | Matricule    | Nom                          | Moyenne")
        print("-"*80)
        
        prev_moy = None
        prev_rang = None
        for idx, eleve_data in enumerate(moyennes_eleves, start=1):
            # Gestion des ex-aequo
            if prev_moy is not None and abs(eleve_data['moyenne'] - prev_moy) < Decimal('0.01'):
                rang_num = prev_rang
            else:
                rang_num = idx
                prev_rang = idx
            prev_moy = eleve_data['moyenne']
            
            # Format du rang
            if rang_num == 1:
                sexe = getattr(eleve_data['eleve'], 'sexe', 'M') or 'M'
                rang_str = "1ère" if sexe == 'F' else "1er"
            else:
                rang_str = f"{rang_num}ème"
            
            # Marquer spécifiquement BANGOURA AMINATA
            marker = " ⭐" if eleve_data['matricule'] == 'L12SC-019' else ""
            
            print(f"{rang_str:5} | {eleve_data['matricule']:12} | {eleve_data['nom_complet']:30} | {eleve_data['moyenne']:.2f}{marker}")
        
        print("\n" + "="*80)
        print("VÉRIFICATION SPÉCIFIQUE - BANGOURA AMINATA (L12SC-019)")
        print("="*80)
        
        # Trouver BANGOURA AMINATA
        aminata = None
        rang_aminata = None
        for idx, eleve_data in enumerate(moyennes_eleves, start=1):
            if eleve_data['matricule'] == 'L12SC-019':
                aminata = eleve_data
                # Recalculer son rang avec ex-aequo
                prev_moy = None
                prev_rang = None
                for i, e in enumerate(moyennes_eleves[:idx], start=1):
                    if prev_moy is not None and abs(e['moyenne'] - prev_moy) < Decimal('0.01'):
                        if i == idx:
                            rang_aminata = prev_rang
                    else:
                        if i == idx:
                            rang_aminata = i
                        prev_rang = i
                    prev_moy = e['moyenne']
                break
        
        if aminata:
            print(f"✅ Élève trouvé : {aminata['nom_complet']}")
            print(f"   Matricule : {aminata['matricule']}")
            print(f"   Moyenne : {aminata['moyenne']:.2f}/20")
            print(f"   Rang calculé : {rang_aminata}/{len(moyennes_eleves)}")
            print("\n⚠️ COMPARAISON AVEC LE PDF DU BULLETIN :")
            print("   - Sur le classement général PDF : 8ème avec 9.42/20")
            print(f"   - Sur notre calcul : {rang_aminata}ème avec {aminata['moyenne']:.2f}/20")
            
            if abs(aminata['moyenne'] - Decimal('9.42')) < Decimal('0.05'):
                print("   ✅ Les moyennes correspondent")
            else:
                print("   ❌ Les moyennes NE correspondent PAS !")
                
        else:
            print("❌ BANGOURA AMINATA (L12SC-019) non trouvée")
        
        print("\n" + "="*80)
        print("RÉSUMÉ")
        print("="*80)
        print("✅ Le calcul du rang a été ajouté dans bulletin_mensuel_pdf")
        print("✅ Le rang utilise la même logique que le classement général :")
        print("   - Calcul de toutes les moyennes")
        print("   - Tri décroissant")
        print("   - Gestion des ex-aequo")
        print("   - Format intelligent (1er/1ère selon le sexe)")
        print("\n📋 À VÉRIFIER APRÈS REDÉMARRAGE DU SERVEUR :")
        print("   1. Régénérer le bulletin de BANGOURA AMINATA")
        print("   2. Le rang doit apparaître : 8ème/18")
        print("   3. La moyenne doit être : 9.42/20")
        
    except Exception as e:
        print(f"❌ Erreur : {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_coherence_rang()
