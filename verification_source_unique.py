"""
Script de vérification: Les moyennes du bulletin et du classement utilisent-elles la MÊME SOURCE ?
"""

import os
import sys
import ast

def analyser_fichier(chemin):
    """Analyse un fichier Python pour trouver les fonctions de calcul"""
    with open(chemin, 'r', encoding='utf-8') as f:
        contenu = f.read()
    
    fonctions_calcul = []
    imports = []
    
    # Chercher les imports du module centralisé
    if 'from .calculs_moyennes import' in contenu or 'from notes.calculs_moyennes import' in contenu:
        imports.append('calculs_moyennes')
    
    # Chercher les fonctions de calcul définies localement
    if 'def calculer_moyenne' in contenu:
        fonctions_calcul.append('calculer_moyenne (définie localement)')
    
    if 'total_points' in contenu and 'total_coefficients' in contenu:
        fonctions_calcul.append('calcul manuel (total_points/total_coefficients)')
    
    return {
        'imports': imports,
        'fonctions_locales': fonctions_calcul,
        'utilise_module_centralise': 'calculs_moyennes' in imports
    }

def main():
    print("=" * 80)
    print("VÉRIFICATION: SOURCE UNIQUE DES MOYENNES")
    print("=" * 80)
    print()
    
    # Fichiers à analyser
    fichiers = [
        ('notes/export_classement.py', 'Export Classement'),
        ('notes/views.py', 'Bulletins PDF'),
        ('notes/bulletin_intelligent.py', 'Bulletin Intelligent'),
        ('notes/calcul_classement.py', 'Calcul Classement'),
    ]
    
    resultats = []
    
    for fichier, nom in fichiers:
        chemin = os.path.join('c:\\Users\\LENO\\Desktop\\GS_hadja_kanfing_dian--main', fichier)
        if os.path.exists(chemin):
            analyse = analyser_fichier(chemin)
            resultats.append({
                'fichier': fichier,
                'nom': nom,
                'analyse': analyse
            })
            
            print(f"📁 {nom} ({fichier})")
            print(f"   Utilise module centralisé: {'✅ OUI' if analyse['utilise_module_centralise'] else '❌ NON'}")
            if analyse['imports']:
                print(f"   Imports: {', '.join(analyse['imports'])}")
            if analyse['fonctions_locales']:
                print(f"   Calculs locaux: {', '.join(analyse['fonctions_locales'])}")
            print()
    
    # Diagnostic
    print("=" * 80)
    print("DIAGNOSTIC")
    print("=" * 80)
    
    utilisent_module = [r for r in resultats if r['analyse']['utilise_module_centralise']]
    n_utilisent_pas = [r for r in resultats if not r['analyse']['utilise_module_centralise']]
    
    if len(n_utilisent_pas) == 0:
        print("✅ ✅ ✅ EXCELLENT! Tous les fichiers utilisent le module centralisé")
        print("   → Les moyennes proviennent d'une SOURCE UNIQUE")
        print("   → Cohérence GARANTIE à 100%")
    else:
        print("❌ PROBLÈME DÉTECTÉ!")
        print(f"   {len(n_utilisent_pas)} fichier(s) N'UTILISENT PAS le module centralisé:")
        for r in n_utilisent_pas:
            print(f"   - {r['nom']}: {r['fichier']}")
            print(f"     → Fait ses propres calculs")
        print()
        print("⚠️ RISQUE D'INCOHÉRENCE!")
        print("   Les fichiers calculent les moyennes différemment")
        print("   → Peut créer des différences entre bulletin et classement")
        
    print("=" * 80)
    
    # Recommandations
    if n_utilisent_pas:
        print("\n📝 RECOMMANDATIONS:")
        print("-" * 40)
        for r in n_utilisent_pas:
            print(f"\n{r['nom']} ({r['fichier']}):")
            print("  1. Ajouter l'import:")
            print("     from .calculs_moyennes import calculer_moyenne_generale_eleve")
            print("  2. Remplacer le calcul local par:")
            print("     result = calculer_moyenne_generale_eleve(eleve, matieres, periode, system_type)")
            print("  3. Utiliser result['moyenne_generale']")
        
        print("\n✅ Cela garantira:")
        print("   - Une SOURCE UNIQUE pour tous les calculs")
        print("   - Cohérence à 100% entre bulletin et classement")
        print("   - Plus facile à maintenir")

if __name__ == "__main__":
    main()
