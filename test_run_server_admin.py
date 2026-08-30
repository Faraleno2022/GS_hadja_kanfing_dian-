from django.contrib.auth import get_user_model
from django.test import TestCase

from run_server import _ensure_default_admin


class DefaultAdminDesktopTests(TestCase):
    def test_cree_un_admin_authentifiable_sur_une_installation_vide(self):
        self.assertTrue(_ensure_default_admin())

        admin = get_user_model().objects.get(username='admin')
        self.assertTrue(admin.is_active)
        self.assertTrue(admin.is_staff)
        self.assertTrue(admin.is_superuser)
        self.assertTrue(admin.check_password('admin1234'))

    def test_repare_un_compte_admin_ordinaire(self):
        get_user_model().objects.create_user(
            username='admin',
            password='ancien-mot-de-passe',
            is_active=False,
        )

        self.assertTrue(_ensure_default_admin())
        admin = get_user_model().objects.get(username='admin')
        self.assertTrue(admin.is_active)
        self.assertTrue(admin.is_superuser)
        self.assertTrue(admin.check_password('admin1234'))

    def test_repare_un_superadmin_sans_mot_de_passe_utilisable(self):
        admin = get_user_model().objects.create_superuser(
            username='admin',
            email='admin@myschool.local',
            password=None,
        )
        self.assertFalse(admin.has_usable_password())

        self.assertTrue(_ensure_default_admin())
        admin.refresh_from_db()
        self.assertTrue(admin.check_password('admin1234'))

    def test_preserve_le_mot_de_passe_personnalise_existant(self):
        admin = get_user_model().objects.create_superuser(
            username='admin',
            email='admin@myschool.local',
            password='mot-de-passe-personnalise',
        )

        self.assertFalse(_ensure_default_admin())
        admin.refresh_from_db()
        self.assertTrue(admin.check_password('mot-de-passe-personnalise'))
        self.assertFalse(admin.check_password('admin1234'))
