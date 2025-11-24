"""
Test spécifique pour vérifier l'affichage des notes et moyennes
"""

import os
import sys
import django

# Configuration Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ecole_moderne.settings')
django.setup()

from notes.models import NoteMensuelle, ClasseNote, MatiereNote
from eleves.models import Eleve
from notes.calculs_moyennes import calculer_moyenne_matiere

def test_affichage_notes():
    """Test complet de l'affichage des notes"""
    print("\n" + "="*80)
    print("🧪 TEST AFFICHAGE NOTES ET MOYENNES")
    print("="*80)
    
    # 1. Vérifier les notes créées
    print("\n1️⃣ VÉRIFICATION DES NOTES:")
    
    # Chercher un élève avec des notes
    eleve_test = Eleve.objects.filter(
        notes_mensuelles__isnull=False
    ).first()
    
    if not eleve_test:
        print("❌ Aucun élève avec notes trouvé")
        return False
    
    print(f"✅ Élève test : {eleve_test.matricule} - {eleve_test.nom} {eleve_test.prenom}")
    
    # Compter ses notes
    notes = NoteMensuelle.objects.filter(eleve=eleve_test)
    print(f"📝 Total notes : {notes.count()}")
    
    # Par mois
    for mois in ['OCTOBRE', 'NOVEMBRE', 'DECEMBRE']:
        nb = notes.filter(mois=mois).count()
        if nb > 0:
            print(f"   • {mois} : {nb} notes")
    
    # 2. Test calcul de moyenne
    print("\n2️⃣ TEST CALCUL MOYENNES:")
    
    # Trouver sa ClasseNote
    classe_note = None
    for cn in ClasseNote.objects.all():
        if eleve_test.classe.nom.upper().replace('È', 'E') in cn.nom.upper().replace('È', 'E'):
            classe_note = cn
            break
    
    if not classe_note:
        print("❌ ClasseNote non trouvée")
        return False
    
    print(f"📚 ClasseNote : {classe_note.nom} (ID: {classe_note.id})")
    
    # Test calcul pour chaque matière
    matieres_testees = 0
    moyennes_calculees = 0
    
    for note in notes.filter(mois='OCTOBRE')[:3]:  # Tester 3 matières
        matiere = note.matiere
        matieres_testees += 1
        
        print(f"\n   🧪 Test matière : {matiere.nom}")
        print(f"      Note directe : {note.note if not note.absent else 'ABSENT'}")
        
        try:
            # Test avec calculs_moyennes.py
            resultat = calculer_moyenne_matiere(
                eleve=eleve_test,
                matiere=matiere,
                periode='OCTOBRE',
                system_type='mensuel'
            )
            
            print(f"      Calcul fonction : {resultat}")
            
            if resultat.get('moyenne_continue'):
                moyennes_calculees += 1
                print(f"      ✅ Moyenne calculée : {resultat['moyenne_continue']}")
            else:
                print(f"      ❌ Aucune moyenne calculée")
                
        except Exception as e:
            print(f"      ❌ Erreur calcul : {e}")
    
    print(f"\n📊 Résumé : {moyennes_calculees}/{matieres_testees} moyennes calculées")
    
    # 3. Test simulation vue bulletin
    print("\n3️⃣ TEST SIMULATION VUE BULLETIN:")
    
    # Simuler la logique de bulletin_dynamique
    matiere_test = notes.filter(mois='OCTOBRE').first().matiere
    
    print(f"   🎯 Test avec {matiere_test.nom}")
    
    # Logique exacte de la vue
    moyenne_continue = None
    
    try:
        note_mensuelle = NoteMensuelle.objects.get(
            eleve=eleve_test,
            matiere=matiere_test,
            mois='OCTOBRE',
            annee_scolaire=classe_note.annee_scolaire
        )
        
        print(f"   📝 Note trouvée : {note_mensuelle.note} (absent: {note_mensuelle.absent})")
        
        if not note_mensuelle.absent and note_mensuelle.note is not None:
            moyenne_continue = float(note_mensuelle.note)
            print(f"   ✅ moyenne_continue = {moyenne_continue}")
        else:
            print(f"   ❌ Note absente ou nulle")
            
    except NoteMensuelle.DoesNotExist:
        print(f"   ❌ NoteMensuelle.DoesNotExist")
    
    # 4. Test structure de données pour template
    print("\n4️⃣ TEST STRUCTURE DONNÉES TEMPLATE:")
    
    # Simuler la structure envoyée au template
    matiere_note = {
        'matiere': matiere_test,
        'moyenne_continue': moyenne_continue,
        'moyenne': None,  # Pour système mensuel
        'note_composition': None,
        'moyenne_matiere': moyenne_continue,
        'points': moyenne_continue * float(matiere_test.coefficient) if moyenne_continue else None
    }
    
    print(f"   📋 Structure matiere_note :")
    for key, value in matiere_note.items():
        if key != 'matiere':
            print(f"      • {key} : {value}")
    
    # Test logique template
    print(f"\n   🎨 Test logique template :")
    
    # Logique du template bulletin_dynamique.html ligne 827-828
    if matiere_note['moyenne']:
        affichage = matiere_note['moyenne']
        source = "moyenne"
    elif matiere_note['moyenne_continue']:
        affichage = matiere_note['moyenne_continue']
        source = "moyenne_continue"
    else:
        affichage = "-"
        source = "aucune"
    
    print(f"      Affichage final : {affichage} (source: {source})")
    
    # 5. URL de test
    print("\n5️⃣ URL DE TEST:")
    url = f"https://www.myschoolgn.space/notes/bulletins/?classe_id={classe_note.id}&eleve_id={eleve_test.id}&periode=OCTOBRE&system_type=mensuel"
    print(f"   🌐 {url}")
    
    return True

