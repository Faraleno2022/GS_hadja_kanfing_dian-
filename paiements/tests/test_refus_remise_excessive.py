"""Un refus de remise conserve le reçu, ses remises et l'échéancier."""
from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse

from eleves.models import Classe, Ecole, Eleve, GrilleTarifaire
from paiements.models import (
    EcheancierPaiement, ModePaiement, Paiement, PaiementRemise,
    RemiseReduction, TypePaiement,
)
from paiements.tests.support import MIDDLEWARE_SANS_LICENCE


@override_settings(MIDDLEWARE=MIDDLEWARE_SANS_LICENCE)
class RefusRemiseExcessiveTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_superuser(
            'refus-remise', 'refus@example.com', 'test',
        )
        self.client.force_login(self.user)
        ecole = Ecole.objects.create(
            nom='École refus', adresse='Conakry', telephone='620000100',
            directeur='Direction',
        )
        classe = Classe.objects.create(
            ecole=ecole, nom='Petite section A', niveau='PETITE_SECTION',
            annee_scolaire='2026-2027',
        )
        self.eleve = Eleve.objects.create(
            matricule='REFUS-001', prenom='Aminata', nom='Test',
            sexe='F', classe=classe,
        )
        self.echeancier = EcheancierPaiement.objects.create(
            eleve=self.eleve, annee_scolaire='2026-2027',
            frais_inscription_du=50000, tranche_1_due=500000,
            tranche_2_due=300000, tranche_3_due=200000,
            date_echeance_inscription=date(2026, 9, 1),
            date_echeance_tranche_1=date(2026, 10, 1),
            date_echeance_tranche_2=date(2027, 1, 1),
            date_echeance_tranche_3=date(2027, 4, 1),
        )
        self.type = TypePaiement.objects.create(nom='Inscription et scolarité annuelle')
        self.mode = ModePaiement.objects.create(nom='Espèces refus')
        self.versement = self.creer_paiement(800000, statut='VALIDE')
        self.paiement = self.creer_paiement(200000)
        self.url = reverse('paiements:appliquer_remise', args=[self.paiement.pk])

    def creer_paiement(self, montant, statut='EN_ATTENTE', annee='2026-2027'):
        return Paiement.objects.create(
            eleve=self.eleve, type_paiement=self.type, mode_paiement=self.mode,
            montant=montant, statut=statut, annee_scolaire=annee,
            date_paiement=date(2026, 9, 8),
        )

    def ajouter_remise(self, paiement, montant, *, deduite=False):
        remise = RemiseReduction.objects.create(
            nom='Remise existante', type_remise='MONTANT_FIXE', valeur=montant,
            motif='GESTE_COMMERCIAL', date_debut=date(2026, 1, 1),
            date_fin=date(2027, 12, 31),
        )
        return PaiementRemise.objects.create(
            paiement=paiement, remise=remise, montant_remise=montant,
            montant_base=500000, montant_tranche_1=montant,
            applique_tranche_1=True, base_calcul='TRANCHE',
            motif='GESTE_COMMERCIAL', deduite_du_paiement=deduite,
        )

    def donnees(self, pourcentage='20', **extra):
        return {
            'montant_original': '200000', 'pourcentage_scolarite': pourcentage,
            'tranches': ['1'], 'base_calcul': 'TRANCHE',
            'motif': 'GESTE_COMMERCIAL', **extra,
        }

    def instantane(self):
        return {
            'paiements': list(Paiement.objects.order_by('pk').values()),
            'remises': list(PaiementRemise.objects.order_by('pk').values()),
            'catalogue': list(RemiseReduction.objects.order_by('pk').values()),
            'echeanciers': list(EcheancierPaiement.objects.order_by('pk').values()),
            'solde': self.echeancier.solde_restant,
        }

    def verifier_refus(self, donnees, maximum='50 000'):
        avant = self.instantane()
        response = self.client.post(self.url, donnees)
        self.assertContains(response, 'Remise refusée', status_code=200)
        self.assertContains(response, f'{maximum} GNF')
        self.assertTemplateUsed(response, 'paiements/appliquer_remise.html')
        self.assertEqual(response.context['form'].tranches_selectionnees(), ['1'])
        self.assertEqual(self.instantane(), avant)
        return response

    def test_refus_sans_erreur_et_sans_creation_de_remise_technique(self):
        # 800 000 + 200 000 + 100 000 > 1 050 000 dus.
        self.verifier_refus(self.donnees())

    def test_refus_conserve_une_remise_deduite_et_le_net_du_recu(self):
        self.paiement.montant = Decimal('180000')
        self.paiement.save()
        self.ajouter_remise(self.paiement, 20000, deduite=True)
        self.verifier_refus(self.donnees())

    def test_refus_tient_compte_des_versements_en_attente(self):
        self.versement.statut = 'EN_ATTENTE'
        self.versement.save()
        self.verifier_refus(self.donnees())

    def test_refus_tient_compte_des_remises_des_autres_versements(self):
        self.ajouter_remise(self.versement, 40000)
        self.verifier_refus(self.donnees('4'), maximum='10 000')

    def test_remise_preconfiguree_refusee_sans_modifier_le_catalogue(self):
        ligne = self.ajouter_remise(self.versement, 100000)
        remise_id = ligne.remise_id
        ligne.delete()
        self.verifier_refus(self.donnees('', remises=[str(remise_id)]))

    def test_limite_exacte_et_remplacement_sans_double_comptage(self):
        self.ajouter_remise(self.paiement, 20000)
        for _ in range(2):
            response = self.client.post(self.url, self.donnees('10'))
            self.assertRedirects(
                response, reverse('paiements:detail_paiement', args=[self.paiement.pk]),
                fetch_redirect_response=False,
            )
            self.paiement.refresh_from_db()
            self.assertEqual(self.paiement.montant, Decimal('200000'))
            self.assertEqual(self.paiement.remises.get().montant_remise, Decimal('50000'))

    def test_deduction_autorisee_quand_la_couverture_reste_dans_le_du(self):
        response = self.client.post(self.url, self.donnees(deduire_du_paiement='1'))
        self.assertEqual(response.status_code, 302)
        self.paiement.refresh_from_db()
        self.assertEqual(self.paiement.montant, Decimal('100000'))
        self.assertEqual(self.paiement.remises.get().montant_remise, Decimal('100000'))

    def test_paiements_annules_et_autres_annees_sont_exclus(self):
        self.creer_paiement(2000000, statut='ANNULE')
        autre_annee = self.creer_paiement(2000000, statut='VALIDE', annee='2025-2026')
        self.ajouter_remise(autre_annee, 100000)
        response = self.client.post(self.url, self.donnees('10'))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(self.paiement.remises.get().montant_remise, Decimal('50000'))

    def test_deduction_refusee_si_la_remise_seule_depasse_le_disponible(self):
        self.verifier_refus(
            self.donnees('100', deduire_du_paiement='1'), maximum='250 000',
        )

    def test_echeancier_absent_affiche_un_refus_sans_aucune_ecriture(self):
        self.echeancier.delete()
        GrilleTarifaire.objects.create(
            ecole=self.eleve.classe.ecole, niveau=self.eleve.classe.niveau,
            annee_scolaire='2026-2027', frais_inscription=50000,
            tranche_1=500000, tranche_2=300000, tranche_3=200000,
        )
        avant = self.instantane()
        response = self.client.post(self.url, self.donnees())
        self.assertContains(response, 'Remise refusée : échéancier annuel introuvable', status_code=200)
        self.assertTemplateUsed(response, 'paiements/appliquer_remise.html')
        self.assertEqual(self.instantane(), avant)

    def test_deduction_annulant_le_recu_refusee_sans_modification(self):
        # 40 % de 500 000 = 200 000 : le reçu deviendrait nul.
        # Même sans dépasser le dû annuel, la base interdit ce montant.
        avant = self.instantane()
        response = self.client.post(self.url, self.donnees('40', deduire_du_paiement='1'))
        self.assertContains(response, 'Remise refusée : la déduction ramènerait le reçu à zéro', status_code=200)
        self.assertEqual(self.instantane(), avant)
