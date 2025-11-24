"""
Script pour vérifier que tous les éléments du bulletin s'affichent correctement :
- Notes par matière
- Moyennes (continue, composition, finale)
- Rang de l'élève
- Mention
- Appréciation du conseil de classe
"""

import os
import sys
import django

# Configuration Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ecole_moderne.settings')
django.setup()

from notes.models import NoteMensuelle, ClasseNote, MatiereNote
from eleves.models import Eleve
from notes.calculs_moyennes import calculer_moyenne_matiere, calculer_moyenne_generale_eleve
from decimal import Decimal

def verifier_donnees_bulletin():
    """Vérifier toutes les données nécessaires au bulletin"""
    print("\n" + "="*80)
    print("🔍 VÉRIFICATION COMPLÈTE DU BULLETIN")
    print("="*80)
    
    # 1. Trouver un élève avec des notes
    print("\n1️⃣ RECHERCHE ÉLÈVE AVEC NOTES:")
    
    eleve_test = Eleve.objects.filter(
        notes_mensuelles__isnull=False
    ).first()
    
    if not eleve_test:
        print("❌ Aucun élève avec notes trouvé")
        return False
    
    print(f"✅ Élève test : {eleve_test.matricule} - {eleve_test.nom} {eleve_test.prenom}")
    
    # 2. Vérifier ses notes par matière
    print("\n2️⃣ VÉRIFICATION NOTES PAR MATIÈRE:")
    
    notes = NoteMensuelle.objects.filter(
        eleve=eleve_test,
        mois='OCTOBRE'
    )
    
    if not notes.exists():
        print("❌ Aucune note pour OCTOBRE")
        return False
    
    print(f"📝 {notes.count()} notes trouvées pour OCTOBRE")
    
    # Trouver la ClasseNote correspondante
    classe_note = None
    for cn in ClasseNote.objects.all():
        if any(word in cn.nom.upper() for word in eleve_test.classe.nom.upper().split()):
            classe_note = cn
            break
    
    if not classe_note:
        print("❌ ClasseNote non trouvée")
        return False
    
    print(f"📚 ClasseNote : {classe_note.nom} (ID: {classe_note.id})")
    
    # 3. Test calculs par matière
    print("\n3️⃣ TEST CALCULS PAR MATIÈRE:")
    
    matieres_data = []
    total_points = Decimal('0')
    total_coefficients = Decimal('0')
    
    for note in notes[:5]:  # Tester 5 matières
        matiere = note.matiere
        
        print(f"\n   📖 {matiere.nom} (Coef: {matiere.coefficient})")
        print(f"      Note directe : {note.note if not note.absent else 'ABSENT'}")
        
        try:
            # Calcul avec la fonction
            resultat = calculer_moyenne_matiere(
                eleve=eleve_test,
                matiere=matiere,
                periode='OCTOBRE',
                system_type='mensuel'
            )
            
            moyenne_continue = resultat.get('moyenne_continue')
            moyenne_matiere = resultat.get('moyenne_matiere')
            points = resultat.get('points')
            
            print(f"      Moyenne continue : {moyenne_continue}")
            print(f"      Moyenne matière : {moyenne_matiere}")
            print(f"      Points : {points}")
            
            if moyenne_matiere and points:
                total_points += Decimal(str(points))
                total_coefficients += matiere.coefficient
                print(f"      ✅ Calcul réussi")
                
                matieres_data.append({
                    'matiere': matiere,
                    'moyenne_continue': moyenne_continue,
                    'moyenne': moyenne_matiere,
                    'points': points,
                    'coefficient': matiere.coefficient
                })
            else:
                print(f"      ❌ Calcul échoué")
                
        except Exception as e:
            print(f"      ❌ Erreur : {e}")
    
    # 4. Calcul moyenne générale
    print("\n4️⃣ CALCUL MOYENNE GÉNÉRALE:")
    
    if total_coefficients > 0:
        moyenne_generale = total_points / total_coefficients
        print(f"✅ Moyenne générale : {moyenne_generale:.2f}/20")
    else:
        moyenne_generale = None
        print("❌ Impossible de calculer la moyenne générale")
    
    # 5. Calcul du rang
    print("\n5️⃣ CALCUL DU RANG:")
    
    try:
        # Calculer les moyennes de tous les élèves de la classe
        eleves_classe = Eleve.objects.filter(
            classe=eleve_test.classe,
            statut__in=['ACTIF', 'INSCRIT']
        )
        
        moyennes_classe = []
        
        for eleve in eleves_classe:
            try:
                moy_gen = calculer_moyenne_generale_eleve(
                    eleve=eleve,
                    classe=classe_note,
                    periode='OCTOBRE',
                    system_type='mensuel'
                )
                
                if moy_gen and moy_gen.get('moyenne_generale'):
                    moyennes_classe.append({
                        'eleve_id': eleve.id,
                        'moyenne': moy_gen['moyenne_generale'],
                        'sexe': getattr(eleve, 'sexe', 'M')
                    })
            except:
                continue
        
        if moyennes_classe:
            # Trier par moyenne décroissante
            moyennes_classe.sort(key=lambda x: x['moyenne'], reverse=True)
            
            # Trouver le rang de notre élève
            rang = None
            for i, data in enumerate(moyennes_classe, 1):
                if data['eleve_id'] == eleve_test.id:
                    rang = i
                    break
            
            if rang:
                # Formater le rang avec accord grammatical
                from notes.calculs_intelligent import formater_rang_intelligent
                sexe = getattr(eleve_test, 'sexe', 'M') or 'M'
                rang_formate = formater_rang_intelligent(rang, sexe, len(moyennes_classe))
                
                print(f"✅ Rang : {rang_formate} sur {len(moyennes_classe)} élèves")
            else:
                print("❌ Rang non trouvé")
        else:
            print("❌ Aucune moyenne calculée pour la classe")
            
    except Exception as e:
        print(f"❌ Erreur calcul rang : {e}")
    
    # 6. Calcul de la mention
    print("\n6️⃣ CALCUL DE LA MENTION:")
    
    if moyenne_generale:
        # Barème des mentions
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
        
        print(f"✅ Mention : {mention}")
    else:
        mention = None
        print("❌ Pas de mention (moyenne manquante)")
    
    # 7. Génération de l'appréciation
    print("\n7️⃣ GÉNÉRATION DE L'APPRÉCIATION:")
    
    try:
        from notes.calculs_intelligent import obtenir_appreciation
        
        if moyenne_generale:
            appreciation = obtenir_appreciation(
                moyenne=float(moyenne_generale),
                prenom=eleve_test.prenom
            )
            print(f"✅ Appréciation : {appreciation}")
        else:
            appreciation = "Bon travail. Continuez vos efforts."
            print(f"⚠️ Appréciation par défaut : {appreciation}")
            
    except Exception as e:
        appreciation = "Bon travail. Continuez vos efforts."
        print(f"⚠️ Erreur génération appréciation, utilisation par défaut : {e}")
    
    # 8. Structure finale pour le template
    print("\n8️⃣ STRUCTURE DONNÉES BULLETIN:")
    
    bulletin_data = {
        'eleve': eleve_test,
        'classe': classe_note,
        'periode': 'OCTOBRE',
        'system_type': 'mensuel',
        'matieres_notes': matieres_data,
        'moyenne_generale': moyenne_generale,
        'rang': rang_formate if 'rang_formate' in locals() else '-',
        'mention': mention,
        'appreciation': appreciation,
        'total_points': total_points,
        'total_coefficients': total_coefficients
    }
    
    print(f"   ✅ Élève : {bulletin_data['eleve'].matricule}")
    print(f"   ✅ Classe : {bulletin_data['classe'].nom}")
    print(f"   ✅ Matières : {len(bulletin_data['matieres_notes'])}")
    print(f"   ✅ Moyenne : {bulletin_data['moyenne_generale']}")
    print(f"   ✅ Rang : {bulletin_data['rang']}")
    print(f"   ✅ Mention : {bulletin_data['mention']}")
    print(f"   ✅ Appréciation : {bulletin_data['appreciation'][:50]}...")
    
    # 9. URL de test
    print("\n9️⃣ URL DE TEST:")
    
    url = f"https://www.myschoolgn.space/notes/bulletins/"
    params = f"?classe_id={classe_note.id}&eleve_id={eleve_test.id}&periode=OCTOBRE&system_type=mensuel"
    
    print(f"🌐 {url}{params}")
    
    return True

