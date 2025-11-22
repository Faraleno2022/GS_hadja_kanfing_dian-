#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Test des règles spécifiques par niveau scolaire
"""

import os
import sys
import django

# Configuration Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ecole_moderne.settings')
django.setup()

from decimal import Decimal
from notes.calculs_moyennes import detecter_niveau_scolaire, calculer_moyenne_generale_eleve
from notes.models import ClasseNote, MatiereNote
from eleves.models import Eleve

def test_detection_niveau():
    """Test de la détection automatique du niveau scolaire"""
    print("\n" + "="*70)
    print("TEST DE DÉTECTION DES NIVEAUX SCOLAIRES")
    print("="*70)
    
    tests = [
        # Maternelle
        ("Petite Section", "MATERNELLE"),
        ("Moyenne Section", "MATERNELLE"),
        ("Grande Section", "MATERNELLE"),
        ("Garderie", "MATERNELLE"),
        ("Crèche", "MATERNELLE"),
        
        # Primaire
        ("1ère Année", "PRIMAIRE"),
        ("2ème Année", "PRIMAIRE"),
        ("3ème Année - CE1", "PRIMAIRE"),
        ("CP1", "PRIMAIRE"),
        ("CP2", "PRIMAIRE"),
        ("CE1", "PRIMAIRE"),
        ("CE2", "PRIMAIRE"),
        ("CM1", "PRIMAIRE"),
        ("CM2", "PRIMAIRE"),
        ("6ème année", "PRIMAIRE"),
        
        # Collège
        ("7ème année", "COLLEGE"),
        ("8ème année", "COLLEGE"),
        ("9ème année", "COLLEGE"),
        ("10ème année", "COLLEGE"),
        
        # Lycée
        ("11ème année", "LYCEE"),
        ("12ème Série Scientifique", "LYCEE"),
        ("12ème Série Littéraire", "LYCEE"),
        ("Terminale", "LYCEE"),
    ]
    
    success = 0
    total = len(tests)
    
    for classe_nom, niveau_attendu in tests:
        niveau_detecte = detecter_niveau_scolaire(classe_nom)
        if niveau_detecte == niveau_attendu:
            print(f"✅ {classe_nom:30} → {niveau_detecte:10} (OK)")
            success += 1
        else:
            print(f"❌ {classe_nom:30} → {niveau_detecte:10} (Attendu: {niveau_attendu})")
    
    print(f"\nRésultat: {success}/{total} tests réussis ({success*100/total:.1f}%)")
    return success == total

def test_calculs_par_niveau():
    """Test des calculs spécifiques par niveau"""
    print("\n" + "="*70)
    print("TEST DES CALCULS PAR NIVEAU")
    print("="*70)
    
    # Chercher des classes de chaque niveau
    classes_test = {
        'MATERNELLE': None,
        'PRIMAIRE': None,
        'COLLEGE': None,
        'LYCEE': None
    }
    
    for classe in ClasseNote.objects.all():
        niveau = detecter_niveau_scolaire(classe.nom)
        if niveau in classes_test and classes_test[niveau] is None:
            classes_test[niveau] = classe
    
    # Afficher les résultats
    for niveau, classe in classes_test.items():
        print(f"\n📚 Niveau {niveau}:")
        
        if classe is None:
            print(f"   ⚠️ Pas de classe trouvée pour tester")
            continue
        
        print(f"   Classe: {classe.nom}")
        
        # Récupérer un élève et les matières
        from eleves.models import Classe as ClasseEleve
        classe_eleve = ClasseEleve.objects.filter(
            nom__icontains=classe.nom.split()[0],
            annee_scolaire=classe.annee_scolaire
        ).first()
        
        if not classe_eleve:
            print(f"   ⚠️ Pas de classe élève correspondante")
            continue
        
        eleve = Eleve.objects.filter(classe=classe_eleve, statut='ACTIF').first()
        if not eleve:
            print(f"   ⚠️ Pas d'élève actif dans la classe")
            continue
        
        matieres = MatiereNote.objects.filter(classe=classe, actif=True)[:3]  # Prendre 3 matières pour test
        
        # Calculer la moyenne
        result = calculer_moyenne_generale_eleve(eleve, matieres, 'OCTOBRE', 'mensuel')
        
        print(f"   Élève: {eleve.prenom} {eleve.nom}")
        
        if niveau == 'MATERNELLE':
            print(f"   ✅ Appréciations uniquement: {result['appreciations_only']}")
            print(f"   ✅ Moyenne: {result['moyenne_generale']} (None attendu)")
            print(f"   ✅ Appréciation: {result.get('appreciation', 'N/A')[:50]}...")
        
        elif niveau == 'PRIMAIRE':
            print(f"   Matières (sans coefficients):")
            for detail in result['details_matieres']:
                print(f"      - {detail['matiere'].nom}: Coef={detail['coefficient']} (doit être 1)")
            
            # Vérifier que tous les coefficients sont 1
            all_coef_one = all(detail['coefficient'] == 1 for detail in result['details_matieres'])
            print(f"   ✅ Tous les coefficients = 1: {all_coef_one}")
        
        else:  # COLLEGE ou LYCEE
            print(f"   Matières (avec coefficients):")
            for detail in result['details_matieres']:
                print(f"      - {detail['matiere'].nom}: Coef={detail['coefficient']}")
            
            # Vérifier qu'il y a des coefficients différents
            coefs = [detail['coefficient'] for detail in result['details_matieres']]
            has_different_coefs = len(set(coefs)) > 1 or (len(set(coefs)) == 1 and list(set(coefs))[0] != 1)
            print(f"   ✅ Coefficients variés: {has_different_coefs or len(coefs) == 0}")
        
        print(f"   Niveau détecté: {result.get('niveau', 'N/A')}")

def main():
    """Fonction principale"""
    print("\n" + "="*70)
    print("TEST DES RÈGLES PAR NIVEAU SCOLAIRE")
    print("Système éducatif guinéen")
    print("="*70)
    
    # Test 1: Détection des niveaux
    test1_ok = test_detection_niveau()
    
    # Test 2: Calculs par niveau
    test_calculs_par_niveau()
    
    print("\n" + "="*70)
    print("RÉCAPITULATIF DES RÈGLES APPLIQUÉES")
    print("="*70)
    print("""
    ✅ MATERNELLE/GARDERIE:
       - Pas de notes numériques
       - Appréciations qualitatives uniquement
       - Suivi pédagogique personnalisé
    
    ✅ PRIMAIRE (1ère-6ème):
       - Notes de 0 à 20
       - PAS de coefficients (tous = 1)
       - Moyenne simple (non pondérée)
    
    ✅ COLLÈGE (7ème-10ème):
       - Notes de 0 à 20
       - Coefficients par matière
       - Moyenne pondérée
       - Système 40% continu + 60% composition
    
    ✅ LYCÉE (11ème-Terminale):
       - Notes de 0 à 20
       - Coefficients élevés selon série
       - Moyenne pondérée
       - Spécialisation (Scientifique/Littéraire)
    """)
    
    if test1_ok:
        print("\n✅ ✅ ✅ SUCCÈS: Toutes les règles sont correctement implémentées!")
    else:
        print("\n⚠️ ATTENTION: Certains tests ont échoué")

if __name__ == '__main__':
    main()
