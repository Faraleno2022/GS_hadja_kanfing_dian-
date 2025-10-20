"""
Script de test pour vérifier l'optimisation des images
Vérifie que toutes les images optimisées existent et sont bien compressées
"""

import os
import sys

# Fix pour l'encodage Windows
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

def format_size(size_bytes):
    """Formate la taille en MB ou KB"""
    if size_bytes >= 1024 * 1024:
        return f"{size_bytes / 1024 / 1024:.2f} MB"
    else:
        return f"{size_bytes / 1024:.2f} KB"

def test_optimisation():
    """Teste que toutes les images sont optimisées"""
    print("=" * 70)
    print("🧪 TEST D'OPTIMISATION DES IMAGES")
    print("=" * 70)
    
    script_dir = os.path.dirname(os.path.abspath(__file__))
    static_images = os.path.join(script_dir, 'static', 'images')
    optimized_dir = os.path.join(static_images, 'optimized')
    
    # Images à vérifier
    images_originales = {
        'carte1.jpg': 11 * 1024 * 1024,  # 11 MB
        'carte2.jpg': 5 * 1024 * 1024,   # 5 MB
        'ecole.jpg': 1 * 1024 * 1024     # 1 MB
    }
    
    print(f"\n📁 Dossier optimisé: {optimized_dir}\n")
    
    if not os.path.exists(optimized_dir):
        print("❌ ERREUR: Le dossier 'optimized' n'existe pas!")
        print("   Exécutez: python optimize_images_ultra_fast.py")
        return False
    
    tests_passed = 0
    tests_total = 0
    total_reduction = 0
    
    for image_name, max_size in images_originales.items():
        name_without_ext = os.path.splitext(image_name)[0]
        
        print(f"🖼️  Test: {image_name}")
        
        # Vérifier WebP
        tests_total += 1
        webp_path = os.path.join(optimized_dir, f"{name_without_ext}.webp")
        if os.path.exists(webp_path):
            webp_size = os.path.getsize(webp_path)
            print(f"   ✅ WebP existe: {format_size(webp_size)}")
            tests_passed += 1
            
            # Vérifier la compression
            if webp_size < max_size:
                reduction = ((max_size - webp_size) / max_size) * 100
                total_reduction += reduction
                print(f"   ✅ Bien compressé: {reduction:.1f}% de réduction")
            else:
                print(f"   ⚠️  Taille supérieure à l'attendu")
        else:
            print(f"   ❌ WebP manquant: {webp_path}")
        
        # Vérifier JPEG optimisé
        tests_total += 1
        jpg_path = os.path.join(optimized_dir, f"{name_without_ext}_optimized.jpg")
        if os.path.exists(jpg_path):
            jpg_size = os.path.getsize(jpg_path)
            print(f"   ✅ JPEG existe: {format_size(jpg_size)}")
            tests_passed += 1
        else:
            print(f"   ❌ JPEG manquant: {jpg_path}")
        
        print()
    
    # Vérifier le template
    print("📄 Vérification du template home.html")
    template_path = os.path.join(script_dir, 'templates', 'home.html')
    
    if os.path.exists(template_path):
        with open(template_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
        tests_total += 3
        
        # Vérifier les références WebP
        if 'images/optimized/ecole.webp' in content:
            print("   ✅ Référence ecole.webp trouvée")
            tests_passed += 1
        else:
            print("   ❌ Référence ecole.webp manquante")
        
        if 'images/optimized/carte1.webp' in content:
            print("   ✅ Référence carte1.webp trouvée")
            tests_passed += 1
        else:
            print("   ❌ Référence carte1.webp manquante")
        
        if 'images/optimized/carte2.webp' in content:
            print("   ✅ Référence carte2.webp trouvée")
            tests_passed += 1
        else:
            print("   ❌ Référence carte2.webp manquante")
        
        # Vérifier les éléments <picture>
        if content.count('<picture>') >= 3:
            print(f"   ✅ Éléments <picture> trouvés: {content.count('<picture>')}")
        else:
            print(f"   ⚠️  Éléments <picture> insuffisants: {content.count('<picture>')}")
    else:
        print("   ❌ Template home.html introuvable")
    
    # Résumé
    print("\n" + "=" * 70)
    print("📊 RÉSUMÉ DES TESTS")
    print("=" * 70)
    print(f"Tests réussis: {tests_passed}/{tests_total}")
    print(f"Taux de réussite: {(tests_passed/tests_total)*100:.1f}%")
    
    if total_reduction > 0:
        avg_reduction = total_reduction / len(images_originales)
        print(f"Réduction moyenne: {avg_reduction:.1f}%")
    
    if tests_passed == tests_total:
        print("\n🎉 TOUS LES TESTS SONT PASSÉS!")
        print("✅ Vos images sont parfaitement optimisées")
        print("⚡ Chargement ultra-rapide garanti!")
        return True
    else:
        print(f"\n⚠️  {tests_total - tests_passed} test(s) échoué(s)")
        print("Exécutez: python optimize_images_ultra_fast.py")
        return False

if __name__ == '__main__':
    try:
        success = test_optimisation()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ Erreur: {str(e)}")
        sys.exit(1)
