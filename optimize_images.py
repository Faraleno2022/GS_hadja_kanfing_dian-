#!/usr/bin/env python
"""
Script d'optimisation des images pour améliorer les performances de chargement.
Compresse et redimensionne les images tout en maintenant la qualité visuelle.
"""
import os
import sys
from pathlib import Path
from PIL import Image, ImageOps
import time

# Configuration
STATIC_IMAGES_DIR = Path(__file__).parent / 'static' / 'images'
OPTIMIZED_DIR = STATIC_IMAGES_DIR / 'optimized'
ORIGINAL_DIR = STATIC_IMAGES_DIR / 'original'

# Paramètres d'optimisation
OPTIMIZATION_SETTINGS = {
    'ecole.jpg': {
        'max_width': 1920,
        'max_height': 1080,
        'quality': 85,
        'description': 'Image hero plein écran'
    },
    'carte1.jpg': {
        'max_width': 800,
        'max_height': 600,
        'quality': 80,
        'description': 'Image de présentation 1'
    },
    'carte2.jpg': {
        'max_width': 800,
        'max_height': 600,
        'quality': 80,
        'description': 'Image de présentation 2'
    }
}

def ensure_directories():
    """Créer les dossiers nécessaires."""
    OPTIMIZED_DIR.mkdir(parents=True, exist_ok=True)
    ORIGINAL_DIR.mkdir(parents=True, exist_ok=True)

def get_file_size(file_path):
    """Obtenir la taille d'un fichier en KB."""
    return os.path.getsize(file_path) / 1024

def backup_original(image_path):
    """Sauvegarder l'image originale."""
    if image_path.exists():
        backup_path = ORIGINAL_DIR / image_path.name
        if not backup_path.exists():
            import shutil
            shutil.copy2(image_path, backup_path)
            print(f"💾 Original sauvegardé: {backup_path}")

def optimize_image(image_path, settings):
    """Optimiser une image selon les paramètres donnés."""
    try:
        # Ouvrir l'image
        with Image.open(image_path) as img:
            # Corriger l'orientation EXIF
            img = ImageOps.exif_transpose(img)
            
            # Convertir en RGB si nécessaire
            if img.mode in ('RGBA', 'P'):
                # Créer un fond blanc pour les images transparentes
                background = Image.new('RGB', img.size, (255, 255, 255))
                if img.mode == 'P':
                    img = img.convert('RGBA')
                background.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
                img = background
            elif img.mode != 'RGB':
                img = img.convert('RGB')
            
            # Redimensionner si nécessaire
            max_width = settings['max_width']
            max_height = settings['max_height']
            
            if img.width > max_width or img.height > max_height:
                # Calculer les nouvelles dimensions en gardant le ratio
                ratio = min(max_width / img.width, max_height / img.height)
                new_width = int(img.width * ratio)
                new_height = int(img.height * ratio)
                
                # Redimensionner avec un algorithme de haute qualité
                img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
                print(f"📏 Redimensionné: {img.width}x{img.height}")
            
            # Sauvegarder l'image optimisée
            optimized_path = OPTIMIZED_DIR / f"{image_path.stem}_optimized{image_path.suffix}"
            
            # Paramètres de sauvegarde JPEG optimisés
            save_kwargs = {
                'format': 'JPEG',
                'quality': settings['quality'],
                'optimize': True,
                'progressive': True,  # JPEG progressif pour un chargement plus fluide
            }
            
            img.save(optimized_path, **save_kwargs)
            
            return optimized_path
            
    except Exception as e:
        print(f"❌ Erreur lors de l'optimisation de {image_path}: {e}")
        return None

def create_webp_version(image_path, settings):
    """Créer une version WebP de l'image pour les navigateurs modernes."""
    try:
        with Image.open(image_path) as img:
            # Corriger l'orientation EXIF
            img = ImageOps.exif_transpose(img)
            
            # Convertir en RGB si nécessaire
            if img.mode in ('RGBA', 'P'):
                background = Image.new('RGB', img.size, (255, 255, 255))
                if img.mode == 'P':
                    img = img.convert('RGBA')
                background.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
                img = background
            elif img.mode != 'RGB':
                img = img.convert('RGB')
            
            # Redimensionner si nécessaire
            max_width = settings['max_width']
            max_height = settings['max_height']
            
            if img.width > max_width or img.height > max_height:
                ratio = min(max_width / img.width, max_height / img.height)
                new_width = int(img.width * ratio)
                new_height = int(img.height * ratio)
                img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
            
            # Sauvegarder en WebP
            webp_path = OPTIMIZED_DIR / f"{image_path.stem}_optimized.webp"
            img.save(webp_path, 'WebP', quality=settings['quality'], method=6)
            
            return webp_path
            
    except Exception as e:
        print(f"⚠️ Impossible de créer la version WebP pour {image_path}: {e}")
        return None

