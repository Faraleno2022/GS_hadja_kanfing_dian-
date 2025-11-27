#!/usr/bin/env python
"""
Correction de l'erreur de syntaxe dans export_classement_pdf_fix.py
"""

import os
import re

def corriger_syntaxe_export_pdf_fix():
    """Corriger l'erreur de syntaxe à la ligne 154"""
    
    try:
        print("🔧 CORRECTION SYNTAXE export_classement_pdf_fix.py")
        
        # Chemin du fichier
        fichier_path = "notes/export_classement_pdf_fix.py"
        
        # Lire le fichier
        with open(fichier_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        print(f"📄 Fichier lu : {fichier_path}")
        
        # Trouver la ligne problématique
        # Pattern à rechercher : {f'<p>■ ATTENTION: ...</p>' if len(sans_notes) > 0 else ''}
        pattern = r'\{f\'<p>■ ATTENTION: \{len\(sans_notes\)\} élève\(s\) n\'ont pas de notes pour cette période</p>\' if len\(sans_notes\) > 0 else \'\}'
        
        # Remplacer par la version correcte avec parenthèses
        replacement = r'(f\'<p>■ ATTENTION: {len(sans_notes)} élève(s) n\'ont pas de notes pour cette période</p>\' if len(sans_notes) > 0 else \'\')'
        
        # Chercher et remplacer
        if re.search(pattern, content):
            content = re.sub(pattern, replacement, content)
            print(f"  ✅ Ligne 154 corrigée : accolades → parenthèses")
        else:
            # Essayer un pattern plus large
            pattern_large = r'\{f\'<p>■ ATTENTION:.*?</p>\' if len\(sans_notes\) > 0 else \'\}'
            if re.search(pattern_large, content):
                content = re.sub(pattern_large, replacement, content)
                print(f"  ✅ Ligne 154 corrigée : accolades → parenthèses")
            else:
                print(f"  ❌ Pattern non trouvé - recherche manuelle nécessaire")
                print(f"  🔍 Recherche de 'ATTENTION' dans le fichier...")
                
                lines = content.split('\n')
                for i, line in enumerate(lines, 1):
                    if 'ATTENTION' in line and 'len(sans_notes)' in line:
                        print(f"    Ligne {i}: {line.strip()}")
                        
                        # Corriger manuellement
                        if '{f\'' in line and '}' in line:
                            # Remplacer les accolades externes par des parenthèses
                            corrected_line = line.replace('{f\'', '(f\'').replace('\'}', '\')')
                            lines[i-1] = corrected_line
                            print(f"    ✅ Corrigée : {corrected_line.strip()}")
                
                content = '\n'.join(lines)
        
        # Sauvegarder le fichier corrigé
        with open(fichier_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        print(f"  ✅ Fichier sauvegardé : {fichier_path}")
        
        # Vérifier la correction
        print(f"\n🔍 VÉRIFICATION DE LA CORRECTION :")
        
        with open(fichier_path, 'r', encoding='utf-8') as f:
            content_check = f.read()
        
        if '(f\'' in content_check and 'ATTENTION' in content_check:
            print(f"  ✅ Syntaxe corrigée : utilisation de parenthèses")
        else:
            print(f"  ❌ Problème persistant - vérification manuelle requise")
        
        print(f"\n🚀 PROCHAINES ÉTAPES :")
        print(f"  1. Redémarrer le serveur : touch ecole_moderne/wsgi.py")
        print(f"  2. Tester la correction : python corriger_classe_12_serie_litteraire.py")
        print(f"  3. Tester l'URL PDF : /notes/exporter-classement-pdf-fix/?classe_id=XX&matiere_id=XX&periode=OCTOBRE")
        
        return True
        
    except Exception as e:
        print(f"❌ Erreur : {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    corriger_syntaxe_export_pdf_fix()
