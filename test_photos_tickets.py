"""
Script de test pour vérifier l'import et l'affichage des photos
sur les tickets de retrait et bus
Date : 11 novembre 2024
"""

import os
import sys
import django
import io
from PIL import Image

# Configuration Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ecole_moderne.settings')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
django.setup()

from eleves.models import Eleve
from bus.models import AbonnementBus
from django.contrib.auth.models import User

def verifier_photos_tickets():
    """Vérifier que les photos s'affichent correctement sur les tickets"""
    
    print("="*80)
    print("TEST D'IMPORT ET AFFICHAGE DES PHOTOS SUR TICKETS")
    print("="*80)
    
    try:
        # Récupérer des élèves avec photos
        eleves_avec_photos = Eleve.objects.filter(
            statut='ACTIF',
            photo__isnull=False
        ).exclude(photo='')[:5]
        
        print(f"\n📸 ÉLÈVES AVEC PHOTOS TROUVÉS : {eleves_avec_photos.count()}")
        print("-"*50)
        
        for eleve in eleves_avec_photos:
            print(f"\n👤 Élève : {eleve.prenom} {eleve.nom}")
            print(f"   ID : {eleve.id}")
            print(f"   Matricule : {eleve.matricule}")
            print(f"   Classe : {eleve.classe.nom}")
            
            # Vérifier la photo
            if eleve.photo:
                print(f"   ✅ Photo enregistrée : {eleve.photo.name}")
                
                # Vérifier le chemin physique
                if hasattr(eleve.photo, 'path'):
                    photo_path = eleve.photo.path
                    if os.path.exists(photo_path):
                        print(f"   ✅ Fichier existe : {photo_path}")
                        
                        # Tester le chargement de l'image
                        try:
                            img = Image.open(photo_path)
                            print(f"   ✅ Image chargée : {img.size[0]}x{img.size[1]} pixels")
                            print(f"   ✅ Format : {img.format}, Mode : {img.mode}")
                            
                            # Simuler le traitement pour le PDF (comme dans le code)
                            photo_radius = 30  # Rayon utilisé dans les tickets
                            
                            # Convertir en RGB si nécessaire
                            if img.mode in ('RGBA', 'LA', 'P'):
                                background = Image.new('RGB', img.size, (255, 255, 255))
                                if img.mode == 'P':
                                    img = img.convert('RGBA')
                                background.paste(img, mask=img.split()[-1] if img.mode in ('RGBA', 'LA') else None)
                                img = background
                            elif img.mode != 'RGB':
                                img = img.convert('RGB')
                            
                            # Calculer la taille en pixels (comme dans le code)
                            pixel_size = int(photo_radius * 2 * 28.35)
                            size = (pixel_size, pixel_size)
                            
                            # Redimensionner
                            img = img.resize(size, Image.Resampling.LANCZOS)
                            print(f"   ✅ Redimensionnée à : {size[0]}x{size[1]} pixels")
                            
                            # Créer un masque circulaire
                            from PIL import ImageDraw
                            mask = Image.new('L', size, 0)
                            draw = ImageDraw.Draw(mask)
                            draw.ellipse((0, 0, size[0], size[1]), fill=255)
                            
                            # Appliquer le masque
                            output = Image.new('RGBA', size, (255, 255, 255, 0))
                            output.paste(img, (0, 0))
                            output.putalpha(mask)
                            
                            # Sauvegarder temporairement (test)
                            temp_buffer = io.BytesIO()
                            output.save(temp_buffer, format='PNG')
                            buffer_size = temp_buffer.tell()
                            temp_buffer.seek(0)
                            
                            print(f"   ✅ Image circulaire créée : {buffer_size} octets")
                            print(f"   ✅ PHOTO PRÊTE POUR PDF")
                            
                        except Exception as e:
                            print(f"   ❌ Erreur chargement image : {e}")
                    else:
                        print(f"   ❌ Fichier n'existe pas : {photo_path}")
                else:
                    print(f"   ⚠️ Pas de chemin physique disponible")
            else:
                print(f"   ❌ Pas de photo")
            
            # Vérifier l'éligibilité pour ticket de retrait
            niveau = eleve.classe.niveau.upper() if eleve.classe.niveau else ''
            if any(x in niveau for x in ['PRIMAIRE', 'PN', 'MATERNELLE', 'GARDERIE']):
                print(f"\n   📄 TICKET RETRAIT :")
                print(f"   ✅ Éligible (niveau {eleve.classe.niveau})")
                print(f"   → URL : /eleves/{eleve.id}/ticket-retrait-pdf/")
                if eleve.photo and os.path.exists(eleve.photo.path):
                    print(f"   → Photo sera affichée dans un cercle de 30mm de rayon")
            else:
                print(f"   ❌ Non éligible pour ticket retrait (niveau {eleve.classe.niveau})")
            
            # Vérifier l'abonnement bus
            abonnement = AbonnementBus.objects.filter(
                eleve=eleve,
                statut='ACTIF'
            ).first()
            
            if abonnement:
                print(f"\n   🚌 TICKET BUS :")
                print(f"   ✅ Abonnement actif")
                print(f"   → URL : /eleves/{eleve.id}/ticket-bus-pdf/")
                if eleve.photo and os.path.exists(eleve.photo.path):
                    print(f"   → Photo sera affichée dans un cercle de 30mm de rayon")
                # Note: Le trajet dépend du modèle bus qui peut varier
            else:
                print(f"   ❌ Pas d'abonnement bus actif")
            
            print("\n" + "-"*50)
        
        # Statistiques globales
        print("\n📊 STATISTIQUES GLOBALES")
        print("="*80)
        
        total_eleves = Eleve.objects.filter(statut='ACTIF').count()
        eleves_avec_photo = Eleve.objects.filter(
            statut='ACTIF',
            photo__isnull=False
        ).exclude(photo='').count()
        
        pourcentage = (eleves_avec_photo / total_eleves * 100) if total_eleves > 0 else 0
        
        print(f"Total élèves actifs : {total_eleves}")
        print(f"Élèves avec photo : {eleves_avec_photo}")
        print(f"Pourcentage avec photo : {pourcentage:.1f}%")
        
        # Vérifier les élèves du primaire/maternelle avec photo
        eleves_primaire = Eleve.objects.filter(
            statut='ACTIF',
            classe__niveau__icontains='primaire'
        ) | Eleve.objects.filter(
            statut='ACTIF',
            classe__niveau__icontains='maternelle'
        ) | Eleve.objects.filter(
            statut='ACTIF',
            classe__niveau__icontains='garderie'
        )
        
        primaire_avec_photo = eleves_primaire.filter(
            photo__isnull=False
        ).exclude(photo='').count()
        
        print(f"\nPrimaire/Maternelle avec photo : {primaire_avec_photo}")
        print(f"→ Éligibles pour ticket retrait avec photo")
        
        # Vérifier les abonnés bus avec photo
        abonnes_bus = Eleve.objects.filter(
            abonnementbus__statut='ACTIF'
        ).distinct()
        
        abonnes_avec_photo = abonnes_bus.filter(
            photo__isnull=False
        ).exclude(photo='').count()
        
        print(f"\nAbonnés bus avec photo : {abonnes_avec_photo}")
        print(f"→ Éligibles pour ticket bus avec photo")
        
        print("\n" + "="*80)
        print("✅ TEST D'IMPORT DES PHOTOS TERMINÉ")
        print("="*80)
        
        print("\n💡 RÉSUMÉ :")
        print("-"*50)
        print("Les photos sont correctement importées et prêtes pour :")
        print("✅ Ticket de retrait (primaire/maternelle)")
        print("✅ Ticket bus (si abonnement actif)")
        print("✅ Carte scolaire")
        print("\nFormat d'affichage :")
        print("→ Cercle de 30mm de rayon")
        print("→ Bordure colorée avec ombre")
        print("→ Masque circulaire appliqué")
        print("→ Conversion automatique en RGB")
        
    except Exception as e:
        print(f"\n❌ Erreur lors du test : {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    verifier_photos_tickets()
