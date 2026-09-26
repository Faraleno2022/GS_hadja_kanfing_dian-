"""Règles reprises des feuilles « Etat » et « Etat Prof final » du classeur de paie."""

from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse

from eleves.models import Ecole

from .models import (
    Enseignant,
    ModeCalculHoraire,
    ParametrePaie,
    PeriodeSalaire,
    PresenceEnseignant,
    TypeEnseignant,
)
from .services import calculer_etat_salaire, masse_salariale, synthese_etats_salaire
from .test_documents_paie import TEST_MIDDLEWARE


@override_settings(MIDDLEWARE=TEST_MIDDLEWARE)
class ClasseurPaieExcelTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_superuser(
            username='paie-excel', email='paie-excel@example.com', password='x-test-123',
        )
        self.ecole = Ecole.objects.create(
            nom='Groupe Scolaire Test', adresse='Diécké',
            telephone='+224620000001', directeur='Direction',
        )
        self.periode = PeriodeSalaire.objects.create(
            mois=5, annee=2026, ecole=self.ecole, cree_par=self.user,
        )
        self.parametre = ParametrePaie.objects.create(
            ecole=self.ecole,
            prime_par_heure_revision=Decimal('10000'),
            prime_professeur_principal=Decimal('50000'),
            retenue_par_jour_chome=Decimal('30000'),
        )
        self.client.force_login(self.user)

    def creer_prof_secondaire(self, **kwargs):
        # Cé Imé MAHOMY : 6 h le lundi, le mardi et le mercredi.
        valeurs = dict(
            nom='MAHOMY', prenoms='Cé Imé', ecole=self.ecole,
            type_enseignant=TypeEnseignant.SECONDAIRE, taux_horaire=Decimal('13500'),
            mode_calcul_horaire=ModeCalculHoraire.HEBDOMADAIRE,
            heures_lundi=Decimal('6'), heures_mardi=Decimal('6'),
            heures_mercredi=Decimal('6'), professeur_principal=True,
            prime_exceptionnelle=Decimal('25000'),
            date_embauche=date(2026, 1, 1), cree_par=self.user,
        )
        valeurs.update(kwargs)
        return Enseignant.objects.create(**valeurs)

    def creer_maitre_primaire(self):
        return Enseignant.objects.create(
            nom='MAHOMY', prenoms='Joseph', ecole=self.ecole,
            type_enseignant=TypeEnseignant.ADMINISTRATEUR, fonction='Chargé de cours',
            salaire_fixe=Decimal('550000'), prime_fonction=Decimal('250000'),
            date_embauche=date(2026, 1, 1), cree_par=self.user,
        )

    def test_calendrier_du_mois_par_defaut(self):
        # Mai 2026 commence un vendredi : 5 vendredis et 5 samedis.
        self.assertEqual(self.periode.occurrences_jours_semaine(), [4, 4, 4, 4, 5, 5])
        self.periode.nb_vendredis = 4
        self.periode.nb_samedis = 3
        self.assertEqual(self.periode.occurrences_jours_semaine(), [4, 4, 4, 4, 4, 3])

    def test_emploi_du_temps_heures_prestees_et_primes(self):
        prof = self.creer_prof_secondaire()
        etat, _ = calculer_etat_salaire(prof, self.periode, self.user)
        self.assertEqual(etat.heures_a_prester, Decimal('72.00'))  # (6+6+6) × 4
        self.assertEqual(etat.total_heures, Decimal('72.00'))

        # 2 heures d'absence : conservées lors des recalculs suivants.
        etat.heures_absence = Decimal('2')
        etat.save()
        etat, _ = calculer_etat_salaire(prof, self.periode, self.user)

        self.assertEqual(etat.mode_calcul_heures, ModeCalculHoraire.HEBDOMADAIRE)
        self.assertEqual(etat.total_heures, Decimal('70.00'))
        self.assertEqual(etat.salaire_base, Decimal('945000.00'))  # 70 × 13 500
        self.assertEqual(etat.prime_fonction, Decimal('50000.00'))  # professeur principal
        self.assertEqual(etat.prime_exceptionnelle, Decimal('25000.00'))  # autres primes
        self.assertEqual(etat.salaire_net, Decimal('1020000.00'))
        self.assertEqual(etat.jours_travailles(20), 26)  # 4+4+4+4+5+5 jours de cours

    def test_calendrier_modifie_puis_ajustement_des_absences(self):
        prof = self.creer_prof_secondaire(
            heures_lundi=Decimal('0'), heures_mardi=Decimal('0'),
            heures_mercredi=Decimal('0'), heures_vendredi=Decimal('4'),
            heures_samedi=Decimal('2'), professeur_principal=False,
            prime_exceptionnelle=Decimal('0'),
        )
        response = self.client.post(
            reverse('salaires:calendrier_periode', args=[self.periode.id]),
            {'nb_vendredis': '4', 'nb_samedis': '3'},
        )
        self.assertEqual(response.status_code, 302)
        self.periode.refresh_from_db()

        etat, _ = calculer_etat_salaire(prof, self.periode, self.user)
        self.assertEqual(etat.heures_a_prester, Decimal('22.00'))  # 4×4 + 2×3

        response = self.client.post(
            reverse('salaires:ajuster_etat_salaire', args=[etat.id]),
            {
                'total_heures': '22', 'taux_horaire_applique': '13500',
                'heures_absence': '4', 'deductions': '0', 'jours_chomes': '0',
                'reappliquer_bareme': '1',
            },
        )
        self.assertEqual(response.status_code, 302)
        etat.refresh_from_db()
        self.assertEqual(etat.total_heures, Decimal('18.00'))
        self.assertEqual(etat.mode_calcul_heures, ModeCalculHoraire.HEBDOMADAIRE)
        self.assertEqual(etat.salaire_base, Decimal('243000.00'))

    def test_mode_emploi_du_temps_exige_des_heures(self):
        from django.core.exceptions import ValidationError

        with self.assertRaises(ValidationError):
            self.creer_prof_secondaire(
                heures_lundi=Decimal('0'), heures_mardi=Decimal('0'),
                heures_mercredi=Decimal('0'),
            )

    def test_jours_chomes_imputation_liee_aux_sanctions(self):
        maitre = self.creer_maitre_primaire()
        PresenceEnseignant.objects.create(
            enseignant=maitre, date=date(2026, 5, 6), statut='ABSENT', pointe_par=self.user,
        )
        PresenceEnseignant.objects.create(
            enseignant=maitre, date=date(2026, 5, 7), statut='ABSENT', justifie=True,
            pointe_par=self.user,
        )
        etat, _ = calculer_etat_salaire(maitre, self.periode, self.user)

        self.assertEqual(etat.jours_chomes, 1)  # l'absence justifiée n'est pas chômée
        self.assertEqual(etat.imputation_sanctions, Decimal('30000.00'))
        self.assertEqual(etat.salaire_brut, Decimal('800000.00'))
        self.assertEqual(etat.salaire_net, Decimal('770000.00'))
        self.assertEqual(etat.jours_travailles(self.parametre.jours_ouvrables), 19)

        sections, totaux = masse_salariale(self.periode)
        self.assertEqual(totaux['total_sanctions'], Decimal('30000.00'))
        self.assertEqual(totaux['total_net'], Decimal('770000.00'))
        synthese = synthese_etats_salaire(self.periode.etats_salaire)
        self.assertEqual(
            synthese['total_brut'] - synthese['total_deductions'] - synthese['total_avances'],
            synthese['total_net'],
        )

    def test_jours_chomes_saisis_a_la_main(self):
        maitre = self.creer_maitre_primaire()
        etat, _ = calculer_etat_salaire(maitre, self.periode, self.user)

        response = self.client.post(
            reverse('salaires:ajuster_etat_salaire', args=[etat.id]),
            {
                'salaire_base': '550000', 'prime_fonction': '250000',
                'jours_chomes': '2', 'deductions': '0',
            },
        )
        self.assertEqual(response.status_code, 302)
        etat, _ = calculer_etat_salaire(maitre, self.periode, self.user)

        self.assertEqual(etat.jours_chomes, 2)
        self.assertEqual(etat.imputation_sanctions, Decimal('60000.00'))
        self.assertEqual(etat.salaire_net, Decimal('740000.00'))

        for nom in ('etat_salaire_detaille_pdf', 'bulletins_paie_pdf'):
            response = self.client.get(reverse(f'salaires:{nom}', args=[self.periode.id]))
            self.assertEqual(response.status_code, 200, nom)

    def test_sanctions_superieures_au_brut_refusees(self):
        maitre = self.creer_maitre_primaire()
        etat, _ = calculer_etat_salaire(maitre, self.periode, self.user)

        response = self.client.post(
            reverse('salaires:ajuster_etat_salaire', args=[etat.id]),
            {
                'salaire_base': '550000', 'prime_fonction': '250000',
                'jours_chomes': '30', 'deductions': '0',
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "imputation des jours chômés")
