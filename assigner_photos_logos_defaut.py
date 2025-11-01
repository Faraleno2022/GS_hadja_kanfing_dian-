"""
Script pour assigner les photos et logos par défaut
Assigne les fichiers créés aux écoles et élèves qui n'en ont pas
"""

import os
import django

# Configuration Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ecole_moderne.settings')
django.setup()

from eleves.models import Eleve, Ecole
from django.core.files import File
from django.conf import settings

def assigner_logos_ecoles():
    """Assigner le logo par défaut aux écoles"""
    print("\n" + "=" * 70)
    print("ASSIGNATION DES LOGOS AUX ÉCOLES")
    print("=" * 70)
    
    logo_path = os.path.join(settings.MEDIA_ROOT, 'ecoles', 'default', 'logo.png')
    
    if not os.path.exists(logo_path):
        print(f"❌ Logo par défaut introuvable: {logo_path}")
        print(f"💡 Exécutez d'abord: python verifier_photos_logos.py")
        return
    
    ecoles = Ecole.objects.filter(logo='') | Ecole.objects.filter(logo__isnull=True)
    count = 0
    
    for ecole in ecoles:
        try:
            with open(logo_path, 'rb') as f:
                ecole.logo.save('logo.png', File(f), save=True)
            print(f"   ✅ Logo assigné à: {ecole.nom}")
            count += 1
        except Exception as e:
            print(f"   ❌ Erreur pour {ecole.nom}: {e}")
    
    print(f"\n✅ {count} logo(s) assigné(s)")
    print(f"✅ Total écoles avec logo: {Ecole.objects.exclude(logo='').exclude(logo__isnull=True).count()}")

def assigner_photos_eleves(limite=None):
    """Assigner la photo par défaut aux élèves"""
    print("\n" + "=" * 70)
    print("ASSIGNATION DES PHOTOS AUX ÉLÈVES")
    print("=" * 70)
    
    photo_path = os.path.join(settings.MEDIA_ROOT, 'eleves', 'default', 'avatar.jpg')
    
    if not os.path.exists(photo_path):
        print(f"❌ Photo par défaut introuvable: {photo_path}")
        print(f"💡 Exécutez d'abord: python verifier_photos_logos.py")
        return
    
    eleves = Eleve.objects.filter(photo='') | Eleve.objects.filter(photo__isnull=True)
    
    if limite:
        eleves = eleves[:limite]
        print(f"ℹ️  Limitation à {limite} élèves")
    
    total = eleves.count()
    count = 0
    
    print(f"\n📊 {total} élève(s) sans photo trouvé(s)")
    
    if total > 100:
        print(f"⚠️  Attention: {total} élèves à traiter")
        print(f"   Cela peut prendre du temps...")
    
    for i, eleve in enumerate(eleves, 1):
        try:
            with open(photo_path, 'rb') as f:
                # Créer un nom de fichier unique
                filename = f"avatar_{eleve.matricule.replace('/', '_')}.jpg"
                eleve.photo.save(filename, File(f), save=True)
            count += 1
            
            if count % 50 == 0:
                print(f"   ✅ {count}/{total} photos assignées...")
                
        except Exception as e:
            print(f"   ❌ Erreur pour {eleve.matricule}: {e}")
    
    print(f"\n✅ {count} photo(s) assignée(s)")
    print(f"✅ Total élèves avec photo: {Eleve.objects.exclude(photo='').exclude(photo__isnull=True).count()}")

def afficher_statistiques():
    """Afficher les statistiques finales"""
    print("\n" + "=" * 70)
    print("STATISTIQUES FINALES")
    print("=" * 70)
    
    # Écoles
    total_ecoles = Ecole.objects.count()
    ecoles_avec_logo = Ecole.objects.exclude(logo='').exclude(logo__isnull=True).count()
    
    print(f"\n🏫 Écoles:")
    print(f"   Total: {total_ecoles}")
    print(f"   Avec logo: {ecoles_avec_logo} ({ecoles_avec_logo/total_ecoles*100:.1f}%)")
    print(f"   Sans logo: {total_ecoles - ecoles_avec_logo}")
    
    # Élèves
    total_eleves = Eleve.objects.count()
    eleves_avec_photo = Eleve.objects.exclude(photo='').exclude(photo__isnull=True).count()
    
    print(f"\n👤 Élèves:")
    print(f"   Total: {total_eleves}")
    print(f"   Avec photo: {eleves_avec_photo} ({eleves_avec_photo/total_eleves*100:.1f}%)")
    print(f"   Sans photo: {total_eleves - eleves_avec_photo}")

def main():
    """Fonction principale"""
    print("\n" + "=" * 70)
    print("ASSIGNATION DES PHOTOS ET LOGOS PAR DÉFAUT")
    print("=" * 70)
    
    try:
        # 1. Assigner les logos
        assigner_logos_ecoles()
        
        # 2. Assigner les photos (limité à 100 pour commencer)
        print("\n⚠️  Assignation des photos limitée à 100 élèves pour le test")
        print("   Pour assigner à tous, modifiez le script")
        assigner_photos_eleves(limite=100)
        
        # 3. Afficher les statistiques
        afficher_statistiques()
        
        print("\n" + "=" * 70)
        print("✅ ASSIGNATION TERMINÉE")
        print("=" * 70)
        
        print("\n📝 PROCHAINES ÉTAPES:")
        print("   1. Tester la génération de tickets")
        print("   2. Vérifier l'affichage des photos")
        print("   3. Remplacer par de vraies photos si nécessaire")
        
        print("\n💡 Pour assigner à TOUS les élèves:")
        print("   Modifiez la ligne: assigner_photos_eleves(limite=None)")
        
    except Exception as e:
        print(f"\n❌ ERREUR: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    main()
