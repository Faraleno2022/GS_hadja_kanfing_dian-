#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Script pour corriger les coefficients des matières selon le niveau scolaire
- MATERNELLE: coefficient = None (pas de notes numériques)
- PRIMAIRE: coefficient = 1.0 (pas de pondération)
- COLLEGE/LYCEE: garder les coefficients existants
"""

import os
import sys
import django

# Configuration Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ecole_moderne.settings')
django.setup()

from notes.models import ClasseNote, MatiereNote
from notes.calculs_moyennes import detecter_niveau_scolaire

def corriger_coefficients():
    """Corriger les coefficients selon le niveau scolaire"""
    print("\n" + "="*70)
    print("CORRECTION DES COEFFICIENTS PAR NIVEAU SCOLAIRE")
    print("="*70)
    
    stats = {
        'MATERNELLE': {'total': 0, 'corriges': 0},
        'PRIMAIRE': {'total': 0, 'corriges': 0},
        'COLLEGE': {'total': 0, 'corriges': 0},
        'LYCEE': {'total': 0, 'corriges': 0}
    }
    
    # Parcourir toutes les classes
    for classe in ClasseNote.objects.filter(actif=True):
        niveau = detecter_niveau_scolaire(classe.nom)
        print(f"\n📚 Classe: {classe.nom} → Niveau: {niveau}")
        
        # Récupérer les matières de cette classe
        matieres = MatiereNote.objects.filter(classe=classe, actif=True)
        
        for matiere in matieres:
            stats[niveau]['total'] += 1
            coefficient_avant = matiere.coefficient
            coefficient_apres = coefficient_avant
            modifie = False
            
            if niveau == 'MATERNELLE':
                # MATERNELLE: Pas de coefficient
                if matiere.coefficient is not None:
                    matiere.coefficient = None
                    coefficient_apres = None
                    modifie = True
                    
            elif niveau == 'PRIMAIRE':
                # PRIMAIRE: Coefficient = 1.0
                if matiere.coefficient != 1.0:
                    matiere.coefficient = 1.0
                    coefficient_apres = 1.0
                    modifie = True
            
            # COLLEGE/LYCEE: Garder les coefficients existants
            
            if modifie:
                matiere.save()
                stats[niveau]['corriges'] += 1
                print(f"   ✅ {matiere.nom}: {coefficient_avant} → {coefficient_apres}")
            else:
                print(f"   ⚪ {matiere.nom}: {coefficient_avant} (OK)")
    
    # Afficher les statistiques
    print("\n" + "="*70)
    print("STATISTIQUES DE CORRECTION")
    print("="*70)
    
    total_matieres = 0
    total_corriges = 0
    
    for niveau, stat in stats.items():
        total_matieres += stat['total']
        total_corriges += stat['corriges']
        
        if stat['total'] > 0:
            pourcentage = (stat['corriges'] * 100) / stat['total']
            print(f"{niveau:12}: {stat['corriges']:3}/{stat['total']:3} matières corrigées ({pourcentage:5.1f}%)")
        else:
            print(f"{niveau:12}: Aucune matière trouvée")
    
    print("-" * 70)
    if total_matieres > 0:
        pourcentage_global = (total_corriges * 100) / total_matieres
        print(f"{'TOTAL':12}: {total_corriges:3}/{total_matieres:3} matières corrigées ({pourcentage_global:5.1f}%)")
    
    print("\n" + "="*70)
    print("RÈGLES APPLIQUÉES")
    print("="*70)
    print("""
    ✅ MATERNELLE/GARDERIE:
       - Coefficient = None (pas de notes numériques)
       - Évaluation par appréciations uniquement
    
    ✅ PRIMAIRE (1ère-6ème):
       - Coefficient = 1.0 (pas de pondération)
       - Moyenne simple de toutes les matières
    
    ✅ COLLÈGE (7ème-10ème):
       - Coefficients variables selon l'importance
       - Moyenne pondérée
    
    ✅ LYCÉE (11ème-Terminale):
       - Coefficients élevés selon la série
       - Moyenne pondérée avec spécialisation
    """)
    
    if total_corriges > 0:
        print(f"✅ ✅ ✅ SUCCÈS: {total_corriges} matières ont été corrigées!")
    else:
        print("✅ ✅ ✅ PARFAIT: Tous les coefficients étaient déjà corrects!")

def verifier_coherence():
    """Vérifier la cohérence des coefficients après correction"""
    print("\n" + "="*70)
    print("VÉRIFICATION DE LA COHÉRENCE")
    print("="*70)
    
    problemes = []
    
    for classe in ClasseNote.objects.filter(actif=True):
        niveau = detecter_niveau_scolaire(classe.nom)
        matieres = MatiereNote.objects.filter(classe=classe, actif=True)
        
        for matiere in matieres:
            if niveau == 'MATERNELLE' and matiere.coefficient is not None:
                problemes.append(f"❌ {classe.nom} - {matiere.nom}: coefficient={matiere.coefficient} (devrait être None)")
            elif niveau == 'PRIMAIRE' and matiere.coefficient != 1.0:
                problemes.append(f"❌ {classe.nom} - {matiere.nom}: coefficient={matiere.coefficient} (devrait être 1.0)")
    
    if problemes:
        print("PROBLÈMES DÉTECTÉS:")
        for probleme in problemes:
            print(f"  {probleme}")
    else:
        print("✅ ✅ ✅ PARFAIT: Tous les coefficients sont cohérents!")
    
    return len(problemes) == 0

def main():
    """Fonction principale"""
    print("\n" + "="*70)
    print("CORRECTION DES COEFFICIENTS DE MATIÈRES")
    print("Système éducatif guinéen")
    print("="*70)
    
    # Étape 1: Correction
    corriger_coefficients()
    
    # Étape 2: Vérification
    coherent = verifier_coherence()
    
    print("\n" + "="*70)
    if coherent:
        print("🎉 MISSION ACCOMPLIE: Tous les coefficients sont maintenant corrects!")
    else:
        print("⚠️ ATTENTION: Des problèmes persistent, relancer le script.")
    print("="*70)

if __name__ == '__main__':
    main()
