"""Correction d'un paiement enregistré (/paiements/modifier/<id>/).

Cas remontés depuis la caisse : le nouveau montant était refusé alors qu'il
était correct (saisie « 175 000 », type de paiement désactivé entre-temps,
année scolaire absente sur un paiement ancien) et l'échéancier conservait
l'ancien montant après correction.
"""

from datetime import date
from decimal import Decimal
from unittest.mock import patch

from django.conf import settings
from django.contrib.auth.models import User
from django.test import TestCase, override_settings
from django.urls import reverse

from eleves.models import Classe, Ecole, Eleve, Responsable
from paiements.forms import MontantGNFField
from paiements.models import (
    EcheancierPaiement, ModePaiement, Paiement, PaiementRemise, TypePaiement,
)

# La vérification de licence renvoie 403 hors installation activée.
MIDDLEWARE_SANS_LICENCE = [
    m for m in settings.MIDDLEWARE if 'licence_middleware' not in m
]


def _jeu_de_donnees(suffixe):
    ecole = Ecole.objects.create(
        nom=f"École {suffixe}", adresse="Conakry",
        telephone="+224622000000", directeur="Directeur",
    )
    classe = Classe.objects.create(
        ecole=ecole, nom="6ème A", niveau="PRIMAIRE_6", annee_scolaire="2025-2026",
    )
    responsable = Responsable.objects.create(
        prenom="Mamadou", nom="Diallo", relation="PERE",
        telephone="+224622100001", adresse="Ratoma", email="papa@test.gn",
    )
    eleve = Eleve.objects.create(
        matricule=f"MAT-{suffixe}", prenom="Aissatou", nom="Camara", sexe="F",
        date_naissance=date(2014, 5, 12), lieu_naissance="Kindia", classe=classe,
        date_inscription=date(2025, 9, 15), statut="ACTIF",
        responsable_principal=responsable,
    )
    return ecole, classe, eleve


class MontantGNFFieldTest(TestCase):
    """La saisie humaine d'un montant doit être acceptée telle quelle."""

    def test_nettoyage_des_saisies_courantes(self):
        for saisie, attendu in [
            ('175000', '175000'),
            ('175 000', '175000'),          # espace ordinaire
            ('175 000', '175000'),     # espace insécable (copier-coller)
            ('175 000 GNF', '175000'),
            ('175000,00', '175000'),
            ('1.750.000', '1750000'),
            ('175.000', '175000'),
        ]:
            with self.subTest(saisie=saisie):
                self.assertEqual(MontantGNFField.nettoyer(saisie), attendu)

    def test_saisie_reellement_invalide_reste_refusee(self):
        champ = MontantGNFField(max_digits=10, decimal_places=0)
        with self.assertRaises(Exception):
            champ.clean('cent mille')


