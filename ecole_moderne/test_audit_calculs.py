"""Régressions des calculs audités le 15 septembre 2026, données fictives."""
from datetime import date, datetime
from decimal import Decimal
from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.test import TestCase, SimpleTestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from paiements.tests import test_school_filtering as payment_fixtures
from paiements.tests.support import MIDDLEWARE_SANS_LICENCE
from paiements.models import Paiement, PaiementRemise, RemiseReduction, EcheancierPaiement
from paiements.allocation import get_payment_allocation
from eleves.models import Classe, Eleve, Ecole
from rapports.views import collecter_donnees_journalieres
from rapports.utils import collecter_donnees_periode
from salaires import tests as salary_fixtures
from salaires.models import EtatSalaire, AvanceSalaire, PeriodeSalaire
from salaires.services import repartir_heures, calculer_etat_salaire
from notes import test_bonus_suivi as notes_fixtures
from notes.models import MatiereNote, NoteMensuelle, CompositionNote
from notes.calculs_moyennes import calculer_moyennes_classe_optimise, calculer_classement_classe, calculer_moyenne_matiere
from bus import test_suivi_classes as bus_fixtures
from bus.models import AbonnementBus, GrilleTarifaireBus


@override_settings(MIDDLEWARE=MIDDLEWARE_SANS_LICENCE)
class AuditRapportsCalculs(TestCase):
    def setUp(self):
        payment_fixtures.SchoolFilteringTests.setUp(self)
        self.user1.refresh_from_db()
        profil = self.user1.profil
        profil.allowed_menus = ['rapports', 'paiements']
        profil.save()
        self.client.force_login(self.user1)

    def remise(self, montant=5000, paiement=None):
        remise = RemiseReduction.objects.create(
            nom='Audit remise ' + str(RemiseReduction.objects.count()),
            type_remise='MONTANT_FIXE', valeur=montant, motif='AUTRE',
            date_debut=date(2023, 1, 1), date_fin=date(2030, 12, 31))
        return PaiementRemise.objects.create(
            paiement=paiement or self.paiement1, remise=remise, montant_remise=montant)

    def echeancier(self, annee, **kwargs):
        return EcheancierPaiement.objects.create(
            eleve=self.eleve1, annee_scolaire=annee,
            date_echeance_inscription=date(2024, 9, 1),
            date_echeance_tranche_1=date(2024, 10, 1),
            date_echeance_tranche_2=date(2025, 1, 1),
            date_echeance_tranche_3=date(2025, 4, 1), **kwargs)

    def rapport_remises(self, **params):
        return self.client.get(reverse('rapports:rapport_remises'), {
            'date_debut': '2024-09-01', 'date_fin': '2024-09-30', **params})

    def test_remises_ne_comptent_pas_deux_fois_le_meme_recu(self):
        self.remise()
        self.remise()
        # Deux reçus de même montant doivent en revanche compter chacun.
        paiement = Paiement.objects.create(eleve=self.eleve1, type_paiement=self.type_insc,
            mode_paiement=self.mode_espece, montant=30000, statut='VALIDE',
            date_paiement=date(2024, 9, 11))
        self.remise(paiement=paiement)
        response = self.rapport_remises()
        self.assertEqual(response.status_code, 200)
        stats = response.context['stats_remises']
        self.assertEqual(stats['total_montants_finals'], 60000)
        self.assertEqual(stats['total_remises'], 15000)
        self.assertEqual(stats['nombre_paiements_avec_remise'], 2)

    def test_rapport_ne_soustrait_pas_remises_au_net_deja_encaisse(self):
        self.remise()
        response = self.rapport_remises()
        self.assertEqual(response.context['stats_remises'].get('montant_avant_remises'), 35000)
        self.assertNotContains(response, 'Différence (Final - Remise)')

    def test_dates_remises_invalides_ne_provoquent_pas_erreur_500(self):
        for params in ({'date_debut': 'invalide'}, {'date_fin': '2024-02-30'},
                       {'date_debut': '2025-01-01', 'date_fin': '2024-01-01'}):
            with self.subTest(params=params):
                self.assertEqual(self.rapport_remises(**params).status_code, 400)

    def test_soldes_journalier_et_periode_deduisent_remises_cumulees(self):
        self.remise(10000)
        for donnees in (
            collecter_donnees_journalieres(date(2024, 9, 10), self.user1),
            collecter_donnees_periode(date(2024, 9, 1), date(2024, 9, 30), 'MENSUEL', self.user1),
        ):
            ecole = donnees['ecoles'][self.ecole1.pk]
            self.assertEqual(ecole['paiements']['reste_a_payer'], 90000)
            self.assertEqual(ecole['classes'][0]['reste'], 90000)
            self.assertEqual(ecole['classes'][0]['remises'], 10000)

    def test_soldes_prennent_les_remises_hors_periode_du_meme_echeancier(self):
        self.remise(10000)
        p = Paiement.objects.create(eleve=self.eleve1, type_paiement=self.type_insc,
            mode_paiement=self.mode_espece, montant=10000, statut='VALIDE',
            date_paiement=date(2024, 10, 10))
        self.echeancier1.tranche_1_payee = 10000
        self.echeancier1.save()
        data = collecter_donnees_journalieres(p.date_paiement, self.user1)['ecoles'][self.ecole1.pk]
        self.assertEqual(data['paiements']['total_remises'], 0)
        self.assertEqual(data['paiements']['reste_a_payer'], 80000)
        self.assertEqual(data['classes'][0]['remises'], 10000)

    def test_annee_echeancier_provient_du_recu_pas_du_calendrier(self):
        self.paiement1.date_paiement = date(2026, 9, 10)
        self.paiement1.save()
        for data in (
            collecter_donnees_journalieres(date(2026, 9, 10), self.user1),
            collecter_donnees_periode(date(2026, 9, 1), date(2026, 9, 30), 'MENSUEL', self.user1),
        ):
            self.assertEqual(data['ecoles'][self.ecole1.pk]['paiements']['total_du_concernes'], 130000)

    def test_plusieurs_annees_un_eleve_effectif_unique(self):
        self.echeancier('2023-2024', frais_inscription_du=10000)
        Paiement.objects.create(eleve=self.eleve1, type_paiement=self.type_insc,
            mode_paiement=self.mode_espece, montant=10000, statut='VALIDE',
            annee_scolaire='2023-2024', date_paiement=date(2024, 7, 1))
        data = collecter_donnees_periode(date(2024, 7, 1), date(2024, 9, 30), 'PERSONNALISE', self.user1)
        classe = data['ecoles'][self.ecole1.pk]['classes'][0]
        self.assertEqual(classe['total_du'], 140000)
        self.assertEqual(classe['effectif'], 1)

    def test_allocation_recu_historique_apres_changement_annee(self):
        nouvelle = Classe.objects.create(ecole=self.ecole1, nom='Suivante',
            niveau='PRIMAIRE_2', annee_scolaire='2025-2026')
        self.echeancier('2025-2026', frais_inscription_du=10000, tranche_1_due=50000)
        Eleve.objects.filter(pk=self.eleve1.pk).update(classe=nouvelle)
        self.paiement1.refresh_from_db()
        allocation = get_payment_allocation(self.paiement1)
        self.assertEqual(allocation['inscription'], 30000)
        self.assertEqual(allocation['tranche_1'], 0)

    def test_depense_payee_reste_dans_rapports_et_ecole(self):
        from depenses.models import CategorieDepense, Fournisseur, Depense
        depense = Depense.objects.create(
            numero_facture='AUDIT-TTC', libelle='Fictive', description='Audit',
            categorie=CategorieDepense.objects.create(nom='Audit', code='AUD'),
            fournisseur=Fournisseur.objects.create(nom='Audit fournisseur', type_fournisseur='ENTREPRISE'),
            montant_ht=10000, taux_tva=18, statut='PAYEE', cree_par=self.user1,
            date_facture=date(2024, 9, 10), date_echeance=date(2024, 9, 30))
        for data in (
            collecter_donnees_journalieres(date(2024, 9, 10), self.user1),
            collecter_donnees_periode(date(2024, 9, 1), date(2024, 9, 30), 'MENSUEL', self.user1),
        ):
            self.assertEqual(data['depenses_globales']['montant_total'], 11800)


    def test_soldes_excluent_remises_en_attente_et_autres_annees(self):
        self.remise(5000, self.paiement2)
        ancien = Paiement.objects.create(eleve=self.eleve1, type_paiement=self.type_insc,
            mode_paiement=self.mode_espece, montant=1000, statut='VALIDE',
            annee_scolaire='2023-2024', date_paiement=date(2024, 1, 1))
        attente = Paiement.objects.create(eleve=self.eleve1, type_paiement=self.type_insc,
            mode_paiement=self.mode_espece, montant=1000, statut='EN_ATTENTE',
            date_paiement=date(2024, 9, 10))
        self.remise(10000, ancien)
        self.remise(10000, attente)
        for data in (
            collecter_donnees_journalieres(date(2024, 9, 10), self.user1),
            collecter_donnees_periode(date(2024, 9, 1), date(2024, 9, 30), 'MENSUEL', self.user1),
        ):
            self.assertEqual(set(data['ecoles']), {self.ecole1.pk})
            row = data['ecoles'][self.ecole1.pk]['classes'][0]
            self.assertEqual(row['remises'], 0)
            self.assertEqual(row['reste'], 100000)

    def test_soldes_sans_compensation_entre_annees_et_sans_annee_non_concernee(self):
        ancien = self.echeancier('2023-2024', frais_inscription_du=10000,
            frais_inscription_paye=20000)
        self.echeancier('2022-2023', frais_inscription_du=900000)
        paiement = Paiement.objects.create(eleve=self.eleve1, type_paiement=self.type_insc,
            mode_paiement=self.mode_espece, montant=20000, statut='VALIDE',
            annee_scolaire=ancien.annee_scolaire, date_paiement=date(2024, 9, 10))
        data = collecter_donnees_journalieres(paiement.date_paiement, self.user1)
        row = data['ecoles'][self.ecole1.pk]['classes'][0]
        self.assertEqual(row['total_du'], 140000)
        self.assertEqual(row['reste'], 100000)
        self.assertEqual(row['effectif'], 1)