def optimize_all_images():
    """Optimiser toutes les images configurées."""
    ensure_directories()
    
    print("🖼️ Optimisation des images - myschool")
    print("=" * 60)
    
    total_original_size = 0
    total_optimized_size = 0
    
    for image_name, settings in OPTIMIZATION_SETTINGS.items():
        image_path = STATIC_IMAGES_DIR / image_name
        
        if not image_path.exists():
            print(f"⚠️ Image non trouvée: {image_path}")
            continue
        
        print(f"\n📸 Traitement: {image_name}")
        print(f"   Description: {settings['description']}")
        
        # Taille originale
        original_size = get_file_size(image_path)
        total_original_size += original_size
        print(f"   Taille originale: {original_size:.1f} KB")
        
        # Sauvegarder l'original
        backup_original(image_path)
        
        # Optimiser l'image
        optimized_path = optimize_image(image_path, settings)
        
        if optimized_path:
            optimized_size = get_file_size(optimized_path)
            total_optimized_size += optimized_size
            reduction = ((original_size - optimized_size) / original_size) * 100
            
            print(f"   ✅ Optimisé: {optimized_size:.1f} KB (-{reduction:.1f}%)")
            
            # Créer une version WebP
            webp_path = create_webp_version(image_path, settings)
            if webp_path:
                webp_size = get_file_size(webp_path)
                webp_reduction = ((original_size - webp_size) / original_size) * 100
                print(f"   🌐 WebP: {webp_size:.1f} KB (-{webp_reduction:.1f}%)")
        else:
            print(f"   ❌ Échec de l'optimisation")
    
    # Résumé
    print("\n" + "=" * 60)
    print("📊 RÉSUMÉ DE L'OPTIMISATION")
    print(f"Taille totale originale: {total_original_size:.1f} KB")
    print(f"Taille totale optimisée: {total_optimized_size:.1f} KB")
    
    if total_original_size > 0:
        total_reduction = ((total_original_size - total_optimized_size) / total_original_size) * 100
        print(f"Réduction totale: {total_reduction:.1f}%")
        print(f"Économie: {total_original_size - total_optimized_size:.1f} KB")

def create_responsive_versions():
    """Créer des versions responsive des images."""
    print("\n🔄 Création des versions responsive...")
    
    responsive_sizes = {
        'small': {'width': 480, 'suffix': '_sm'},
        'medium': {'width': 768, 'suffix': '_md'},
        'large': {'width': 1200, 'suffix': '_lg'}
    }
    
    for image_name in OPTIMIZATION_SETTINGS.keys():
        image_path = STATIC_IMAGES_DIR / image_name
        
        if not image_path.exists():
            continue
        
        print(f"📱 Versions responsive pour: {image_name}")
        
        try:
            with Image.open(image_path) as img:
                img = ImageOps.exif_transpose(img)
                
                if img.mode != 'RGB':
                    if img.mode in ('RGBA', 'P'):
                        background = Image.new('RGB', img.size, (255, 255, 255))
                        if img.mode == 'P':
                            img = img.convert('RGBA')
                        background.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
                        img = background
                    else:
                        img = img.convert('RGB')
                
                for size_name, size_config in responsive_sizes.items():
                    if img.width > size_config['width']:
                        ratio = size_config['width'] / img.width
                        new_height = int(img.height * ratio)
                        
                        resized_img = img.resize((size_config['width'], new_height), Image.Resampling.LANCZOS)
                        
                        # Sauvegarder la version responsive
                        responsive_path = OPTIMIZED_DIR / f"{image_path.stem}{size_config['suffix']}{image_path.suffix}"
                        resized_img.save(responsive_path, 'JPEG', quality=80, optimize=True)
                        
                        size_kb = get_file_size(responsive_path)
                        print(f"   {size_name}: {size_config['width']}px - {size_kb:.1f} KB")
                        
        except Exception as e:
            print(f"❌ Erreur responsive pour {image_name}: {e}")

def show_help():
    """Afficher l'aide."""
    print("""
🖼️ Optimiseur d'Images - myschool

Usage:
    python optimize_images.py [commande]

Commandes:
    optimize    - Optimiser toutes les images (défaut)
    responsive  - Créer des versions responsive
    all         - Optimiser + versions responsive
    help        - Afficher cette aide

Fonctionnalités:
    ✅ Compression JPEG optimisée
    ✅ Redimensionnement intelligent
    ✅ Versions WebP pour navigateurs modernes
    ✅ Versions responsive (mobile, tablette, desktop)
    ✅ Sauvegarde automatique des originaux
    ✅ Correction de l'orientation EXIF
    ✅ JPEG progressif pour chargement fluide

Images traitées:
    - ecole.jpg     : Image hero (1920x1080, 85% qualité)
    - carte1.jpg    : Présentation 1 (800x600, 80% qualité)
    - carte2.jpg    : Présentation 2 (800x600, 80% qualité)

Dossiers:
    - static/images/original/   : Sauvegardes des originaux
    - static/images/optimized/  : Images optimisées
""")

if __name__ == "__main__":
    try:
        from PIL import Image, ImageOps
    except ImportError:
        print("❌ Pillow n'est pas installé. Installez-le avec:")
        print("   pip install Pillow")
        sys.exit(1)
    
    command = sys.argv[1].lower() if len(sys.argv) > 1 else 'optimize'
    
    if command == 'optimize':
        optimize_all_images()
    elif command == 'responsive':
        create_responsive_versions()
    elif command == 'all':
        optimize_all_images()
        create_responsive_versions()
    elif command == 'help':
        show_help()
    else:
        print(f"❌ Commande inconnue: {command}")
        show_help()
        sys.exit(1)
    
    print("\n🎉 Optimisation terminée!")
    print("💡 N'oubliez pas de redémarrer le serveur Django pour voir les changements.")
