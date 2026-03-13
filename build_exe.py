#!/usr/bin/env python
"""
MySchoolGN - Script de compilation automatique
===============================================
Ce script automatise la compilation de l'application en .exe
avec PyInstaller et prepare le dossier de distribution.
"""

import os
import sys
import shutil
import subprocess

# Repertoire du projet
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DIST_DIR = os.path.join(BASE_DIR, 'dist')
BUILD_DIR = os.path.join(BASE_DIR, 'build')
OUTPUT_DIR = os.path.join(DIST_DIR, 'MySchoolGN')


def step(msg):
    print(f"\n{'='*60}")
    print(f"  {msg}")
    print(f"{'='*60}\n")


def check_prereqs():
    """Verifie les prerequis."""
    step("Verification des prerequis")

    # Verifier PyInstaller
    try:
        import PyInstaller
        print(f"  [OK] PyInstaller {PyInstaller.__version__}")
    except ImportError:
        print("  [MANQUANT] PyInstaller - Installation en cours...")
        subprocess.check_call([sys.executable, '-m', 'pip', 'install', 'pyinstaller'])
        print("  [OK] PyInstaller installe")

    # Verifier Django
    try:
        import django
        print(f"  [OK] Django {django.get_version()}")
    except ImportError:
        print("  [ERREUR] Django non installe!")
        sys.exit(1)

    # Verifier les autres dependances critiques
    for pkg_name, import_name in [('reportlab', 'reportlab'), ('openpyxl', 'openpyxl'),
                                   ('Pillow', 'PIL'), ('python-dotenv', 'dotenv')]:
        try:
            __import__(import_name)
            print(f"  [OK] {pkg_name}")
        except ImportError:
            print(f"  [MANQUANT] {pkg_name} - Installation...")
            subprocess.check_call([sys.executable, '-m', 'pip', 'install', pkg_name])


def collect_static():
    """Collecte les fichiers statiques Django."""
    step("Collecte des fichiers statiques")
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ecole_moderne.settings')
    os.environ['DJANGO_DEBUG'] = 'true'
    os.environ['DJANGO_SECRET_KEY'] = 'build-key-temp'

    try:
        subprocess.check_call([
            sys.executable, 'manage.py', 'collectstatic', '--noinput'
        ], cwd=BASE_DIR)
        print("  [OK] Fichiers statiques collectes")
    except subprocess.CalledProcessError:
        print("  [AVERTISSEMENT] Erreur lors de collectstatic (non critique)")


def run_pyinstaller():
    """Execute PyInstaller avec le fichier spec."""
    step("Compilation avec PyInstaller")

    spec_file = os.path.join(BASE_DIR, 'myschool.spec')
    if not os.path.exists(spec_file):
        print(f"  [ERREUR] Fichier spec introuvable: {spec_file}")
        sys.exit(1)

    # Nettoyer les anciens builds
    for d in [BUILD_DIR, os.path.join(DIST_DIR, 'MySchoolGN')]:
        if os.path.exists(d):
            print(f"  Suppression de {d}...")
            shutil.rmtree(d)

    # Lancer PyInstaller
    cmd = [
        sys.executable, '-m', 'PyInstaller',
        '--clean',
        '--noconfirm',
        spec_file
    ]
    print(f"  Commande: {' '.join(cmd)}")
    subprocess.check_call(cmd, cwd=BASE_DIR)
    print("  [OK] Compilation terminee")


def copy_extra_files():
    """Copie les fichiers supplementaires dans le dossier de distribution."""
    step("Copie des fichiers supplementaires")

    if not os.path.exists(OUTPUT_DIR):
        print(f"  [ERREUR] Dossier de sortie introuvable: {OUTPUT_DIR}")
        return

    # Copier les templates (au cas ou PyInstaller les aurait manques)
    templates_src = os.path.join(BASE_DIR, 'templates')
    templates_dst = os.path.join(OUTPUT_DIR, 'templates')
    if os.path.exists(templates_src) and not os.path.exists(templates_dst):
        shutil.copytree(templates_src, templates_dst)
        print("  [OK] Templates copies")

    # Copier les fichiers statiques
    static_src = os.path.join(BASE_DIR, 'static')
    static_dst = os.path.join(OUTPUT_DIR, 'static')
    if os.path.exists(static_src) and not os.path.exists(static_dst):
        shutil.copytree(static_src, static_dst)
        print("  [OK] Fichiers statiques copies")

    # Copier le dossier media
    media_src = os.path.join(BASE_DIR, 'media')
    media_dst = os.path.join(OUTPUT_DIR, 'media')
    if os.path.exists(media_src) and not os.path.exists(media_dst):
        shutil.copytree(media_src, media_dst)
        print("  [OK] Dossier media copie")

    # Copier la base de donnees
    db_src = os.path.join(BASE_DIR, 'db.sqlite3')
    db_dst = os.path.join(OUTPUT_DIR, 'db.sqlite3')
    if os.path.exists(db_src) and not os.path.exists(db_dst):
        shutil.copy2(db_src, db_dst)
        print("  [OK] Base de donnees copiee")

    # Creer les dossiers necessaires
    for folder in ['logs', 'media']:
        folder_path = os.path.join(OUTPUT_DIR, folder)
        os.makedirs(folder_path, exist_ok=True)

    print("  [OK] Fichiers supplementaires copies")


