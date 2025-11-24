"""
Script pour vérifier les notes mensuelles et créer des notes de test si nécessaire
"""

import os
import sys
import django
import random
from decimal import Decimal

# Configuration Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ecole_moderne.settings')
django.setup()

from notes.models import NoteMensuelle, ClasseNote, MatiereNote
from eleves.models import Eleve
from django.db import transaction

def verifier_notes_mensuelles(classe_nom="9ÈME ANNÉE", mois="OCTOBRE"):
    """Vérifier l'existence des notes mensuelles"""
    print(f"\n{'='*70}")
    print(f"🔍 VÉRIFICATION DES NOTES MENSUELLES")
    print(f"{'='*70}\n")
    
    # Trouver la classe
    try:
        classe = ClasseNote.objects.get(nom__icontains=classe_nom)
        print(f"✅ Classe trouvée : {classe.nom}")
        print(f"   Année scolaire : {classe.annee_scolaire}")
    except ClasseNote.DoesNotExist:
        print(f"❌ Classe '{classe_nom}' non trouvée")
        return False
    
    # Lister les élèves
    eleves = Eleve.objects.filter(classe__nom=classe.nom, statut='INSCRIT')
    print(f"\n📊 Élèves inscrits : {eleves.count()}")
    
    # Compter les notes existantes
    notes_count = 0
    for eleve in eleves:
        notes = NoteMensuelle.objects.filter(
            eleve=eleve,
            mois=mois,
            annee_scolaire=classe.annee_scolaire
        ).count()
        if notes > 0:
            notes_count += 1
    
    print(f"📝 Élèves avec notes pour {mois} : {notes_count}/{eleves.count()}")
    
    if notes_count == 0:
        print(f"\n⚠️ AUCUNE NOTE MENSUELLE TROUVÉE POUR {mois}")
        return False
    
    return True

def creer_notes_test(classe_nom="9ÈME ANNÉE", mois="OCTOBRE", confirmer=True):
    """Créer des notes de test pour une classe et un mois"""
    
    if confirmer:
        print(f"\n⚠️ ATTENTION : Cette action va créer des notes de TEST")
        print(f"   Classe : {classe_nom}")
        print(f"   Mois : {mois}")
        reponse = input("\n👉 Voulez-vous continuer ? (oui/non) : ")
        if reponse.lower() not in ['oui', 'o', 'yes', 'y']:
            print("❌ Opération annulée")
            return
    
    print(f"\n{'='*70}")
    print(f"🎲 CRÉATION DE NOTES DE TEST")
    print(f"{'='*70}\n")
    
    try:
        with transaction.atomic():
            # Trouver la classe
            classe = ClasseNote.objects.get(nom__icontains=classe_nom)
            print(f"✅ Classe : {classe.nom}")
            
            # Récupérer les matières
            matieres = MatiereNote.objects.filter(classe=classe)
            print(f"📚 Matières : {matieres.count()}")
            
            # Récupérer les élèves
            eleves = Eleve.objects.filter(
                classe__nom=classe.nom,
                statut='INSCRIT'
            )
            print(f"👥 Élèves : {eleves.count()}")
            
            notes_creees = 0
            
            for eleve in eleves:
                for matiere in matieres:
                    # Vérifier si la note existe déjà
                    exists = NoteMensuelle.objects.filter(
                        eleve=eleve,
                        matiere=matiere,
                        mois=mois,
                        annee_scolaire=classe.annee_scolaire
                    ).exists()
                    
                    if not exists:
                        # Générer une note aléatoire entre 8 et 18
                        note_value = Decimal(str(random.uniform(8, 18))).quantize(Decimal('0.1'))
                        
                        # 5% de chance d'absence
                        absent = random.random() < 0.05
                        
                        NoteMensuelle.objects.create(
                            eleve=eleve,
                            matiere=matiere,
                            mois=mois,
                            annee_scolaire=classe.annee_scolaire,
                            note=None if absent else note_value,
                            absent=absent,
                            observations="Note de test" if not absent else "Absent"
                        )
                        notes_creees += 1
            
            print(f"\n✅ {notes_creees} notes créées avec succès !")
            
            # Afficher un échantillon
            print(f"\n📊 Échantillon de notes créées :")
            sample_notes = NoteMensuelle.objects.filter(
                mois=mois,
                annee_scolaire=classe.annee_scolaire,
                eleve__in=eleves[:3]
            )[:10]
            
            for note in sample_notes:
                status = "ABS" if note.absent else f"{note.note}/20"
                print(f"   • {note.eleve.matricule} - {note.matiere.nom[:15]:15} : {status}")
                
    except Exception as e:
        print(f"❌ Erreur : {e}")
        return False
    
    return True

def afficher_statistiques(classe_nom="9ÈME ANNÉE", mois="OCTOBRE"):
    """Afficher les statistiques des notes mensuelles"""
    print(f"\n{'='*70}")
    print(f"📊 STATISTIQUES DES NOTES MENSUELLES")
    print(f"{'='*70}\n")
    
    try:
        classe = ClasseNote.objects.get(nom__icontains=classe_nom)
        
        # Statistiques par matière
        matieres = MatiereNote.objects.filter(classe=classe)
        
        for matiere in matieres:
            notes = NoteMensuelle.objects.filter(
                matiere=matiere,
                mois=mois,
                annee_scolaire=classe.annee_scolaire,
                absent=False,
                note__isnull=False
            )
            
            if notes.exists():
                notes_list = [float(n.note) for n in notes]
                moyenne = sum(notes_list) / len(notes_list) if notes_list else 0
                print(f"📚 {matiere.nom:25} : {notes.count():3} notes, Moy: {moyenne:.2f}/20")
            else:
                print(f"📚 {matiere.nom:25} : Aucune note")
                
    except Exception as e:
        print(f"❌ Erreur : {e}")

if __name__ == "__main__":
    print("\n" + "="*70)
    print("🎓 GESTIONNAIRE DE NOTES MENSUELLES")
    print("="*70)
    
    # Menu principal
    print("\nQue voulez-vous faire ?")
    print("1. Vérifier les notes existantes")
    print("2. Créer des notes de test")
    print("3. Afficher les statistiques")
    print("4. Tout faire (1+2+3)")
    
    choix = input("\nVotre choix (1-4) : ")
    
    if choix == "1":
        verifier_notes_mensuelles()
    elif choix == "2":
        if not verifier_notes_mensuelles():
            creer_notes_test()
        else:
            print("\n✅ Des notes existent déjà !")
    elif choix == "3":
        afficher_statistiques()
    elif choix == "4":
        if not verifier_notes_mensuelles():
            creer_notes_test(confirmer=True)
        afficher_statistiques()
    else:
        print("❌ Choix invalide")
    
    print("\n" + "="*70)
    print("✅ TERMINÉ")
    print("="*70)
