"""Connexion et gestion de comptes dont le telephone est facultatif."""
import time

from django import forms
from django.contrib.auth.models import User
from django.core.cache import cache
from django.test import TestCase, override_settings
from django.urls import reverse

from ecole_moderne.middleware_config import production_middlewares
from paiements.tests.support import MIDDLEWARE_SANS_LICENCE
from paiements.tests import test_school_filtering as fixtures
from eleves.models import Ecole
from utilisateurs.forms import (
    ComptableCreationForm, SousUtilisateurCreationForm,
    SousUtilisateurModificationForm,
)
from utilisateurs.models import Profil


@override_settings(
    MIDDLEWARE=production_middlewares(MIDDLEWARE_SANS_LICENCE),
    DEBUG=False, ALLOWED_HOSTS=['testserver'], SECURE_SSL_REDIRECT=False,
    CACHES={'default': {'BACKEND': 'django.core.cache.backends.locmem.LocMemCache'}},
)
class TelephoneFacultatifTests(TestCase):
    def setUp(self):
        fixtures.SchoolFilteringTests.setUp(self)
        Profil.objects.filter(user=self.user1).update(telephone='')
        cache.clear()
        self.client.force_login(self.user1)
        self.destination = reverse('paiements:detail_paiement', args=[self.paiement1.pk])

    def test_connexion_sans_telephone_ouvre_la_page_demandee(self):
        self.client.logout()
        response = self.client.post(
            reverse('utilisateurs:login') + '?next=' + self.destination,
            {'username': self.user1.username, 'password': 'pass12345'},
            follow=True,
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.redirect_chain, [(self.destination, 302)])
        self.assertEqual(self.client.session['_auth_user_id'], str(self.user1.pk))
        self.assertFalse(self.client.session.get('phone_verified', False))

    def test_page_protegee_sans_telephone_conserve_session_et_activite(self):
        for telephone in ('', '   '):
            with self.subTest(telephone=telephone):
                Profil.objects.filter(user=self.user1).update(telephone=telephone)
                response = self.client.get(self.destination)
                self.assertEqual(response.status_code, 200)
                self.assertIn('_auth_user_id', self.client.session)
                self.assertGreater(self.client.session['last_activity'], time.time() - 10)

    def test_ancienne_page_verification_sans_telephone_conserve_destination(self):
        for method in ('get', 'post'):
            with self.subTest(method=method):
                response = getattr(self.client, method)(
                    reverse('utilisateurs:verify_phone'),
                    {'next': self.destination}, follow=True,
                )
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.redirect_chain, [(self.destination, 302)])
                self.assertIn('_auth_user_id', self.client.session)
                self.assertFalse(self.client.session.get('phone_verified', False))

    def test_sans_telephone_redirection_externe_refusee(self):
        for method in ('get', 'post'):
            with self.subTest(method=method):
                response = getattr(self.client, method)(
                    reverse('utilisateurs:verify_phone'),
                    {'next': '//site-non-autorise.invalid/'},
                )
                self.assertEqual(response.status_code, 302)
                self.assertEqual(response.url, reverse('eleves:liste_eleves'))
                self.assertIn('_auth_user_id', self.client.session)

    def test_sans_telephone_expiration_inactivite_reste_appliquee(self):
        session = self.client.session
        session['last_activity'] = time.time() - 1900
        session.save()
        response = self.client.get(self.destination)
        self.assertRedirects(response, reverse('utilisateurs:login'))
        self.assertNotIn('_auth_user_id', self.client.session)

    def test_sans_telephone_profil_revoque_reste_refuse(self):
        for field in ('actif', 'is_validated'):
            with self.subTest(field=field):
                Profil.objects.filter(user=self.user1).update(actif=True, is_validated=True)
                self.client.force_login(self.user1)
                Profil.objects.filter(user=self.user1).update(**{field: False})
                response = self.client.get(self.destination)
                self.assertRedirects(response, reverse('utilisateurs:login'))
                self.assertNotIn('_auth_user_id', self.client.session)

    def test_sans_telephone_mauvais_mot_de_passe_reste_refuse(self):
        self.client.logout()
        response = self.client.post(reverse('utilisateurs:login'), {
            'username': self.user1.username, 'password': 'MauvaisMotDePasse2026!',
        })
        self.assertEqual(response.status_code, 200)
        self.assertNotIn('_auth_user_id', self.client.session)

    def test_absence_de_profil_ne_donne_pas_acces(self):
        Profil.objects.filter(user=self.user1).delete()
        response = self.client.get(self.destination)
        self.assertRedirects(response, reverse('utilisateurs:login'))
        self.assertNotIn('_auth_user_id', self.client.session)

    def test_ajout_telephone_demande_verification(self):
        self.assertEqual(self.client.get(self.destination).status_code, 200)
        Profil.objects.filter(user=self.user1).update(telephone='+224620000099')
        response = self.client.get(self.destination)
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.url.startswith(reverse('utilisateurs:verify_phone')))

    def test_retrait_telephone_ne_force_pas_reverification(self):
        for age in (0, 9 * 3600):
            with self.subTest(age=age):
                session = self.client.session
                session['phone_verified'] = True
                session['phone_verified_at'] = time.time() - age
                session.save()
                self.assertEqual(self.client.get(self.destination).status_code, 200)
                self.assertIn('_auth_user_id', self.client.session)
                self.assertFalse(self.client.session.get('phone_verified', False))

    def test_superuser_sans_profil_reste_connecte(self):
        admin = User.objects.create_superuser(
            username='admin_sans_tel', password='AdministrationSolide2026!',
        )
        self.client.force_login(admin)
        Profil.objects.filter(user=admin).delete()
        response = self.client.get(
            reverse('utilisateurs:verify_phone'), {'next': self.destination}, follow=True,
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.redirect_chain, [(self.destination, 302)])
        self.assertIn('_auth_user_id', self.client.session)

    def test_creation_compte_principal_sans_telephone(self):
        admin = User.objects.create_superuser(
            username='admin_creation', password='AdministrationSolide2026!',
        )
        self.client.force_login(admin)
        ecole = Ecole.objects.create(
            nom='Ecole sans compte principal', adresse='Conakry',
            telephone='+224620000088', directeur='Direction', etat='VALIDE',
        )
        response = self.client.post(reverse('utilisateurs:creer_compte'), {
            'username': 'principal_sans_tel', 'password': 'PrincipalSolide2026!',
            'password2': 'PrincipalSolide2026!', 'ecole': ecole.pk,
        })
        self.assertEqual(response.status_code, 302)
        profil = Profil.objects.get(user__username='principal_sans_tel')
        self.assertEqual(profil.telephone, '')
        self.assertTrue(profil.est_compte_principal)
        self.assertTrue(profil.is_validated)


