import os
import sys
import json

# Initialiser Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ecole_moderne.settings')
import django
from django.conf import settings

django.setup()

from django.contrib.auth import get_user_model
from django.test import Client
from django.urls import reverse
from administration.models import CorbeilleItem
from django.utils import timezone


def main():
    print("\n🚀 Test AJAX suppression corbeille")
    User = get_user_model()

    # Créer/obtenir un superuser de test
    username = 'admin_cascade_test'
    password = 'Passw0rd!123'
    user, created = User.objects.get_or_create(username=username, defaults={
        'is_superuser': True,
        'is_staff': True,
        'email': 'admin_cascade_test@example.com'
    })
    if created:
        user.set_password(password)
        user.save()
        print("✅ Superuser créé")
    else:
        # S'assurer des droits
        if not user.is_superuser or not user.is_staff:
            user.is_superuser = True
            user.is_staff = True
            user.set_password(password)
            user.save()
        print("ℹ️ Superuser existant utilisé")

    # Créer un item de corbeille factice
    item = CorbeilleItem.objects.create(
        app_label='eleves',
        model_name='eleve',
        object_id='999999',
        data={'nom': 'Test', 'details': 'Item factice pour test suppression'},
        ecole_id=None,
        description='Item test suppression AJAX',
        deleted_by=user,
        deleted_at=timezone.now()
    )
    print(f"✅ Item corbeille créé: ID={item.id}")

    # Autoriser l'hôte testserver pour éviter DisallowedHost
    try:
        if 'testserver' not in settings.ALLOWED_HOSTS:
            settings.ALLOWED_HOSTS.append('testserver')
    except Exception:
        pass

    # Désactiver les vérifications CSRF pour ce test ciblé
    client = Client(enforce_csrf_checks=False)

    # Login
    assert client.login(username=username, password=password), "Échec login superuser"
    print("✅ Login réussi")

    # Appel AJAX delete
    delete_url = reverse('administration:corbeille_delete', args=[item.id])
    resp = client.post(delete_url, HTTP_X_REQUESTED_WITH='XMLHttpRequest')

    print(f"HTTP {resp.status_code}")
    try:
        data = json.loads(resp.content.decode('utf-8'))
    except Exception:
        print("Réponse:", resp.content[:200])
        raise

    print("Réponse JSON:", data)
    assert data.get('success') is True, f"Suppression AJAX échouée: {data}"
    print("🎉 Succès: suppression AJAX confirmée")


if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        print("\n💥 ERREUR:", e)
        sys.exit(1)
