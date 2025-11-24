"""
Diagnostic complet pour identifier pourquoi les notes et moyennes ne s'affichent pas
"""

import os
import sys
import django

# Configuration Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ecole_moderne.settings')
django.setup()

from notes.models import NoteMensuelle, ClasseNote, MatiereNote
from eleves.models import Eleve
from django.db.models import Count, Avg, Q

def diagnostic_notes_mensuelles():
    """Diagnostic des notes mensuelles"""
    print("\n" + "="*80)
    print("🔍 DIAGNOSTIC COMPLET - NOTES MENSUELLES")
    print("="*80)
    
    # 1. Vérifier les notes créées
    print("\n1️⃣ VÉRIFICATION DES NOTES CRÉÉES:")
    
    total_notes = NoteMensuelle.objects.count()
    print(f"   • Total notes mensuelles : {total_notes}")
    
    if total_notes == 0:
        print("   ❌ AUCUNE NOTE MENSUELLE TROUVÉE")
        return False
    
    # Par mois
    print("\n   📅 Répartition par mois :")
    mois_stats = NoteMensuelle.objects.values('mois').annotate(nb=Count('id')).order_by('mois')
    for ms in mois_stats:
        print(f"      • {ms['mois']} : {ms['nb']} notes")
    
    # Par classe
    print("\n   📚 Répartition par classe :")
    classe_stats = NoteMensuelle.objects.values(
        'matiere__classe__nom',
        'matiere__classe__id'
    ).annotate(nb=Count('id')).order_by('-nb')[:5]
    
    for cs in classe_stats:
        print(f"      • {cs['matiere__classe__nom']} (ID: {cs['matiere__classe__id']}) : {cs['nb']} notes")
    
    return True

def diagnostic_calculs_moyennes():
    """Diagnostic des calculs de moyennes"""
    print("\n2️⃣ DIAGNOSTIC DES CALCULS DE MOYENNES:")
    
    # Vérifier le fichier calculs_moyennes.py
    try:
        from notes.calculs_moyennes import calculer_moyenne_matiere, calculer_moyenne_generale_eleve
        print("   ✅ Module calculs_moyennes importé avec succès")
        
        # Test avec un élève qui a des notes
        eleve_test = None
        for note in NoteMensuelle.objects.all()[:1]:
            eleve_test = note.eleve
            break
        
        if eleve_test:
            print(f"\n   🧪 Test avec élève : {eleve_test.matricule} - {eleve_test.nom}")
            
            # Tester le calcul de moyenne pour une matière
            for note in NoteMensuelle.objects.filter(eleve=eleve_test)[:1]:
                matiere = note.matiere
                try:
                    resultat = calculer_moyenne_matiere(
                        eleve=eleve_test,
                        matiere=matiere,
                        periode=note.mois,
                        system_type='mensuel'
                    )
                    print(f"      • {matiere.nom} : {resultat}")
                except Exception as e:
                    print(f"      ❌ Erreur calcul {matiere.nom} : {e}")
                break
        
    except ImportError as e:
        print(f"   ❌ Erreur import calculs_moyennes : {e}")
        return False
    
    return True

def diagnostic_vues_bulletins():
    """Diagnostic des vues de bulletins"""
    print("\n3️⃣ DIAGNOSTIC DES VUES BULLETINS:")
    
    # Vérifier la vue bulletin_dynamique
    try:
        from notes.views import bulletin_dynamique
        print("   ✅ Vue bulletin_dynamique importée")
        
        # Vérifier l'import NoteMensuelle dans views.py
        import inspect
        source = inspect.getsource(bulletin_dynamique)
        
        if 'NoteMensuelle' in source:
            print("   ✅ NoteMensuelle utilisé dans bulletin_dynamique")
        else:
            print("   ⚠️ NoteMensuelle pas trouvé dans bulletin_dynamique")
        
        if "system_type == 'mensuel'" in source:
            print("   ✅ Logique mensuelle présente")
        else:
            print("   ❌ Logique mensuelle manquante")
            
    except Exception as e:
        print(f"   ❌ Erreur vue bulletin : {e}")
        return False
    
    return True

def diagnostic_templates():
    """Diagnostic des templates"""
    print("\n4️⃣ DIAGNOSTIC DES TEMPLATES:")
    
    # Vérifier les templates
    template_paths = [
        'c:/Users/LENO/Desktop/GS_hadja_kanfing_dian--main/templates/notes/bulletin_dynamique.html',
        'c:/Users/LENO/Desktop/GS_hadja_kanfing_dian--main/templates/notes/bulletin_dynamique_single.html'
    ]
    
    for path in template_paths:
        if os.path.exists(path):
            print(f"   ✅ Template trouvé : {os.path.basename(path)}")
            
            # Vérifier le contenu
            with open(path, 'r', encoding='utf-8') as f:
                content = f.read()
                
                if 'moyenne_continue' in content:
                    print(f"      ✅ Variable moyenne_continue présente")
                else:
                    print(f"      ❌ Variable moyenne_continue manquante")
                
                if 'system_type' in content:
                    print(f"      ✅ Variable system_type présente")
                else:
                    print(f"      ❌ Variable system_type manquante")
        else:
            print(f"   ❌ Template manquant : {os.path.basename(path)}")

