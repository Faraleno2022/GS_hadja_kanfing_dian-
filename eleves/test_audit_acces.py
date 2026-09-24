from django.contrib.auth.models import User
from django.test import TestCase, override_settings
from django.urls import reverse
from django.core.cache import cache

from paiements.tests.support import MIDDLEWARE_SANS_LICENCE
from .models import Classe, Ecole, Eleve


@override_settings(MIDDLEWARE=MIDDLEWARE_SANS_LICENCE)
class IsolationEcoleAuditTests(TestCase):
    def setUp(self):
        cache.clear()
        self.user = User.objects.create_user('admin-ecole-audit')
        self.ecole = Ecole.objects.create(nom='École A', etat='VALIDE')
        self.autre = Ecole.objects.create(nom='École B', etat='VALIDE')
        profil = self.user.profil
        profil.role = 'ADMIN'
        profil.ecole = self.ecole
        profil.actif = profil.is_validated = True
        profil.save()
        self.client.force_login(self.user)
        self.classes = []
        self.eleves = []
        for ecole in (self.ecole, self.autre):
            classe = Classe.objects.create(ecole=ecole, nom='1ère année', niveau='PRIMAIRE_1', annee_scolaire='2026-2027')
            self.classes.append(classe)
            self.eleves.append(Eleve.objects.create(classe=classe, matricule=f'ACC-{ecole.pk}', prenom='Élève', nom='Audit', sexe='F'))

    def test_liste_eleves_limitee_a_lecole_de_ladmin(self):
        response = self.client.get(reverse('eleves:liste_eleves'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.eleves[0].matricule)
        self.assertNotContains(response, self.eleves[1].matricule)

    def test_fiche_autre_ecole_refusee_a_ladmin(self):
        self.assertEqual(self.client.get(reverse('eleves:detail_eleve', args=[self.eleves[1].pk])).status_code, 404)

    def test_classes_limitees_a_lecole_de_ladmin(self):
        response = self.client.get(reverse('eleves:gestion_classes'))
        self.assertEqual(list(response.context['classes'].values_list('pk', flat=True)), [self.classes[0].pk])

    def test_configuration_autre_ecole_refusee(self):
        response = self.client.get(reverse('eleves:configurer_ecole', args=[self.autre.pk]))
        self.assertEqual(response.status_code, 403)

    def test_compte_sans_ecole_ne_lit_pas_les_eleves(self):
        self.user.profil.ecole = None
        self.user.profil.save()
        response = self.client.get(reverse('eleves:liste_eleves'))
        for eleve in self.eleves:
            self.assertNotContains(response, eleve.matricule)