@override_settings(MIDDLEWARE=MIDDLEWARE_SANS_LICENCE)
class ModificationMontantPaiementTest(TestCase):

    def setUp(self):
        self.user = User.objects.create_superuser('caissier', 'c@c.gn', 'x')
        self.client.force_login(self.user)
        self.ecole, self.classe, self.eleve = _jeu_de_donnees('mod')
        self.type_p = TypePaiement.objects.create(nom="Scolarité")
        self.mode_p = ModePaiement.objects.create(nom="Espèces")
        self.echeancier = EcheancierPaiement.objects.create(
            eleve=self.eleve, annee_scolaire="2025-2026",
            frais_inscription_du=Decimal('100000'),
            tranche_1_due=Decimal('300000'),
            tranche_2_due=Decimal('300000'),
            tranche_3_due=Decimal('300000'),
            date_echeance_inscription=date(2025, 9, 30),
            date_echeance_tranche_1=date(2025, 12, 31),
            date_echeance_tranche_2=date(2026, 3, 31),
            date_echeance_tranche_3=date(2026, 6, 30),
        )
        self.paiement = Paiement.objects.create(
            eleve=self.eleve, type_paiement=self.type_p, mode_paiement=self.mode_p,
            montant=Decimal('120000'), date_paiement=date(2025, 10, 20),
        )

    def _corriger(self, montant, **extra):
        donnees = {
            'type_paiement': self.type_p.pk,
            'mode_paiement': self.mode_p.pk,
            'montant': montant,
            'date_paiement': '2025-10-20',
            'reference_externe': '',
            'observations': '',
            'motif_modification': 'Montant saisi incomplet le jour même',
        }
        donnees.update(extra)
        return self.client.post(
            reverse('paiements:modifier_paiement', args=[self.paiement.pk]),
            donnees, follow=True,
        )

    def test_montant_saisi_avec_espaces(self):
        self._corriger('175 000 GNF')
        self.paiement.refresh_from_db()
        self.assertEqual(self.paiement.montant, Decimal('175000'))

    def test_montant_saisi_avec_decimales_nulles(self):
        self._corriger('175000,00')
        self.paiement.refresh_from_db()
        self.assertEqual(self.paiement.montant, Decimal('175000'))

    def test_type_desactive_ne_bloque_pas_la_correction(self):
        self.type_p.actif = False
        self.type_p.save()
        self.mode_p.actif = False
        self.mode_p.save()

        reponse = self._corriger('175000')
        self.paiement.refresh_from_db()
        self.assertEqual(self.paiement.montant, Decimal('175000'))
        self.assertEqual(reponse.status_code, 200)

    def test_annee_scolaire_absente_est_reparee(self):
        Paiement.objects.filter(pk=self.paiement.pk).update(annee_scolaire='')

        reponse = self._corriger('175000')

        self.assertEqual(reponse.status_code, 200)
        self.paiement.refresh_from_db()
        self.assertEqual(self.paiement.montant, Decimal('175000'))
        self.assertEqual(self.paiement.annee_scolaire, '2025-2026')

    def test_annee_scolaire_mal_formee_est_reparee(self):
        Paiement.objects.filter(pk=self.paiement.pk).update(annee_scolaire='2025-26')

        self._corriger('175000')

        self.paiement.refresh_from_db()
        self.assertEqual(self.paiement.montant, Decimal('175000'))
        self.assertEqual(self.paiement.annee_scolaire, '2025-2026')

    def test_echec_reaffiche_le_formulaire_sans_erreur_500(self):
        """Aucune année exploitable : message clair, saisie conservée."""
        Paiement.objects.filter(pk=self.paiement.pk).update(annee_scolaire='')
        Classe.objects.filter(pk=self.classe.pk).update(annee_scolaire='')
        EcheancierPaiement.objects.filter(pk=self.echeancier.pk).delete()

        reponse = self._corriger('175000')

        self.assertEqual(reponse.status_code, 200)
        formulaire = reponse.context['form']
        self.assertTrue(formulaire.non_field_errors())
        self.assertIn("n'a pas pu être enregistrée", formulaire.non_field_errors()[0])
        self.paiement.refresh_from_db()
        self.assertEqual(self.paiement.montant, Decimal('120000'))

    def test_echeancier_resynchronise_apres_correction(self):
        from paiements.views import _valider_paiement_impl

        _valider_paiement_impl(self.paiement, self.user)
        self.echeancier.refresh_from_db()
        self.assertEqual(self.echeancier.frais_inscription_paye, Decimal('100000'))

        self._corriger('175000')

        self.paiement.refresh_from_db()
        self.echeancier.refresh_from_db()
        self.assertEqual(self.paiement.montant, Decimal('175000'))
        # Repassé en attente : plus aucune imputation de l'ancien montant.
        self.assertEqual(self.paiement.statut, 'EN_ATTENTE')
        self.assertEqual(self.echeancier.frais_inscription_paye, Decimal('0'))
        self.assertEqual(self.echeancier.tranche_1_payee, Decimal('0'))

        # La revalidation impute bien le nouveau montant.
        _valider_paiement_impl(self.paiement, self.user)
        self.echeancier.refresh_from_db()
        self.assertEqual(
            self.echeancier.frais_inscription_paye + self.echeancier.tranche_1_payee,
            Decimal('175000'),
        )

    def test_changement_de_type_seul_resynchronise_lecheancier(self):
        """Changer uniquement le type (sans toucher au montant) doit aussi
        resynchroniser l'échéancier : le type détermine si le montant est
        classé en inscription ou en tranche (_nature_frais)."""
        from paiements.views import _valider_paiement_impl

        _valider_paiement_impl(self.paiement, self.user)
        autre_type = TypePaiement.objects.create(nom="Réinscription")

        with patch('paiements.views._auto_validate_echeancier_for_eleve') as resync:
            self._corriger('120000', type_paiement=autre_type.pk)

        self.paiement.refresh_from_db()
        self.assertEqual(self.paiement.type_paiement_id, autre_type.pk)
        resync.assert_called()

    def test_montant_actuel_affiche_dans_le_formulaire(self):
        reponse = self.client.get(
            reverse('paiements:modifier_paiement', args=[self.paiement.pk])
        )
        self.assertEqual(reponse.status_code, 200)
        self.assertContains(reponse, 'value="120000"')