class AuditArrondisHeures(SimpleTestCase):
    def test_repartition_petits_totaux_ne_devient_jamais_negative(self):
        for total in ('0.01', '0.03', '1.00', '12.37'):
            for n in range(1, 12):
                lignes = repartir_heures(Decimal(total), [(i, Decimal(1)) for i in range(n)])
                self.assertTrue(all(h >= 0 for _, _, h in lignes), (total, n, lignes))
                self.assertEqual(sum(h for _, _, h in lignes), Decimal(total))


@override_settings(MIDDLEWARE=MIDDLEWARE_SANS_LICENCE)
class AuditSalairesCalculs(TestCase):
    def setUp(self):
        salary_fixtures.MoteurPaieTests.setUp(self)
        self.enseignant = salary_fixtures.MoteurPaieTests.creer_fixe(self)
        self.etat, _ = calculer_etat_salaire(self.enseignant, self.periode, self.user)

    def test_rapport_periode_sans_validation_n_inclut_pas_anciens_salaires(self):
        self.etat.valide = True
        self.etat.date_validation = timezone.make_aware(datetime(2026, 7, 1, 12))
        self.etat.save()
        data = collecter_donnees_periode(date(2026, 8, 1), date(2026, 8, 31), 'MENSUEL', self.user)
        self.assertEqual(data['ecoles'][self.ecole.pk]['salaires']['montant_total'], 0)

    def test_dernier_jour_rapport_inclus_sans_anciens_salaires(self):
        self.etat.valide = True
        self.etat.date_validation = timezone.make_aware(datetime(2026, 7, 31, 18))
        self.etat.save()
        ancienne = PeriodeSalaire.objects.create(ecole=self.ecole, mois=6, annee=2026, cree_par=self.user)
        EtatSalaire.objects.create(enseignant=self.enseignant, periode=ancienne,
            salaire_base=800000, salaire_net=800000, valide=True, calcule_par=self.user,
            date_validation=timezone.make_aware(datetime(2026, 6, 30, 12)))
        data = collecter_donnees_periode(date(2026, 7, 1), date(2026, 7, 31), 'MENSUEL', self.user)
        self.assertEqual(data['ecoles'][self.ecole.pk]['salaires']['montant_total'], 1000000)

    def test_avance_validee_ne_peut_pas_etre_deplacee_pour_changer_ancien_net(self):
        avance = AvanceSalaire.objects.create(enseignant=self.enseignant, periode=self.periode, montant=200000)
        self.etat.refresh_from_db()
        self.etat.valide = True
        self.etat.save()
        autre = PeriodeSalaire.objects.create(ecole=self.ecole, mois=8, annee=2026, cree_par=self.user)
        avance.periode = autre
        with self.assertRaises(ValidationError):
            avance.save()
        avance.refresh_from_db()
        self.etat.refresh_from_db()
        self.assertEqual(avance.periode_id, self.periode.pk)
        self.assertEqual(self.etat.salaire_net, 800000)


    def test_deplacement_avance_ouverte_recalcule_les_deux_periodes(self):
        avance = AvanceSalaire.objects.create(enseignant=self.enseignant,
            periode=self.periode, montant=200000)
        autre = PeriodeSalaire.objects.create(ecole=self.ecole, mois=8, annee=2026, cree_par=self.user)
        etat_autre, _ = calculer_etat_salaire(self.enseignant, autre, self.user)
        avance.periode = autre
        avance.save()
        self.etat.refresh_from_db()
        etat_autre.refresh_from_db()
        self.assertEqual(self.etat.salaire_net, 1000000)
        self.assertEqual(etat_autre.salaire_net, 800000)

    def test_echec_recalcul_avance_annule_creation_et_suppression(self):
        from unittest.mock import patch
        with patch('salaires.services.synchroniser_avances_etat', side_effect=RuntimeError('test')):
            with self.assertRaises(RuntimeError):
                AvanceSalaire.objects.create(enseignant=self.enseignant,
                    periode=self.periode, montant=200000)
        self.assertFalse(AvanceSalaire.objects.exists())
        avance = AvanceSalaire.objects.create(enseignant=self.enseignant,
            periode=self.periode, montant=200000)
        pk = avance.pk
        with patch('salaires.services.synchroniser_avances_etat', side_effect=RuntimeError('test')):
            with self.assertRaises(RuntimeError):
                avance.delete()
        self.assertTrue(AvanceSalaire.objects.filter(pk=pk).exists())
        self.etat.refresh_from_db()
        self.assertEqual(self.etat.salaire_net, 800000)




