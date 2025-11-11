"""
Script pour corriger l'export du classement et s'assurer que les rangs et moyennes s'affichent
"""
import os
import sys
import django
from decimal import Decimal

# Configuration Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ecole_moderne.settings')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
django.setup()

from eleves.models import Eleve, Classe
from notes.models import ClasseNote, MatiereNote, NoteMensuelle, CompositionNote
from datetime import datetime

def verifier_et_corriger_classement():
    """Vérifier et corriger le problème de classement"""
    
    print("="*80)
    print("VÉRIFICATION ET CORRECTION DU CLASSEMENT")
    print("="*80)
    
    # 1. Identifier le problème avec les matricules GSE/CL7
    print("\n1. RECHERCHE DES ÉLÈVES PROBLÉMATIQUES")
    print("-"*50)
    
    # Rechercher les élèves par différents critères
    eleves_gse = Eleve.objects.filter(matricule__icontains='GSE')
    
    if eleves_gse.exists():
        print(f"✅ {eleves_gse.count()} élève(s) trouvé(s) avec 'GSE' dans le matricule:")
        for eleve in eleves_gse[:5]:
            print(f"   - {eleve.matricule}: {eleve.nom} {eleve.prenom}")
            
            # Vérifier ses notes mensuelles
            notes_mens = NoteMensuelle.objects.filter(eleve=eleve)
            notes_comp = CompositionNote.objects.filter(eleve=eleve)
            
            print(f"     → Notes mensuelles: {notes_mens.count()}")
            print(f"     → Notes composition: {notes_comp.count()}")
            
            if notes_mens.count() == 0 and notes_comp.count() == 0:
                print(f"     ⚠️ AUCUNE NOTE SAISIE POUR CET ÉLÈVE!")
    else:
        print("❌ Aucun élève avec 'GSE' dans le matricule")
        print("   → Les matricules de l'image peuvent ne pas correspondre à la base de données actuelle")
    
    # 2. Trouver une classe pour tester
    print("\n2. TEST AVEC UNE CLASSE EXISTANTE")
    print("-"*50)
    
    # Prendre une classe avec des notes
    classe_test = None
    for cn in ClasseNote.objects.all():
        # Vérifier si cette classe a des élèves avec des notes
        try:
            classe_eleve = Classe.objects.filter(
                nom=cn.nom,
                annee_scolaire=cn.annee_scolaire,
                ecole=cn.ecole
            ).first()
            
            if classe_eleve:
                eleves = Eleve.objects.filter(classe=classe_eleve, statut='ACTIF')
                
                # Vérifier si au moins un élève a des notes
                for eleve in eleves[:5]:
                    if NoteMensuelle.objects.filter(eleve=eleve).exists():
                        classe_test = cn
                        break
                
                if classe_test:
                    break
        except:
            continue
    
    if classe_test:
        print(f"✅ Classe test trouvée: {classe_test.nom}")
        
        # Simuler le calcul du classement
        print("\n3. CALCUL DU CLASSEMENT DE TEST")
        print("-"*50)
        
        classe_eleve = Classe.objects.filter(
            nom=classe_test.nom,
            annee_scolaire=classe_test.annee_scolaire,
            ecole=classe_test.ecole
        ).first()
        
        if classe_eleve:
            eleves = Eleve.objects.filter(classe=classe_eleve, statut='ACTIF').order_by('nom', 'prenom')
            matieres = MatiereNote.objects.filter(classe=classe_test, actif=True)
            
            classement_data = []
            periode = "DECEMBRE"  # Utiliser une période qui a des notes
            
            for eleve in eleves:
                total_notes = Decimal('0')
                total_coefficients = Decimal('0')
                nb_notes = 0
                
                for matiere in matieres:
                    try:
                        note_obj = NoteMensuelle.objects.get(
                            eleve=eleve,
                            matiere=matiere,
                            mois=periode,
                            annee_scolaire=classe_test.annee_scolaire
                        )
                        
                        if not note_obj.absent and note_obj.note:
                            coefficient = matiere.coefficient or Decimal('1')
                            total_notes += note_obj.note * coefficient
                            total_coefficients += coefficient
                            nb_notes += 1
                    except NoteMensuelle.DoesNotExist:
                        pass
                
                # Calculer la moyenne
                if total_coefficients > 0:
                    moyenne = float(total_notes / total_coefficients)
                    classement_data.append({
                        'matricule': eleve.matricule,
                        'nom_complet': f"{eleve.nom} {eleve.prenom}",
                        'moyenne': round(moyenne, 2),
                        'nb_notes': nb_notes,
                        'sexe': eleve.sexe
                    })
                else:
                    classement_data.append({
                        'matricule': eleve.matricule,
                        'nom_complet': f"{eleve.nom} {eleve.prenom}",
                        'moyenne': None,
                        'nb_notes': 0,
                        'sexe': eleve.sexe
                    })
            
            # Trier et attribuer les rangs
            eleves_avec_notes = [e for e in classement_data if e['moyenne'] is not None]
            eleves_sans_notes = [e for e in classement_data if e['moyenne'] is None]
            
            # Trier par moyenne décroissante
            eleves_avec_notes.sort(key=lambda x: x['moyenne'], reverse=True)
            
            # Attribuer les rangs
            rang = 1
            for i, eleve_data in enumerate(eleves_avec_notes):
                if i > 0 and eleve_data['moyenne'] == eleves_avec_notes[i-1]['moyenne']:
                    eleve_data['rang'] = eleves_avec_notes[i-1]['rang']
                else:
                    eleve_data['rang'] = rang
                rang += 1
            
            # Marquer les élèves sans notes
            for eleve_data in eleves_sans_notes:
                eleve_data['rang'] = '-'
            
            # Afficher les résultats
            print(f"\n📊 RÉSULTATS DU CLASSEMENT ({classe_test.nom})")
            print("-"*80)
            print(f"{'Rang':<8} {'Matricule':<15} {'Nom Complet':<30} {'Moyenne /20':<12} {'Notes':<8}")
            print("-"*80)
            
            # Top 5 avec notes
            for data in eleves_avec_notes[:5]:
                rang_affiche = formater_rang_correctement(data['rang'], data['sexe'])
                print(f"{rang_affiche:<8} {data['matricule']:<15} {data['nom_complet'][:30]:<30} {data['moyenne']:>10.2f}  {data['nb_notes']:>6}")
            
            if eleves_sans_notes:
                print("...")
                # Quelques élèves sans notes
                for data in eleves_sans_notes[:3]:
                    print(f"{'-':<8} {data['matricule']:<15} {data['nom_complet'][:30]:<30} {'Non saisi':>12} {data['nb_notes']:>6}")
            
            print("-"*80)
            print(f"Total: {len(eleves)} élèves")
            print(f"Avec notes: {len(eleves_avec_notes)}")
            print(f"Sans notes: {len(eleves_sans_notes)}")
            
            # Recommandations
            print("\n4. DIAGNOSTIC DU PROBLÈME")
            print("-"*50)
            
            if len(eleves_sans_notes) > 0:
                print(f"⚠️ {len(eleves_sans_notes)} élève(s) sans notes!")
                print("   Causes possibles:")
                print("   1. Les notes n'ont pas été saisies pour ces élèves")
                print("   2. Les élèves ont été ajoutés après la saisie des notes")
                print("   3. Les notes ont été saisies pour une autre période")
                
                print("\n   Solutions:")
                print("   → Vérifier la saisie des notes pour la période sélectionnée")
                print("   → S'assurer que tous les élèves ont des notes dans toutes les matières")
                print("   → Utiliser le module de saisie des notes pour compléter les notes manquantes")
    else:
        print("❌ Aucune classe avec des notes trouvée")
    
    print("\n" + "="*80)
    print("SOLUTION PROPOSÉE")
    print("="*80)
    print("\n✅ Pour corriger le problème des rangs et moyennes qui n'apparaissent pas:")
    print("1. Vérifiez que les notes sont saisies pour tous les élèves")
    print("2. Assurez-vous que la période sélectionnée correspond aux notes saisies")
    print("3. Vérifiez la correspondance entre les classes de notes et les classes d'élèves")
    print("4. Les matricules doivent correspondre exactement entre les deux systèmes")

def formater_rang_correctement(rang, sexe):
    """Formater le rang avec l'accord grammatical"""
    if rang == '-':
        return '-'
    
    rang_num = int(rang)
    if rang_num == 1:
        return "1ère" if sexe == 'F' else "1er"
    else:
        return f"{rang_num}ème"

if __name__ == "__main__":
    verifier_et_corriger_classement()
