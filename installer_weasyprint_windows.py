#!/usr/bin/env python
"""
Script d'installation automatique de WeasyPrint sur Windows
Installe GTK+ et configure WeasyPrint pour les bulletins PDF
"""
import os
import sys
import subprocess
import urllib.request
import zipfile
import shutil
from pathlib import Path

def print_step(step, message):
    """Afficher une étape avec formatage"""
    print(f"\n🔧 ÉTAPE {step}: {message}")
    print("=" * (len(message) + 15))

def run_command(command, description):
    """Exécuter une commande avec gestion d'erreur"""
    print(f"📋 {description}...")
    try:
        result = subprocess.run(command, shell=True, capture_output=True, text=True)
        if result.returncode == 0:
            print(f"✅ {description} - Succès")
            return True
        else:
            print(f"❌ {description} - Erreur:")
            print(f"   {result.stderr}")
            return False
    except Exception as e:
        print(f"❌ {description} - Exception: {e}")
        return False

def check_admin_rights():
    """Vérifier les droits administrateur"""
    try:
        import ctypes
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False

def install_chocolatey():
    """Installer Chocolatey si pas présent"""
    print_step(1, "INSTALLATION CHOCOLATEY")
    
    # Vérifier si Chocolatey est déjà installé
    if run_command("choco --version", "Vérification Chocolatey"):
        print("✅ Chocolatey déjà installé")
        return True
    
    print("📋 Installation de Chocolatey...")
    
    # Commande d'installation Chocolatey
    install_cmd = '''
    Set-ExecutionPolicy Bypass -Scope Process -Force;
    [System.Net.ServicePointManager]::SecurityProtocol = [System.Net.ServicePointManager]::SecurityProtocol -bor 3072;
    iex ((New-Object System.Net.WebClient).DownloadString('https://community.chocolatey.org/install.ps1'))
    '''
    
    # Exécuter via PowerShell
    powershell_cmd = f'powershell -Command "{install_cmd}"'
    
    if run_command(powershell_cmd, "Installation Chocolatey"):
        print("✅ Chocolatey installé avec succès")
        return True
    else:
        print("❌ Échec installation Chocolatey")
        return False

def install_gtk_runtime():
    """Installer GTK+ Runtime via Chocolatey"""
    print_step(2, "INSTALLATION GTK+ RUNTIME")
    
    commands = [
        ("choco install gtk-runtime -y", "Installation GTK+ Runtime"),
        ("choco install msys2 -y", "Installation MSYS2 (optionnel)"),
    ]
    
    success = True
    for cmd, desc in commands:
        if not run_command(cmd, desc):
            success = False
    
    return success

def install_weasyprint():
    """Installer/Réinstaller WeasyPrint"""
    print_step(3, "INSTALLATION WEASYPRINT")
    
    commands = [
        ("pip uninstall weasyprint -y", "Désinstallation WeasyPrint existant"),
        ("pip install --upgrade pip", "Mise à jour pip"),
        ("pip install weasyprint", "Installation WeasyPrint"),
    ]
    
    for cmd, desc in commands:
        run_command(cmd, desc)
    
    return True

def test_weasyprint():
    """Tester WeasyPrint"""
    print_step(4, "TEST WEASYPRINT")
    
    test_script = '''
import sys
try:
    from weasyprint import HTML, CSS
    from weasyprint.text.fonts import FontConfiguration
    print("✅ WeasyPrint importé avec succès")
    
    # Test de génération PDF simple
    html_content = "<html><body><h1>Test WeasyPrint</h1><p>Ceci est un test.</p></body></html>"
    pdf_bytes = HTML(string=html_content).write_pdf()
    print(f"✅ PDF généré avec succès ({len(pdf_bytes)} bytes)")
    
    sys.exit(0)
except ImportError as e:
    print(f"❌ Erreur import: {e}")
    sys.exit(1)
except Exception as e:
    print(f"❌ Erreur génération: {e}")
    sys.exit(1)
'''
    
    # Écrire le script de test
    with open('test_weasyprint_temp.py', 'w', encoding='utf-8') as f:
        f.write(test_script)
    
    # Exécuter le test
    success = run_command("python test_weasyprint_temp.py", "Test WeasyPrint")
    
    # Nettoyer
    try:
        os.remove('test_weasyprint_temp.py')
    except:
        pass
    
    return success

def configure_environment():
    """Configurer les variables d'environnement"""
    print_step(5, "CONFIGURATION ENVIRONNEMENT")
    
    # Chemins GTK+ typiques
    gtk_paths = [
        r"C:\ProgramData\chocolatey\lib\gtk-runtime\tools\gtk\bin",
        r"C:\tools\msys64\mingw64\bin",
        r"C:\msys64\mingw64\bin",
    ]
    
    current_path = os.environ.get('PATH', '')
    
    for gtk_path in gtk_paths:
        if os.path.exists(gtk_path) and gtk_path not in current_path:
            print(f"📋 Ajout du chemin GTK+: {gtk_path}")
            os.environ['PATH'] = f"{gtk_path};{current_path}"
            
            # Commande pour ajouter de façon permanente
            setx_cmd = f'setx PATH "%PATH%;{gtk_path}"'
            run_command(setx_cmd, f"Ajout permanent du chemin {gtk_path}")
    
    return True

def main():
    """Fonction principale d'installation"""
    print("🚀 INSTALLATION WEASYPRINT POUR WINDOWS")
    print("=" * 45)
    
    # Vérifier les droits admin
    if not check_admin_rights():
        print("⚠️  ATTENTION: Droits administrateur recommandés")
        print("   Relancez ce script en tant qu'administrateur pour une installation complète")
        input("   Appuyez sur Entrée pour continuer quand même...")
    
    success_steps = 0
    total_steps = 5
    
    # Étape 1: Chocolatey
    if install_chocolatey():
        success_steps += 1
    
    # Étape 2: GTK+ Runtime
    if install_gtk_runtime():
        success_steps += 1
    
    # Étape 3: WeasyPrint
    if install_weasyprint():
        success_steps += 1
    
    # Étape 4: Configuration environnement
    if configure_environment():
        success_steps += 1
    
    # Étape 5: Test
    if test_weasyprint():
        success_steps += 1
    
    # Résultats
    print(f"\n🎯 RÉSULTATS INSTALLATION")
    print("=" * 30)
    print(f"Étapes réussies: {success_steps}/{total_steps}")
    
    if success_steps == total_steps:
        print("✅ INSTALLATION COMPLÈTE RÉUSSIE!")
        print("\n🎉 WeasyPrint est maintenant fonctionnel")
        print("📋 Vous pouvez maintenant générer des bulletins PDF individuels")
        print("\n🔗 Test immédiat:")
        print("   http://127.0.0.1:8000/notes/bulletins/pdf/?classe_id=59&eleve_id=422&periode=OCTOBRE&system_type=mensuel")
    else:
        print("⚠️  INSTALLATION PARTIELLE")
        print("\n📋 Solutions alternatives:")
        print("1. Redémarrer l'ordinateur et relancer ce script")
        print("2. Installer manuellement GTK+ Runtime")
        print("3. Utiliser la consultation des notes en attendant")
    
    print(f"\n📄 Log d'installation sauvegardé dans: weasyprint_install.log")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n❌ Installation interrompue par l'utilisateur")
    except Exception as e:
        print(f"\n❌ Erreur inattendue: {e}")
        import traceback
        traceback.print_exc()
