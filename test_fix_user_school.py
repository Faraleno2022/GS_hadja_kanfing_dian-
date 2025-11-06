"""
Script de test pour vérifier que le problème user_school est résolu
"""
import os
import django

# Configuration Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ecole_moderne.settings')
django.setup()

from django.contrib.auth.models import User
from utilisateurs.utils import user_school, user_is_admin

def test_user_school_import():
    """Test que user_school est bien importable"""
    print("✓ user_school est importable depuis utilisateurs.utils")
    return True

def test_user_school_function():
    """Test que user_school fonctionne correctement"""
    try:
        # Créer un utilisateur de test
        test_user = User.objects.first()
        if test_user:
            result = user_school(test_user)
            print(f"✓ user_school({test_user.username}) retourne: {result}")
            return True
        else:
            print("⚠ Aucun utilisateur trouvé pour le test")
            return False
    except Exception as e:
        print(f"✗ Erreur lors du test de user_school: {e}")
        return False

def test_views_import():
    """Test que les vues peuvent être importées sans erreur"""
    try:
        from eleves.views import export_tous_eleves_pdf, export_eleves_classe_pdf
        print("✓ Les vues export_tous_eleves_pdf et export_eleves_classe_pdf sont importables")
        return True
    except Exception as e:
        print(f"✗ Erreur lors de l'import des vues: {e}")
        return False

if __name__ == '__main__':
    print("=" * 60)
    print("TEST DE CORRECTION DU PROBLÈME user_school")
    print("=" * 60)
    print()
    
    tests = [
        test_user_school_import,
        test_user_school_function,
        test_views_import,
    ]
    
    results = []
    for test in tests:
        try:
            results.append(test())
        except Exception as e:
            print(f"✗ Erreur inattendue: {e}")
            results.append(False)
        print()
    
    print("=" * 60)
    print(f"RÉSULTATS: {sum(results)}/{len(results)} tests réussis")
    print("=" * 60)
    
    if all(results):
        print("✓ Tous les tests sont passés avec succès!")
    else:
        print("⚠ Certains tests ont échoué")
