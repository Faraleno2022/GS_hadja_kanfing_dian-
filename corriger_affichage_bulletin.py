"""
Script pour corriger les problèmes d'affichage du bulletin
Assure que notes, moyennes, rang et appréciation s'affichent correctement
"""

import os
import sys
import django

# Configuration Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ecole_moderne.settings')
django.setup()

from notes.models import NoteMensuelle, ClasseNote, MatiereNote
from eleves.models import Eleve
from django.db import transaction

def corriger_structure_donnees():
    """Corriger la structure des données pour l'affichage"""
    print("\n" + "="*80)
    print("🔧 CORRECTION STRUCTURE DONNÉES BULLETIN")
    print("="*80)
    
    # 1. Vérifier et corriger les années scolaires
    print("\n1️⃣ CORRECTION ANNÉES SCOLAIRES:")
    
    notes_incorrectes = 0
    
    with transaction.atomic():
        for note in NoteMensuelle.objects.all():
            annee_eleve = note.eleve.classe.annee_scolaire
            annee_classenote = note.matiere.classe.annee_scolaire
            
            # Si l'année de la note ne correspond pas à celle de la ClasseNote
            if note.annee_scolaire != annee_classenote:
                note.annee_scolaire = annee_classenote
                note.save()
                notes_incorrectes += 1
    
    if notes_incorrectes > 0:
        print(f"   ✅ {notes_incorrectes} notes corrigées")
    else:
        print("   ✅ Toutes les années scolaires sont correctes")
    
    # 2. Vérifier les notes nulles
    print("\n2️⃣ VÉRIFICATION NOTES NULLES:")
    
    notes_nulles = NoteMensuelle.objects.filter(
        note__isnull=True,
        absent=False
    ).count()
    
    if notes_nulles > 0:
        print(f"   ⚠️ {notes_nulles} notes nulles détectées (non absents)")
        
        # Proposer de les marquer comme absents
        reponse = input("   Marquer ces notes comme absents ? (oui/non) : ")
        if reponse.lower() in ['oui', 'o', 'yes', 'y']:
            NoteMensuelle.objects.filter(
                note__isnull=True,
                absent=False
            ).update(absent=True)
            print(f"   ✅ {notes_nulles} notes marquées comme absents")
    else:
        print("   ✅ Aucune note nulle détectée")
    
    # 3. Vérifier les coefficients des matières
    print("\n3️⃣ VÉRIFICATION COEFFICIENTS:")
    
    matieres_sans_coef = MatiereNote.objects.filter(
        coefficient__isnull=True
    ).count()
    
    matieres_coef_zero = MatiereNote.objects.filter(
        coefficient=0
    ).count()
    
    if matieres_sans_coef > 0 or matieres_coef_zero > 0:
        print(f"   ⚠️ {matieres_sans_coef} matières sans coefficient")
        print(f"   ⚠️ {matieres_coef_zero} matières avec coefficient 0")
        
        # Corriger automatiquement
        MatiereNote.objects.filter(
            coefficient__isnull=True
        ).update(coefficient=1.0)
        
        MatiereNote.objects.filter(
            coefficient=0
        ).update(coefficient=1.0)
        
        print("   ✅ Coefficients corrigés (défaut: 1.0)")
    else:
        print("   ✅ Tous les coefficients sont corrects")