def diagnostic_export_classement():
    """Diagnostic de l'export classement"""
    print("\n5️⃣ DIAGNOSTIC EXPORT CLASSEMENT:")
    
    try:
        from notes.export_classement import calculer_moyenne_eleve_periode
        print("   ✅ Module export_classement importé")
        
        # Test avec un élève
        eleve_test = Eleve.objects.filter(
            notes_mensuelles__isnull=False
        ).first()
        
        if eleve_test:
            print(f"   🧪 Test avec élève : {eleve_test.matricule}")
            
            # Trouver sa classe
            classe_note = ClasseNote.objects.filter(
                nom__icontains=eleve_test.classe.nom.split()[0]
            ).first()
            
            if classe_note:
                try:
                    moyenne = calculer_moyenne_eleve_periode(
                        eleve=eleve_test,
                        classe=classe_note,
                        periode='OCTOBRE',
                        type_calcul='general'
                    )
                    print(f"      ✅ Moyenne calculée : {moyenne}")
                except Exception as e:
                    print(f"      ❌ Erreur calcul moyenne : {e}")
            else:
                print("      ❌ ClasseNote non trouvée")
        else:
            print("      ❌ Aucun élève avec notes trouvé")
            
    except ImportError as e:
        print(f"   ❌ Erreur import export_classement : {e}")

def test_creation_bulletin():
    """Test de création d'un bulletin"""
    print("\n6️⃣ TEST CRÉATION BULLETIN:")
    
    # Trouver un élève avec des notes
    eleve_test = Eleve.objects.filter(
        notes_mensuelles__isnull=False
    ).first()
    
    if not eleve_test:
        print("   ❌ Aucun élève avec notes pour le test")
        return
    
    print(f"   🧪 Test avec élève : {eleve_test.matricule} - {eleve_test.nom}")
    
    # Trouver sa ClasseNote
    classe_note = ClasseNote.objects.filter(
        nom__icontains=eleve_test.classe.nom.split()[0]
    ).first()
    
    if not classe_note:
        print("   ❌ ClasseNote non trouvée")
        return
    
    print(f"   📚 ClasseNote : {classe_note.nom} (ID: {classe_note.id})")
    
    # Compter ses notes
    nb_notes = NoteMensuelle.objects.filter(
        eleve=eleve_test,
        mois='OCTOBRE'
    ).count()
    
    print(f"   📝 Notes OCTOBRE : {nb_notes}")
    
    if nb_notes > 0:
        # Afficher quelques notes
        notes = NoteMensuelle.objects.filter(
            eleve=eleve_test,
            mois='OCTOBRE'
        )[:3]
        
        print("   📊 Échantillon notes :")
        for note in notes:
            status = "ABSENT" if note.absent else f"{note.note}/20"
            print(f"      • {note.matiere.nom} : {status}")
        
        # URL de test
        print(f"\n   🌐 URL de test :")
        print(f"      https://www.myschoolgn.space/notes/bulletins/?classe_id={classe_note.id}&eleve_id={eleve_test.id}&periode=OCTOBRE&system_type=mensuel")

def recommandations():
    """Recommandations de correction"""
    print("\n" + "="*80)
    print("💡 RECOMMANDATIONS DE CORRECTION")
    print("="*80)
    
    print("\n🔧 Actions à effectuer :")
    print("1. Vérifier que les notes sont bien créées")
    print("2. Vérifier les calculs de moyennes")
    print("3. Vérifier les templates")
    print("4. Tester les URLs de bulletins")
    print("5. Vérifier les exports de classement")
    
    print("\n🚀 Commandes de test :")
    print("   cd ~/GS_hadja_kanfing_dian-")
    print("   python diagnostic_complet_notes.py")
    print("   python manage.py shell")
    print("   >>> from notes.models import NoteMensuelle")
    print("   >>> print(NoteMensuelle.objects.count())")

if __name__ == "__main__":
    print("🔍 DÉMARRAGE DU DIAGNOSTIC COMPLET")
    
    # Exécuter tous les diagnostics
    diagnostic_notes_mensuelles()
    diagnostic_calculs_moyennes()
    diagnostic_vues_bulletins()
    diagnostic_templates()
    diagnostic_export_classement()
    test_creation_bulletin()
    recommandations()
    
    print("\n" + "="*80)
    print("✅ DIAGNOSTIC TERMINÉ")
    print("="*80)