class AuditNotesCalculs(TestCase):
    suivi = notes_fixtures.BonusSuiviTests.suivi

    def setUp(self):
        notes_fixtures.BonusSuiviTests.setUp(self)
        Ecole.objects.filter(pk=self.ecole1.pk).update(bonus_suivi_actif=False)
        self.autre = Eleve.objects.create(classe=self.classe1, matricule='AUD-NOTE', nom='Autre', prenom='Test', sexe='M')
        self.math = MatiereNote.objects.create(classe=self.cn, nom='Mathématiques', code='MAT', coefficient=2)
        NoteMensuelle.objects.create(eleve=self.eleve1, matiere=self.math, annee_scolaire=self.annee, mois='OCTOBRE', note=4)
        cache.clear()

    def test_cache_respecte_selection_eleves_et_matieres(self):
        calculer_moyennes_classe_optimise([self.eleve1], [self.matiere], 'OCTOBRE')
        autre = calculer_moyennes_classe_optimise([self.autre], [self.matiere], 'OCTOBRE')
        self.assertEqual(set(autre), {self.autre.pk})
        complet = calculer_moyennes_classe_optimise([self.eleve1], [self.matiere, self.math], 'OCTOBRE')
        self.assertEqual(complet[self.eleve1.pk]['moyenne_generale'], 8)

    def test_cache_classement_respecte_selection(self):
        calculer_classement_classe([self.eleve1], [self.matiere], 'OCTOBRE')
        resultat = calculer_classement_classe([self.eleve1, self.autre], [self.matiere], 'OCTOBRE')
        self.assertEqual(resultat['total_eleves'], 2)
        self.assertEqual(set(resultat['rang_map']), {self.eleve1.pk, self.autre.pk})

    def test_cache_classement_recalcule_apres_modification_note(self):
        calculer_classement_classe([self.eleve1], [self.matiere], 'OCTOBRE')
        self.note.note = 5
        self.note.save()
        resultat = calculer_classement_classe([self.eleve1], [self.matiere], 'OCTOBRE')
        self.assertEqual(resultat['moyennes_par_eleve'][self.eleve1.pk], 5)

    def test_composition_absente_identique_en_selection_et_en_classe(self):
        CompositionNote.objects.create(eleve=self.autre, matiere=self.matiere,
            periode='TRIMESTRE_1', annee_scolaire=self.annee, note=16)
        individuel = calculer_moyenne_matiere(self.eleve1, self.matiere, 'TRIMESTRE_1', 'trimestre')
        groupe = calculer_moyennes_classe_optimise([self.eleve1], [self.matiere], 'TRIMESTRE_1', 'trimestre', use_cache=False)
        self.assertEqual(individuel['note_composition'], 0)
        self.assertEqual(groupe[self.eleve1.pk]['moyenne_generale'], 4.8)

    def test_absence_semestre_ne_reprend_pas_note_ancien_trimestre(self):
        CompositionNote.objects.create(eleve=self.eleve1, matiere=self.matiere,
            periode='TRIMESTRE_1', annee_scolaire=self.annee, note=16)
        CompositionNote.objects.create(eleve=self.eleve1, matiere=self.matiere,
            periode='SEMESTRE_1', annee_scolaire=self.annee, note=None, absent=True)
        resultat = calculer_moyenne_matiere(self.eleve1, self.matiere, 'SEMESTRE_1', 'semestre')
        self.assertEqual(resultat['note_composition'], 0)


    def test_cache_recalcule_apres_modification_coefficient(self):
        calculer_classement_classe([self.eleve1], [self.matiere, self.math], 'OCTOBRE')
        self.math.coefficient = 6
        self.math.save()
        resultat = calculer_classement_classe([self.eleve1], [self.matiere, self.math], 'OCTOBRE')
        self.assertEqual(resultat['moyennes_par_eleve'][self.eleve1.pk], 6)