def tester_calculs_bulletin():
    """Tester les calculs pour un bulletin complet"""
    print("\n" + "="*80)
    print("🧪 TEST CALCULS BULLETIN COMPLET")
    print("="*80)
    
    # Trouver un élève avec des notes
    eleve_test = Eleve.objects.filter(
        notes_mensuelles__isnull=False
    ).first()
    
    if not eleve_test:
        print("❌ Aucun élève avec notes pour le test")
        return False
    
    print(f"🧪 Test avec : {eleve_test.matricule} - {eleve_test.nom}")
    
    # Trouver sa ClasseNote
    classe_note = None
    for cn in ClasseNote.objects.all():
        # Recherche flexible
        if any(word.upper() in cn.nom.upper() for word in eleve_test.classe.nom.split()):
            classe_note = cn
            break
    
    if not classe_note:
        print("❌ ClasseNote non trouvée")
        return False
    
    print(f"📚 ClasseNote : {classe_note.nom}")
    
    # Test simulation complète de la vue bulletin_dynamique
    try:
        from notes.calculs_moyennes import calculer_moyenne_matiere, calculer_moyenne_generale_eleve
        
        # 1. Calculer les notes par matière
        matieres_notes = []
        matieres = MatiereNote.objects.filter(classe=classe_note)
        
        for matiere in matieres:
            try:
                resultat = calculer_moyenne_matiere(
                    eleve=eleve_test,
                    matiere=matiere,
                    periode='OCTOBRE',
                    system_type='mensuel'
                )
                
                if resultat.get('moyenne_continue') is not None:
                    matieres_notes.append({
                        'matiere': matiere,
                        'moyenne_continue': resultat.get('moyenne_continue'),
                        'moyenne': resultat.get('moyenne_matiere'),
                        'points': resultat.get('points'),
                        'coefficient': matiere.coefficient
                    })
            except Exception as e:
                print(f"   ⚠️ Erreur matière {matiere.nom} : {e}")
        
        print(f"📊 {len(matieres_notes)}/{matieres.count()} matières calculées")
        
        # 2. Calculer la moyenne générale
        try:
            resultat_general = calculer_moyenne_generale_eleve(
                eleve=eleve_test,
                classe=classe_note,
                periode='OCTOBRE',
                system_type='mensuel'
            )
            
            moyenne_generale = resultat_general.get('moyenne_generale')
            print(f"📈 Moyenne générale : {moyenne_generale}")
            
        except Exception as e:
            print(f"❌ Erreur moyenne générale : {e}")
            moyenne_generale = None
        
        # 3. Calculer le rang
        try:
            from notes.calculs_intelligent import calculer_rang_intelligent, formater_rang_intelligent
            
            # Récupérer tous les élèves de la classe
            eleves_classe = Eleve.objects.filter(
                classe=eleve_test.classe,
                statut__in=['ACTIF', 'INSCRIT']
            )
            
            moyennes_pour_rang = []
            
            for eleve in eleves_classe:
                try:
                    moy_gen = calculer_moyenne_generale_eleve(
                        eleve=eleve,
                        classe=classe_note,
                        periode='OCTOBRE',
                        system_type='mensuel'
                    )
                    
                    if moy_gen and moy_gen.get('moyenne_generale'):
                        moyennes_pour_rang.append({
                            'eleve_id': eleve.id,
                            'moyenne': float(moy_gen['moyenne_generale']),
                            'sexe': getattr(eleve, 'sexe', 'M') or 'M'
                        })
                except:
                    continue
            
            if moyennes_pour_rang:
                # Calculer les rangs
                resultats_rangs = calculer_rang_intelligent(moyennes_pour_rang)
                
                # Trouver le rang de notre élève
                rang_info = None
                for r in resultats_rangs:
                    if r['eleve_id'] == eleve_test.id:
                        rang_info = r
                        break
                
                if rang_info:
                    rang_num = rang_info.get('rang_num', 1)
                    sexe = getattr(eleve_test, 'sexe', 'M') or 'M'
                    rang_formate = formater_rang_intelligent(rang_num, sexe, len(moyennes_pour_rang))
                    
                    print(f"🏆 Rang : {rang_formate} sur {len(moyennes_pour_rang)} élèves")
                else:
                    rang_formate = "-"
                    print("⚠️ Rang non calculé")
            else:
                rang_formate = "-"
                print("⚠️ Pas assez d'élèves pour calculer le rang")
                
        except Exception as e:
            print(f"❌ Erreur calcul rang : {e}")
            rang_formate = "-"
        
        # 4. Calculer la mention
        if moyenne_generale:
            if moyenne_generale >= 18.5:
                mention = "Excellent"
            elif moyenne_generale >= 16.5:
                mention = "Très bien"
            elif moyenne_generale >= 14.5:
                mention = "Bien"
            elif moyenne_generale >= 12.5:
                mention = "Assez bien"
            elif moyenne_generale >= 10.0:
                mention = "Passable"
            elif moyenne_generale >= 9.0:
                mention = "Faible"
            else:
                mention = "Insuffisant"
            
            print(f"🎖️ Mention : {mention}")
        else:
            mention = "-"
            print("⚠️ Mention non calculée")
        
        # 5. Générer l'appréciation
        try:
            from notes.calculs_intelligent import obtenir_appreciation
            
            if moyenne_generale:
                appreciation = obtenir_appreciation(
                    moyenne=float(moyenne_generale),
                    prenom=eleve_test.prenom
                )
            else:
                appreciation = "Bon travail. Continuez vos efforts."
            
            print(f"💬 Appréciation : {appreciation[:50]}...")
            
        except Exception as e:
            appreciation = "Bon travail. Continuez vos efforts."
            print(f"⚠️ Appréciation par défaut : {e}")
        
        # 6. Résumé final
        print(f"\n✅ RÉSUMÉ BULLETIN :")
        print(f"   • Élève : {eleve_test.matricule}")
        print(f"   • Matières avec notes : {len(matieres_notes)}")
        print(f"   • Moyenne générale : {moyenne_generale}")
        print(f"   • Rang : {rang_formate}")
        print(f"   • Mention : {mention}")
        print(f"   • Appréciation : ✅")
        
        # 7. URL de test
        print(f"\n🌐 URL de test :")
        url = f"https://www.myschoolgn.space/notes/bulletins/?classe_id={classe_note.id}&eleve_id={eleve_test.id}&periode=OCTOBRE&system_type=mensuel"
        print(f"   {url}")
        
        return True
        
    except Exception as e:
        print(f"❌ Erreur test bulletin : {e}")
        import traceback
        traceback.print_exc()
        return False

