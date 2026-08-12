"""Correction d'un paiement enregistré (/paiements/modifier/<id>/).

Cas remontés depuis la caisse : le nouveau montant était refusé alors qu'il
était correct (saisie « 175 000 », type de paiement désactivé entre-temps,
année scolaire absente sur un paiement ancien) et l'échéancier conservait
l'ancien montant après correction.
"""

from datetime import date
from decimal import Decimal

from django.conf import settings
from django.contrib.auth.models import User
from django.test import TestCase, override_settings
from django.urls import reverse

from eleves.models import Classe, Ecole, Eleve, Responsable
from paiements.forms import MontantGNFField
from paiements.models import (
    EcheancierPaiement, ModePaiement, Paiement, TypePaiement,
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

    def test_montant_actuel_affiche_dans_le_formulaire(self):
        reponse = self.client.get(
            reverse('paiements:modifier_paiement', args=[self.paiement.pk])
        )
        self.assertEqual(reponse.status_code, 200)
        self.assertContains(reponse, 'value="120000"')
