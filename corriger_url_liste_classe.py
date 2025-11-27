#!/usr/bin/env python
"""
Correction de l'erreur 'liste_classe' -> 'liste_eleves'
"""

import os
import re

def corriger_url_liste_classe():
    """Corriger les références à 'liste_classe' par 'liste_eleves'"""
    
    try:
        print("🔧 CORRECTION URL 'liste_classe' -> 'liste_eleves'")
        
        # Rechercher les fichiers qui contiennent 'liste_classe'
        fichiers_a_verifier = [
            'eleves/views.py',
            'eleves/views_import.py',
            'templates/eleves/*.html',
            'templates/eleves/*/*.html'
        ]
        
        fichiers_modifies = []
        
        for fichier_pattern in fichiers_a_verifier:
            if '*' in fichier_pattern:
                # Gérer les patterns avec wildcard
                import glob
                fichiers = glob.glob(fichier_pattern)
            else:
                fichiers = [fichier_pattern] if os.path.exists(fichier_pattern) else []
            
            for fichier in fichiers:
                try:
                    with open(fichier, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    original_content = content
                    
                    # Remplacer les références à 'liste_classe'
                    content = re.sub(r"reverse\('liste_classe'\)", "reverse('eleves:liste_eleves')", content)
                    content = re.sub(r"url 'liste_classe'", "url 'eleves:liste_eleves'", content)
                    content = re.sub(r"{% url 'liste_classe' %}", "{% url 'eleves:liste_eleves' %}", content)
                    content = re.sub(r"name='liste_classe'", "name='liste_eleves'", content)
                    
                    if content != original_content:
                        with open(fichier, 'w', encoding='utf-8') as f:
                            f.write(content)
                        fichiers_modifies.append(fichier)
                        print(f"  ✅ Corrigé : {fichier}")
                        
                except Exception as e:
                    print(f"  ❌ Erreur avec {fichier}: {str(e)}")
        
        if fichiers_modifies:
            print(f"\n📋 Fichiers modifiés : {len(fichiers_modifies)}")
            for fichier in fichiers_modifies:
                print(f"  • {fichier}")
        else:
            print(f"\n📋 Aucun fichier trouvé avec 'liste_classe'")
        
        # Ajouter l'URL manquante si nécessaire
        print(f"\n🔍 VÉRIFICATION URLs ELEVES :")
        
        urls_path = "eleves/urls.py"
        if os.path.exists(urls_path):
            with open(urls_path, 'r', encoding='utf-8') as f:
                urls_content = f.read()
            
            if 'liste_classe' in urls_content:
                print(f"  ❌ 'liste_classe' trouvé dans urls.py - doit être remplacé")
                
                # Remplacer dans urls.py
                urls_content = urls_content.replace("name='liste_classe'", "name='liste_eleves'")
                
                with open(urls_path, 'w', encoding='utf-8') as f:
                    f.write(urls_content)
                
                print(f"  ✅ URLs corrigées")
            else:
                print(f"  ✅ Pas de 'liste_classe' dans urls.py")
        
        print(f"\n🚀 SOLUTIONS POSSIBLES :")
        print(f"  1. Utiliser : reverse('eleves:liste_eleves')")
        print(f"  2. Utiliser : {% url 'eleves:liste_eleves' %}")
        print(f"  3. Rediriger vers : /eleves/liste/")
        
        print(f"\n🌟 URLS CORRECTES DISPONIBLES :")
        print(f"  • eleves:liste_eleves -> /eleves/liste/")
        print(f"  • eleves:gestion_classes -> /eleves/classes/")
        print(f"  • eleves:detail_eleve -> /eleves/<id>/")
        
        return True
        
    except Exception as e:
        print(f"❌ Erreur : {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    corriger_url_liste_classe()
