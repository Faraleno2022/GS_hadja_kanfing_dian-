from django.contrib.auth.models import AnonymousUser, User
from django.test import TestCase

from .permissions import has_any_permission, has_permission


class PermissionsAuditTests(TestCase):
    def test_permissions_simples_et_groupees_sont_coherentes(self):
        user = User.objects.create_user('audit-permissions')
        for role in ('COMPTABLE', 'ENSEIGNANT', 'ADMIN'):
            user.profil.role = role
            user.profil.est_compte_principal = False
            user.profil.peut_valider_paiements = False
            user.profil.peut_supprimer_paiements = False
            user.profil.save()
            for permission in ('peut_valider_paiements', 'peut_gerer_notes', 'peut_supprimer_paiements'):
                with self.subTest(role=role, permission=permission):
                    self.assertEqual(has_any_permission(user, [permission]), has_permission(user, permission))
        self.assertFalse(has_any_permission(AnonymousUser(), ['peut_valider_paiements']))

    def test_comptable_ne_recoit_pas_de_droit_de_suppression_implicite(self):
        user = User.objects.create_user('audit-comptable-suppression')
        user.profil.role = 'COMPTABLE'
        user.profil.est_compte_principal = False
        user.profil.peut_supprimer_paiements = False
        user.profil.save()
        self.assertTrue(has_any_permission(user, ['peut_valider_paiements']))
        self.assertFalse(has_any_permission(user, ['peut_supprimer_paiements']))
