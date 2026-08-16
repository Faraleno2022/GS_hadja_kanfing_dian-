from datetime import date, time
from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse

from eleves.models import Classe, Ecole
from salaires.forms import EnseignantForm, PresenceForm
from salaires.models import (
    AffectationClasse,
    DetailHeuresClasse,
    Enseignant,
    EtatSalaire,
    PeriodeSalaire,
    PresenceEnseignant,
    TypeEnseignant,
)
from salaires.services import (
    calculer_salaires_periode,
    recalculer_salaire_enseignant,
)
from salaires.views_presences import _actualiser_salaire_ouvert


class PayrollEngineTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_superuser(
            username='admin-paie',
            password='test-secret',
            email='paie@example.com',
        )
        self.ecole = Ecole.objects.create(
            nom='École Test Paie',
            adresse='Conakry',
            telephone='+224622000001',
            directeur='Direction',
        )
        self.periode = PeriodeSalaire.objects.create(
            mois=1,
            annee=2025,
            ecole=self.ecole,
            nombre_semaines=Decimal('4'),
            cree_par=self.user,
        )

    def creer_secondaire(self, nom='HORAIRE', date_embauche=date(2024, 1, 1), taux='10000'):
        return Enseignant.objects.create(
            nom=nom,
            prenoms='Enseignant',
            ecole=self.ecole,
            type_enseignant=TypeEnseignant.SECONDAIRE,
            statut='ACTIF',
            taux_horaire=Decimal(taux),
            heures_mensuelles=Decimal('120'),
            date_embauche=date_embauche,
            cree_par=self.user,
        )

    def creer_fixe(self, nom='FIXE', date_embauche=date(2024, 1, 1), salaire='310000'):
        return Enseignant.objects.create(
            nom=nom,
            prenoms='Enseignant',
            ecole=self.ecole,
            type_enseignant=TypeEnseignant.PRIMAIRE,
            statut='ACTIF',
            salaire_fixe=Decimal(salaire),
            date_embauche=date_embauche,
            cree_par=self.user,
        )

    def ajouter_heures(self, enseignant, heures):
        for index, valeur in enumerate(heures, start=1):
            PresenceEnseignant.objects.create(
                enseignant=enseignant,
                date=date(2025, 1, index),
                statut='PRESENT',
                heures_travaillees=Decimal(valeur),
                pointe_par=self.user,
            )

    def creer_classe(self, nom):
        return Classe.objects.create(
            ecole=self.ecole,
            nom=nom,
            niveau='COLLEGE_7',
            annee_scolaire='2024-2025',
        )

    def test_salaire_horaire_utilise_uniquement_les_pointages_reels(self):
        enseignant = self.creer_secondaire()
        self.ajouter_heures(enseignant, ['8', '8', '8', '8', '8'])

        calculer_salaires_periode(self.periode, self.user)

        etat = EtatSalaire.objects.get(enseignant=enseignant, periode=self.periode)
        self.assertEqual(etat.total_heures, Decimal('40.00'))
        self.assertEqual(etat.salaire_base, Decimal('400000.00'))
        self.assertEqual(etat.salaire_net, Decimal('400000.00'))
        self.assertEqual(etat.taux_horaire_applique, Decimal('10000.00'))

    def test_sans_pointage_le_salaire_horaire_est_nul(self):
        enseignant = self.creer_secondaire()

        calculer_salaires_periode(self.periode, self.user)

        etat = EtatSalaire.objects.get(enseignant=enseignant, periode=self.periode)
        self.assertEqual(etat.total_heures, Decimal('0.00'))
        self.assertEqual(etat.salaire_base, Decimal('0.00'))
        self.assertEqual(etat.details_heures.count(), 0)

    def test_arrivee_et_depart_calculent_les_heures_et_le_salaire(self):
        enseignant = self.creer_secondaire()
        presence = PresenceEnseignant.objects.create(
            enseignant=enseignant,
            date=date(2025, 1, 10),
            statut='PRESENT',
            heure_arrivee=time(8, 15),
            heure_depart=time(16, 45),
            pointe_par=self.user,
        )

        self.assertEqual(presence.heures_travaillees, Decimal('8.5'))
        self.assertTrue(
            _actualiser_salaire_ouvert(enseignant, presence.date, self.user)
        )
        etat = EtatSalaire.objects.get(enseignant=enseignant, periode=self.periode)
        self.assertEqual(etat.total_heures, Decimal('8.50'))
        self.assertEqual(etat.salaire_base, Decimal('85000.00'))
        self.assertEqual(etat.libelle_source_heures, 'Pointages arrivée / départ')

    def test_saisie_mensuelle_globale_calcule_et_remplace_les_pointages(self):
        enseignant = self.creer_secondaire()
        self.ajouter_heures(enseignant, ['8', '8'])
        etat = EtatSalaire.objects.create(
            enseignant=enseignant,
            periode=self.periode,
            heures_mensuelles_saisies=Decimal('72'),
            salaire_base=Decimal('0'),
            salaire_net=Decimal('0'),
            calcule_par=self.user,
        )

        recalculer_salaire_enseignant(
            enseignant, self.periode, self.user, etat=etat
        )

        etat.refresh_from_db()
        self.assertEqual(etat.total_heures, Decimal('72.00'))
        self.assertEqual(etat.salaire_base, Decimal('720000.00'))
        self.assertEqual(etat.libelle_source_heures, 'Saisie mensuelle globale')

    def test_effacer_la_saisie_mensuelle_revient_aux_pointages(self):
        enseignant = self.creer_secondaire()
        self.ajouter_heures(enseignant, ['8', '8'])
        calculer_salaires_periode(self.periode, self.user)
        etat = EtatSalaire.objects.get(enseignant=enseignant)
        self.client.force_login(self.user)

        response = self.client.post(
            reverse('salaires:modifier_etat_salaire', args=[etat.id]),
            {
                'heures_mensuelles_saisies': '72',
                'primes': '0',
                'deductions': '10000',
                'observations': '',
            },
        )
        self.assertEqual(response.status_code, 302)
        etat.refresh_from_db()
        self.assertEqual(etat.total_heures, Decimal('72.00'))
        self.assertEqual(etat.salaire_net, Decimal('710000.00'))

        self.client.post(
            reverse('salaires:modifier_etat_salaire', args=[etat.id]),
            {
                'heures_mensuelles_saisies': '',
                'primes': '0',
                'deductions': '0',
                'observations': '',
            },
        )
        etat.refresh_from_db()
        self.assertIsNone(etat.heures_mensuelles_saisies)
        self.assertEqual(etat.total_heures, Decimal('16.00'))
        self.assertEqual(etat.salaire_base, Decimal('160000.00'))

    def test_etat_valide_n_est_pas_modifie_par_un_nouveau_pointage(self):
        enseignant = self.creer_secondaire()
        self.ajouter_heures(enseignant, ['8'])
        calculer_salaires_periode(self.periode, self.user)
        etat = EtatSalaire.objects.get(enseignant=enseignant)
        etat.valide = True
        etat.save()
        PresenceEnseignant.objects.create(
            enseignant=enseignant,
            date=date(2025, 1, 2),
            statut='PRESENT',
            heures_travaillees=Decimal('8'),
            pointe_par=self.user,
        )

        resultat = recalculer_salaire_enseignant(
            enseignant, self.periode, self.user
        )

        self.assertIsNone(resultat)
        etat.refresh_from_db()
        self.assertEqual(etat.total_heures, Decimal('8.00'))

    def test_repartition_par_classe_est_proportionnelle_et_utilise_nombre_semaines(self):
        enseignant = self.creer_secondaire()
        classe_1 = self.creer_classe('7ème A')
        classe_2 = self.creer_classe('7ème B')
        AffectationClasse.objects.create(
            enseignant=enseignant,
            classe=classe_1,
            heures_par_semaine=Decimal('10'),
            date_debut=date(2024, 9, 1),
        )
        AffectationClasse.objects.create(
            enseignant=enseignant,
            classe=classe_2,
            heures_par_semaine=Decimal('20'),
            date_debut=date(2024, 9, 1),
        )
        self.ajouter_heures(enseignant, ['8', '8', '8', '6'])

        calculer_salaires_periode(self.periode, self.user)

        details = list(
            DetailHeuresClasse.objects.filter(etat_salaire__enseignant=enseignant)
            .select_related('affectation_classe__classe')
            .order_by('affectation_classe__classe__nom')
        )
        self.assertEqual([d.heures_realisees for d in details], [Decimal('10.00'), Decimal('20.00')])
        self.assertEqual([d.heures_prevues for d in details], [Decimal('40.00'), Decimal('80.00')])

    def test_affectation_historique_de_la_periode_est_utilisee(self):
        enseignant = self.creer_secondaire()
        classe = self.creer_classe('Historique')
        affectation = AffectationClasse.objects.create(
            enseignant=enseignant,
            classe=classe,
            heures_par_semaine=Decimal('10'),
            date_debut=date(2024, 9, 1),
            date_fin=date(2025, 1, 31),
            actif=False,
        )
        self.ajouter_heures(enseignant, ['8'])

        calculer_salaires_periode(self.periode, self.user)

        detail = DetailHeuresClasse.objects.get(etat_salaire__enseignant=enseignant)
        self.assertEqual(detail.affectation_classe, affectation)
        self.assertEqual(detail.heures_realisees, Decimal('8.00'))

    def test_secondaire_sans_affectation_ne_cree_pas_de_detail_invalide(self):
        enseignant = self.creer_secondaire()
        self.ajouter_heures(enseignant, ['8'])

        calculer_salaires_periode(self.periode, self.user)

        etat = EtatSalaire.objects.get(enseignant=enseignant)
        self.assertEqual(etat.salaire_base, Decimal('80000.00'))
        self.assertFalse(etat.details_heures.exists())

    def test_salaire_fixe_est_proratise_et_embauche_apres_periode_est_exclue(self):
        milieu_mois = self.creer_fixe(nom='MILIEU', date_embauche=date(2025, 1, 16))
        apres_periode = self.creer_fixe(nom='APRES', date_embauche=date(2025, 2, 1))
        EtatSalaire.objects.create(
            enseignant=apres_periode,
            periode=self.periode,
            salaire_base=Decimal('310000'),
            salaire_net=Decimal('310000'),
            calcule_par=self.user,
        )

        calculer_salaires_periode(self.periode, self.user)

        etat = EtatSalaire.objects.get(enseignant=milieu_mois)
        self.assertEqual(etat.salaire_base, Decimal('160000.00'))
        self.assertFalse(EtatSalaire.objects.filter(enseignant=apres_periode).exists())

    def test_cadre_reste_au_salaire_fixe_meme_avec_des_pointages(self):
        cadre = Enseignant.objects.create(
            nom='CADRE',
            prenoms='Administration',
            ecole=self.ecole,
            type_enseignant=TypeEnseignant.ADMINISTRATEUR,
            statut='ACTIF',
            salaire_fixe=Decimal('1500000'),
            date_embauche=date(2024, 1, 1),
            cree_par=self.user,
        )
        self.ajouter_heures(cadre, ['8', '8'])

        calculer_salaires_periode(self.periode, self.user)

        etat = EtatSalaire.objects.get(enseignant=cadre)
        self.assertIsNone(etat.total_heures)
        self.assertEqual(etat.salaire_base, Decimal('1500000.00'))
        self.assertEqual(etat.libelle_source_heures, 'Salaire fixe')

    def test_secondaire_peut_etre_cree_avec_le_seul_taux_horaire(self):
        form = EnseignantForm(
            data={
                'nom': 'SANS VOLUME',
                'prenoms': 'Horaire',
                'telephone': '',
                'adresse': '',
                'ecole': self.ecole.id,
                'type_enseignant': TypeEnseignant.SECONDAIRE,
                'statut': 'ACTIF',
                'taux_horaire': '10000',
                'salaire_fixe': '',
                'heures_mensuelles': '',
                'date_embauche': '2025-01-01',
            },
            user=self.user,
        )

        self.assertTrue(form.is_valid(), form.errors)

    def test_calcul_complet_est_atomique(self):
        self.creer_fixe(nom='PREMIER')
        self.creer_fixe(nom='SECOND')
        from salaires import services

        calcul_original = services._calculer_etat_enseignant
        appels = {'nombre': 0}

        def echouer_au_second(*args, **kwargs):
            appels['nombre'] += 1
            if appels['nombre'] == 2:
                raise RuntimeError('erreur simulée')
            return calcul_original(*args, **kwargs)

        with patch('salaires.services._calculer_etat_enseignant', side_effect=echouer_au_second):
            with self.assertRaises(RuntimeError):
                calculer_salaires_periode(self.periode, self.user)

        self.assertEqual(EtatSalaire.objects.count(), 0)

    def test_taux_horaire_reste_fige_apres_modification_enseignant(self):
        enseignant = self.creer_secondaire()
        self.ajouter_heures(enseignant, ['8'])
        calculer_salaires_periode(self.periode, self.user)
        etat = EtatSalaire.objects.get(enseignant=enseignant)

        enseignant.taux_horaire = Decimal('20000')
        enseignant.save()
        etat.refresh_from_db()

        self.assertEqual(etat.taux_horaire_applique, Decimal('10000.00'))
        self.assertEqual(etat.salaire_base, Decimal('80000.00'))

    def test_montants_et_heures_negatifs_sont_refuses_par_les_modeles(self):
        with self.assertRaises(ValidationError):
            self.creer_fixe(salaire='-100000')
        with self.assertRaises(ValidationError):
            self.creer_secondaire(taux='-10000')

        enseignant = self.creer_fixe()
        with self.assertRaises(ValidationError):
            EtatSalaire.objects.create(
                enseignant=enseignant,
                periode=self.periode,
                salaire_base=Decimal('100000'),
                primes=Decimal('-1'),
                salaire_net=Decimal('0'),
                calcule_par=self.user,
            )
        with self.assertRaises(ValidationError):
            EtatSalaire.objects.create(
                enseignant=enseignant,
                periode=self.periode,
                salaire_base=Decimal('100000'),
                deductions=Decimal('-1'),
                salaire_net=Decimal('0'),
                calcule_par=self.user,
            )
        with self.assertRaises(ValidationError):
            PresenceEnseignant.objects.create(
                enseignant=enseignant,
                date=date(2025, 1, 1),
                heures_travaillees=Decimal('-1'),
                pointe_par=self.user,
            )

        secondaire = self.creer_secondaire(nom='AFFECTATION')
        with self.assertRaises(ValidationError):
            AffectationClasse.objects.create(
                enseignant=secondaire,
                classe=self.creer_classe('Classe négative'),
                heures_par_semaine=Decimal('-1'),
                date_debut=date(2025, 1, 1),
            )
        with self.assertRaises(ValidationError):
            PresenceEnseignant.objects.create(
                enseignant=enseignant,
                date=date(2025, 1, 2),
                heures_travaillees=Decimal('25'),
                pointe_par=self.user,
            )

    def test_retenues_superieures_au_brut_sont_refusees(self):
        enseignant = self.creer_fixe()
        with self.assertRaises(ValidationError):
            EtatSalaire.objects.create(
                enseignant=enseignant,
                periode=self.periode,
                salaire_base=Decimal('100000'),
                primes=Decimal('10000'),
                deductions=Decimal('110001'),
                salaire_net=Decimal('0'),
                calcule_par=self.user,
            )

    def test_presence_presente_sans_horaires_ne_fait_pas_planter_le_formulaire(self):
        enseignant = self.creer_fixe()
        form = PresenceForm(
            data={
                'enseignant': enseignant.id,
                'date': '2025-01-10',
                'statut': 'PRESENT',
                'heure_arrivee': '',
                'heure_depart': '',
                'heures_travaillees': '',
                'observations': '',
                'justifie': '',
            },
            ecole=self.ecole,
        )
        self.assertTrue(form.is_valid(), form.errors)

    def test_pointage_partiel_est_refuse(self):
        enseignant = self.creer_fixe()
        with self.assertRaises(ValidationError):
            PresenceEnseignant.objects.create(
                enseignant=enseignant,
                date=date(2025, 1, 1),
                heure_arrivee=time(8, 0),
                heure_depart=None,
                pointe_par=self.user,
            )

    def test_absence_avec_heures_est_refusee(self):
        enseignant = self.creer_fixe()
        with self.assertRaises(ValidationError):
            PresenceEnseignant.objects.create(
                enseignant=enseignant,
                date=date(2025, 1, 1),
                statut='ABSENT',
                heures_travaillees=Decimal('8'),
                pointe_par=self.user,
            )

    def test_interface_modifie_primes_retenues_et_observations(self):
        enseignant = self.creer_fixe(salaire='300000')
        calculer_salaires_periode(self.periode, self.user)
        etat = EtatSalaire.objects.get(enseignant=enseignant)
        self.client.force_login(self.user)

        response = self.client.post(
            reverse('salaires:modifier_etat_salaire', args=[etat.id]),
            {
                'primes': '50000',
                'deductions': '20000',
                'observations': 'Ajustement test',
            },
        )

        self.assertEqual(response.status_code, 302)
        etat.refresh_from_db()
        self.assertEqual(etat.primes, Decimal('50000.00'))
        self.assertEqual(etat.deductions, Decimal('20000.00'))
        self.assertEqual(etat.salaire_net, Decimal('330000.00'))
        self.assertEqual(etat.observations, 'Ajustement test')
