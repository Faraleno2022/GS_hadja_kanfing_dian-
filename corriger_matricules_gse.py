"""
Script pour corriger les matricules au format GSE et s'assurer que les notes sont saisies
"""
import os
import sys
import django

# Configuration Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ecole_moderne.settings')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
django.setup()

from eleves.models import Eleve, Classe
from notes.models import ClasseNote, MatiereNote, NoteMensuelle
from decimal import Decimal
from datetime import datetime

def corriger_matricules_et_notes():
    """Corriger les matricules GSE et vérifier les notes"""
    
    print("="*80)
    print("CORRECTION DES MATRICULES ET VÉRIFICATION DES NOTES")
    print("="*80)
    
    # 1. Chercher les élèves avec matricules problématiques
    print("\n1. RECHERCHE DES MATRICULES AU FORMAT GSE")
    print("-"*50)
    
    # Chercher spécifiquement les matricules mentionnés
    matricules_problematiques = [
        "GSE/CL7-001",
        "GSE/GSE/CL7-002",
        "GSE/CL7-002"
    ]
    
    eleves_trouves = []
    
    for matricule in matricules_problematiques:
        eleve = Eleve.objects.filter(matricule=matricule).first()
        if eleve:
            eleves_trouves.append(eleve)
            print(f"✅ Trouvé : {matricule} - {eleve.nom} {eleve.prenom}")
        else:
            # Chercher par nom si le matricule n'existe pas
            print(f"❌ Non trouvé : {matricule}")
            
            # Chercher si CAMARA OUMAR ou LENO FARA existent
            if "001" in matricule:
                eleves_possibles = Eleve.objects.filter(nom="CAMARA", prenom="OUMAR")
                if eleves_possibles.exists():
                    eleve = eleves_possibles.first()
                    print(f"   → Élève trouvé par nom : {eleve.nom} {eleve.prenom} (Matricule actuel : {eleve.matricule})")
                    eleves_trouves.append(eleve)
            
            elif "002" in matricule:
                eleves_possibles = Eleve.objects.filter(nom="LENO", prenom="FARA")
                if eleves_possibles.exists():
                    eleve = eleves_possibles.first()
                    print(f"   → Élève trouvé par nom : {eleve.nom} {eleve.prenom} (Matricule actuel : {eleve.matricule})")
                    eleves_trouves.append(eleve)
    
    if not eleves_trouves:
        print("\n⚠️ Aucun élève trouvé avec ces matricules ou noms")
        print("   → Vous devez d'abord créer ces élèves dans le système")
        print("   → Ou utiliser les matricules existants au format 2025/xxxxx")
        return
    
    # 2. Vérifier les notes de ces élèves
    print("\n2. VÉRIFICATION DES NOTES")
    print("-"*50)
    
    for eleve in eleves_trouves:
        print(f"\n📚 Élève : {eleve.nom} {eleve.prenom} ({eleve.matricule})")
        print(f"   Classe : {eleve.classe.nom if eleve.classe else 'Non assigné'}")
        
        # Vérifier les notes mensuelles
        notes_mensuelles = NoteMensuelle.objects.filter(eleve=eleve)
        
        if notes_mensuelles.exists():
            print(f"   ✅ {notes_mensuelles.count()} note(s) mensuelle(s) trouvée(s)")
            
            # Calculer la moyenne pour le mois le plus récent
            dernier_mois = notes_mensuelles.order_by('-mois').first().mois
            notes_mois = notes_mensuelles.filter(mois=dernier_mois)
            
            total = Decimal('0')
            count = 0
            for note in notes_mois:
                if note.note and not note.absent:
                    total += note.note
                    count += 1
            
            if count > 0:
                moyenne = total / count
                print(f"   → Moyenne {dernier_mois} : {moyenne:.2f}/20")
                print(f"   ✅ CET ÉLÈVE DEVRAIT AVOIR UN RANG ET UNE MOYENNE")
            else:
                print(f"   ⚠️ Toutes les notes sont absentes ou nulles")
        else:
            print(f"   ❌ AUCUNE NOTE SAISIE")
            print(f"   → Cet élève apparaîtra comme 'Non saisi' dans le classement")
    
    # 3. Proposer des solutions
    print("\n" + "="*80)
    print("SOLUTIONS PROPOSÉES")
    print("="*80)
    
    print("\n📝 Option 1 : CORRIGER LES MATRICULES")
    print("-"*50)
    print("Si vous voulez garder le format GSE, modifiez les matricules dans la base :")
    
    for i, (old_mat, nom, prenom) in enumerate([
        ("GSE/CL7-001", "CAMARA", "OUMAR"),
        ("GSE/GSE/CL7-002", "LENO", "FARA")
    ], 1):
        print(f"\n{i}. Pour {nom} {prenom} :")
        print(f"   UPDATE eleves_eleve")
        print(f"   SET matricule = '{old_mat}'")
        print(f"   WHERE nom = '{nom}' AND prenom = '{prenom}';")
    
    print("\n📊 Option 2 : SAISIR LES NOTES MANQUANTES")
    print("-"*50)
    print("Pour les élèves sans notes :")
    print("1. Aller dans : Notes > Saisie des notes")
    print("2. Sélectionner la classe de l'élève")
    print("3. Sélectionner la période (ex: DECEMBRE)")
    print("4. Saisir les notes pour chaque matière")
    
    print("\n🔄 Option 3 : UTILISER L'EXPORT CORRIGÉ")
    print("-"*50)
    print("Utilisez la nouvelle URL d'export qui gère mieux les cas sans notes :")
    print("/notes/exporter-classement-fixed/")
    print("\nParamètres à utiliser :")
    print("- classe_id : ID de la classe")
    print("- periode : OCTOBRE, NOVEMBRE, DECEMBRE, etc.")
    print("- type_note : mensuelle ou composition")
    
    print("\n✅ Une fois les corrections effectuées, le classement affichera :")
    print("- Les rangs (1er, 2ème, 3ème, etc.)")
    print("- Les moyennes calculées")
    print("- 'Pas de notes' pour les élèves sans notes (au lieu de 'Non saisi')")

if __name__ == "__main__":
    corriger_matricules_et_notes()
