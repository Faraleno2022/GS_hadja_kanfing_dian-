#!/usr/bin/env python
"""
Script pour activer la permission d'importation d'élèves pour les comptables
"""
import os
import sys
import django

# Configuration Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ecole_moderne.settings')
django.setup()

from utilisateurs.models import Profil
from django.contrib.auth.models import User

def activer_import_eleves_comptables():
    """
    Active la permission d'importation d'élèves pour tous les comptables
    """
    # Récupérer tous les profils de comptables
    comptables = Profil.objects.filter(role='COMPTABLE')
    
    if not comptables.exists():
        print("❌ Aucun comptable trouvé dans le système.")
        return
    
    print(f"📊 Traitement de {comptables.count()} comptable(s)...\n")
    
    comptables_updated = 0
    for profil in comptables:
        if not profil.peut_importer_eleves:
            profil.peut_importer_eleves = True
            profil.save(update_fields=['peut_importer_eleves'])
            comptables_updated += 1
            print(f"✅ {profil.user.get_full_name()} ({profil.user.username}) - Permission accordée")
        else:
            print(f"⚠️  {profil.user.get_full_name()} ({profil.user.username}) - Permission déjà active")
    
    print(f"\n{'='*70}")
    print(f"✅ Opération terminée !")
    print(f"   • Comptables traités : {comptables.count()}")
    print(f"   • Permissions accordées : {comptables_updated}")
    print(f"   • Permissions déjà actives : {comptables.count() - comptables_updated}")

def accorder_permission_comptable_specifique(username):
    """
    Accorde la permission à un comptable spécifique
    """
    try:
        user = User.objects.get(username=username)
        if not hasattr(user, 'profil'):
            print(f"❌ L'utilisateur {username} n'a pas de profil.")
            return
        
        profil = user.profil
        if profil.role != 'COMPTABLE':
            print(f"❌ L'utilisateur {username} n'est pas un comptable (Rôle: {profil.get_role_display()})")
            return
        
        profil.peut_importer_eleves = True
        profil.save(update_fields=['peut_importer_eleves'])
        print(f"✅ Permission accordée à {user.get_full_name()} ({username})")
    except User.DoesNotExist:
        print(f"❌ Utilisateur {username} non trouvé.")

if __name__ == '__main__':
    if len(sys.argv) > 1:
        username = sys.argv[1]
        print(f"Activation de la permission pour le comptable: {username}\n")
        accorder_permission_comptable_specifique(username)
    else:
        print("Activation de la permission d'importation d'élèves pour TOUS les comptables\n")
        activer_import_eleves_comptables()