@override_settings(MIDDLEWARE=MIDDLEWARE_SANS_LICENCE)
class ApplicationRemisePaiementTest(TestCase):
    """appliquer_remise_paiement refuse tout paiement déjà VALIDE (« Seuls les
    paiements en attente peuvent recevoir des remises ») : une remise ne peut
    donc être ajoutée qu'avant validation. La validation qui suit doit alors
    correctement intégrer la remise dans le calcul du solde restant."""

    def setUp(self):
        self.user = User.objects.create_superuser('caissier2', 'c2@c.gn', 'x')
        self.client.force_login(self.user)
        self.ecole, self.classe, self.eleve = _jeu_de_donnees('rem')
        self.type_p = TypePaiement.objects.create(nom="Scolarité")
        self.mode_p = ModePaiement.objects.create(nom="Espèces")
        self.echeancier = EcheancierPaiement.objects.create(
            eleve=self.eleve, annee_scolaire="2025-2026",
            frais_inscription_du=Decimal('0'),
            tranche_1_due=Decimal('100000'),
            tranche_2_due=Decimal('0'),
            tranche_3_due=Decimal('0'),
            date_echeance_inscription=date(2025, 9, 30),
            date_echeance_tranche_1=date(2025, 12, 31),
            date_echeance_tranche_2=date(2026, 3, 31),
            date_echeance_tranche_3=date(2026, 6, 30),
        )
        # En attente : une remise ne peut être accordée qu'avant validation.
        self.paiement = Paiement.objects.create(
            eleve=self.eleve, type_paiement=self.type_p, mode_paiement=self.mode_p,
            montant=Decimal('90000'), date_paiement=date(2025, 10, 20),
            statut='EN_ATTENTE',
        )

    def test_remise_accordee_avant_validation_couvre_le_solde(self):
        from paiements.models import RemiseReduction
        from paiements.views import _valider_paiement_impl

        remise = RemiseReduction.objects.create(
            nom='Remise solde', type_remise='MONTANT_FIXE', valeur=Decimal('10000'),
            motif='AUTRE', date_debut=date(2025, 9, 1), date_fin=date(2026, 6, 30),
            cree_par=self.user,
        )

        reponse = self.client.post(
            reverse('paiements:appliquer_remise', args=[self.paiement.pk]),
            {
                'remises': [remise.pk],
                'tranches': ['1'],
                'base_calcul': 'paiement_echeance',
                'motif': 'AUTRE',
                'montant_original': '90000',
            },
            follow=True,
        )
        self.assertEqual(reponse.status_code, 200)
        self.assertTrue(PaiementRemise.objects.filter(paiement=self.paiement).exists())

        # La validation doit imputer le paiement (90000) ET la remise (10000)
        # sur la tranche due (100000) : le solde tombe à zéro.
        _valider_paiement_impl(self.paiement, self.user)

        self.echeancier.refresh_from_db()
        self.assertEqual(self.echeancier.solde_restant, Decimal('0'))
        self.assertEqual(self.echeancier.statut, 'PAYE_COMPLET')

    def _remise_existante(self):
        from paiements.models import RemiseReduction
        remise = RemiseReduction.objects.create(
            nom='Remise existante', type_remise='MONTANT_FIXE', valeur=5000,
            motif='AUTRE', date_debut=date(2025, 1, 1), date_fin=date(2025, 12, 31),
        )
        return PaiementRemise.objects.create(
            paiement=self.paiement, remise=remise, montant_remise=5000,
        )

    def _appliquer_pourcentage(self, pourcentage, **donnees):
        data = {
            'montant_original': '90000', 'pourcentage_scolarite': str(pourcentage),
            'tranches': ['1'], 'base_calcul': 'tranches_dues', 'motif': 'AUTRE',
        }
        data.update(donnees)
        return self.client.post(
            reverse('paiements:appliquer_remise', args=[self.paiement.pk]), data,
        )

    def _assert_remise_preservee(self, ligne):
        ligne.refresh_from_db()
        self.paiement.refresh_from_db()
        self.echeancier.refresh_from_db()
        self.assertEqual(ligne.montant_remise, 5000)
        self.assertEqual(self.paiement.remises.count(), 1)
        self.assertEqual(self.paiement.montant, 90000)
        self.assertEqual(self.paiement.statut, 'EN_ATTENTE')
        self.assertEqual(self.echeancier.tranche_1_payee, 0)
        self.assertEqual(self.echeancier.solde_restant, 100000)

    def test_ouverture_formulaire_avec_et_sans_remise(self):
        url = reverse('paiements:appliquer_remise', args=[self.paiement.pk])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'paiements/appliquer_remise.html')
        self.assertEqual(response.context['tranches_info'][0]['due'], 100000)
        self._remise_existante()
        response = self.client.get(url)
        self.assertContains(response, 'Remise existante')

    def test_depassement_affiche_refus_et_preserve_remise_existante(self):
        ligne = self._remise_existante()
        response = self._appliquer_pourcentage(50)
        self.assertEqual(response.status_code, 200)
        erreur = str(response.context['form'].errors)
        self.assertIn('Remise refusée', erreur)
        self.assertIn('10 000 GNF', erreur)
        self._assert_remise_preservee(ligne)
        self.assertFalse(self.paiement.remises.filter(remise__nom='Remise scolarité 50%').exists())

    def test_echeancier_introuvable_affiche_message_et_preserve_remises(self):
        from django.contrib.messages import get_messages
        ligne = self._remise_existante()
        with patch('paiements.views._echeancier_for_payment', return_value=None), patch(
            'paiements.views.ensure_echeancier_for_eleve', return_value=None,
        ):
            response = self._appliquer_pourcentage(10)
        self.assertRedirects(response, reverse('paiements:detail_paiement', args=[self.paiement.pk]))
        textes = [str(message) for message in get_messages(response.wsgi_request)]
        self.assertTrue(any('échéancier annuel introuvable' in texte for texte in textes))
        self._assert_remise_preservee(ligne)

    def test_remise_egale_au_solde_acceptee(self):
        response = self._appliquer_pourcentage(10)
        self.assertRedirects(response, reverse('paiements:detail_paiement', args=[self.paiement.pk]))
        self.assertEqual(self.paiement.remises.get().montant_remise, 10000)

    def test_refus_tient_compte_des_autres_versements(self):
        autre = Paiement.objects.create(
            eleve=self.eleve, type_paiement=self.type_p, mode_paiement=self.mode_p,
            montant=5000, date_paiement=self.paiement.date_paiement,
            annee_scolaire=self.paiement.annee_scolaire, statut='EN_ATTENTE',
        )
        response = self._appliquer_pourcentage(10)
        self.assertEqual(response.status_code, 200)
        erreur = str(response.context['form'].errors)
        self.assertIn('Remise refusée', erreur)
        self.assertIn('5 000 GNF', erreur)
        self.assertFalse(self.paiement.remises.exists())
        autre.refresh_from_db()
        self.assertEqual(autre.montant, 5000)

    def test_formulaire_invalide_preserve_remise_existante(self):
        ligne = self._remise_existante()
        response = self._appliquer_pourcentage(10, tranches=[])
        self.assertEqual(response.status_code, 200)
        self.assertIn('tranches', response.context['form'].errors)
        self._assert_remise_preservee(ligne)

    def test_meme_remise_cochee_et_pourcentage_affiche_erreur_formulaire(self):
        from paiements.models import RemiseReduction
        ligne = self._remise_existante()
        remise = RemiseReduction.objects.create(
            nom='Remise scolarité 10%', type_remise='POURCENTAGE', valeur=10,
            motif='AUTRE', date_debut=date(2025, 1, 1), date_fin=date(2025, 12, 31),
        )
        response = self._appliquer_pourcentage(10, remises=[remise.pk])
        self.assertEqual(response.status_code, 200)
        self.assertIn('pourcentage_scolarite', response.context['form'].errors)
        self._assert_remise_preservee(ligne)

    def test_raccourcis_motif_exigent_une_tranche(self):
        ligne = self._remise_existante()
        for motif in ('MOITIE', 'NE_PAIE_RIEN'):
            with self.subTest(motif=motif):
                response = self._appliquer_pourcentage('', motif=motif, tranches=[])
                self.assertEqual(response.status_code, 200)
                self.assertIn('tranches', response.context['form'].errors)
                self._assert_remise_preservee(ligne)

    def test_raccourcis_motif_refusent_remise_cochee_en_double(self):
        from paiements.models import RemiseReduction
        ligne = self._remise_existante()
        for motif, pourcentage in (('MOITIE', 50), ('NE_PAIE_RIEN', 100)):
            with self.subTest(motif=motif):
                remise = RemiseReduction.objects.create(
                    nom=f'Remise scolarité {pourcentage}%', type_remise='POURCENTAGE',
                    valeur=pourcentage, motif=motif, date_debut=date(2025, 1, 1),
                    date_fin=date(2025, 12, 31),
                )
                response = self._appliquer_pourcentage('', motif=motif, remises=[remise.pk])
                self.assertEqual(response.status_code, 200)
                self.assertIn('pourcentage_scolarite', response.context['form'].errors)
                self._assert_remise_preservee(ligne)

    def test_remises_distinctes_peuvent_etre_cumulees(self):
        from paiements.models import RemiseReduction
        self.paiement.montant = 80000
        self.paiement.save()
        remise = RemiseReduction.objects.create(
            nom='Remise fratrie', type_remise='POURCENTAGE', valeur=10,
            motif='FRATRIE', date_debut=date(2025, 1, 1), date_fin=date(2025, 12, 31),
        )
        response = self._appliquer_pourcentage(10, remises=[remise.pk], montant_original='80000')
        self.assertRedirects(response, reverse('paiements:detail_paiement', args=[self.paiement.pk]))
        self.assertEqual(self.paiement.remises.count(), 2)
        self.assertEqual(sum(ligne.montant_remise for ligne in self.paiement.remises.all()), 20000)
