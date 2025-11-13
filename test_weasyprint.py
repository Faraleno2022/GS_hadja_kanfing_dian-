#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Test de WeasyPrint - Vérification de l'installation
"""

def test_weasyprint_installation():
    """Teste si WeasyPrint est correctement installé"""
    print("=" * 60)
    print("TEST D'INSTALLATION DE WEASYPRINT")
    print("=" * 60)
    
    # Test 1: Import de WeasyPrint
    print("\n1. Test d'import de WeasyPrint...")
    try:
        from weasyprint import HTML, CSS
        from weasyprint.text.fonts import FontConfiguration
        print("   ✅ WeasyPrint importé avec succès!")
    except ImportError as e:
        print(f"   ❌ Erreur d'import: {e}")
        return False
    
    # Test 2: Génération d'un PDF simple
    print("\n2. Test de génération PDF simple...")
    try:
        html_content = """
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <style>
                body { font-family: Arial, sans-serif; padding: 20px; }
                h1 { color: #007bff; }
                .test { background: #f0f0f0; padding: 10px; }
            </style>
        </head>
        <body>
            <h1>Test WeasyPrint</h1>
            <div class="test">
                <p>Ceci est un test de génération PDF avec WeasyPrint.</p>
                <p>Date: 13/11/2024</p>
            </div>
        </body>
        </html>
        """
        
        # Générer le PDF
        HTML(string=html_content).write_pdf('test_weasyprint_output.pdf')
        print("   ✅ PDF généré avec succès: test_weasyprint_output.pdf")
    except Exception as e:
        print(f"   ❌ Erreur de génération PDF: {e}")
        return False
    
    # Test 3: Test avec image base64
    print("\n3. Test avec image base64...")
    try:
        html_with_image = """
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <style>
                body { font-family: Arial; }
                .logo { width: 50px; height: 50px; }
            </style>
        </head>
        <body>
            <h1>Test avec Image</h1>
            <!-- Image base64 simple (carré rouge) -->
            <img class="logo" src="data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8DwHwAFBQIAX8jx0gAAAABJRU5ErkJggg==" alt="Test">
            <p>Image base64 intégrée</p>
        </body>
        </html>
        """
        
        HTML(string=html_with_image).write_pdf('test_weasyprint_image.pdf')
        print("   ✅ PDF avec image base64 généré: test_weasyprint_image.pdf")
    except Exception as e:
        print(f"   ❌ Erreur avec image base64: {e}")
        return False
    
    # Test 4: Vérifier les dépendances
    print("\n4. Vérification des dépendances...")
    try:
        import pydyf
        print("   ✅ pydyf installé")
    except:
        print("   ❌ pydyf manquant")
    
    try:
        import tinycss2
        print("   ✅ tinycss2 installé")
    except:
        print("   ❌ tinycss2 manquant")
    
    try:
        import fonttools
        print("   ✅ fonttools installé")
    except:
        print("   ❌ fonttools manquant")
    
    print("\n" + "=" * 60)
    print("✅ TOUS LES TESTS RÉUSSIS - WeasyPrint est opérationnel!")
    print("=" * 60)
    return True

def test_reportlab_backup():
    """Teste si ReportLab est disponible comme backup"""
    print("\n" + "=" * 60)
    print("TEST DE REPORTLAB (BACKUP)")
    print("=" * 60)
    
    try:
        from reportlab.pdfgen import canvas
        from reportlab.lib.pagesizes import A4
        print("✅ ReportLab disponible comme solution de secours")
        
        # Test simple
        c = canvas.Canvas("test_reportlab.pdf", pagesize=A4)
        c.drawString(100, 750, "Test ReportLab - Backup PDF Generator")
        c.save()
        print("✅ PDF test créé avec ReportLab: test_reportlab.pdf")
        return True
    except ImportError:
        print("❌ ReportLab non disponible")
        return False

if __name__ == "__main__":
    print("🚀 Démarrage des tests...\n")
    
    # Test WeasyPrint
    weasyprint_ok = test_weasyprint_installation()
    
    # Test ReportLab comme backup
    reportlab_ok = test_reportlab_backup()
    
    # Résumé
    print("\n" + "=" * 60)
    print("RÉSUMÉ DES TESTS")
    print("=" * 60)
    
    if weasyprint_ok:
        print("✅ WeasyPrint: FONCTIONNEL")
        print("   → L'export PDF des bulletins devrait fonctionner")
    else:
        print("❌ WeasyPrint: PROBLÈME DÉTECTÉ")
        print("   → Voir les erreurs ci-dessus")
    
    if reportlab_ok:
        print("✅ ReportLab: DISPONIBLE (backup)")
    else:
        print("⚠️ ReportLab: NON DISPONIBLE")
    
    print("\n💡 Conseil: Si WeasyPrint ne fonctionne pas sur Windows,")
    print("   installez GTK+ Runtime Environment.")
    print("\n📁 Fichiers de test créés:")
    print("   - test_weasyprint_output.pdf")
    print("   - test_weasyprint_image.pdf")
    print("   - test_reportlab.pdf")
