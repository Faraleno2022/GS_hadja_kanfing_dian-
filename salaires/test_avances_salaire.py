from datetime import date
from decimal import Decimal

from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse

from eleves.models import Ecole

from .models import (
    AvanceSalaire,
    Enseignant,
    EtatSalaire,
    PeriodeSalaire,
    RemboursementAvance,
    TypeEnseignant,
)
from .services import calculer_etat_salaire


TEST_MIDDLEWARE = tuple(
    middleware for middleware in settings.MIDDLEWARE
    if middleware != 'ecole_moderne.licence_middleware.LicenceMiddleware'
)


@override_settings(MIDDLEWARE=TEST_MIDDLEWARE)
class AvancesSalaireTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_superuser(
            username='avances-admin',
            email='avances@example.com',
            password='mot-de-passe-test',
        )
        self.ecole = Ecole.objects.create(
            nom='École avances',
            adresse='Conakry',
            telephone='+224611000000',
            directeur='Direction',
        )
        self.enseignant = Enseignant.objects.create(
            nom='CAMARA',
            prenoms='Aminata',
            ecole=self.ecole,
            type_enseignant=TypeEnseignant.PRIMAIRE,
            statut='ACTIF',
            salaire_fixe=Decimal('100000'),
            date_embauche=date(2025, 1, 1),
            cree_par=self.user,
        )
        self.periode_juillet = PeriodeSalaire.objects.create(
            mois=7,
            annee=2026,
            ecole=self.ecole,
            cree_par=self.user,
        )
        self.client.force_login(self.user)

    def calculer(self, periode):
        return calculer_etat_salaire(self.enseignant, periode, self.user)[0]

    def ajouter(self, montant='25000', periode=None, **extra):
        periode = periode or self.periode_juillet
        donnees = {
            'enseignant': self.enseignant.pk,
            'periode_prevue': periode.pk,
            'date_avance': '2026-07-15',
            'montant': montant,
            'reference_externe': 'REC-AV-001',
            'motif': 'Besoin familial urgent',
        }
        donnees.update(extra)
        return self.client.post(reverse('salaires:ajouter_avance'), donnees)

    def test_ajout_avance_recalcule_immediatement_le_salaire(self):
        self.calculer(self.periode_juillet)

        response = self.ajouter('25 000 GNF')

        self.assertRedirects(response, reverse('salaires:liste_avances'))
        avance = AvanceSalaire.objects.get()
        etat = EtatSalaire.objects.get(
            enseignant=self.enseignant, periode=self.periode_juillet
        )
        self.assertEqual(avance.montant, Decimal('25000'))
        self.assertEqual(etat.avances_deduites, Decimal('25000.00'))
        self.assertEqual(etat.salaire_net, Decimal('75000.00'))
        self.assertEqual(
            RemboursementAvance.objects.get().montant, Decimal('25000.00')
        )

    def test_reliquat_est_reporte_sur_la_periode_suivante(self):
        etat_juillet = self.calculer(self.periode_juillet)
        self.ajouter('150000')
        etat_juillet.refresh_from_db()
        self.assertEqual(etat_juillet.avances_deduites, Decimal('100000.00'))
        self.assertEqual(etat_juillet.salaire_net, Decimal('0.00'))

        response = self.client.post(
            reverse('salaires:valider_etat_salaire', args=[etat_juillet.pk])
        )
        self.assertEqual(response.status_code, 302)

        periode_aout = PeriodeSalaire.objects.create(
            mois=8, annee=2026, ecole=self.ecole, cree_par=self.user
        )
        etat_aout = self.calculer(periode_aout)

        self.assertEqual(etat_aout.avances_deduites, Decimal('50000.00'))
        self.assertEqual(etat_aout.salaire_net, Decimal('50000.00'))
        avance = AvanceSalaire.objects.get()
        self.assertEqual(avance.solde_restant, Decimal('0.00'))

    def test_modification_et_suppression_recalculent_les_brouillons(self):
        etat = self.calculer(self.periode_juillet)
        self.ajouter('20000')
        avance = AvanceSalaire.objects.get()

        response = self.client.post(
            reverse('salaires:modifier_avance', args=[avance.pk]),
            {
                'enseignant': self.enseignant.pk,
                'periode_prevue': self.periode_juillet.pk,
                'date_avance': '2026-07-15',
                'montant': '40 000',
                'reference_externe': 'REC-AV-002',
                'motif': 'Motif corrigé',
                'enseignant_cible': self.enseignant.pk,
            },
        )
        self.assertRedirects(response, reverse('salaires:liste_avances'))
        etat.refresh_from_db()
        self.assertEqual(etat.avances_deduites, Decimal('40000.00'))
        self.assertEqual(etat.salaire_net, Decimal('60000.00'))

        response = self.client.post(
            reverse('salaires:supprimer_avance', args=[avance.pk])
        )
        self.assertRedirects(response, reverse('salaires:liste_avances'))
        etat.refresh_from_db()
        self.assertEqual(etat.avances_deduites, Decimal('0.00'))
        self.assertEqual(etat.salaire_net, Decimal('100000.00'))
        self.assertFalse(AvanceSalaire.objects.exists())

    def test_baisse_du_salaire_rejoue_la_retenue_d_avance(self):
        etat = self.calculer(self.periode_juillet)
        self.ajouter('90000')
        etat.refresh_from_db()
        self.assertEqual(etat.avances_deduites, Decimal('90000.00'))

        response = self.client.post(
            reverse('salaires:ajuster_etat_salaire', args=[etat.pk]),
            {
                'salaire_base': '50000',
                'prime_exceptionnelle': '0',
                'deductions': '0',
                'observations': 'Salaire corrigé avant validation',
            },
        )

        self.assertEqual(response.status_code, 302)
        etat.refresh_from_db()
        self.assertEqual(etat.salaire_base, Decimal('50000.00'))
        self.assertEqual(etat.avances_deduites, Decimal('50000.00'))
        self.assertEqual(etat.salaire_net, Decimal('0.00'))
        self.assertEqual(AvanceSalaire.objects.get().solde_restant, Decimal('40000.00'))

    def test_avance_figee_apres_validation(self):
        etat = self.calculer(self.periode_juillet)
        self.ajouter('25000')
        avance = AvanceSalaire.objects.get()
        self.client.post(
            reverse('salaires:valider_etat_salaire', args=[etat.pk])
        )

        response = self.client.post(
            reverse('salaires:supprimer_avance', args=[avance.pk]),
            follow=True,
        )

        self.assertTrue(AvanceSalaire.objects.filter(pk=avance.pk).exists())
        self.assertContains(response, 'Suppression impossible')

    def test_liste_et_tableau_de_bord_affichent_les_soldes(self):
        self.calculer(self.periode_juillet)
        self.ajouter('25000')

        liste = self.client.get(reverse('salaires:liste_avances'))
        dashboard = self.client.get(reverse('salaires:tableau_bord'))

        self.assertEqual(liste.status_code, 200)
        self.assertContains(liste, 'REC-AV-001')
        self.assertContains(liste, 'Total avancé')
        self.assertEqual(dashboard.status_code, 200)
        self.assertContains(dashboard, 'Solde des avances à récupérer')

    def test_cartes_avances_comptent_uniquement_les_retenues_validees(self):
        etat = self.calculer(self.periode_juillet)
        self.ajouter('150000')

        # La retenue calculée sur un brouillon reste prévisionnelle : l'avance
        # entière doit encore apparaître comme étant à récupérer.
        dashboard = self.client.get(reverse('salaires:tableau_bord'))
        liste = self.client.get(reverse('salaires:liste_avances'))
        self.assertEqual(dashboard.context['stats']['avances_en_cours'], 1)
        self.assertEqual(
            dashboard.context['stats']['solde_avances'], Decimal('150000')
        )
        self.assertEqual(liste.context['synthese']['rembourse'], Decimal('0'))
        self.assertEqual(liste.context['synthese']['reste'], Decimal('150000'))

        # Après validation, les 100 000 GNF retenus deviennent récupérés et le
        # reliquat de 50 000 GNF reste en cours pour une période suivante.
        self.client.post(
            reverse('salaires:valider_etat_salaire', args=[etat.pk])
        )
        dashboard = self.client.get(reverse('salaires:tableau_bord'))
        liste = self.client.get(reverse('salaires:liste_avances'))
        self.assertEqual(dashboard.context['stats']['avances_en_cours'], 1)
        self.assertEqual(
            dashboard.context['stats']['solde_avances'], Decimal('50000.00')
        )
        self.assertEqual(
            liste.context['synthese']['rembourse'], Decimal('100000.00')
        )
        self.assertEqual(liste.context['synthese']['reste'], Decimal('50000.00'))