def create_launcher_bat():
    """Cree un fichier .bat de lancement facile."""
    step("Creation du lanceur .bat")

    bat_content = '''@echo off
title MySchoolGN - Systeme de Gestion Scolaire
echo.
echo ============================================================
echo    MySchoolGN - Systeme de Gestion Scolaire
echo    Version Offline
echo ============================================================
echo.
echo Demarrage du serveur...
echo.
cd /d "%~dp0"
MySchoolGN.exe
pause
'''
    bat_path = os.path.join(OUTPUT_DIR, 'Demarrer_MySchoolGN.bat')
    with open(bat_path, 'w', encoding='utf-8') as f:
        f.write(bat_content)
    print(f"  [OK] Lanceur cree: {bat_path}")


def create_stop_bat():
    """Cree un fichier .bat pour arreter le serveur."""
    bat_content = '''@echo off
echo Arret de MySchoolGN...
taskkill /F /IM MySchoolGN.exe >nul 2>&1
echo Serveur arrete.
timeout /t 2 >nul
'''
    bat_path = os.path.join(OUTPUT_DIR, 'Arreter_MySchoolGN.bat')
    with open(bat_path, 'w', encoding='utf-8') as f:
        f.write(bat_content)
    print(f"  [OK] Script d'arret cree: {bat_path}")


def copy_gtk_dlls():
    """Copie les DLLs GTK/Pango/Cairo pour WeasyPrint offline."""
    step("Copie des DLLs GTK pour WeasyPrint")

    gtk_dll_dir = r'C:\msys64\mingw64\bin'
    internal_dir = os.path.join(OUTPUT_DIR, '_internal')

    if not os.path.isdir(gtk_dll_dir):
        print("  [AVERTISSEMENT] MSYS2 non trouve - DLLs GTK non copiees")
        return

    gtk_dlls = [
        'libpango-1.0-0.dll', 'libpangocairo-1.0-0.dll',
        'libpangoft2-1.0-0.dll', 'libpangowin32-1.0-0.dll',
        'libcairo-2.dll', 'libcairo-gobject-2.dll',
        'libgobject-2.0-0.dll', 'libglib-2.0-0.dll',
        'libgio-2.0-0.dll', 'libgmodule-2.0-0.dll',
        'libgdk_pixbuf-2.0-0.dll', 'libfontconfig-1.dll',
        'libfreetype-6.dll', 'libfribidi-0.dll',
        'libharfbuzz-0.dll', 'libintl-8.dll',
        'libiconv-2.dll', 'libpixman-1-0.dll',
        'libpng16-16.dll', 'libexpat-1.dll',
        'libpcre2-8-0.dll', 'zlib1.dll',
        'libffi-8.dll', 'libgraphite2.dll',
        'libbrotlidec.dll', 'libbrotlicommon.dll',
        'libbz2-1.dll', 'libstdc++-6.dll',
        'libgcc_s_seh-1.dll', 'libwinpthread-1.dll',
    ]

    copied = 0
    for dll in gtk_dlls:
        src = os.path.join(gtk_dll_dir, dll)
        dst = os.path.join(internal_dir, dll)
        if os.path.exists(src) and not os.path.exists(dst):
            shutil.copy2(src, dst)
            copied += 1
    print(f"  [OK] {copied} DLLs GTK copiees dans _internal/")

    # Copier les loaders GdkPixbuf
    loaders_src = r'C:\msys64\mingw64\lib\gdk-pixbuf-2.0\2.10.0\loaders'
    loaders_dst = os.path.join(internal_dir, 'lib', 'gdk-pixbuf-2.0', '2.10.0', 'loaders')
    if os.path.isdir(loaders_src) and not os.path.isdir(loaders_dst):
        shutil.copytree(loaders_src, loaders_dst)
        # Copier aussi le loaders.cache
        cache_src = os.path.join(os.path.dirname(loaders_src), 'loaders.cache')
        if os.path.exists(cache_src):
            shutil.copy2(cache_src, os.path.join(os.path.dirname(loaders_dst), 'loaders.cache'))
        print("  [OK] GdkPixbuf loaders copies")


def show_summary():
    """Affiche le resume de la compilation."""
    step("COMPILATION TERMINEE")

    # Calculer la taille du dossier
    total_size = 0
    for dirpath, dirnames, filenames in os.walk(OUTPUT_DIR):
        for f in filenames:
            fp = os.path.join(dirpath, f)
            total_size += os.path.getsize(fp)
    size_mb = total_size / (1024 * 1024)

    print(f"  Dossier de sortie: {OUTPUT_DIR}")
    print(f"  Taille totale:     {size_mb:.1f} Mo")
    print(f"")
    print(f"  Fichiers principaux:")
    print(f"    - MySchoolGN.exe           (Application)")
    print(f"    - Demarrer_MySchoolGN.bat  (Lanceur)")
    print(f"    - Arreter_MySchoolGN.bat   (Arret)")
    print(f"")
    print(f"  Pour tester:")
    print(f"    1. Ouvrez le dossier: {OUTPUT_DIR}")
    print(f"    2. Double-cliquez sur 'Demarrer_MySchoolGN.bat'")
    print(f"    3. Le navigateur s'ouvrira sur http://127.0.0.1:8000")
    print(f"")
    print(f"  Pour creer l'installateur:")
    print(f"    - Installez Inno Setup (https://jrsoftware.org/isinfo.php)")
    print(f"    - Compilez le fichier 'installer_myschool.iss'")
    print(f"")


def main():
    print("")
    print("*" * 60)
    print("  MySchoolGN - Compilation en .exe")
    print("*" * 60)

    os.chdir(BASE_DIR)

    check_prereqs()
    collect_static()
    run_pyinstaller()
    copy_extra_files()
    copy_gtk_dlls()
    create_launcher_bat()
    create_stop_bat()
    show_summary()


if __name__ == '__main__':
    main()
