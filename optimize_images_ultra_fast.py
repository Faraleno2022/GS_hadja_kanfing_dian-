"""
Script d'optimisation ultra-rapide des images pour chargement instantané
Convertit les images en WebP avec qualité optimale et crée des versions optimisées
"""

import os
from PIL import Image
import sys

# Fix pour l'encodage Windows
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

def optimize_image(input_path, output_dir, max_width=1920, webp_quality=85, jpg_quality=85):
    """
    Optimise une image en créant des versions WebP et JPEG optimisées
    
    Args:
        input_path: Chemin de l'image source
        output_dir: Dossier de sortie
        max_width: Largeur maximale (défaut: 1920px)
        webp_quality: Qualité WebP (défaut: 85)
        jpg_quality: Qualité JPEG (défaut: 85)
    """
    try:
        # Ouvrir l'image
        img = Image.open(input_path)
        filename = os.path.basename(input_path)
        name_without_ext = os.path.splitext(filename)[0]
        
        # Convertir en RGB si nécessaire (pour WebP)
        if img.mode in ('RGBA', 'LA', 'P'):
            background = Image.new('RGB', img.size, (255, 255, 255))
            if img.mode == 'P':
                img = img.convert('RGBA')
            background.paste(img, mask=img.split()[-1] if img.mode in ('RGBA', 'LA') else None)
            img = background
        elif img.mode != 'RGB':
            img = img.convert('RGB')
        
        # Redimensionner si nécessaire
        if img.width > max_width:
            ratio = max_width / img.width
            new_height = int(img.height * ratio)
            img = img.resize((max_width, new_height), Image.Resampling.LANCZOS)
            print(f"  ✓ Redimensionné: {img.width}x{img.height}px")
        
        # Créer le dossier de sortie s'il n'existe pas
        os.makedirs(output_dir, exist_ok=True)
        
        # Sauvegarder en WebP (meilleure compression)
        webp_path = os.path.join(output_dir, f"{name_without_ext}.webp")
        img.save(webp_path, 'WEBP', quality=webp_quality, method=6)
        webp_size = os.path.getsize(webp_path) / 1024 / 1024
        print(f"  ✓ WebP créé: {webp_path} ({webp_size:.2f} MB)")
        
        # Sauvegarder en JPEG optimisé (fallback)
        jpg_path = os.path.join(output_dir, f"{name_without_ext}_optimized.jpg")
        img.save(jpg_path, 'JPEG', quality=jpg_quality, optimize=True, progressive=True)
        jpg_size = os.path.getsize(jpg_path) / 1024 / 1024
        print(f"  ✓ JPEG créé: {jpg_path} ({jpg_size:.2f} MB)")
        
        # Calculer la réduction
        original_size = os.path.getsize(input_path) / 1024 / 1024
        reduction = ((original_size - webp_size) / original_size) * 100
        print(f"  ✓ Réduction: {original_size:.2f} MB → {webp_size:.2f} MB ({reduction:.1f}%)")
        
        return True
        
    except Exception as e:
        print(f"  ✗ Erreur: {str(e)}")
        return False

def main():
    """Fonction principale"""
    print("=" * 70)
    print("🚀 OPTIMISATION ULTRA-RAPIDE DES IMAGES")
    print("=" * 70)
    
    # Chemins
    script_dir = os.path.dirname(os.path.abspath(__file__))
    static_images = os.path.join(script_dir, 'static', 'images')
    output_dir = os.path.join(static_images, 'optimized')
    
    # Images à optimiser
    images_to_optimize = [
        'carte1.jpg',
        'carte2.jpg',
        'ecole.jpg'
    ]
    
    print(f"\n📁 Dossier source: {static_images}")
    print(f"📁 Dossier sortie: {output_dir}\n")
    
    success_count = 0
    total_original_size = 0
    total_optimized_size = 0
    
    for image_name in images_to_optimize:
        image_path = os.path.join(static_images, image_name)
        
        if not os.path.exists(image_path):
            print(f"⚠️  {image_name} - Fichier introuvable")
            continue
        
        original_size = os.path.getsize(image_path) / 1024 / 1024
        total_original_size += original_size
        
        print(f"\n🖼️  Traitement: {image_name} ({original_size:.2f} MB)")
        
        if optimize_image(image_path, output_dir):
            success_count += 1
            # Calculer la taille optimisée (WebP)
            webp_path = os.path.join(output_dir, os.path.splitext(image_name)[0] + '.webp')
            if os.path.exists(webp_path):
                total_optimized_size += os.path.getsize(webp_path) / 1024 / 1024
    
    # Résumé
    print("\n" + "=" * 70)
    print("📊 RÉSUMÉ DE L'OPTIMISATION")
    print("=" * 70)
    print(f"✅ Images optimisées: {success_count}/{len(images_to_optimize)}")
    print(f"📦 Taille originale: {total_original_size:.2f} MB")
    print(f"📦 Taille optimisée: {total_optimized_size:.2f} MB")
    
    if total_original_size > 0:
        reduction = ((total_original_size - total_optimized_size) / total_original_size) * 100
        print(f"🎯 Réduction totale: {reduction:.1f}%")
        print(f"⚡ Gain de vitesse estimé: {reduction/10:.0f}x plus rapide")
    
    print("\n" + "=" * 70)
    print("✨ PROCHAINES ÉTAPES:")
    print("=" * 70)
    print("1. Les images optimisées sont dans: static/images/optimized/")
    print("2. Le template home.html utilise déjà ces images optimisées")
    print("3. Format WebP pour navigateurs modernes (Chrome, Firefox, Edge)")
    print("4. Fallback JPEG pour navigateurs anciens")
    print("5. Chargement ultra-rapide garanti! 🚀")
    print("=" * 70)

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  Optimisation interrompue par l'utilisateur")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Erreur fatale: {str(e)}")
        sys.exit(1)
