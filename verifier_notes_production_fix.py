"""
Script CORRIGÉ pour vérifier les notes mensuelles en production
Gère le cas où plusieurs classes ont le même nom
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
    
    # Rechercher toutes les classes qui correspondent
    classes = ClasseNote.objects.filter(nom__icontains=classe_nom)
    
    if not classes.exists():
        print(f"❌ Aucune classe contenant '{classe_nom}' trouvée")
        return False
    
    if classes.count() > 1:
        print(f"⚠️ {classes.count()} classes trouvées pour '{classe_nom}':")
        for idx, c in enumerate(classes, 1):
            print(f"   {idx}. {c.nom} - {c.annee_scolaire} (ID: {c.id})")
        
        # Sélection de la classe la plus récente
        classe = classes.order_by('-annee_scolaire', 'id').first()
        print(f"\n✅ Sélection automatique : {classe.nom} ({classe.annee_scolaire})")
    else:
        classe = classes.first()
        print(f"✅ Classe trouvée : {classe.nom}")
    
    print(f"   Année scolaire : {classe.annee_scolaire}")
    print(f"   ID : {classe.id}")
    
    # Lister les élèves
    eleves = Eleve.objects.filter(classe__nom__icontains=classe.nom.replace('È', 'E'), statut='INSCRIT')
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
            # Trouver la classe (gestion classes multiples)
            classes = ClasseNote.objects.filter(nom__icontains=classe_nom)
            
            if not classes.exists():
                print(f"❌ Aucune classe trouvée pour '{classe_nom}'")
                return False
            
            if classes.count() > 1:
                print(f"⚠️ {classes.count()} classes trouvées:")
                for idx, c in enumerate(classes, 1):
                    print(f"   {idx}. {c.nom} - {c.annee_scolaire} (ID: {c.id})")
                
                # Demander à l'utilisateur de choisir
                try:
                    choix = input(f"\nChoisissez le numéro (1-{classes.count()}) : ")
                    classe = classes[int(choix) - 1]
                except (ValueError, IndexError):
                    print("❌ Choix invalide, sélection automatique de la plus récente")
                    classe = classes.order_by('-annee_scolaire', 'id').first()
            else:
                classe = classes.first()
            
            print(f"\n✅ Classe sélectionnée : {classe.nom} ({classe.annee_scolaire})")
            
            # Récupérer les matières
            matieres = MatiereNote.objects.filter(classe=classe)
            print(f"📚 Matières : {matieres.count()}")
            
            if not matieres.exists():
                print("❌ Aucune matière configurée pour cette classe")
                return False
            
            # Récupérer les élèves
            eleves = Eleve.objects.filter(
                classe__nom__icontains=classe.nom.replace('È', 'E'),
                classe__annee_scolaire=classe.annee_scolaire,
                statut='INSCRIT'
            )
            print(f"👥 Élèves : {eleves.count()}")
            
            if not eleves.exists():
                print("❌ Aucun élève inscrit dans cette classe")
                return False
            
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
        import traceback
        traceback.print_exc()
        return False
    
    return True

def afficher_statistiques(classe_nom="9ÈME ANNÉE", mois="OCTOBRE"):
    """Afficher les statistiques des notes mensuelles"""
    print(f"\n{'='*70}")
    print(f"📊 STATISTIQUES DES NOTES MENSUELLES")
    print(f"{'='*70}\n")
    
    try:
        # Gestion classes multiples
        classes = ClasseNote.objects.filter(nom__icontains=classe_nom)
        
        if not classes.exists():
            print(f"❌ Aucune classe trouvée pour '{classe_nom}'")
            return
        
        classe = classes.order_by('-annee_scolaire', 'id').first()
        print(f"Classe : {classe.nom} ({classe.annee_scolaire})\n")
        
        # Statistiques par matière
        matieres = MatiereNote.objects.filter(classe=classe)
        
        if not matieres.exists():
            print("❌ Aucune matière configurée")
            return
        
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
                min_note = min(notes_list) if notes_list else 0
                max_note = max(notes_list) if notes_list else 0
                print(f"📚 {matiere.nom:25} : {notes.count():3} notes")
                print(f"   Moyenne: {moyenne:.2f}/20, Min: {min_note:.1f}, Max: {max_note:.1f}")
            else:
                print(f"📚 {matiere.nom:25} : Aucune note")
                
    except Exception as e:
        print(f"❌ Erreur : {e}")
        import traceback
        traceback.print_exc()

def diagnostic_complet():
    """Diagnostic complet du système de notes"""
    print("\n" + "="*70)
    print("🔍 DIAGNOSTIC COMPLET DU SYSTÈME")
    print("="*70)
    
    # 1. Lister toutes les classes 9ème
    print("\n📚 TOUTES LES CLASSES 9ÈME :")
    classes_9 = ClasseNote.objects.filter(nom__icontains='9')
    
    if classes_9.exists():
        for c in classes_9:
            nb_matieres = MatiereNote.objects.filter(classe=c).count()
            print(f"   • ID {c.id}: {c.nom} - {c.annee_scolaire} ({nb_matieres} matières)")
    else:
        print("   ❌ Aucune classe 9ème trouvée")
    
    # 2. Chercher l'élève CL9-011
    print("\n👤 RECHERCHE ÉLÈVE CL9-011 :")
    try:
        eleve = Eleve.objects.get(matricule='CL9-011')
        print(f"   ✅ Trouvé : {eleve.nom} {eleve.prenom}")
        print(f"   • Classe : {eleve.classe.nom}")
        print(f"   • Année : {eleve.classe.annee_scolaire}")
        print(f"   • Statut : {eleve.statut}")
        
        # Compter ses notes
        nb_notes = NoteMensuelle.objects.filter(
            eleve=eleve,
            mois='OCTOBRE'
        ).count()
        print(f"   • Notes OCTOBRE : {nb_notes}")
        
    except Eleve.DoesNotExist:
        print("   ❌ Élève non trouvé")
    
    # 3. Statistiques globales
    print("\n📊 STATISTIQUES GLOBALES :")
    total_notes = NoteMensuelle.objects.filter(mois='OCTOBRE').count()
    print(f"   • Total notes OCTOBRE (toute l'école) : {total_notes}")
    
    # Par année scolaire
    from django.db.models import Count
    stats = NoteMensuelle.objects.filter(mois='OCTOBRE').values('annee_scolaire').annotate(nb=Count('id'))
    for s in stats:
        print(f"   • Année {s['annee_scolaire']} : {s['nb']} notes")

if __name__ == "__main__":
    print("\n" + "="*70)
    print("🎓 GESTIONNAIRE DE NOTES MENSUELLES (VERSION CORRIGÉE)")
    print("="*70)
    
    # Menu principal
    print("\nQue voulez-vous faire ?")
    print("1. Vérifier les notes existantes")
    print("2. Créer des notes de test")
    print("3. Afficher les statistiques")
    print("4. Diagnostic complet")
    print("5. Tout faire (1+2+3+4)")
    
    choix = input("\nVotre choix (1-5) : ")
    
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
        diagnostic_complet()
    elif choix == "5":
        diagnostic_complet()
        if not verifier_notes_mensuelles():
            creer_notes_test(confirmer=True)
        afficher_statistiques()
    else:
        print("❌ Choix invalide")
    
    print("\n" + "="*70)
    print("✅ TERMINÉ")
    print("="*70)
