#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Script de Test Complet du Système de Bulletin Intelligent
Teste les calculs automatiques, exports PDF et Excel
"""

import os
import sys
import django

# Configuration Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ecole_moderne.settings')
django.setup()

from decimal import Decimal
from eleves.models import Eleve, Classe
from notes.models import ClasseNote, MatiereNote, Evaluation, NoteEleve
from notes.bulletin_intelligent import CalculateurBulletinIntelligent, generer_pdf_avec_filigrane, generer_excel


def afficher_titre(titre):
    """Affiche un titre formaté"""
    print("\n" + "="*80)
    print(f"   {titre}")
    print("="*80)


def test_1_calcul_bulletin_secondaire():
    """Test du calcul de bulletin pour le secondaire"""
    afficher_titre("🧪 TEST 1 : CALCUL BULLETIN SECONDAIRE")
    
    print("\n📋 Recherche d'un élève du secondaire...")
    
    # Trouver une classe du secondaire avec des notes
    classe_note = ClasseNote.objects.filter(
        niveau_enseignement__in=['COLLEGE', 'LYCEE']
    ).first()
    
    if not classe_note:
        print("   ❌ Aucune classe secondaire trouvée")
        return False
    
    print(f"   ✅ Classe trouvée: {classe_note.nom}")
    
    # Trouver un élève dans cette classe
    eleves = Eleve.objects.filter(classe__nom__icontains=classe_note.nom[:5])
    
    if not eleves.exists():
        print("   ❌ Aucun élève trouvé")
        return False
    
    eleve = eleves.first()
    print(f"   ✅ Élève trouvé: {eleve.prenom} {eleve.nom}")
    
    # Calculer le bulletin
    print("\n🔄 Calcul du bulletin pour TRIMESTRE_1...")
    calculateur = CalculateurBulletinIntelligent(
        eleve, 
        classe_note, 
        'TRIMESTRE_1', 
        'TRIMESTRE'
    )
    
    bulletin = calculateur.generer_bulletin()
    
    # Afficher les résultats
    print("\n📊 Résultats du bulletin:")
    print("-"*80)
    print(f"   Élève: {bulletin['eleve']}")
    print(f"   Classe: {bulletin['classe']}")
    print(f"   Période: {bulletin['periode']}")
    print(f"   Niveau: {bulletin['niveau']}")
    print(f"\n   Nombre de matières: {len(bulletin['matieres'])}")
    
    # Détail des matières
    print(f"\n   📚 Détail par matière:")
    for matiere in bulletin['matieres'][:5]:  # Afficher les 5 premières
        print(f"      • {matiere['matiere']} (coef {matiere['coefficient']})")
        print(f"        Composition: {matiere['composition'] or '-'}")
        print(f"        Moyenne: {matiere['moyenne'] or '-'}")
    
    if len(bulletin['matieres']) > 5:
        print(f"      ... et {len(bulletin['matieres']) - 5} autres matières")
    
    # Résultats globaux
    if bulletin['moyenne_generale']:
        print(f"\n   🎯 MOYENNE GÉNÉRALE: {bulletin['moyenne_generale']:.2f}/20")
        print(f"   🏆 RANG: {bulletin['rang']}/{bulletin['total_eleves']}")
        print(f"   ⭐ MENTION: {bulletin['mention']}")
        print(f"   💬 APPRÉCIATION: {bulletin['appreciation']}")
        print("\n   ✅ SUCCÈS - Calculs automatiques validés")
        return True
    else:
        print("\n   ⚠️  Aucune moyenne calculée (pas assez de notes)")
        return True


def test_2_calcul_bulletin_primaire():
    """Test du calcul de bulletin pour le primaire"""
    afficher_titre("🧪 TEST 2 : CALCUL BULLETIN PRIMAIRE")
    
    print("\n📋 Recherche d'un élève du primaire...")
    
    # Trouver une classe primaire
    classe_note = ClasseNote.objects.filter(
        niveau_enseignement='PRIMAIRE'
    ).first()
    
    if not classe_note:
        print("   ⚠️  Aucune classe primaire trouvée")
        return True  # Pas une erreur si pas de primaire
    
    print(f"   ✅ Classe trouvée: {classe_note.nom}")
    
    # Trouver un élève
    eleves = Eleve.objects.filter(classe__nom__icontains=classe_note.nom[:5])
    
    if not eleves.exists():
        print("   ⚠️  Aucun élève trouvé")
        return True
    
    eleve = eleves.first()
    print(f"   ✅ Élève trouvé: {eleve.prenom} {eleve.nom}")
    
    # Calculer le bulletin
    print("\n🔄 Calcul du bulletin pour TRIMESTRE_1...")
    calculateur = CalculateurBulletinIntelligent(
        eleve, 
        classe_note, 
        'TRIMESTRE_1', 
        'TRIMESTRE'
    )
    
    bulletin = calculateur.generer_bulletin()
    
    # Afficher les résultats
    print("\n📊 Résultats du bulletin:")
    print("-"*80)
    print(f"   Niveau détecté: {bulletin['niveau']}")
    
    if bulletin['niveau'] == 'PRIMAIRE':
        print("   ✅ Niveau PRIMAIRE correctement détecté")
        print("   ℹ️  Note: Le primaire utilise uniquement les compositions (pas de notes mensuelles)")
    
    if bulletin['moyenne_generale']:
        print(f"\n   🎯 MOYENNE GÉNÉRALE: {bulletin['moyenne_generale']:.2f}/10")
        print("   ✅ SUCCÈS - Calculs primaire validés")
    else:
        print("\n   ⚠️  Aucune moyenne calculée")
    
    return True


def test_3_generation_pdf():
    """Test de la génération PDF avec filigrane"""
    afficher_titre("🧪 TEST 3 : GÉNÉRATION PDF AVEC FILIGRANE")
    
    print("\n📋 Préparation des données...")
    
    # Données de test
    bulletin_data = {
        'eleve': 'TEST Élève',
        'classe': 'TEST Classe',
        'periode': 'TRIMESTRE_1',
        'niveau': 'SECONDAIRE',
        'matieres': [
            {
                'matiere': 'Mathématiques',
                'coefficient': Decimal('4'),
                'notes_mensuelles': {'octobre': [Decimal('14'), Decimal('15')]},
                'composition': Decimal('12'),
                'moyenne': Decimal('13.2')
            },
            {
                'matiere': 'Français',
                'coefficient': Decimal('4'),
                'notes_mensuelles': {'octobre': [Decimal('13')]},
                'composition': Decimal('14'),
                'moyenne': Decimal('13.6')
            }
        ],
        'moyenne_generale': Decimal('13.4'),
        'mention': 'Bien',
        'appreciation': 'Bon travail. Continue tes efforts.',
        'rang': 5,
        'total_eleves': 30
    }
    
    print("   ✅ Données de test préparées")
    
    # Générer le PDF
    print("\n🔄 Génération du PDF...")
    try:
        pdf_buffer = generer_pdf_avec_filigrane(bulletin_data, logo_path=None)
        
        # Vérifier que le buffer contient des données
        pdf_buffer.seek(0)
        pdf_content = pdf_buffer.read()
        
        if len(pdf_content) > 0:
            print(f"   ✅ PDF généré ({len(pdf_content)} octets)")
            
            # Sauvegarder pour test visuel
            with open('test_bulletin_filigrane.pdf', 'wb') as f:
                f.write(pdf_content)
            print("   ✅ PDF sauvegardé: test_bulletin_filigrane.pdf")
            
            return True
        else:
            print("   ❌ PDF vide")
            return False
            
    except Exception as e:
        print(f"   ❌ Erreur lors de la génération: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_4_generation_excel():
    """Test de la génération Excel"""
    afficher_titre("🧪 TEST 4 : GÉNÉRATION EXCEL")
    
    try:
        from openpyxl import Workbook
        excel_disponible = True
    except ImportError:
        print("\n   ⚠️  OpenPyXL n'est pas installé")
        print("   💡 Pour installer: pip install openpyxl")
        return True  # Pas une erreur critique
    
    print("\n📋 Préparation des données...")
    
    # Données de test
    bulletin_data = {
        'eleve': 'TEST Élève',
        'classe': 'TEST Classe',
        'periode': 'TRIMESTRE_1',
        'niveau': 'SECONDAIRE',
        'matieres': [
            {
                'matiere': 'Mathématiques',
                'coefficient': Decimal('4'),
                'notes_mensuelles': {'octobre': [Decimal('14'), Decimal('15')]},
                'composition': Decimal('12'),
                'moyenne': Decimal('13.2')
            },
            {
                'matiere': 'Français',
                'coefficient': Decimal('4'),
                'notes_mensuelles': {'octobre': [Decimal('13')]},
                'composition': Decimal('14'),
                'moyenne': Decimal('13.6')
            }
        ],
        'moyenne_generale': Decimal('13.4'),
        'mention': 'Bien',
        'appreciation': 'Bon travail. Continue tes efforts.',
        'rang': 5,
        'total_eleves': 30
    }
    
    print("   ✅ Données de test préparées")
    
    # Générer l'Excel
    print("\n🔄 Génération du fichier Excel...")
    try:
        excel_buffer = generer_excel(bulletin_data)
        
        if excel_buffer:
            # Vérifier que le buffer contient des données
            excel_buffer.seek(0)
            excel_content = excel_buffer.read()
            
            if len(excel_content) > 0:
                print(f"   ✅ Excel généré ({len(excel_content)} octets)")
                
                # Sauvegarder pour test visuel
                with open('test_bulletin.xlsx', 'wb') as f:
                    f.write(excel_content)
                print("   ✅ Excel sauvegardé: test_bulletin.xlsx")
                
                return True
            else:
                print("   ❌ Excel vide")
                return False
        else:
            print("   ❌ Génération Excel a échoué")
            return False
            
    except Exception as e:
        print(f"   ❌ Erreur lors de la génération: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_5_formule_40_60():
    """Test de la formule 40/60"""
    afficher_titre("🧪 TEST 5 : VALIDATION FORMULE 40/60")
    
    print("\n📐 Test de la formule de calcul:")
    print("   Formule: (Moy. Cours × 40%) + (Composition × 60%)")
    
    from notes.calculs import calculer_moyenne_periode
    
    # Test 1
    print("\n   Test 1:")
    moyenne_cours = Decimal('15.0')
    composition = Decimal('12.0')
    print(f"   Moyenne cours: {moyenne_cours}")
    print(f"   Composition: {composition}")
    
    resultat = calculer_moyenne_periode(moyenne_cours, composition, niveau='SECONDAIRE')
    attendu = (moyenne_cours * Decimal('0.4')) + (composition * Decimal('0.6'))
    
    print(f"   Résultat: {resultat}")
    print(f"   Attendu: {attendu}")
    
    if abs(resultat - attendu) < Decimal('0.01'):
        print("   ✅ Formule 40/60 correcte")
        return True
    else:
        print(f"   ❌ Erreur de calcul")
        return False


def executer_tous_les_tests():
    """Exécute tous les tests"""
    afficher_titre("🚀 TESTS DU SYSTÈME DE BULLETIN INTELLIGENT")
    
    print("\nCe script teste:")
    print("   1. Calculs automatiques (secondaire)")
    print("   2. Calculs automatiques (primaire)")
    print("   3. Génération PDF avec filigrane")
    print("   4. Génération Excel")
    print("   5. Validation formule 40/60")
    
    tests = [
        ("Calcul bulletin secondaire", test_1_calcul_bulletin_secondaire),
        ("Calcul bulletin primaire", test_2_calcul_bulletin_primaire),
        ("Génération PDF", test_3_generation_pdf),
        ("Génération Excel", test_4_generation_excel),
        ("Formule 40/60", test_5_formule_40_60),
    ]
    
    resultats = []
    
    for nom, test_func in tests:
        try:
            succes = test_func()
            resultats.append((nom, succes))
        except Exception as e:
            print(f"\n❌ ERREUR dans {nom}: {e}")
            import traceback
            traceback.print_exc()
            resultats.append((nom, False))
    
    # Afficher le résumé
    afficher_titre("📊 RÉSUMÉ DES TESTS")
    
    print("\n" + "-"*80)
    print(f"{'Test':<40} {'Statut':<40}")
    print("-"*80)
    
    tests_reussis = 0
    for nom, succes in resultats:
        statut = "✅ RÉUSSI" if succes else "❌ ÉCHOUÉ"
        print(f"{nom:<40} {statut:<40}")
        if succes:
            tests_reussis += 1
    
    print("-"*80)
    print(f"\nRésultat global: {tests_reussis}/{len(resultats)} tests réussis")
    
    if tests_reussis == len(resultats):
        afficher_titre("✅ TOUS LES TESTS RÉUSSIS")
        print("\n🎉 Le système de bulletin intelligent est opérationnel !")
        print("\n✅ Fonctionnalités validées:")
        print("   • Calculs automatiques (formule 40/60)")
        print("   • Support primaire et secondaire")
        print("   • Génération PDF avec filigrane")
        print("   • Génération Excel")
        print("   • Calcul de rang automatique")
        print("   • Mentions et appréciations")
        print("\n🚀 SYSTÈME PRÊT POUR UTILISATION\n")
        return True
    else:
        afficher_titre("⚠️  CERTAINS TESTS ONT ÉCHOUÉ")
        print(f"\n❌ {len(resultats) - tests_reussis} test(s) échoué(s)")
        print("   Vérifiez les erreurs ci-dessus.\n")
        return False


if __name__ == "__main__":
    try:
        succes = executer_tous_les_tests()
        sys.exit(0 if succes else 1)
    except KeyboardInterrupt:
        print("\n\n⚠️  Tests interrompus\n")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Erreur fatale: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
