"""Les encaissements de juillet-août appartiennent à l'année qui commence.

Les réinscriptions et premiers versements sont encaissés avant la rentrée de
septembre. L'ancienne règle (coupure au 1er septembre) les étiquetait sur
l'année qui s'achève, alors que la classe et l'échéancier de l'élève portaient
déjà l'année suivante. Conséquence chez le client après mise à jour : ces
paiements disparaissaient de la liste, ne comptaient dans aucun solde et les
reçus annonçaient un dû intégral à des familles à jour.
"""

from datetime import date
from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse
from reportlab.pdfgen.canvas import Canvas

from eleves.models import Classe, Ecole, Eleve, GrilleTarifaire, Responsable
from paiements.models import (
    EcheancierPaiement,
    ModePaiement,
    Paiement,
    TypePaiement,
)
from paiements.payment_engine import (
    annee_scolaire_coherente,
    realigner_annees_paiements,
    school_year_from_date,
    situation_echeancier,
)
from paiements.tests.support import TEST_MIDDLEWARE
from utilisateurs.models import Profil


class RegleAnneeScolaireTests(TestCase):
    """La date seule ne doit plus renvoyer un versement d'été en arrière."""

    def test_versement_de_juillet_appartient_a_l_annee_qui_commence(self):
        self.assertEqual(school_year_from_date(date(2026, 7, 1)), '2026-2027')
        self.assertEqual(school_year_from_date(date(2026, 8, 15)), '2026-2027')

    def test_versement_du_printemps_reste_sur_l_annee_en_cours(self):
        self.assertEqual(school_year_from_date(date(2026, 6, 30)), '2025-2026')
        self.assertEqual(school_year_from_date(date(2027, 1, 10)), '2026-2027')

    def test_correction_de_date_dans_la_periode_conserve_l_annee(self):
        self.assertEqual(
            annee_scolaire_coherente('2026-2027', date(2026, 8, 20)),
            '2026-2027',
        )
        self.assertEqual(
            annee_scolaire_coherente('2026-2027', date(2027, 4, 2)),
            '2026-2027',
        )

    def test_correction_de_date_hors_periode_recalcule_l_annee(self):
        self.assertEqual(
            annee_scolaire_coherente('2026-2027', date(2028, 2, 3)),
            '2027-2028',
        )

    def test_annee_absente_deduite_de_la_date(self):
        self.assertEqual(
            annee_scolaire_coherente('', date(2026, 8, 15)), '2026-2027'
        )


class _DossierRentree(TestCase):
    """Élève inscrit en 2026-2027, réinscription réglée le 15/08/2026."""

    def setUp(self):
        for cible, valeur in (
            (
                'ecole_moderne.licence_middleware._check_license_cached',
                {'valid': True, 'trial': False, 'days_left': 999},
            ),
            (
                'ecole_moderne.licence_middleware._check_integrity_cached',
                {'valid': True, 'reason': ''},
            ),
        ):
            correctif = patch(cible, return_value=valeur)
            correctif.start()
            self.addCleanup(correctif.stop)

        self.ecole = Ecole.objects.create(
            nom='Groupe Scolaire Rentrée', adresse='Conakry',
            telephone='+224620000030', directeur='Direction',
        )
        self.classe = Classe.objects.create(
            ecole=self.ecole, nom='7ème année', niveau='COLLEGE_7',
            annee_scolaire='2026-2027',
        )
        responsable = Responsable.objects.create(
            prenom='Parent', nom='Rentrée', relation='PERE',
            telephone='+224620000031', adresse='Conakry',
        )
        self.eleve = Eleve.objects.create(
            matricule='CL1-001', prenom='Binta', nom='Diallo', sexe='F',
            date_naissance=date(2013, 3, 2), lieu_naissance='Conakry',
            classe=self.classe, date_inscription=date(2026, 8, 1),
            responsable_principal=responsable,
        )
        self.echeancier = EcheancierPaiement.objects.create(
            eleve=self.eleve, annee_scolaire='2026-2027',
            nature_frais='REINSCRIPTION',
            frais_inscription_du=Decimal('30000'),
            tranche_1_due=Decimal('500000'),
            tranche_2_due=Decimal('500000'),
            tranche_3_due=Decimal('500000'),
            date_echeance_inscription=date(2026, 8, 1),
            date_echeance_tranche_1=date(2026, 11, 15),
            date_echeance_tranche_2=date(2027, 1, 29),
            date_echeance_tranche_3=date(2027, 4, 1),
        )
        self.type_reinscription = TypePaiement.objects.create(nom='Réinscription')
        self.mode = ModePaiement.objects.create(nom='Espèces')

        User = get_user_model()
        self.comptable = User.objects.create_user(
            username='comptable', password='pass12345'
        )
        Profil.objects.update_or_create(
            user=self.comptable,
            defaults={
                'role': 'COMPTABLE',
                'ecole': self.ecole,
                'telephone': '+224620000032',
                'peut_consulter_rapports': True,
            },
        )

    def _paiement(self, annee=None, jour=date(2026, 8, 1)):
        paiement = Paiement.objects.create(
            eleve=self.eleve,
            type_paiement=self.type_reinscription,
            mode_paiement=self.mode,
            montant=Decimal('30000'),
            date_paiement=jour,
            statut='VALIDE',
        )
        if annee is not None and paiement.annee_scolaire != annee:
            Paiement.objects.filter(pk=paiement.pk).update(annee_scolaire=annee)
            paiement.refresh_from_db()
        return paiement


