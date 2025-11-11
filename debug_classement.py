"""
Script de débogage pour vérifier les notes et le classement
"""
import os
import sys
import django

# Configuration Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ecole_moderne.settings')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
django.setup()

from eleves.models import Eleve, Classe
from notes.models import ClasseNote, MatiereNote, NoteMensuelle, CompositionNote
from decimal import Decimal
from datetime import datetime

def debug_classement():
    """Vérifier pourquoi les rangs et moyennes n'apparaissent pas"""
    
    print("="*80)
    print("DÉBOGAGE DU SYSTÈME DE CLASSEMENT")
    print("="*80)
    
    # 1. Vérifier les élèves
    print("\n1. VÉRIFICATION DES ÉLÈVES")
    print("-"*50)
    
    # Chercher les élèves par matricule partiel
    eleves = Eleve.objects.filter(matricule__icontains='CL7').order_by('matricule')[:5]
    
    if not eleves:
        print("❌ Aucun élève trouvé avec 'CL7' dans le matricule")
        
        # Afficher quelques élèves existants
        print("\n📋 Élèves existants (échantillon):")
        for eleve in Eleve.objects.filter(statut='ACTIF')[:5]:
            print(f"   - {eleve.matricule}: {eleve.nom} {eleve.prenom} (Classe: {eleve.classe.nom})")
    else:
        print(f"✅ {len(eleves)} élève(s) trouvé(s) avec 'CL7':")
        for eleve in eleves:
            print(f"   - {eleve.matricule}: {eleve.nom} {eleve.prenom}")
            print(f"     Classe: {eleve.classe.nom if eleve.classe else 'Non assigné'}")
    
    # 2. Vérifier les classes de notes
    print("\n2. VÉRIFICATION DES CLASSES DE NOTES")
    print("-"*50)
    
    classes_notes = ClasseNote.objects.all()[:5]
    
    if not classes_notes:
        print("❌ Aucune classe de notes trouvée")
    else:
        print(f"✅ {ClasseNote.objects.count()} classe(s) de notes trouvée(s):")
        for cn in classes_notes:
            print(f"   - {cn.nom} ({cn.annee_scolaire})")
            
            # Vérifier les matières
            matieres = MatiereNote.objects.filter(classe=cn, actif=True)
            print(f"     → {matieres.count()} matière(s) active(s)")
            
            # Vérifier les élèves correspondants
            try:
                classe_eleve = Classe.objects.filter(
                    nom=cn.nom,
                    annee_scolaire=cn.annee_scolaire,
                    ecole=cn.ecole
                ).first()
                
                if classe_eleve:
                    nb_eleves = Eleve.objects.filter(classe=classe_eleve, statut='ACTIF').count()
                    print(f"     → {nb_eleves} élève(s) actif(s) dans cette classe")
                else:
                    print(f"     ⚠️ Pas de classe élève correspondante")
            except Exception as e:
                print(f"     ❌ Erreur: {e}")
    
    # 3. Vérifier les notes mensuelles
    print("\n3. VÉRIFICATION DES NOTES MENSUELLES")
    print("-"*50)
    
    notes_mensuelles = NoteMensuelle.objects.all()[:10]
    
    if not notes_mensuelles:
        print("❌ Aucune note mensuelle trouvée dans la base de données")
    else:
        print(f"✅ {NoteMensuelle.objects.count()} note(s) mensuelle(s) trouvée(s):")
        
        # Statistiques par mois
        from django.db.models import Count
        stats_mois = NoteMensuelle.objects.values('mois').annotate(count=Count('id')).order_by('-count')
        
        for stat in stats_mois[:3]:
            print(f"   - {stat['mois']}: {stat['count']} notes")
        
        # Afficher quelques exemples
        print("\n   Exemples de notes:")
        for note in notes_mensuelles[:5]:
            print(f"   - {note.eleve.nom} {note.eleve.prenom}: {note.note}/20")
            print(f"     Matière: {note.matiere.nom}, Mois: {note.mois}")
    
    # 4. Vérifier les notes de composition
    print("\n4. VÉRIFICATION DES NOTES DE COMPOSITION")
    print("-"*50)
    
    notes_composition = CompositionNote.objects.all()[:10]
    
    if not notes_composition:
        print("❌ Aucune note de composition trouvée dans la base de données")
    else:
        print(f"✅ {CompositionNote.objects.count()} note(s) de composition trouvée(s):")
        
        # Statistiques par période
        stats_periode = CompositionNote.objects.values('periode').annotate(count=Count('id')).order_by('-count')
        
        for stat in stats_periode[:3]:
            print(f"   - {stat['periode']}: {stat['count']} notes")
        
        # Afficher quelques exemples
        print("\n   Exemples de notes:")
        for note in notes_composition[:5]:
            print(f"   - {note.eleve.nom} {note.eleve.prenom}: {note.note}/20")
            print(f"     Matière: {note.matiere.nom}, Période: {note.periode}")
    
    # 5. Test de calcul de moyenne
    print("\n5. TEST DE CALCUL DE MOYENNE")
    print("-"*50)
    
    # Prendre un élève avec des notes
    eleve_test = None
    
    # Chercher un élève avec des notes mensuelles
    if NoteMensuelle.objects.exists():
        note_test = NoteMensuelle.objects.first()
        eleve_test = note_test.eleve
        print(f"✅ Test avec l'élève: {eleve_test.nom} {eleve_test.prenom}")
        
        # Calculer sa moyenne pour le mois de la note
        notes_eleve = NoteMensuelle.objects.filter(
            eleve=eleve_test,
            mois=note_test.mois,
            annee_scolaire=note_test.annee_scolaire
        )
        
        total_notes = Decimal('0')
        total_coefficients = Decimal('0')
        
        print(f"   Notes pour {note_test.mois}:")
        for note in notes_eleve:
            if not note.absent and note.note:
                coefficient = note.matiere.coefficient or Decimal('1')
                total_notes += note.note * coefficient
                total_coefficients += coefficient
                print(f"   - {note.matiere.nom}: {note.note}/20 (coef: {coefficient})")
        
        if total_coefficients > 0:
            moyenne = total_notes / total_coefficients
            print(f"   → Moyenne calculée: {moyenne:.2f}/20")
        else:
            print(f"   → Pas de notes pour calculer une moyenne")
    else:
        print("❌ Aucun élève avec des notes pour tester")
    
    # 6. Vérifier la configuration du système de notes
    print("\n6. CONFIGURATION DU SYSTÈME")
    print("-"*50)
    
    print(f"Année scolaire courante: {datetime.now().year}")
    print(f"Nombre total d'élèves actifs: {Eleve.objects.filter(statut='ACTIF').count()}")
    print(f"Nombre total de classes: {Classe.objects.count()}")
    print(f"Nombre total de classes de notes: {ClasseNote.objects.count()}")
    print(f"Nombre total de matières: {MatiereNote.objects.count()}")
    
    # Recommandations
    print("\n" + "="*80)
    print("RECOMMANDATIONS")
    print("="*80)
    
    if NoteMensuelle.objects.count() == 0 and CompositionNote.objects.count() == 0:
        print("⚠️ AUCUNE NOTE SAISIE DANS LE SYSTÈME!")
        print("   → Vous devez d'abord saisir des notes pour que le classement fonctionne")
        print("   → Allez dans le module Notes > Saisie des notes")
    
    if ClasseNote.objects.count() == 0:
        print("⚠️ AUCUNE CLASSE DE NOTES CONFIGURÉE!")
        print("   → Créez d'abord des classes de notes dans le module Notes")
    
    if MatiereNote.objects.count() == 0:
        print("⚠️ AUCUNE MATIÈRE CONFIGURÉE!")
        print("   → Ajoutez des matières pour chaque classe de notes")
    
    print("\n✅ Fin du débogage")

if __name__ == "__main__":
    debug_classement()