def test_export_classement():
    """Test de l'export classement"""
    print("\n" + "="*80)
    print("🧪 TEST EXPORT CLASSEMENT")
    print("="*80)
    
    try:
        from notes.export_classement import calculer_moyenne_eleve_periode
        
        # Trouver une classe avec des notes
        classe_avec_notes = None
        
        for cn in ClasseNote.objects.all():
            nb_notes = NoteMensuelle.objects.filter(
                matiere__classe=cn,
                mois='OCTOBRE'
            ).count()
            
            if nb_notes > 0:
                classe_avec_notes = cn
                print(f"✅ Classe test : {cn.nom} ({nb_notes} notes)")
                break
        
        if not classe_avec_notes:
            print("❌ Aucune classe avec notes trouvée")
            return False
        
        # Trouver un élève de cette classe
        eleve_test = None
        
        # Recherche flexible
        for eleve in Eleve.objects.filter(statut__in=['ACTIF', 'INSCRIT']):
            if NoteMensuelle.objects.filter(
                eleve=eleve,
                matiere__classe=classe_avec_notes,
                mois='OCTOBRE'
            ).exists():
                eleve_test = eleve
                break
        
        if not eleve_test:
            print("❌ Aucun élève avec notes trouvé")
            return False
        
        print(f"✅ Élève test : {eleve_test.matricule}")
        
        # Test calcul moyenne
        try:
            moyenne = calculer_moyenne_eleve_periode(
                eleve=eleve_test,
                classe=classe_avec_notes,
                periode='OCTOBRE',
                type_calcul='general'
            )
            
            print(f"✅ Moyenne calculée : {moyenne}")
            
            if moyenne and moyenne > 0:
                print("✅ Export classement devrait fonctionner")
            else:
                print("❌ Moyenne nulle - problème dans le calcul")
                
        except Exception as e:
            print(f"❌ Erreur calcul moyenne export : {e}")
            import traceback
            traceback.print_exc()
            
    except ImportError as e:
        print(f"❌ Erreur import export_classement : {e}")

def corrections_proposees():
    """Propose des corrections"""
    print("\n" + "="*80)
    print("🔧 CORRECTIONS PROPOSÉES")
    print("="*80)
    
    print("\n📝 Problèmes potentiels identifiés :")
    print("1. Décalage entre Classe (élèves) et ClasseNote (notes)")
    print("2. Année scolaire non correspondante")
    print("3. Notes créées mais pas dans la bonne ClasseNote")
    print("4. Calculs de moyennes qui échouent silencieusement")
    
    print("\n🔧 Solutions à appliquer :")
    print("1. Vérifier la correspondance Classe ↔ ClasseNote")
    print("2. Corriger l'année scolaire si nécessaire")
    print("3. Recréer les notes avec la bonne ClasseNote")
    print("4. Ajouter des logs de debug dans les calculs")
    
    print("\n🚀 Commandes de correction :")
    print("   cd ~/GS_hadja_kanfing_dian-")
    print("   python test_notes_affichage.py")
    print("   python reparer_lien_classe_notes.py")

if __name__ == "__main__":
    print("🔍 DÉMARRAGE DES TESTS D'AFFICHAGE")
    
    if test_affichage_notes():
        test_export_classement()
    
    corrections_proposees()
    
    print("\n" + "="*80)
    print("✅ TESTS TERMINÉS")
    print("="*80)