class TelephoneFacultatifFormTests(TestCase):
    def setUp(self):
        fixtures.SchoolFilteringTests.setUp(self)
        self.data = {
            'username': 'agent_sans_tel', 'role': 'SECRETAIRE',
            'ecole': self.ecole1.pk, 'password1': 'NouveauCompteSolide2026!',
            'password2': 'NouveauCompteSolide2026!', 'allowed_menus': ['eleves'],
        }

    def test_creation_comptable_sans_telephone(self):
        form = ComptableCreationForm(data=self.data)
        self.assertTrue(form.is_valid(), form.errors)
        user = form.save()
        user.refresh_from_db()
        self.assertEqual(user.profil.telephone, '')

    def test_creation_sous_utilisateur_sans_telephone(self):
        form = SousUtilisateurCreationForm(
            data=self.data, principal_profil=self.user1.profil,
        )
        self.assertTrue(form.is_valid(), form.errors)
        user = form.save()
        user.refresh_from_db()
        self.assertEqual(user.profil.telephone, '')
        self.assertTrue(user.profil.is_validated)

    def test_modification_sous_utilisateur_efface_telephone(self):
        form = SousUtilisateurModificationForm(
            data={**self.data, 'username': self.user1.username, 'actif': True},
            profil=self.user1.profil,
        )
        self.assertTrue(form.is_valid(), form.errors)
        user = form.save()
        user.refresh_from_db()
        self.assertEqual(user.profil.telephone, '')
        self.assertTrue(user.profil.actif)

    def test_formulaire_modele_admin_accepte_telephone_vide(self):
        form_class = forms.modelform_factory(Profil, fields=['telephone'])
        form = form_class(data={'telephone': ''}, instance=self.user1.profil)
        self.assertTrue(form.is_valid(), form.errors)
        form.save()
        self.user1.profil.refresh_from_db()
        self.assertEqual(self.user1.profil.telephone, '')

    def test_numero_renseigne_invalide_reste_refuse(self):
        data = {**self.data, 'telephone': 'numero-invalide'}
        forms_to_test = [
            ComptableCreationForm(data=data),
            SousUtilisateurCreationForm(data=data, principal_profil=self.user1.profil),
            SousUtilisateurModificationForm(data=data, profil=self.user1.profil),
        ]
        for form in forms_to_test:
            with self.subTest(form=type(form).__name__):
                self.assertFalse(form.is_valid())
                self.assertIn('telephone', form.errors)
