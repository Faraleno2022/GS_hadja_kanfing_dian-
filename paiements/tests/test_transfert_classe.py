from datetime import date
from decimal import Decimal

from django.db.models import Sum
from django.test import TestCase

from eleves.models import Classe, Ecole, Eleve, GrilleTarifaire
from paiements.models import (
    EcheancierPaiement,
    ModePaiement,
    Paiement,
    PaiementRemise,
    RemiseReduction,
    TypePaiement,
)

ZERO = Decimal('0')


class TransfertClassePaiementTests(TestCase):
    def setUp(self):
        self.ecole = Ecole.objects.create(
            nom='Ecole transfert',
            adresse='Conakry',
            telephone='+224620000001',
            directeur='Direction',
        )
        self.ancienne_classe = Classe.objects.create(
            ecole=self.ecole,
            nom='7eme A',
            niveau='COLLEGE_7',
            annee_scolaire='2025-2026',
        )
        self.nouvelle_classe = Classe.objects.create(
            ecole=self.ecole,
            nom='8eme A',
            niveau='COLLEGE_8',
            annee_scolaire='2025-2026',
        )
        self.classe_annee_suivante = Classe.objects.create(
            ecole=self.ecole,
            nom='8eme A',
            niveau='COLLEGE_8',
            annee_scolaire='2026-2027',
        )
        GrilleTarifaire.objects.create(
            ecole=self.ecole,
            niveau='COLLEGE_7',
            annee_scolaire='2025-2026',
            frais_inscription=Decimal('100000'),
            frais_reinscription=Decimal('75000'),
            tranche_1=Decimal('500000'),
            tranche_2=Decimal('500000'),
            tranche_3=Decimal('400000'),
        )
        GrilleTarifaire.objects.create(
            ecole=self.ecole,
            niveau='COLLEGE_8',
            annee_scolaire='2025-2026',
            frais_inscription=Decimal('200000'),
            frais_reinscription=Decimal('150000'),
            tranche_1=Decimal('600000'),
            tranche_2=Decimal('600000'),
            tranche_3=Decimal('400000'),
        )
        GrilleTarifaire.objects.create(
            ecole=self.ecole,
            niveau='COLLEGE_8',
            annee_scolaire='2026-2027',
            frais_inscription=Decimal('250000'),
            frais_reinscription=Decimal('175000'),
            tranche_1=Decimal('625000'),
            tranche_2=Decimal('625000'),
            tranche_3=Decimal('425000'),
        )
        self.eleve = Eleve.objects.create(
            matricule='CN7-900',
            prenom='Aminata',
            nom='Diallo',
            sexe='F',
            classe=self.ancienne_classe,
            date_naissance=date(2012, 5, 10),
            date_inscription=date(2025, 9, 1),
        )
        self.type_paiement = TypePaiement.objects.create(
            nom='Inscription et scolarite annuelle'
        )
        self.mode_paiement = ModePaiement.objects.create(
            nom='Especes transfert'
        )
        self.echeancier = EcheancierPaiement.objects.create(
            eleve=self.eleve,
            annee_scolaire='2025-2026',
            frais_inscription_du=Decimal('100000'),
            tranche_1_due=Decimal('500000'),
            tranche_2_due=Decimal('500000'),
            tranche_3_due=Decimal('400000'),
            date_echeance_inscription=date(2025, 9, 30),
            date_echeance_tranche_1=date(2026, 1, 15),
            date_echeance_tranche_2=date(2026, 3, 15),
            date_echeance_tranche_3=date(2026, 5, 15),
        )

    def creer_paiement_valide(self, montant, annee='2025-2026'):
        return Paiement.objects.create(
            eleve=self.eleve,
            type_paiement=self.type_paiement,
            mode_paiement=self.mode_paiement,
            numero_recu='',
            montant=Decimal(montant),
            annee_scolaire=annee,
            date_paiement=date(2025, 10, 1),
            statut='VALIDE',
        )

    def test_transfert_meme_annee_recalcule_et_conserve_le_paiement(self):
        paiement = self.creer_paiement_valide('600000')

        self.eleve.classe = self.nouvelle_classe
        self.eleve.save()
        self.echeancier.refresh_from_db()
        paiement.refresh_from_db()

        self.assertEqual(self.echeancier.total_du, Decimal('1800000'))
        self.assertEqual(self.echeancier.total_paye, Decimal('600000'))
        self.assertEqual(self.echeancier.solde_restant, Decimal('1200000'))
        self.assertEqual(paiement.annee_scolaire, '2025-2026')
        self.assertEqual(
            self.eleve._financial_transfer_info['credit_non_affecte'], ZERO
        )

    def test_transfert_nouvelle_annee_conserve_l_ancien_echeancier(self):
        paiement = self.creer_paiement_valide('600000')

        self.eleve.classe = self.classe_annee_suivante
        self.eleve.save()

        self.echeancier.refresh_from_db()
        nouvel_echeancier = EcheancierPaiement.objects.get(
            eleve=self.eleve,
            annee_scolaire='2026-2027',
        )
        paiement.refresh_from_db()

        self.assertEqual(self.echeancier.annee_scolaire, '2025-2026')
        self.assertEqual(self.echeancier.total_du, Decimal('1500000'))
        self.assertEqual(nouvel_echeancier.nature_frais, 'REINSCRIPTION')
        self.assertEqual(nouvel_echeancier.total_du, Decimal('1850000'))
        self.assertEqual(nouvel_echeancier.total_paye, ZERO)
        self.assertEqual(paiement.annee_scolaire, '2025-2026')
        self.assertEqual(self.eleve.echeanciers.count(), 2)
        self.assertEqual(self.eleve.echeancier, nouvel_echeancier)

    def test_tarif_inferieur_signale_un_credit_sans_perdre_le_paiement(self):
        GrilleTarifaire.objects.filter(
            ecole=self.ecole,
            niveau='COLLEGE_8',
            annee_scolaire='2025-2026',
        ).update(
            frais_inscription=Decimal('100000'),
            tranche_1=Decimal('200000'),
            tranche_2=Decimal('100000'),
            tranche_3=Decimal('100000'),
        )
        self.creer_paiement_valide('600000')

        self.eleve.classe = self.nouvelle_classe
        self.eleve.save()
        self.echeancier.refresh_from_db()

        self.assertEqual(self.echeancier.total_du, Decimal('500000'))
        self.assertEqual(self.echeancier.total_paye, Decimal('500000'))
        self.assertEqual(self.echeancier.statut, 'PAYE_COMPLET')
        self.assertEqual(
            self.eleve._financial_transfer_info['credit_non_affecte'],
            Decimal('100000'),
        )
        self.assertEqual(
            Paiement.objects.filter(eleve=self.eleve, statut='VALIDE').aggregate(
                total=Sum('montant')
            )['total'],
            Decimal('600000'),
        )

    def test_remise_est_rejouee_apres_le_changement_de_tarif(self):
        paiement = self.creer_paiement_valide('600000')
        remise = RemiseReduction.objects.create(
            nom='Remise transfert',
            type_remise='MONTANT_FIXE',
            valeur=Decimal('100000'),
            motif='SOCIALE',
            date_debut=date(2025, 9, 1),
            date_fin=date(2026, 8, 31),
        )
        PaiementRemise.objects.create(
            paiement=paiement,
            remise=remise,
            montant_remise=Decimal('100000'),
            montant_base=Decimal('600000'),
            montant_tranche_1=Decimal('100000'),
            applique_tranche_1=True,
            motif='GESTE_COMMERCIAL',
        )

        self.eleve.classe = self.nouvelle_classe
        self.eleve.save()
        self.echeancier.refresh_from_db()

        info = self.eleve._financial_transfer_info
        self.assertEqual(info['total_remises'], Decimal('100000'))
        self.assertEqual(self.echeancier.solde_restant, Decimal('1100000'))