@override_settings(MIDDLEWARE=TEST_MIDDLEWARE)
class SoldeDeLaRentreeTests(_DossierRentree):
    """Un versement d'août doit compter dans le solde de l'année en cours."""

    def test_paiement_du_15_aout_compte_dans_l_echeancier(self):
        self._paiement()

        situation = situation_echeancier(
            self.echeancier, date_reference=date(2026, 8, 20)
        )

        self.assertEqual(situation['total_encaisse'], Decimal('30000'))
        self.assertEqual(situation['solde_restant'], Decimal('1500000'))

    def test_paiement_importe_sans_annee_compte_aussi(self):
        # Les dossiers importés ou synchronisés arrivent sans année : la
        # fenêtre de repli doit couvrir la période des réinscriptions.
        paiement = self._paiement(annee='')

        situation = situation_echeancier(
            self.echeancier, date_reference=date(2026, 8, 20)
        )

        self.assertEqual(paiement.annee_scolaire, '')
        self.assertEqual(situation['total_encaisse'], Decimal('30000'))


@override_settings(MIDDLEWARE=TEST_MIDDLEWARE)
class RealignementApresMiseAJourTests(_DossierRentree):
    """Réparation des paiements étiquetés sur l'année précédente."""

    def test_paiement_d_aout_est_recolle_sur_l_annee_de_l_echeancier(self):
        paiement = self._paiement(annee='2025-2026')

        corriges = realigner_annees_paiements(Paiement, EcheancierPaiement)

        paiement.refresh_from_db()
        self.assertEqual(corriges, 1)
        self.assertEqual(paiement.annee_scolaire, '2026-2027')

    def test_paiement_de_l_annee_precedente_reste_intact(self):
        # Un règlement de janvier appartient bien à l'année précédente :
        # la réparation ne doit surtout pas le déplacer.
        paiement = self._paiement(annee='2025-2026', jour=date(2026, 1, 20))

        corriges = realigner_annees_paiements(Paiement, EcheancierPaiement)

        paiement.refresh_from_db()
        self.assertEqual(corriges, 0)
        self.assertEqual(paiement.annee_scolaire, '2025-2026')

    def test_paiement_deja_bien_etiquete_n_est_pas_touche(self):
        paiement = self._paiement()

        corriges = realigner_annees_paiements(Paiement, EcheancierPaiement)

        paiement.refresh_from_db()
        self.assertEqual(corriges, 0)
        self.assertEqual(paiement.annee_scolaire, '2026-2027')


@override_settings(MIDDLEWARE=TEST_MIDDLEWARE)
class ListeEtCorrectionTests(_DossierRentree):
    """Le paiement saisi doit rester visible, y compris après correction."""

    def setUp(self):
        super().setUp()
        self.client.force_login(self.comptable)

    def test_paiement_d_aout_apparait_dans_la_liste(self):
        paiement = self._paiement()

        reponse = self.client.get(reverse('paiements:liste_paiements'))

        self.assertEqual(reponse.status_code, 200)
        self.assertIn(paiement, list(reponse.context['paiements']))
        self.assertEqual(reponse.context['paiements_hors_annee'], 0)

    def test_paiement_masque_par_l_annee_est_signale(self):
        self._paiement(annee='2025-2026')

        reponse = self.client.get(reverse('paiements:liste_paiements'))

        self.assertEqual(list(reponse.context['paiements']), [])
        self.assertEqual(reponse.context['paiements_hors_annee'], 1)
        self.assertContains(reponse, 'paiement(s) masqué(s)')

    def test_correction_de_date_ne_deplace_pas_l_annee(self):
        paiement = self._paiement()

        reponse = self.client.post(
            reverse(
                'paiements:modifier_paiement',
                kwargs={'paiement_id': paiement.id},
            ),
            {
                'type_paiement': self.type_reinscription.id,
                'mode_paiement': self.mode.id,
                'montant': '30000',
                'date_paiement': '2026-08-10',
                'reference_externe': '',
                'observations': '',
                'motif_modification': 'Date saisie à l’envers',
            },
        )

        paiement.refresh_from_db()
        self.assertEqual(reponse.status_code, 302)
        self.assertEqual(paiement.date_paiement, date(2026, 8, 10))
        self.assertEqual(paiement.annee_scolaire, '2026-2027')


