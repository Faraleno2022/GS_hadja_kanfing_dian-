from datetime import date, time
from decimal import Decimal
from unittest.mock import patch

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase, override_settings
from django.urls import reverse

from eleves.models import Classe, Ecole

from .forms import EnseignantForm, EtatSalaireAjustementForm, PresenceForm
from .models import (
    AffectationClasse,
    AvanceSalaire,
    Enseignant,
    EtatSalaire,
    ModeCalculHoraire,
    PeriodeSalaire,
    PresenceEnseignant,
    SourceHeuresSalaire,
    TypeEnseignant,
)
from .services import calculer_etat_salaire as calculer_etat_salaire_reel


LICENCE_MIDDLEWARE = 'ecole_moderne.licence_middleware.LicenceMiddleware'
TEST_MIDDLEWARE = tuple(
    middleware for middleware in settings.MIDDLEWARE
    if middleware != LICENCE_MIDDLEWARE
)


@override_settings(MIDDLEWARE=TEST_MIDDLEWARE)
class MoteurPaieTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_superuser(
            username='audit-paie',
            email='audit-paie@example.com',
            password='mot-de-passe-test',
        )
        self.ecole = Ecole.objects.create(
            nom='École test paie',
            adresse='Conakry',
            telephone='+224610000000',
            directeur='Direction test',
        )
        self.classe_a = Classe.objects.create(
            ecole=self.ecole,
            nom='Classe A',
            niveau='COLLEGE_7',
            annee_scolaire='2025-2026',
        )
        self.classe_b = Classe.objects.create(
            ecole=self.ecole,
            nom='Classe B',
            niveau='COLLEGE_8',
            annee_scolaire='2025-2026',
        )
        self.periode = PeriodeSalaire.objects.create(
            mois=7,
            annee=2026,
            ecole=self.ecole,
            nombre_semaines=Decimal('4'),
            cree_par=self.user,
        )
        self.client.force_login(self.user)

    def creer_secondaire(self, nom='Secondaire', taux='10000'):
        return Enseignant.objects.create(
            nom=nom,
            prenoms='Test',
            ecole=self.ecole,
            type_enseignant=TypeEnseignant.SECONDAIRE,
            statut='ACTIF',
            taux_horaire=Decimal(taux),
            heures_mensuelles=Decimal('120'),
            date_embauche=date(2025, 1, 1),
            cree_par=self.user,
        )

    def creer_fixe(self, nom='Fixe', salaire='1000000', embauche=date(2025, 1, 1)):
        return Enseignant.objects.create(
            nom=nom,
            prenoms='Test',
            ecole=self.ecole,
            type_enseignant=TypeEnseignant.PRIMAIRE,
            statut='ACTIF',
            salaire_fixe=Decimal(salaire),
            heures_mensuelles=Decimal('160'),
            date_embauche=embauche,
            cree_par=self.user,
        )

    def affecter(self, enseignant, classe, heures, **kwargs):
        valeurs = {
            'enseignant': enseignant,
            'classe': classe,
            'heures_par_semaine': Decimal(heures),
            'date_debut': date(2025, 1, 1),
            'actif': True,
        }
        valeurs.update(kwargs)
        return AffectationClasse.objects.create(**valeurs)

    def pointer(self, enseignant, jours, heures=8):
        for jour in jours:
            PresenceEnseignant.objects.create(
                enseignant=enseignant,
                date=date(2026, 7, jour),
                statut='PRESENT',
                heures_travaillees=Decimal(heures),
                pointe_par=self.user,
            )

    def calculer(self):
        return self.client.post(
            reverse('salaires:calculer_salaires', args=[self.periode.id])
        )

    def test_net_egale_base_plus_primes_moins_retenues(self):
        enseignant = self.creer_fixe()
        etat = EtatSalaire.objects.create(
            enseignant=enseignant,
            periode=self.periode,
            salaire_base=Decimal('1000000'),
            primes=Decimal('100000'),
            deductions=Decimal('25000'),
            salaire_net=Decimal('0'),
            calcule_par=self.user,
        )
        self.assertEqual(etat.salaire_net, Decimal('1075000.00'))

    def test_avance_est_deduite_du_salaire_net(self):
        enseignant = self.creer_fixe()

        response = self.client.post(
            reverse('salaires:ajouter_avance'),
            {
                'enseignant': enseignant.id,
                'periode': self.periode.id,
                'montant': '200000',
                'date_avance': '2026-07-10',
                'mode_paiement': '',
                'reference_externe': 'REC-AV-001',
                'motif': 'Besoin familial',
            },
        )

        self.assertRedirects(response, reverse('salaires:liste_avances'))
        avance = AvanceSalaire.objects.get(enseignant=enseignant)
        self.assertEqual(avance.montant, Decimal('200000'))
        etat = EtatSalaire.objects.get(
            enseignant=enseignant,
            periode=self.periode,
        )
        self.assertEqual(etat.avances, Decimal('200000.00'))
        self.assertEqual(etat.salaire_net, Decimal('800000.00'))

    def test_modifier_et_supprimer_avance_recalcule_le_net(self):
        enseignant = self.creer_fixe()
        etat, _ = calculer_etat_salaire_reel(
            enseignant, self.periode, self.user
        )
        avance = AvanceSalaire.objects.create(
            enseignant=enseignant,
            periode=self.periode,
            montant=Decimal('100000'),
            date_avance=date(2026, 7, 10),
            cree_par=self.user,
        )
        etat.refresh_from_db()
        self.assertEqual(etat.salaire_net, Decimal('900000.00'))

        response = self.client.post(
            reverse('salaires:modifier_avance', args=[avance.id]),
            {
                'enseignant': enseignant.id,
                'periode': self.periode.id,
                'montant': '250000',
                'date_avance': '2026-07-10',
                'mode_paiement': '',
                'reference_externe': '',
                'motif': 'Montant corrigé',
            },
        )
        self.assertRedirects(response, reverse('salaires:liste_avances'))
        etat.refresh_from_db()
        self.assertEqual(etat.avances, Decimal('250000.00'))
        self.assertEqual(etat.salaire_net, Decimal('750000.00'))

        response = self.client.post(
            reverse('salaires:supprimer_avance', args=[avance.id])
        )
        self.assertRedirects(response, reverse('salaires:liste_avances'))
        self.assertFalse(AvanceSalaire.objects.filter(pk=avance.pk).exists())
        etat.refresh_from_db()
        self.assertEqual(etat.avances, Decimal('0.00'))
        self.assertEqual(etat.salaire_net, Decimal('1000000.00'))

    def test_avance_superieure_au_salaire_disponible_est_refusee(self):
        enseignant = self.creer_fixe()
        calculer_etat_salaire_reel(enseignant, self.periode, self.user)

        response = self.client.post(
            reverse('salaires:ajouter_avance'),
            {
                'enseignant': enseignant.id,
                'periode': self.periode.id,
                'montant': '1000001',
                'date_avance': '2026-07-10',
                'mode_paiement': '',
                'reference_externe': '',
                'motif': '',
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'salaire disponible')
        self.assertFalse(AvanceSalaire.objects.exists())

    def test_avance_verrouillee_apres_validation_du_salaire(self):
        enseignant = self.creer_fixe()
        etat, _ = calculer_etat_salaire_reel(
            enseignant, self.periode, self.user
        )
        avance = AvanceSalaire.objects.create(
            enseignant=enseignant,
            periode=self.periode,
            montant=Decimal('100000'),
            date_avance=date(2026, 7, 10),
            cree_par=self.user,
        )
        etat.valide = True
        etat.save()

        response = self.client.post(
            reverse('salaires:supprimer_avance', args=[avance.id])
        )

        self.assertRedirects(response, reverse('salaires:liste_avances'))
        self.assertTrue(AvanceSalaire.objects.filter(pk=avance.pk).exists())

    def test_liste_avances_affiche_historique_et_actions(self):
        enseignant = self.creer_fixe()
        calculer_etat_salaire_reel(enseignant, self.periode, self.user)
        AvanceSalaire.objects.create(
            enseignant=enseignant,
            periode=self.periode,
            montant=Decimal('125000'),
            date_avance=date(2026, 7, 10),
            reference_externe='AV-LISTE-001',
            cree_par=self.user,
        )

        response = self.client.get(reverse('salaires:liste_avances'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Avances de salaire')
        self.assertContains(response, 'AV-LISTE-001')
        self.assertContains(response, enseignant.nom_complet)

    def test_salaire_horaire_utilise_le_pointage_reel(self):
        enseignant = self.creer_secondaire()
        self.affecter(enseignant, self.classe_a, '10')
        self.pointer(enseignant, range(1, 6))

        self.calculer()

        etat = EtatSalaire.objects.get(enseignant=enseignant, periode=self.periode)
        self.assertEqual(etat.total_heures, Decimal('40.00'))
        self.assertEqual(etat.mode_calcul_heures, ModeCalculHoraire.POINTAGE)
        self.assertEqual(etat.taux_horaire_applique, Decimal('10000.00'))
        self.assertEqual(etat.salaire_base, Decimal('400000.00'))

    def test_total_mensuel_global_calcule_le_salaire_sans_pointage(self):
        enseignant = self.creer_secondaire()
        enseignant.mode_calcul_horaire = ModeCalculHoraire.MENSUEL
        enseignant.heures_mensuelles = Decimal('75.50')
        enseignant.save()

        self.calculer()

        etat = EtatSalaire.objects.get(enseignant=enseignant, periode=self.periode)
        self.assertEqual(etat.total_heures, Decimal('75.50'))
        self.assertEqual(etat.mode_calcul_heures, ModeCalculHoraire.MENSUEL)
        self.assertEqual(etat.salaire_base, Decimal('755000.00'))

    def test_mode_mensuel_ignore_les_pointages_pour_eviter_le_double_compte(self):
        enseignant = self.creer_secondaire()
        enseignant.mode_calcul_horaire = ModeCalculHoraire.MENSUEL
        enseignant.heures_mensuelles = Decimal('60')
        enseignant.save()
        self.pointer(enseignant, range(1, 6))

        self.calculer()

        etat = EtatSalaire.objects.get(enseignant=enseignant, periode=self.periode)
        self.assertEqual(etat.total_heures, Decimal('60.00'))
        self.assertEqual(etat.salaire_base, Decimal('600000.00'))

    def test_secondaire_sans_affectation_ne_plante_pas(self):
        enseignant = self.creer_secondaire()
        self.pointer(enseignant, [1])

        response = self.calculer()

        self.assertEqual(response.status_code, 302)
        etat = EtatSalaire.objects.get(enseignant=enseignant, periode=self.periode)
        self.assertEqual(etat.salaire_base, Decimal('80000.00'))
        self.assertFalse(etat.details_heures.exists())

    def test_absence_de_pointage_donne_zero_heure(self):
        enseignant = self.creer_secondaire()

        self.calculer()

        etat = EtatSalaire.objects.get(enseignant=enseignant, periode=self.periode)
        self.assertEqual(etat.total_heures, Decimal('0.00'))
        self.assertEqual(etat.salaire_base, Decimal('0.00'))

    def test_heures_saisies_sans_pointage_sont_conservees_au_recalcul(self):
        enseignant = self.creer_secondaire()
        self.calculer()
        etat = EtatSalaire.objects.get(
            enseignant=enseignant, periode=self.periode
        )

        response = self.client.post(
            reverse('salaires:ajuster_etat_salaire', args=[etat.id]),
            {
                'salaire_base': '0',
                'taux_horaire_applique': '12000',
                'total_heures': '42.5',
                'primes': '0',
                'deductions': '0',
                'observations': 'Heures transmises par le secondaire',
            },
        )

        self.assertEqual(response.status_code, 302)
        etat.refresh_from_db()
        self.assertEqual(etat.total_heures, Decimal('42.50'))
        self.assertEqual(etat.taux_horaire_applique, Decimal('12000.00'))
        self.assertEqual(etat.salaire_base, Decimal('510000.00'))
        self.assertEqual(
            etat.mode_calcul_heures, SourceHeuresSalaire.SAISIE
        )
        self.assertTrue(etat.ajuste_manuellement)

        self.calculer()
        etat.refresh_from_db()
        self.assertEqual(etat.total_heures, Decimal('42.50'))
        self.assertEqual(etat.taux_horaire_applique, Decimal('12000.00'))
        self.assertEqual(etat.salaire_base, Decimal('510000.00'))

    def test_pointages_calculent_heures_et_jours_et_bloquent_saisie_heures(self):
        enseignant = self.creer_secondaire()
        self.pointer(enseignant, [1, 2, 3])
        PresenceEnseignant.objects.create(
            enseignant=enseignant,
            date=date(2026, 7, 4),
            statut='ABSENT',
            pointe_par=self.user,
        )
        self.calculer()
        etat = EtatSalaire.objects.get(
            enseignant=enseignant, periode=self.periode
        )
        self.assertEqual(etat.total_heures, Decimal('24.00'))
        self.assertEqual(etat.nombre_jours_presence, 3)

        response = self.client.post(
            reverse('salaires:ajuster_etat_salaire', args=[etat.id]),
            {
                'salaire_base': '0',
                'taux_horaire_applique': '12500',
                'total_heures': '99',
                'primes': '0',
                'deductions': '0',
                'observations': '',
            },
        )

        self.assertEqual(response.status_code, 302)
        etat.refresh_from_db()
        self.assertEqual(etat.total_heures, Decimal('24.00'))
        self.assertEqual(etat.taux_horaire_applique, Decimal('12500.00'))
        self.assertEqual(etat.salaire_base, Decimal('300000.00'))
        self.assertEqual(etat.mode_calcul_heures, ModeCalculHoraire.POINTAGE)

        response = self.client.get(
            reverse('salaires:fiche_paie_pdf', args=[etat.id])
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/pdf')

    def test_pointage_arrivee_depart_recalcule_immediatement_le_salaire(self):
        enseignant = self.creer_secondaire()

        with patch(
            'salaires.views_presences.user_school', return_value=self.ecole
        ):
            response = self.client.post(
                reverse('salaires:pointer_presence'),
                {
                    'date': '2026-07-01',
                    'enseignants': [str(enseignant.id)],
                    f'statut_{enseignant.id}': 'PRESENT',
                    f'heure_arrivee_{enseignant.id}': '08:00',
                    f'heure_depart_{enseignant.id}': '16:30',
                },
            )

        self.assertEqual(response.status_code, 302)
        etat = EtatSalaire.objects.get(enseignant=enseignant, periode=self.periode)
        self.assertEqual(etat.total_heures, Decimal('8.50'))
        self.assertEqual(etat.salaire_base, Decimal('85000.00'))

    def test_repartition_respecte_les_heures_hebdomadaires(self):
        enseignant = self.creer_secondaire()
        self.affecter(enseignant, self.classe_a, '10')
        self.affecter(enseignant, self.classe_b, '20')
        self.pointer(enseignant, range(1, 16))

        self.calculer()

        etat = EtatSalaire.objects.get(enseignant=enseignant, periode=self.periode)
        details = list(
            etat.details_heures.order_by('affectation_classe__classe__nom')
            .values_list('heures_prevues', 'heures_realisees')
        )
        self.assertEqual(
            details,
            [
                (Decimal('40.00'), Decimal('40.00')),
                (Decimal('80.00'), Decimal('80.00')),
            ],
        )

    def test_affectation_historique_cloturee_est_utilisee(self):
        enseignant = self.creer_secondaire()
        self.affecter(
            enseignant,
            self.classe_a,
            '10',
            date_debut=date(2026, 7, 1),
            date_fin=date(2026, 7, 31),
            actif=False,
        )
        self.pointer(enseignant, range(1, 6))

        self.calculer()

        etat = EtatSalaire.objects.get(enseignant=enseignant, periode=self.periode)
        detail = etat.details_heures.get()
        self.assertEqual(detail.heures_prevues, Decimal('40.00'))
        self.assertEqual(detail.heures_realisees, Decimal('40.00'))

    def test_forfait_est_proratise_selon_date_embauche(self):
        enseignant = self.creer_fixe(
            salaire='3100000', embauche=date(2026, 7, 16)
        )

        self.calculer()

        etat = EtatSalaire.objects.get(enseignant=enseignant, periode=self.periode)
        self.assertEqual(etat.salaire_base, Decimal('1600000.00'))

    def test_salaire_fixe_ne_depend_pas_des_heures_pointees(self):
        enseignant = self.creer_fixe(salaire='1000000')
        self.pointer(enseignant, range(1, 6))

        self.calculer()

        etat = EtatSalaire.objects.get(enseignant=enseignant, periode=self.periode)
        self.assertIsNone(etat.total_heures)
        self.assertEqual(etat.mode_calcul_heures, '')
        self.assertEqual(etat.salaire_base, Decimal('1000000.00'))

    def test_embauche_apres_periode_est_exclue(self):
        enseignant = self.creer_fixe(embauche=date(2026, 8, 1))

        self.calculer()

        self.assertFalse(
            EtatSalaire.objects.filter(
                enseignant=enseignant, periode=self.periode
            ).exists()
        )

    def test_calcul_du_lot_est_atomique(self):
        self.creer_fixe(nom='A enseignant')
        self.creer_fixe(nom='B enseignant')
        appels = 0

        def calcul_avec_erreur(enseignant, periode, utilisateur):
            nonlocal appels
            appels += 1
            if appels == 2:
                raise RuntimeError('erreur simulée')
            return calculer_etat_salaire_reel(enseignant, periode, utilisateur)

        with patch('salaires.views.calculer_etat_salaire', side_effect=calcul_avec_erreur):
            self.calculer()

        self.assertEqual(EtatSalaire.objects.count(), 0)

    def test_salaire_negatif_est_refuse_par_le_formulaire(self):
        form = EnseignantForm(
            data={
                'nom': 'Fixe',
                'prenoms': 'Négatif',
                'ecole': self.ecole.id,
                'type_enseignant': TypeEnseignant.PRIMAIRE,
                'statut': 'ACTIF',
                'salaire_fixe': '-100000',
                'heures_mensuelles': '160',
                'date_embauche': '2025-01-01',
            },
            user=self.user,
        )
        self.assertFalse(form.is_valid())
        self.assertIn('salaire_fixe', form.errors)

    def test_formulaire_pointage_accepte_des_heures_mensuelles_vides(self):
        form = EnseignantForm(
            data={
                'nom': 'Horaire',
                'prenoms': 'Pointage',
                'ecole': self.ecole.id,
                'type_enseignant': TypeEnseignant.SECONDAIRE,
                'statut': 'ACTIF',
                'taux_horaire': '10000',
                'mode_calcul_horaire': ModeCalculHoraire.POINTAGE,
                'heures_mensuelles': '',
                'date_embauche': '2025-01-01',
            },
            user=self.user,
        )

        self.assertTrue(form.is_valid(), form.errors)

    def test_formulaire_mensuel_exige_le_total_global(self):
        form = EnseignantForm(
            data={
                'nom': 'Horaire',
                'prenoms': 'Mensuel',
                'ecole': self.ecole.id,
                'type_enseignant': TypeEnseignant.SECONDAIRE,
                'statut': 'ACTIF',
                'taux_horaire': '10000',
                'mode_calcul_horaire': ModeCalculHoraire.MENSUEL,
                'heures_mensuelles': '',
                'date_embauche': '2025-01-01',
            },
            user=self.user,
        )

        self.assertFalse(form.is_valid())
        self.assertIn('heures_mensuelles', form.errors)

    @patch('salaires.views.timezone.localdate', return_value=date(2026, 7, 15))
    def test_modification_du_total_mensuel_recalcule_le_salaire(
        self, _localdate
    ):
        enseignant = self.creer_secondaire()

        response = self.client.post(
            reverse('salaires:modifier_enseignant', args=[enseignant.id]),
            {
                'nom': enseignant.nom,
                'prenoms': enseignant.prenoms,
                'ecole': self.ecole.id,
                'type_enseignant': TypeEnseignant.SECONDAIRE,
                'statut': 'ACTIF',
                'taux_horaire': '10000',
                'mode_calcul_horaire': ModeCalculHoraire.MENSUEL,
                'heures_mensuelles': '80',
                'date_embauche': '2025-01-01',
                'affectations-TOTAL_FORMS': '1',
                'affectations-INITIAL_FORMS': '0',
                'affectations-MIN_NUM_FORMS': '0',
                'affectations-MAX_NUM_FORMS': '1000',
                'affectations-0-classe': str(self.classe_a.pk),
                'affectations-0-heures_par_semaine': '20',
                'affectations-0-date_debut': '2025-01-01',
                'affectations-0-actif': 'on',
            },
        )

        self.assertEqual(response.status_code, 302)
        etat = EtatSalaire.objects.get(enseignant=enseignant, periode=self.periode)
        self.assertEqual(etat.total_heures, Decimal('80.00'))
        self.assertEqual(etat.salaire_base, Decimal('800000.00'))

    def test_salaire_negatif_est_refuse_hors_formulaire(self):
        with self.assertRaises(ValidationError):
            self.creer_fixe(salaire='-100000')

    def test_recalcul_supprime_un_brouillon_devenu_ineligible(self):
        enseignant = self.creer_fixe()
        self.calculer()
        self.assertTrue(
            EtatSalaire.objects.filter(
                enseignant=enseignant, periode=self.periode
            ).exists()
        )

        enseignant.statut = 'DEMISSIONNAIRE'
        enseignant.save(update_fields=['statut'])
        self.calculer()

        self.assertFalse(
            EtatSalaire.objects.filter(
                enseignant=enseignant, periode=self.periode
            ).exists()
        )

    def test_un_brouillon_ineligible_ne_peut_pas_etre_valide(self):
        enseignant = self.creer_fixe()
        etat = EtatSalaire.objects.create(
            enseignant=enseignant,
            periode=self.periode,
            salaire_base=Decimal('1000000'),
            salaire_net=Decimal('1000000'),
            calcule_par=self.user,
        )
        enseignant.statut = 'DEMISSIONNAIRE'
        enseignant.save(update_fields=['statut'])

        response = self.client.post(
            reverse('salaires:valider_etat_salaire', args=[etat.id])
        )

        self.assertEqual(response.status_code, 302)
        etat.refresh_from_db()
        self.assertFalse(etat.valide)

    def test_retenue_superieure_au_brut_est_refusee(self):
        enseignant = self.creer_fixe()
        etat = EtatSalaire.objects.create(
            enseignant=enseignant,
            periode=self.periode,
            salaire_base=Decimal('1000000'),
            salaire_net=Decimal('1000000'),
            calcule_par=self.user,
        )
        etat.deductions = Decimal('1000001')
        with self.assertRaises(ValidationError):
            etat.save()

    def test_ajustement_primes_retenues_recalcule_le_net(self):
        enseignant = self.creer_fixe()
        etat = EtatSalaire.objects.create(
            enseignant=enseignant,
            periode=self.periode,
            salaire_base=Decimal('1000000'),
            salaire_net=Decimal('1000000'),
            calcule_par=self.user,
        )

        response = self.client.post(
            reverse('salaires:ajuster_etat_salaire', args=[etat.id]),
            {
                'primes': '100000',
                'deductions': '25000',
                'observations': 'Ajustement contrôlé',
            },
        )

        self.assertEqual(response.status_code, 302)
        etat.refresh_from_db()
        self.assertEqual(etat.salaire_net, Decimal('1075000.00'))
        self.assertEqual(etat.observations, 'Ajustement contrôlé')

    def test_salaire_fixe_modifie_reste_stable_apres_recalcul(self):
        enseignant = self.creer_fixe()
        self.pointer(enseignant, [1, 2])
        self.calculer()
        etat = EtatSalaire.objects.get(
            enseignant=enseignant, periode=self.periode
        )

        response = self.client.post(
            reverse('salaires:ajuster_etat_salaire', args=[etat.id]),
            {
                'salaire_base': '1150000',
                'primes': '50000',
                'deductions': '0',
                'observations': 'Salaire de base ajusté',
            },
        )

        self.assertEqual(response.status_code, 302)
        self.calculer()
        etat.refresh_from_db()
        self.assertEqual(etat.salaire_base, Decimal('1150000.00'))
        self.assertEqual(etat.salaire_net, Decimal('1200000.00'))
        self.assertEqual(etat.nombre_jours_presence, 2)
        self.assertTrue(etat.ajuste_manuellement)

    def test_formulaire_presence_sans_heures_ne_plante_plus(self):
        enseignant = self.creer_secondaire()
        form = PresenceForm(
            data={
                'enseignant': enseignant.id,
                'date': '2026-07-01',
                'statut': 'PRESENT',
                'observations': '',
            },
            ecole=self.ecole,
        )
        self.assertFalse(form.is_valid())
        self.assertIn('__all__', form.errors)

    def test_presence_calcule_les_heures_et_limite_les_statuts_absents(self):
        enseignant = self.creer_secondaire()
        presence = PresenceEnseignant.objects.create(
            enseignant=enseignant,
            date=date(2026, 7, 1),
            statut='PRESENT',
            heure_arrivee=time(8, 0),
            heure_depart=time(16, 30),
            pointe_par=self.user,
        )
        self.assertEqual(presence.heures_travaillees, Decimal('8.50'))

        presence.statut = 'ABSENT'
        with self.assertRaises(ValidationError):
            presence.save()

    def test_nombre_semaines_invalide_est_refuse(self):
        response = self.client.post(
            reverse('salaires:creer_periode'),
            {
                'mois': '8',
                'annee': '2026',
                'ecole': str(self.ecole.id),
                'nombre_semaines': '-1',
            },
        )
        self.assertEqual(response.status_code, 302)
        self.assertFalse(
            PeriodeSalaire.objects.filter(
                ecole=self.ecole, mois=8, annee=2026
            ).exists()
        )

    def test_creation_periode_regroupe_et_calcule_les_enseignants(self):
        enseignant_fixe = self.creer_fixe(nom='Primaire actif')
        enseignant_secondaire = self.creer_secondaire(nom='Secondaire actif')
        enseignant_futur = self.creer_fixe(
            nom='Embauche future', embauche=date(2026, 9, 1)
        )

        response = self.client.post(
            reverse('salaires:creer_periode'),
            {
                'mois': '8',
                'annee': '2026',
                'ecole': str(self.ecole.id),
                'nombre_semaines': '4.33',
            },
        )

        periode = PeriodeSalaire.objects.get(
            ecole=self.ecole, mois=8, annee=2026
        )
        self.assertRedirects(
            response,
            f"{reverse('salaires:etats_salaire')}?periode={periode.id}",
            fetch_redirect_response=False,
        )
        etats = EtatSalaire.objects.filter(periode=periode)
        self.assertSetEqual(
            set(etats.values_list('enseignant_id', flat=True)),
            {enseignant_fixe.id, enseignant_secondaire.id},
        )
        self.assertFalse(
            etats.filter(enseignant=enseignant_futur).exists()
        )
        self.assertEqual(
            etats.get(enseignant=enseignant_fixe).salaire_base,
            Decimal('1000000.00'),
        )

    def test_creation_periode_et_calcul_sont_atomiques(self):
        self.creer_fixe(nom='A enseignant')
        self.creer_fixe(nom='B enseignant')
        appels = 0

        def calcul_avec_erreur(enseignant, periode, utilisateur):
            nonlocal appels
            appels += 1
            if appels == 2:
                raise RuntimeError('erreur simulée')
            return calculer_etat_salaire_reel(enseignant, periode, utilisateur)

        with patch(
            'salaires.views.calculer_etat_salaire',
            side_effect=calcul_avec_erreur,
        ):
            self.client.post(
                reverse('salaires:creer_periode'),
                {
                    'mois': '8',
                    'annee': '2026',
                    'ecole': str(self.ecole.id),
                    'nombre_semaines': '4.33',
                },
            )

        self.assertFalse(
            PeriodeSalaire.objects.filter(
                ecole=self.ecole, mois=8, annee=2026
            ).exists()
        )
        self.assertEqual(EtatSalaire.objects.count(), 0)

    def test_formulaire_ajustement_refuse_les_valeurs_negatives(self):
        enseignant = self.creer_fixe()
        etat = EtatSalaire.objects.create(
            enseignant=enseignant,
            periode=self.periode,
            salaire_base=Decimal('1000000'),
            salaire_net=Decimal('1000000'),
            calcule_par=self.user,
        )
        form = EtatSalaireAjustementForm(
            data={'primes': '-1', 'deductions': '0', 'observations': ''},
            instance=etat,
        )
        self.assertFalse(form.is_valid())
        self.assertIn('primes', form.errors)

    def donnees_creation_enseignant(self, type_enseignant, **valeurs):
        donnees = {
            'nom': 'Camara',
            'prenoms': 'Fatoumata',
            'telephone': '+224610000001',
            'email': 'fatoumata@example.com',
            'adresse': 'Conakry',
            'ecole': str(self.ecole.pk),
            'type_enseignant': type_enseignant,
            'statut': 'ACTIF',
            'fonction': '',
            'taux_horaire': '',
            'mode_calcul_horaire': ModeCalculHoraire.POINTAGE,
            'salaire_fixe': '1500000',
            'heures_mensuelles': '',
            'date_embauche': '2026-07-01',
            'affectations-TOTAL_FORMS': '3',
            'affectations-INITIAL_FORMS': '0',
            'affectations-MIN_NUM_FORMS': '0',
            'affectations-MAX_NUM_FORMS': '1000',
        }
        donnees.update(valeurs)
        return donnees

    def test_creation_primaire_enregistre_sa_classe_principale(self):
        classe = Classe.objects.create(
            ecole=self.ecole,
            nom='Primaire 3 A',
            niveau='PRIMAIRE_3',
            annee_scolaire='2026-2027',
        )
        donnees = self.donnees_creation_enseignant(
            TypeEnseignant.PRIMAIRE,
            **{
                'affectations-0-classe': str(classe.pk),
                'affectations-0-date_debut': '2026-07-01',
                'affectations-0-actif': 'on',
            },
        )

        response = self.client.post(
            reverse('salaires:ajouter_enseignant'),
            donnees,
        )

        self.assertEqual(
            response.status_code,
            302,
            (
                {
                    'enseignant': response.context['form'].errors,
                    'affectations': response.context['affectations'].errors,
                    'global': response.context[
                        'affectations'
                    ].non_form_errors(),
                }
                if response.context
                else response.content[:500]
            ),
        )
        enseignant = Enseignant.objects.get(email='fatoumata@example.com')
        self.assertRedirects(
            response,
            reverse('salaires:detail_enseignant', args=[enseignant.pk]),
        )
        affectation = enseignant.affectations.get()
        self.assertEqual(affectation.classe, classe)
        self.assertIsNone(affectation.heures_par_semaine)

    def test_creation_secondaire_enregistre_plusieurs_affectations(self):
        donnees = self.donnees_creation_enseignant(
            TypeEnseignant.SECONDAIRE,
            salaire_fixe='',
            taux_horaire='10000',
            **{
                'affectations-0-classe': str(self.classe_a.pk),
                'affectations-0-heures_par_semaine': '8',
                'affectations-0-matiere': 'Mathématiques',
                'affectations-0-date_debut': '2026-07-01',
                'affectations-0-actif': 'on',
                'affectations-1-classe': str(self.classe_b.pk),
                'affectations-1-heures_par_semaine': '6',
                'affectations-1-matiere': 'Mathématiques',
                'affectations-1-date_debut': '2026-07-01',
                'affectations-1-actif': 'on',
            },
        )

        response = self.client.post(
            reverse('salaires:ajouter_enseignant'),
            donnees,
        )

        self.assertEqual(
            response.status_code,
            302,
            (
                response.context['affectations'].errors
                if response.context
                else response.content[:500]
            ),
        )
        enseignant = Enseignant.objects.get(email='fatoumata@example.com')
        self.assertEqual(response.status_code, 302)
        self.assertSetEqual(
            set(enseignant.affectations.values_list('classe_id', flat=True)),
            {self.classe_a.pk, self.classe_b.pk},
        )
        self.assertEqual(
            enseignant.affectations.get(classe=self.classe_a).heures_par_semaine,
            Decimal('8'),
        )

    def test_creation_administrateur_enregistre_sa_fonction(self):
        donnees = self.donnees_creation_enseignant(
            TypeEnseignant.ADMINISTRATEUR,
            fonction='Comptable',
        )

        response = self.client.post(
            reverse('salaires:ajouter_enseignant'),
            donnees,
        )

        self.assertEqual(
            response.status_code,
            302,
            (
                response.context['form'].errors
                if response.context
                else response.content[:500]
            ),
        )
        enseignant = Enseignant.objects.get(email='fatoumata@example.com')
        self.assertEqual(response.status_code, 302)
        self.assertEqual(enseignant.fonction, 'Comptable')
        self.assertFalse(enseignant.affectations.exists())

    def test_creation_administrateur_exige_la_fonction(self):
        response = self.client.post(
            reverse('salaires:ajouter_enseignant'),
            self.donnees_creation_enseignant(TypeEnseignant.ADMINISTRATEUR),
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'La fonction est obligatoire')
        self.assertFalse(
            Enseignant.objects.filter(email='fatoumata@example.com').exists()
        )

    def test_classe_d_une_autre_ecole_est_refusee(self):
        autre_ecole = Ecole.objects.create(
            nom='Autre école',
            adresse='Kindia',
            telephone='+224620000000',
            directeur='Autre direction',
        )
        classe = Classe.objects.create(
            ecole=autre_ecole,
            nom='Primaire externe',
            niveau='PRIMAIRE_2',
            annee_scolaire='2026-2027',
        )
        donnees = self.donnees_creation_enseignant(
            TypeEnseignant.PRIMAIRE,
            **{
                'affectations-0-classe': str(classe.pk),
                'affectations-0-date_debut': '2026-07-01',
                'affectations-0-actif': 'on',
            },
        )

        response = self.client.post(
            reverse('salaires:ajouter_enseignant'),
            donnees,
        )

        self.assertEqual(response.status_code, 200)
        self.assertFalse(
            Enseignant.objects.filter(email='fatoumata@example.com').exists()
        )

    def test_api_classes_filtre_le_niveau_demande(self):
        classe_primaire = Classe.objects.create(
            ecole=self.ecole,
            nom='Primaire API',
            niveau='PRIMAIRE_4',
            annee_scolaire='2026-2027',
        )

        response = self.client.get(
            reverse('salaires:classes_affectables_enseignant'),
            {
                'ecole': self.ecole.pk,
                'type_enseignant': TypeEnseignant.PRIMAIRE,
            },
        )

        self.assertEqual(response.status_code, 200)
        ids = {ligne['id'] for ligne in response.json()['classes']}
        self.assertIn(classe_primaire.pk, ids)
        self.assertNotIn(self.classe_a.pk, ids)

    def test_creation_personnel_services_avec_prime_et_salaire_fixe(self):
        categories = [TypeEnseignant.CHAUFFEUR, TypeEnseignant.VIGILE,
                      TypeEnseignant.ENTRETIEN, TypeEnseignant.NOUNOU,
                      TypeEnseignant.RESTAURATION]
        for categorie in categories:
            with self.subTest(categorie=categorie):
                response = self.client.post(reverse('salaires:ajouter_enseignant'),
                    self.donnees_creation_enseignant(categorie, nom=categorie,
                                                     prime_mensuelle='50000'))
                self.assertEqual(response.status_code, 302)
                personne = Enseignant.objects.get(nom=categorie)
                self.assertTrue(personne.est_salaire_fixe)
                self.assertFalse(personne.affectations.exists())
                self.assertEqual(personne.prime_mensuelle, Decimal('50000'))
                etat, _ = calculer_etat_salaire_reel(personne, self.periode, self.user)
                self.assertEqual(etat.salaire_base, Decimal('1500000'))
                self.assertEqual(etat.primes, Decimal('50000'))
                self.assertEqual(etat.salaire_net, Decimal('1550000'))
                page = self.client.get(reverse('salaires:liste_enseignants'),
                                       {'type_enseignant': categorie})
                self.assertContains(page, personne.get_type_enseignant_display())

    def test_prime_mensuelle_et_ponctuelle_ne_se_cumulent_pas_au_recalcul(self):
        personne = self.creer_fixe()
        personne.prime_mensuelle = Decimal('50000')
        personne.save()
        etat, _ = calculer_etat_salaire_reel(personne, self.periode, self.user)
        response = self.client.post(reverse('salaires:ajuster_etat_salaire', args=[etat.pk]),
                                   {'primes': '75000', 'deductions': '10000',
                                    'observations': 'Prime mensuelle + remplacement'})
        self.assertEqual(response.status_code, 302)
        personne.prime_mensuelle = Decimal('60000')
        personne.save()
        for _ in range(2):
            etat, _ = calculer_etat_salaire_reel(personne, self.periode, self.user)
            self.assertEqual(etat.primes, Decimal('75000'))
            self.assertEqual(etat.salaire_net, Decimal('1065000'))
        suivante = PeriodeSalaire.objects.create(mois=8, annee=2026,
                    ecole=self.ecole, nombre_semaines=4, cree_par=self.user)
        prochain, _ = calculer_etat_salaire_reel(personne, suivante, self.user)
        self.assertEqual(prochain.primes, Decimal('60000'))
        self.assertEqual(prochain.salaire_net, Decimal('1060000'))
        etat.valide = True
        etat.valide_par = self.user
        etat.save()
        _, modifie = calculer_etat_salaire_reel(personne, self.periode, self.user)
        self.assertFalse(modifie)
        etat.refresh_from_db()
        self.assertEqual(etat.primes, Decimal('75000'))

    def test_personnel_prime_negative_et_salaire_absent_refuses(self):
        for valeurs, champ in [({'prime_mensuelle': '-1'}, 'prime_mensuelle'),
                               ({'salaire_fixe': ''}, 'salaire_fixe')]:
            form = EnseignantForm(self.donnees_creation_enseignant(
                TypeEnseignant.CHAUFFEUR, **valeurs), user=self.user)
            self.assertFalse(form.is_valid())
            self.assertIn(champ, form.errors)
        personne = self.creer_fixe()
        personne.prime_mensuelle = Decimal('-1')
        with self.assertRaises(ValidationError):
            personne.save()
