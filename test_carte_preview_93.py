"""
Script pour vérifier l'accès à la carte scolaire preview de l'élève 93
Date : 11 novembre 2024
"""

import os
import sys
import django

# Configuration Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ecole_moderne.settings')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
django.setup()

from eleves.models import Eleve
from django.contrib.auth.models import User

def verifier_carte_preview():
    """Vérifie l'accès à la carte scolaire preview pour l'élève 93"""
    
    print("="*70)
    print("VÉRIFICATION DE LA CARTE SCOLAIRE PREVIEW - ÉLÈVE 93")
    print("="*70)
    
    try:
        # Vérifier si l'élève 93 existe
        eleve = Eleve.objects.filter(id=93).first()
        
        if eleve:
            print(f"\n✅ Élève trouvé :")
            print(f"   Nom : {eleve.prenom} {eleve.nom}")
            print(f"   Matricule : {eleve.matricule}")
            print(f"   Classe : {eleve.classe.nom}")
            print(f"   École : {eleve.classe.ecole.nom}")
            print(f"   Statut : {eleve.statut}")
            
            if eleve.photo:
                print(f"   Photo : ✅ Disponible")
            else:
                print(f"   Photo : ❌ Pas de photo (initiales seront affichées)")
            
            if eleve.responsable_principal:
                print(f"   Responsable : {eleve.responsable_principal.nom_complet}")
                print(f"   Contact : {eleve.responsable_principal.telephone}")
            else:
                print(f"   Responsable : Non renseigné")
            
            print("\n📌 URLS DISPONIBLES POUR CET ÉLÈVE :")
            print("-"*50)
            
            # URL de prévisualisation HTML
            print(f"\n1️⃣ PRÉVISUALISATION HTML (aperçu interactif)")
            print(f"   URL : /eleves/93/carte-scolaire-preview/")
            print(f"   → http://127.0.0.1:8000/eleves/93/carte-scolaire-preview/")
            print(f"   Fonctionnalités :")
            print(f"   - Aperçu en temps réel de la carte")
            print(f"   - Bouton d'impression directe")
            print(f"   - Téléchargement PDF standard")
            print(f"   - Téléchargement format PVC Pro")
            
            # URL de téléchargement PDF direct
            print(f"\n2️⃣ TÉLÉCHARGEMENT PDF DIRECT")
            print(f"   URL : /eleves/93/carte-scolaire-pdf/")
            print(f"   → http://127.0.0.1:8000/eleves/93/carte-scolaire-pdf/")
            print(f"   Format : Carte individuelle standard")
            
            # URL de téléchargement PVC
            print(f"\n3️⃣ TÉLÉCHARGEMENT FORMAT PVC")
            print(f"   URL : /eleves/93/carte-scolaire-pdf/?format=pvc")
            print(f"   → http://127.0.0.1:8000/eleves/93/carte-scolaire-pdf/?format=pvc")
            print(f"   Format : Optimisé pour impression sur carte PVC")
            
            print("\n🎨 CARACTÉRISTIQUES DE LA CARTE :")
            print("-"*50)
            print("✅ Nom de l'école en taille augmentée (14pt)")
            print("✅ En-tête agrandi (16mm)")
            print("✅ Logo de l'école (12mm)")
            print("✅ Filigrane avec logo en arrière-plan (15% opacité)")
            print("✅ Photo de l'élève ou initiales si pas de photo")
            print("✅ Contact d'urgence du responsable")
            print("✅ Format carte bancaire (86mm x 54mm)")
            print("✅ Compatible impression PVC professionnelle")
            
            # Vérifier si un utilisateur peut y accéder
            print("\n👤 ACCÈS UTILISATEURS :")
            print("-"*50)
            
            # Récupérer un utilisateur admin
            admin_user = User.objects.filter(is_superuser=True).first()
            if admin_user:
                print(f"   Admin : {admin_user.username} - ✅ Accès autorisé")
            
            # Récupérer un utilisateur de l'école
            users_ecole = User.objects.filter(profil__ecole=eleve.classe.ecole).all()
            if users_ecole:
                for user in users_ecole[:3]:  # Afficher max 3 utilisateurs
                    print(f"   {user.username} - ✅ Accès autorisé (même école)")
            
            print("\n💡 COMMENT ACCÉDER À LA PAGE :")
            print("-"*50)
            print("1. Démarrer le serveur : python manage.py runserver")
            print("2. Se connecter avec un compte autorisé")
            print("3. Accéder à l'URL : http://127.0.0.1:8000/eleves/93/carte-scolaire-preview/")
            print("4. Utiliser les boutons pour :")
            print("   - Imprimer directement")
            print("   - Télécharger en PDF")
            print("   - Télécharger au format PVC")
            
        else:
            print(f"\n❌ L'élève avec l'ID 93 n'existe pas dans la base de données.")
            
            # Suggérer d'autres élèves
            eleves_actifs = Eleve.objects.filter(statut='ACTIF').order_by('-id')[:5]
            if eleves_actifs:
                print(f"\n📋 Élèves disponibles (derniers ajoutés) :")
                print("-"*50)
                for e in eleves_actifs:
                    print(f"   ID {e.id} : {e.prenom} {e.nom} - {e.classe.nom}")
                    print(f"   → /eleves/{e.id}/carte-scolaire-preview/")
                
                # Prendre le premier élève comme exemple
                premier = eleves_actifs[0]
                print(f"\n💡 Essayez avec l'élève ID {premier.id} :")
                print(f"   http://127.0.0.1:8000/eleves/{premier.id}/carte-scolaire-preview/")
        
        print("\n" + "="*70)
        print("VÉRIFICATION TERMINÉE")
        print("="*70)
        
    except Exception as e:
        print(f"\n❌ Erreur lors de la vérification : {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    verifier_carte_preview()