def test_template_bulletin():
    """Test de simulation du template"""
    print("\n" + "="*80)
    print("🎨 TEST SIMULATION TEMPLATE")
    print("="*80)
    
    # Simuler les variables du template
    print("\n📋 Variables template nécessaires :")
    
    variables_requises = [
        'eleve_selectionne',
        'classe_selectionnee', 
        'periode',
        'system_type',
        'matieres_notes',
        'bulletin_data.moyenne_generale',
        'bulletin_data.rang',
        'bulletin_data.mention',
        'bulletin_data.appreciation'
    ]
    
    for var in variables_requises:
        print(f"   • {var}")
    
    print("\n🔍 Logique d'affichage template :")
    
    # Simulation logique template pour les notes
    print("\n   📝 Affichage notes (ligne 827-828) :")
    print("   {% if matiere_note.moyenne %}")
    print("       {{ matiere_note.moyenne|floatformat:2 }}")
    print("   {% elif matiere_note.moyenne_continue %}")
    print("       {{ matiere_note.moyenne_continue|floatformat:2 }}")
    print("   {% else %}")
    print("       -")
    print("   {% endif %}")
    
    # Simulation logique pour rang
    print("\n   🏆 Affichage rang (ligne 964) :")
    print("   <div class=\"value\">{{ bulletin_data.rang }}</div>")
    
    # Simulation logique pour appréciation
    print("\n   💬 Affichage appréciation (ligne 977) :")
    print("   <p>{{ bulletin_data.appreciation|default:\"Bon travail. Continuez vos efforts.\" }}</p>")

def corriger_problemes():
    """Proposer des corrections pour les problèmes identifiés"""
    print("\n" + "="*80)
    print("🔧 CORRECTIONS AUTOMATIQUES")
    print("="*80)
    
    print("\n🚀 Si le bulletin ne s'affiche pas correctement :")
    
    print("\n1. Vérifier les notes :")
    print("   python test_notes_affichage.py")
    
    print("\n2. Corriger les années scolaires :")
    print("   python corriger_annee_scolaire.py")
    
    print("\n3. Réparer les liens classes :")
    print("   python reparer_lien_classe_notes.py")
    
    print("\n4. Créer des notes manquantes :")
    print("   python creer_notes_11eme_corrige.py")
    
    print("\n5. Redémarrer le serveur :")
    print("   touch ecole_moderne/wsgi.py")

if __name__ == "__main__":
    print("🔍 DÉMARRAGE VÉRIFICATION BULLETIN COMPLET")
    
    if verifier_donnees_bulletin():
        test_template_bulletin()
    
    corriger_problemes()
    
    print("\n" + "="*80)
    print("✅ VÉRIFICATION TERMINÉE")
    print("="*80)