@override_settings(MIDDLEWARE=MIDDLEWARE_SANS_LICENCE)
class AuditTransportCalculs(TestCase):
    versement = bus_fixtures.SuiviBusClasseTests.versement

    def setUp(self):
        bus_fixtures.SuiviBusClasseTests.setUp(self)
        self.user.refresh_from_db()
        profil = self.user.profil
        profil.allowed_menus = ['bus', 'rapports']
        profil.save()

    def rapport(self):
        response = self.client.get(reverse('rapports:rapport_transport'))
        self.assertEqual(response.status_code, 200)
        return response

    def test_transport_deux_versements_un_abonne_tarif_annuel_unique(self):
        self.versement()
        self.versement(periodicite='ANNUEL', montant=100000)
        data = self.rapport().context['totals']
        self.assertEqual(data['nb_abonnes'], 1)
        self.assertEqual(data['total_du'], 400000)
        self.assertEqual(data['total_paye'], 150000)
        self.assertEqual(data['reste'], 250000)

    def test_transport_suspendu_ne_supprime_pas_argent_deja_recu(self):
        self.versement(statut='SUSPENDU', montant=50000)
        self.assertEqual(self.rapport().context['totals']['total_paye'], 50000)

    def test_transport_annee_active_et_ecole_uniquement(self):
        self.versement()
        self.versement(eleve=self.autre_eleve, grille=self.autre_grille, montant=80000)
        ancienne = GrilleTarifaireBus.objects.create(ecole=self.ecole, zone='Ancienne',
            annee_scolaire='2025-2026', tranche_1=100000, tranche_2=100000, tranche_3=100000)
        self.versement(grille=ancienne, montant=200000)
        data = self.rapport().context
        self.assertEqual(len(data['lignes']), 1)
        self.assertEqual(data['totals']['total_paye'], 50000)
        self.assertEqual(data['totals']['total_du'], 400000)

    def test_transport_sans_grille_ne_presente_pas_un_faux_solde(self):
        self.versement(grille=None, montant=50000)
        data = self.rapport().context
        self.assertEqual(data['totals']['total_paye'], 50000)
        self.assertIsNone(data['lignes'][0]['reste'])
        self.assertIsNone(data['totals']['reste'])

    def test_transport_sans_ecole_ne_divulgue_aucun_montant(self):
        self.versement(eleve=self.autre_eleve, grille=self.autre_grille)
        profil = self.user.profil
        profil.ecole = None
        profil.save()
        self.assertEqual(self.rapport().context['lignes'], [])


    def test_transport_modification_suppression_et_transfert_recalculent(self):
        a = self.versement()
        b = self.versement()
        a.montant = 70000
        a.save()
        self.assertEqual(self.rapport().context['totals']['reste'], 280000)
        b.delete()
        self.assertEqual(self.rapport().context['totals']['reste'], 330000)
        nouvelle = Classe.objects.create(ecole=self.ecole, nom='Classe B',
            niveau=self.classe.niveau, annee_scolaire=self.classe.annee_scolaire)
        self.eleve.classe = nouvelle
        self.eleve.save()
        data = self.rapport().context
        self.assertEqual(len(data['lignes']), 1)
        self.assertEqual(data['lignes'][0]['classe'], nouvelle.nom)
        self.assertEqual(data['totals']['reste'], 330000)
