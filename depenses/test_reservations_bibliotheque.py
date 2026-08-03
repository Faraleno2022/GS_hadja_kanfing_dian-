from datetime import date, timedelta

from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from eleves.models import Classe, Ecole, Eleve
from utilisateurs.models import Profil

from .models_bibliotheque import (
    CategorieLivre,
    Emprunt,
    Livre,
    ParametreBibliotheque,
    Reservation,
)


MIDDLEWARE_SANS_LICENCE = [
    middleware
    for middleware in settings.MIDDLEWARE
    if middleware != 'ecole_moderne.licence_middleware.LicenceMiddleware'
]


@override_settings(MIDDLEWARE=MIDDLEWARE_SANS_LICENCE)
class ReservationsBibliothequeTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.ecole = Ecole.objects.create(
            nom='Ecole bibliotheque',
            adresse='Conakry',
            telephone='+224622111111',
            email='bibliotheque@ecole.local',
            directeur='Direction',
            etat='VALIDE',
        )
        self.autre_ecole = Ecole.objects.create(
            nom='Autre bibliotheque',
            adresse='Conakry',
            telephone='+224622222222',
            email='autre-bibliotheque@ecole.local',
            directeur='Direction',
            etat='VALIDE',
        )
        self.classe = Classe.objects.create(
            ecole=self.ecole,
            nom='8e A',
            niveau='COLLEGE_8',
            annee_scolaire='2026-2027',
            capacite_max=40,
        )
        self.autre_classe = Classe.objects.create(
            ecole=self.autre_ecole,
            nom='8e B',
            niveau='COLLEGE_8',
            annee_scolaire='2026-2027',
            capacite_max=40,
        )
        self.user = User.objects.create_user('bibliothecaire', password='secret')
        self.autre_user = User.objects.create_user('autre_bibliothecaire', password='secret')
        Profil.objects.filter(user=self.user).update(
            role='ADMIN',
            telephone='+224622333333',
            ecole=self.ecole,
            actif=True,
            is_validated=True,
        )
        Profil.objects.filter(user=self.autre_user).update(
            role='ADMIN',
            telephone='+224622444444',
            ecole=self.autre_ecole,
            actif=True,
            is_validated=True,
        )
        self.eleve = Eleve.objects.create(
            matricule='BIB-001',
            prenom='Aminata',
            nom='Diallo',
            sexe='F',
            classe=self.classe,
            statut='ACTIF',
            cree_par=self.user,
        )
        self.eleve_attente = Eleve.objects.create(
            matricule='BIB-002',
            prenom='Mamadou',
            nom='Bah',
            sexe='M',
            classe=self.classe,
            statut='ACTIF',
            cree_par=self.user,
        )
        self.autre_eleve = Eleve.objects.create(
            matricule='AUT-BIB-001',
            prenom='Fanta',
            nom='Camara',
            sexe='F',
            classe=self.autre_classe,
            statut='ACTIF',
            cree_par=self.autre_user,
        )
        self.categorie = CategorieLivre.objects.create(
            nom='Romans',
            code='ROM-TEST',
        )
        self.livre = Livre.objects.create(
            code_livre='LIV-TEST-001',
            titre='Le livre disponible',
            auteur='Auteur Test',
            categorie=self.categorie,
            emplacement='Rayon A',
            nombre_exemplaires=1,
            exemplaires_disponibles=1,
            statut='DISPONIBLE',
            cree_par=self.user,
        )
        ParametreBibliotheque.objects.create(
            duree_emprunt_defaut=14,
            duree_reservation_defaut=7,
            nombre_emprunts_max=3,
            nombre_reservations_max=2,
            modifie_par=self.user,
        )
        self.client.force_login(self.user)

    def reserver(self, livre=None, eleve=None):
        return self.client.post(reverse('depenses:creer_reservation'), {
            'livre': (livre or self.livre).pk,
            'eleve': (eleve or self.eleve).pk,
            'observations': '',
        })

    def test_reservation_bloque_un_exemplaire_disponible(self):
        response = self.reserver()

        self.assertRedirects(response, reverse('depenses:liste_reservations'))
        reservation = Reservation.objects.get()
        self.assertEqual(reservation.statut, 'DISPONIBLE')
        self.assertIsNotNone(reservation.date_notification)
        self.livre.refresh_from_db()
        self.assertEqual(self.livre.exemplaires_disponibles, 0)
        self.assertEqual(self.livre.statut, 'RESERVE')

    def test_reservation_en_double_est_refusee(self):
        self.reserver()
        response = self.reserver()

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'déjà une réservation active')
        self.assertEqual(Reservation.objects.count(), 1)

    def test_annulation_libere_exemplaire(self):
        self.reserver()
        reservation = Reservation.objects.get()

        response = self.client.post(
            reverse('depenses:annuler_reservation', args=[reservation.pk])
        )

        self.assertRedirects(response, reverse('depenses:liste_reservations'))
        reservation.refresh_from_db()
        self.livre.refresh_from_db()
        self.assertEqual(reservation.statut, 'ANNULEE')
        self.assertEqual(self.livre.exemplaires_disponibles, 1)
        self.assertEqual(self.livre.statut, 'DISPONIBLE')

    def test_conversion_en_emprunt_ne_retire_pas_deux_fois_le_stock(self):
        self.reserver()
        reservation = Reservation.objects.get()

        response = self.client.post(
            reverse('depenses:emprunter_reservation', args=[reservation.pk])
        )

        self.assertRedirects(response, reverse('depenses:liste_emprunts'))
        reservation.refresh_from_db()
        self.livre.refresh_from_db()
        emprunt = Emprunt.objects.get()
        self.assertEqual(reservation.statut, 'EMPRUNTEE')
        self.assertEqual(emprunt.eleve, self.eleve)
        self.assertEqual(self.livre.exemplaires_disponibles, 0)
        self.assertEqual(self.livre.statut, 'EMPRUNTE')

    def test_retour_attribue_livre_au_premier_eleve_en_attente(self):
        self.livre.exemplaires_disponibles = 0
        self.livre.statut = 'EMPRUNTE'
        self.livre.save(update_fields=['exemplaires_disponibles', 'statut'])
        emprunt = Emprunt.objects.create(
            numero_emprunt='EMP-TEST-001',
            livre=self.livre,
            eleve=self.eleve,
            date_emprunt=date.today() - timedelta(days=2),
            date_retour_prevue=date.today() + timedelta(days=12),
            statut='EN_COURS',
            cree_par=self.user,
        )
        self.reserver(eleve=self.eleve_attente)
        reservation = Reservation.objects.get()
        self.assertEqual(reservation.statut, 'EN_ATTENTE')

        response = self.client.post(
            reverse('depenses:retourner_livre', args=[emprunt.pk]),
            {'etat_retour': 'BON', 'observations': ''},
        )

        self.assertRedirects(response, reverse('depenses:liste_emprunts'))
        reservation.refresh_from_db()
        self.livre.refresh_from_db()
        self.assertEqual(reservation.statut, 'DISPONIBLE')
        self.assertIsNotNone(reservation.date_notification)
        self.assertEqual(self.livre.exemplaires_disponibles, 0)
        self.assertEqual(self.livre.statut, 'RESERVE')

    def test_expiration_libere_automatiquement_exemplaire(self):
        self.reserver()
        reservation = Reservation.objects.get()
        Reservation.objects.filter(pk=reservation.pk).update(
            date_expiration=timezone.now() - timedelta(minutes=1)
        )

        response = self.client.get(reverse('depenses:liste_reservations'))

        self.assertEqual(response.status_code, 200)
        reservation.refresh_from_db()
        self.livre.refresh_from_db()
        self.assertEqual(reservation.statut, 'EXPIREE')
        self.assertEqual(self.livre.exemplaires_disponibles, 1)

    def test_reservations_autre_ecole_sont_masquees(self):
        autre_livre = Livre.objects.create(
            code_livre='LIV-AUTRE-001',
            titre='Livre autre école',
            auteur='Auteur',
            categorie=self.categorie,
            emplacement='Rayon B',
            nombre_exemplaires=1,
            exemplaires_disponibles=0,
            statut='EMPRUNTE',
            cree_par=self.autre_user,
        )
        Reservation.objects.create(
            numero_reservation='RES-AUTRE-001',
            livre=autre_livre,
            eleve=self.autre_eleve,
            date_expiration=timezone.now() + timedelta(days=7),
            cree_par=self.autre_user,
        )

        response = self.client.get(reverse('depenses:liste_reservations'))

        self.assertNotContains(response, 'Livre autre école')
        self.assertNotContains(response, 'AUT-BIB-001')