@override_settings(MIDDLEWARE=TEST_MIDDLEWARE)
class EcheancesDeLaBonneAnneeTests(TestCase):
    """Une grille d'une autre année ne doit pas dater les échéances du passé."""

    def setUp(self):
        self.ecole = Ecole.objects.create(
            nom='Ecole grille', adresse='Conakry',
            telephone='+224620000040', directeur='Direction',
        )
        self.classe = Classe.objects.create(
            ecole=self.ecole, nom='7ème année', niveau='COLLEGE_7',
            annee_scolaire='2026-2027',
        )
        responsable = Responsable.objects.create(
            prenom='Parent', nom='Grille', relation='MERE',
            telephone='+224620000041', adresse='Conakry',
        )
        self.eleve = Eleve.objects.create(
            matricule='GRI-001', prenom='Sory', nom='Camara', sexe='M',
            date_naissance=date(2013, 5, 6), lieu_naissance='Conakry',
            classe=self.classe, date_inscription=date(2026, 8, 1),
            responsable_principal=responsable,
        )
        # Seule grille disponible : celle de l'année précédente, avec ses
        # dates d'échéance. Le moteur s'y replie pour les montants.
        GrilleTarifaire.objects.create(
            ecole=self.ecole, niveau='COLLEGE_7', annee_scolaire='2025-2026',
            frais_inscription=Decimal('30000'),
            frais_reinscription=Decimal('30000'),
            tranche_1=Decimal('500000'),
            tranche_2=Decimal('500000'),
            tranche_3=Decimal('500000'),
            date_echeance_tranche_2_defaut=date(2026, 1, 29),
        )

    def test_echeance_heritee_d_une_autre_annee_est_ecartee(self):
        from paiements.views import ensure_echeancier_for_eleve

        echeancier = ensure_echeancier_for_eleve(self.eleve)

        self.assertEqual(echeancier.annee_scolaire, '2026-2027')
        self.assertEqual(echeancier.tranche_2_due, Decimal('500000'))
        self.assertEqual(echeancier.date_echeance_tranche_2, date(2027, 3, 15))


@override_settings(MIDDLEWARE=TEST_MIDDLEWARE)
class PeriodeDesRapportsTests(_DossierRentree):
    """Le rapport d'une année doit couvrir ses réinscriptions d'été."""

    def setUp(self):
        super().setUp()
        self.client.force_login(self.comptable)

    def test_periode_commence_avec_les_reinscriptions(self):
        self._paiement()

        reponse = self.client.get(
            reverse('paiements:liste_eleves_soldes'), {'annee': '2026-2027'}
        )

        self.assertEqual(reponse.status_code, 200)
        self.assertEqual(reponse.context['periode_debut'], date(2026, 7, 1))


@override_settings(MIDDLEWARE=TEST_MIDDLEWARE)
class RecuEleveSansPhotoTests(_DossierRentree):
    """Le reçu d'un élève sans photo garde son cadre à initiales et son nom."""

    def setUp(self):
        super().setUp()
        self.client.force_login(self.comptable)

    def test_cadre_initiales_et_nom_sont_dessines(self):
        paiement = self._paiement()
        textes = []
        original = Canvas.drawCentredString

        def espion(canvas_obj, x, y, texte, *args, **kwargs):
            textes.append(texte)
            return original(canvas_obj, x, y, texte, *args, **kwargs)

        with patch.object(Canvas, 'drawCentredString', espion):
            reponse = self.client.get(
                reverse(
                    'paiements:generer_recu_pdf',
                    kwargs={'paiement_id': paiement.id},
                )
            )

        self.assertEqual(reponse.status_code, 200)
        self.assertIn('Pas de photo', textes)
        self.assertIn('BD', textes)
        self.assertIn(self.eleve.nom_complet, textes)
