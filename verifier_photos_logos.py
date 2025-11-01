"""
Script de vérification des photos et logos
Vérifie que les chemins sont corrects et les fichiers existent
"""

import os
import django

# Configuration Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ecole_moderne.settings')
django.setup()

from eleves.models import Eleve, Ecole
from django.conf import settings

def verifier_logos_ecoles():
    """Vérifier les logos des écoles"""
    print("\n" + "=" * 70)
    print("VÉRIFICATION DES LOGOS D'ÉCOLES")
    print("=" * 70)
    
    ecoles = Ecole.objects.all()
    
    for ecole in ecoles:
        print(f"\n📍 École: {ecole.nom}")
        
        if ecole.logo:
            print(f"   Logo défini: {ecole.logo.name}")
            
            # Vérifier si le fichier existe
            try:
                if hasattr(ecole.logo, 'path'):
                    logo_path = ecole.logo.path
                    if os.path.exists(logo_path):
                        file_size = os.path.getsize(logo_path) / 1024  # Ko
                        print(f"   ✅ Fichier existe: {logo_path}")
                        print(f"   ✅ Taille: {file_size:.2f} Ko")
                    else:
                        print(f"   ❌ Fichier introuvable: {logo_path}")
                else:
                    print(f"   ⚠️  Pas de chemin physique (peut-être stockage distant)")
            except Exception as e:
                print(f"   ❌ Erreur: {e}")
        else:
            print(f"   ⚠️  Aucun logo défini")
            print(f"   💡 Conseil: Ajoutez un logo dans l'admin Django")

def verifier_photos_eleves():
    """Vérifier les photos des élèves"""
    print("\n" + "=" * 70)
    print("VÉRIFICATION DES PHOTOS D'ÉLÈVES")
    print("=" * 70)
    
    eleves = Eleve.objects.all()
    total = eleves.count()
    avec_photo = 0
    sans_photo = 0
    photo_manquante = 0
    
    print(f"\n📊 Total élèves: {total}")
    
    for eleve in eleves:
        if eleve.photo:
            avec_photo += 1
            try:
                if hasattr(eleve.photo, 'path'):
                    photo_path = eleve.photo.path
                    if not os.path.exists(photo_path):
                        photo_manquante += 1
                        print(f"   ❌ Photo manquante: {eleve.matricule} - {eleve.nom_complet}")
                        print(f"      Chemin: {photo_path}")
            except Exception as e:
                photo_manquante += 1
                print(f"   ❌ Erreur pour {eleve.matricule}: {e}")
        else:
            sans_photo += 1
    
    print(f"\n📊 Statistiques:")
    print(f"   ✅ Avec photo: {avec_photo} ({avec_photo/total*100:.1f}%)")
    print(f"   ⚠️  Sans photo: {sans_photo} ({sans_photo/total*100:.1f}%)")
    print(f"   ❌ Photo manquante: {photo_manquante}")
    
    if sans_photo > 0:
        print(f"\n💡 Conseil: {sans_photo} élève(s) n'ont pas de photo")
        print(f"   Ajoutez des photos via l'admin Django ou le formulaire d'inscription")

def verifier_configuration_media():
    """Vérifier la configuration des médias"""
    print("\n" + "=" * 70)
    print("VÉRIFICATION DE LA CONFIGURATION MEDIA")
    print("=" * 70)
    
    print(f"\n📁 MEDIA_URL: {settings.MEDIA_URL}")
    print(f"📁 MEDIA_ROOT: {settings.MEDIA_ROOT}")
    
    if os.path.exists(settings.MEDIA_ROOT):
        print(f"✅ Dossier MEDIA_ROOT existe")
        
        # Lister les sous-dossiers
        subdirs = [d for d in os.listdir(settings.MEDIA_ROOT) 
                  if os.path.isdir(os.path.join(settings.MEDIA_ROOT, d))]
        
        if subdirs:
            print(f"\n📂 Sous-dossiers trouvés:")
            for subdir in subdirs:
                subdir_path = os.path.join(settings.MEDIA_ROOT, subdir)
                file_count = len([f for f in os.listdir(subdir_path) 
                                if os.path.isfile(os.path.join(subdir_path, f))])
                print(f"   - {subdir}: {file_count} fichier(s)")
        else:
            print(f"⚠️  Aucun sous-dossier dans MEDIA_ROOT")
    else:
        print(f"❌ Dossier MEDIA_ROOT n'existe pas: {settings.MEDIA_ROOT}")
        print(f"💡 Créez le dossier avec: mkdir {settings.MEDIA_ROOT}")

def creer_photo_par_defaut():
    """Créer une photo par défaut pour les tests"""
    print("\n" + "=" * 70)
    print("CRÉATION D'UNE PHOTO PAR DÉFAUT")
    print("=" * 70)
    
    try:
        from PIL import Image, ImageDraw, ImageFont
        
        # Créer le dossier si nécessaire
        default_photo_dir = os.path.join(settings.MEDIA_ROOT, 'eleves', 'default')
        os.makedirs(default_photo_dir, exist_ok=True)
        
        # Créer une image par défaut
        img = Image.new('RGB', (400, 400), color='#e0e0e0')
        draw = ImageDraw.Draw(img)
        
        # Dessiner un cercle
        draw.ellipse([100, 100, 300, 300], fill='#9e9e9e', outline='#757575', width=5)
        
        # Ajouter une icône utilisateur simplifiée
        # Tête
        draw.ellipse([170, 140, 230, 200], fill='#757575')
        # Corps
        draw.ellipse([140, 200, 260, 320], fill='#757575')
        
        # Sauvegarder
        default_photo_path = os.path.join(default_photo_dir, 'avatar.jpg')
        img.save(default_photo_path, 'JPEG', quality=85)
        
        print(f"✅ Photo par défaut créée: {default_photo_path}")
        print(f"💡 Utilisez cette photo pour les élèves sans photo")
        
        return default_photo_path
        
    except Exception as e:
        print(f"❌ Erreur lors de la création: {e}")
        return None