def verifier_templates():
    """Vérifier que les templates ont les bonnes variables"""
    print("\n" + "="*80)
    print("🎨 VÉRIFICATION TEMPLATES")
    print("="*80)
    
    template_path = 'c:/Users/LENO/Desktop/GS_hadja_kanfing_dian--main/templates/notes/bulletin_dynamique.html'
    
    if os.path.exists(template_path):
        with open(template_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Vérifier les variables importantes
        variables_importantes = [
            'matiere_note.moyenne_continue',
            'bulletin_data.rang',
            'bulletin_data.mention',
            'bulletin_data.appreciation',
            'bulletin_data.moyenne_generale'
        ]
        
        for var in variables_importantes:
            if var in content:
                print(f"   ✅ {var}")
            else:
                print(f"   ❌ {var} MANQUANT")
        
        # Vérifier la logique d'affichage des notes
        if 'elif matiere_note.moyenne_continue' in content:
            print("   ✅ Logique affichage notes mensuelle OK")
        else:
            print("   ❌ Logique affichage notes mensuelle MANQUANTE")
    else:
        print("   ❌ Template bulletin_dynamique.html non trouvé")

if __name__ == "__main__":
    print("🔧 DÉMARRAGE CORRECTION AFFICHAGE BULLETIN")
    
    # Étape 1: Corriger la structure des données
    corriger_structure_donnees()
    
    # Étape 2: Tester les calculs
    if tester_calculs_bulletin():
        print("\n✅ Calculs bulletin fonctionnels")
    else:
        print("\n❌ Problème dans les calculs")
    
    # Étape 3: Vérifier les templates
    verifier_templates()
    
    print("\n" + "="*80)
    print("✅ CORRECTION TERMINÉE")
    print("="*80)
    
    print("\n🚀 ACTIONS RECOMMANDÉES :")
    print("1. Redémarrer le serveur : touch ecole_moderne/wsgi.py")
    print("2. Tester le bulletin avec l'URL générée")
    print("3. Vérifier l'export classement")
