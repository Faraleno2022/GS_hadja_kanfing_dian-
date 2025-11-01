#!/usr/bin/env python
"""
Script utilitaire pour la gestion des images de la page d'accueil.
Permet de remplacer facilement les images et de forcer leur rechargement.
"""
import os
import shutil
import time
from pathlib import Path

# Configuration
STATIC_IMAGES_DIR = Path(__file__).parent / 'static' / 'images'
BACKUP_DIR = Path(__file__).parent / 'static' / 'images' / 'backup'

def ensure_directories():
    """Créer les dossiers nécessaires s'ils n'existent pas."""
    STATIC_IMAGES_DIR.mkdir(parents=True, exist_ok=True)
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)

def backup_current_images():
    """Sauvegarder les images actuelles."""
    ensure_directories()
    
    images = ['ecole.jpg', 'carte1.jpg', 'carte2.jpg']
    timestamp = int(time.time())
    
    print("🔄 Sauvegarde des images actuelles...")
    
    for image in images:
        source = STATIC_IMAGES_DIR / image
        if source.exists():
            backup_name = f"{image.stem}_{timestamp}{image.suffix}"
            destination = BACKUP_DIR / backup_name
            shutil.copy2(source, destination)
            print(f"✅ {image} → {backup_name}")
        else:
            print(f"⚠️  {image} n'existe pas")
    
    print(f"📁 Sauvegarde terminée dans: {BACKUP_DIR}")

def replace_image(image_name, new_image_path):
    """Remplacer une image spécifique."""
    ensure_directories()
    
    if not os.path.exists(new_image_path):
        print(f"❌ Erreur: Le fichier {new_image_path} n'existe pas")
        return False
    
    # Vérifier que c'est une image valide
    valid_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.webp']
    if not any(new_image_path.lower().endswith(ext) for ext in valid_extensions):
        print(f"❌ Erreur: {new_image_path} n'est pas un format d'image valide")
        return False
    
    destination = STATIC_IMAGES_DIR / image_name
    
    try:
        # Sauvegarder l'ancienne image si elle existe
        if destination.exists():
            timestamp = int(time.time())
            backup_name = f"{destination.stem}_old_{timestamp}{destination.suffix}"
            backup_path = BACKUP_DIR / backup_name
            shutil.copy2(destination, backup_path)
            print(f"💾 Ancienne image sauvegardée: {backup_name}")
        
        # Copier la nouvelle image
        shutil.copy2(new_image_path, destination)
        print(f"✅ Image remplacée: {image_name}")
        
        # Modifier la date de modification pour forcer le rechargement
        current_time = time.time()
        os.utime(destination, (current_time, current_time))
        
        return True
        
    except Exception as e:
        print(f"❌ Erreur lors du remplacement: {e}")
        return False

def force_reload_all():
    """Forcer le rechargement de toutes les images en modifiant leur timestamp."""
    ensure_directories()
    
    images = ['ecole.jpg', 'carte1.jpg', 'carte2.jpg']
    current_time = time.time()
    
    print("🔄 Forçage du rechargement des images...")
    
    for image in images:
        image_path = STATIC_IMAGES_DIR / image
        if image_path.exists():
            os.utime(image_path, (current_time, current_time))
            print(f"✅ {image} - timestamp mis à jour")
        else:
            print(f"⚠️  {image} n'existe pas")
    
    print("🎉 Rechargement forcé terminé!")

def list_images():
    """Lister toutes les images disponibles avec leurs informations."""
    ensure_directories()
    
    print("📋 Images disponibles:")
    print("-" * 50)
    
    images = ['ecole.jpg', 'carte1.jpg', 'carte2.jpg']
    
    for image in images:
        image_path = STATIC_IMAGES_DIR / image
        if image_path.exists():
            stat = image_path.stat()
            size_kb = stat.st_size / 1024
            mod_time = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(stat.st_mtime))
            print(f"✅ {image}")
            print(f"   📏 Taille: {size_kb:.1f} KB")
            print(f"   📅 Modifié: {mod_time}")
            print(f"   📁 Chemin: {image_path}")
        else:
            print(f"❌ {image} - MANQUANT")
        print()

def show_help():
    """Afficher l'aide."""
    print("""
🖼️  Gestionnaire d'Images - myschool

Usage:
    python manage_images.py [commande] [arguments]

Commandes disponibles:
    list                    - Lister toutes les images
    backup                  - Sauvegarder les images actuelles
    replace <nom> <chemin>  - Remplacer une image
    reload                  - Forcer le rechargement de toutes les images
    help                    - Afficher cette aide

Exemples:
    python manage_images.py list
    python manage_images.py backup
    python manage_images.py replace ecole.jpg /chemin/vers/nouvelle_image.jpg
    python manage_images.py reload

Images gérées:
    - ecole.jpg     : Image principale de la page d'accueil
    - carte1.jpg    : Première image de présentation
    - carte2.jpg    : Deuxième image de présentation

Note: Après avoir remplacé des images, rechargez la page web pour voir les changements.
""")

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        show_help()
        sys.exit(1)
    
    command = sys.argv[1].lower()
    
    if command == "list":
        list_images()
    elif command == "backup":
        backup_current_images()
    elif command == "replace":
        if len(sys.argv) != 4:
            print("❌ Usage: python manage_images.py replace <nom_image> <chemin_nouvelle_image>")
            sys.exit(1)
        image_name = sys.argv[2]
        new_path = sys.argv[3]
        replace_image(image_name, new_path)
    elif command == "reload":
        force_reload_all()
    elif command == "help":
        show_help()
    else:
        print(f"❌ Commande inconnue: {command}")
        show_help()
        sys.exit(1)