def creer_logo_par_defaut():
    """Créer un logo par défaut pour les tests"""
    print("\n" + "=" * 70)
    print("CRÉATION D'UN LOGO PAR DÉFAUT")
    print("=" * 70)
    
    try:
        from PIL import Image, ImageDraw, ImageFont
        
        # Créer le dossier si nécessaire
        default_logo_dir = os.path.join(settings.MEDIA_ROOT, 'ecoles', 'default')
        os.makedirs(default_logo_dir, exist_ok=True)
        
        # Créer une image de logo
        img = Image.new('RGB', (500, 500), color='white')
        draw = ImageDraw.Draw(img)
        
        # Dessiner un cercle bleu
        draw.ellipse([50, 50, 450, 450], fill='#3b82f6', outline='#1e40af', width=10)
        
        # Dessiner un livre simplifié au centre
        draw.rectangle([150, 180, 350, 320], fill='white')
        draw.line([250, 180, 250, 320], fill='#3b82f6', width=5)
        
        # Sauvegarder
        default_logo_path = os.path.join(default_logo_dir, 'logo.png')
        img.save(default_logo_path, 'PNG')
        
        print(f"✅ Logo par défaut créé: {default_logo_path}")
        print(f"💡 Utilisez ce logo pour les écoles sans logo")
        
        return default_logo_path
        
    except Exception as e:
        print(f"❌ Erreur lors de la création: {e}")
        return None

def afficher_recommandations():
    """Afficher les recommandations"""
    print("\n" + "=" * 70)
    print("RECOMMANDATIONS")
    print("=" * 70)
    
    print("\n📸 Pour les Photos d'Élèves:")
    print("   1. Format recommandé: JPG ou PNG")
    print("   2. Taille recommandée: 400x400 pixels minimum")
    print("   3. Poids maximum: 2 Mo")
    print("   4. Fond neutre de préférence")
    
    print("\n🏫 Pour les Logos d'Écoles:")
    print("   1. Format recommandé: PNG (avec transparence)")
    print("   2. Taille recommandée: 500x500 pixels")
    print("   3. Poids maximum: 1 Mo")
    print("   4. Fond transparent de préférence")
    
    print("\n📁 Chemins de Stockage:")
    print(f"   - Photos élèves: {os.path.join(settings.MEDIA_ROOT, 'eleves')}")
    print(f"   - Logos écoles: {os.path.join(settings.MEDIA_ROOT, 'ecoles')}")
    
    print("\n🔧 Comment Ajouter:")
    print("   1. Via l'admin Django: http://127.0.0.1:8000/admin/")
    print("   2. Via le formulaire d'inscription")
    print("   3. Via l'API (si disponible)")

def tester_generation_ticket():
    """Tester la génération d'un ticket"""
    print("\n" + "=" * 70)
    print("TEST DE GÉNÉRATION DE TICKET")
    print("=" * 70)
    
    # Prendre un élève au hasard
    eleve = Eleve.objects.filter(statut='ACTIF').first()
    
    if not eleve:
        print("❌ Aucun élève actif trouvé")
        return
    
    print(f"\n👤 Élève de test: {eleve.nom_complet} ({eleve.matricule})")
    print(f"   Classe: {eleve.classe.nom}")
    print(f"   École: {eleve.classe.ecole.nom}")
    
    # Vérifier la photo
    if eleve.photo:
        try:
            if hasattr(eleve.photo, 'path') and os.path.exists(eleve.photo.path):
                print(f"   ✅ Photo: Disponible")
            else:
                print(f"   ⚠️  Photo: Définie mais fichier manquant")
        except:
            print(f"   ⚠️  Photo: Erreur de vérification")
    else:
        print(f"   ⚠️  Photo: Non définie")
    
    # Vérifier le logo
    if eleve.classe.ecole.logo:
        try:
            if hasattr(eleve.classe.ecole.logo, 'path') and os.path.exists(eleve.classe.ecole.logo.path):
                print(f"   ✅ Logo école: Disponible")
            else:
                print(f"   ⚠️  Logo école: Défini mais fichier manquant")
        except:
            print(f"   ⚠️  Logo école: Erreur de vérification")
    else:
        print(f"   ⚠️  Logo école: Non défini")
    
    print(f"\n💡 Pour tester la génération:")
    print(f"   URL: http://127.0.0.1:8000/eleves/{eleve.id}/ticket-retrait-pdf/")

def main():
    """Fonction principale"""
    print("\n" + "=" * 70)
    print("VÉRIFICATION DES PHOTOS ET LOGOS")
    print("=" * 70)
    
    try:
        # 1. Vérifier la configuration
        verifier_configuration_media()
        
        # 2. Vérifier les logos
        verifier_logos_ecoles()
        
        # 3. Vérifier les photos
        verifier_photos_eleves()
        
        # 4. Créer des fichiers par défaut
        creer_photo_par_defaut()
        creer_logo_par_defaut()
        
        # 5. Afficher les recommandations
        afficher_recommandations()
        
        # 6. Tester la génération
        tester_generation_ticket()
        
        print("\n" + "=" * 70)
        print("✅ VÉRIFICATION TERMINÉE")
        print("=" * 70)
        
    except Exception as e:
        print(f"\n❌ ERREUR: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    main()
