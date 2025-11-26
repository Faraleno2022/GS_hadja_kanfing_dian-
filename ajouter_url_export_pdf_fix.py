#!/usr/bin/env python
"""
Ajouter l'URL de l'export PDF fix dans notes/urls.py
"""

import os
import re

def ajouter_url_export_pdf_fix():
    """Ajouter l'URL de l'export PDF fix dans notes/urls.py"""
    
    try:
        print("🔧 AJOUT URL EXPORT PDF FIX")
        
        # Chemin du fichier URLs
        urls_path = "notes/urls.py"
        
        # Lire le fichier actuel
        with open(urls_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        print(f"📄 Fichier lu : {urls_path}")
        
        # Vérifier si l'URL existe déjà
        if 'exporter_classement_pdf_fix' in content:
            print(f"  ✅ URL déjà présente - Pas de modification nécessaire")
            return True
        
        # Trouver où insérer le nouvel import
        # Chercher la ligne avec les imports d'export_classement
        import_pattern = r'(from \.export_classement import .*)'
        import_match = re.search(import_pattern, content)
        
        if import_match:
            # Ajouter après la ligne existante
            old_import = import_match.group(1)
            new_import = old_import + '\nfrom .export_classement_pdf_fix import exporter_classement_pdf_fix'
            content = content.replace(old_import, new_import)
            print(f"  ✅ Import ajouté")
        else:
            # Ajouter au début des imports
            import_section = re.search(r'(from django\.urls import .*)', content)
            if import_section:
                old_import = import_section.group(1)
                new_import = old_import + '\nfrom .export_classement_pdf_fix import exporter_classement_pdf_fix'
                content = content.replace(old_import, new_import)
                print(f"  ✅ Import ajouté au début")
            else:
                print(f"  ❌ Impossible de trouver où ajouter l'import")
                return False
        
        # Trouver où insérer la nouvelle URL
        # Chercher la section des URLs d'export
        url_pattern = r"(path\('exporter-classement-fixed/', .*\))"
        url_match = re.search(url_pattern, content)
        
        if url_match:
            # Ajouter après la ligne exporter-classement-fixed
            old_url = url_match.group(1)
            new_url = old_url + "\n    path('exporter-classement-pdf-fix/', exporter_classement_pdf_fix, name='exporter_classement_pdf_fix'),"
            content = content.replace(old_url, new_url)
            print(f"  ✅ URL ajoutée après exporter-classement-fixed")
        else:
            # Chercher une autre URL d'export
            url_pattern2 = r"(path\('exporter-classement/', .*\))"
            url_match2 = re.search(url_pattern2, content)
            
            if url_match2:
                old_url = url_match2.group(1)
                new_url = old_url + "\n    path('exporter-classement-pdf-fix/', exporter_classement_pdf_fix, name='exporter_classement_pdf_fix'),"
                content = content.replace(old_url, new_url)
                print(f"  ✅ URL ajoutée après exporter-classement")
            else:
                # Ajouter à la fin du urlpatterns
                urlpatterns_pattern = r"(urlpatterns = \[)"
                urlpatterns_match = re.search(urlpatterns_pattern, content)
                
                if urlpatterns_match:
                    old_urlpatterns = urlpatterns_match.group(1)
                    new_urlpatterns = old_urlpatterns + "\n    path('exporter-classement-pdf-fix/', exporter_classement_pdf_fix, name='exporter_classement_pdf_fix'),"
                    content = content.replace(old_urlpatterns, new_urlpatterns)
                    print(f"  ✅ URL ajoutée au début du urlpatterns")
                else:
                    print(f"  ❌ Impossible de trouver où ajouter l'URL")
                    return False
        
        # Sauvegarder le fichier modifié
        with open(urls_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        print(f"  ✅ Fichier sauvegardé : {urls_path}")
        
        # Afficher le contenu ajouté
        print(f"\n📋 Contenu ajouté :")
        print(f"  Import : from .export_classement_pdf_fix import exporter_classement_pdf_fix")
        print(f"  URL    : path('exporter-classement-pdf-fix/', exporter_classement_pdf_fix, name='exporter_classement_pdf_fix'),")
        
        print(f"\n🚀 PROCHAINES ÉTAPES :")
        print(f"  1. Redémarrer le serveur : touch ecole_moderne/wsgi.py")
        print(f"  2. Tester l'URL : /notes/exporter-classement-pdf-fix/?classe_id=4&matiere_id=41&periode=OCTOBRE")
        
        return True
        
    except Exception as e:
        print(f"❌ Erreur : {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    ajouter_url_export_pdf_fix()
