#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Script pour remplacer "myschool" par "myschool" dans tous les fichiers
"""

import os
import glob

# Textes à remplacer
ANCIEN_NOM = "myschool"
NOUVEAU_NOM = "myschool"

# Variations à remplacer
VARIATIONS = [
    ("myschool", "myschool"),
    ("myschool", "myschool"),
    ("myschool", "myschool"),
    ("myschool", "myschool"),
    ("myschool", "myschool"),
    ("myschool", "myschool"),
    ("myschool", "myschool"),
    ("myschool", "myschool"),
    ("myschool", "myschool"),
    ("myschool", "myschool"),
    ("myschool", "myschool"),
]

# Extensions de fichiers à traiter
EXTENSIONS = [
    '*.py', '*.html', '*.js', '*.css', '*.md', '*.txt',
    '*.json', '*.yml', '*.yaml', '*.xml'
]

# Dossiers à exclure
EXCLUSIONS = [
    'venv', '__pycache__', '.git', 'node_modules',
    'static/admin', 'migrations', 'media'
]

def doit_exclure(chemin):
    """Vérifie si un chemin doit être exclu"""
    for exclusion in EXCLUSIONS:
        if exclusion in chemin:
            return True
    return False

def remplacer_dans_fichier(fichier):
    """Remplace les occurrences dans un fichier"""
    try:
        with open(fichier, 'r', encoding='utf-8') as f:
            contenu = f.read()
        
        contenu_original = contenu
        modifications = 0
        
        # Appliquer tous les remplacements
        for ancien, nouveau in VARIATIONS:
            if ancien in contenu:
                nb = contenu.count(ancien)
                contenu = contenu.replace(ancien, nouveau)
                modifications += nb
        
        # Sauvegarder si modifications
        if contenu != contenu_original:
            with open(fichier, 'w', encoding='utf-8') as f:
                f.write(contenu)
            return modifications
        
        return 0
    
    except Exception as e:
        print(f"   ❌ Erreur : {e}")
        return 0

def main():
    print("\n" + "="*80)
    print(" "*20 + "🔄 REMPLACEMENT DU NOM DE L'ÉCOLE")
    print("="*80)
    
    print(f"\nAncien nom : myschool")
    print(f"Nouveau nom : myschool")
    
    print("\n🔍 Recherche des fichiers...")
    
    fichiers_traites = 0
    fichiers_modifies = 0
    total_remplacements = 0
    
    # Parcourir tous les fichiers
    for extension in EXTENSIONS:
        for fichier in glob.glob(f'**/{extension}', recursive=True):
            if doit_exclure(fichier):
                continue
            
            fichiers_traites += 1
            nb_remplacements = remplacer_dans_fichier(fichier)
            
            if nb_remplacements > 0:
                fichiers_modifies += 1
                total_remplacements += nb_remplacements
                print(f"   ✅ {fichier} : {nb_remplacements} remplacement(s)")
    
    print("\n" + "="*80)
    print(" "*25 + "📊 RÉSUMÉ")
    print("="*80)
    
    print(f"\n   Fichiers traités : {fichiers_traites}")
    print(f"   Fichiers modifiés : {fichiers_modifies}")
    print(f"   Total remplacements : {total_remplacements}")
    
    if fichiers_modifies > 0:
        print("\n✅ REMPLACEMENT TERMINÉ !")
        print("\n⚠️  IMPORTANT :")
        print("   1. Vérifiez que les changements sont corrects")
        print("   2. Redémarrez le serveur Django")
        print("   3. Videz le cache du navigateur (Ctrl+F5)")
    else:
        print("\nℹ️  Aucune occurrence trouvée à remplacer")
    
    print("\n" + "="*80 + "\n")

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  Opération annulée\n")
    except Exception as e:
        print(f"\n❌ Erreur : {e}")
        import traceback
        traceback.print_exc()
