from datetime import date
from decimal import Decimal

from django.test import TestCase
from django.db.models import Sum

from eleves.models import Classe, Ecole, Eleve, GrilleTarifaire
from paiements.models import (
    EcheancierPaiement,
    ModePaiement,
    Paiement,
    TypePaiement,
)


class TransfertClassePaiementTests(TestCase):
    def setUp(self):
        self.ecole = Ecole.objects.create(
            nom="Ecole transfert",
            adresse="Conakry",
            telephone="+224620000001",
            directeur="Direction",
        )
        self.ancienne_classe = Classe.objects.create(
            ecole=self.ecole,
            nom="7eme A",
            niveau="COLLEGE_7",
            annee_scolaire="2025-2026",
        )
        self.nouvelle_classe = Classe.objects.create(
            ecole=self.ecole,
            nom="8eme A",
            niveau="COLLEGE_8",
            annee_scolaire="2025-2026",
        )
        self.classe_annee_suivante = Classe.objects.create(
            ecole=self.ecole,
            nom="8eme A",
            niveau="COLLEGE_8",
            annee_scolaire="2026-2027",
        )
        GrilleTarifaire.objects.create(
            ecole=self.ecole,
            niveau="COLLEGE_7",
            annee_scolaire="2025-2026",
            frais_inscription=Decimal("100000"),
            frais_reinscription=Decimal("75000"),
            tranche_1=Decimal("500000"),
            tranche_2=Decimal("500000"),
            tranche_3=Decimal("400000"),
        )
        GrilleTarifaire.objects.create(
            ecole=self.ecole,
            niveau="COLLEGE_8",
            annee_scolaire="2025-2026",
            frais_inscription=Decimal("200000"),
            frais_reinscription=Decimal("150000"),
            tranche_1=Decimal("600000"),
            tranche_2=Decimal("600000"),
            tranche_3=Decimal("400000"),
        )
        GrilleTarifaire.objects.create(
            ecole=self.ecole,
            niveau="COLLEGE_8",
            annee_scolaire="2026-2027",
            frais_inscription=Decimal("250000"),
            frais_reinscription=Decimal("175000"),
            tranche_1=Decimal("625000"),
            tranche_2=Decimal("625000"),
            tranche_3=Decimal("425000"),
        )
        self.eleve = Eleve.objects.create(
            matricule="CN7-900",
            prenom="Aminata",
            nom="Diallo",
            sexe="F",
            classe=self.ancienne_classe,
            date_inscription=date(2025, 9, 1),
        )
        self.type_paiement = TypePaiement.objects.create(nom="Scolarite annuelle")
        self.mode_paiement = ModePaiement.objects.create(nom="Especes transfert")
        self.echeancier = EcheancierPaiement.objects.create(
            eleve=self.eleve,
            annee_scolaire="2025-2026",
            frais_inscription_du=Decimal("100000"),
            tranche_1_due=Decimal("500000"),
            tranche_2_due=Decimal("500000"),
            tranche_3_due=Decimal("400000"),
            date_echeance_inscription=date(2025, 9, 30),
            date_echeance_tranche_1=date(2026, 1, 15),
            date_echeance_tranche_2=date(2026, 3, 15),
            date_echeance_tranche_3=date(2026, 5, 15),
        )

    def creer_paiement_valide(self, montant, annee="2025-2026"):
        return Paiement.objects.create(
            eleve=self.eleve,
            type_paiement=self.type_paiement,
            mode_paiement=self.mode_paiement,
            numero_recu="",
            montant=Decimal(montant),
            annee_scolaire=annee,
            date_paiement=date(2025, 10, 1),
            statut="VALIDE",
        )

    def test_transfert_meme_annee_applique_nouvelle_grille_et_conserve_paiement(self):
        paiement = self.creer_paiement_valide("600000")

        self.eleve.classe = self.nouvelle_classe
        self.eleve.save()
        self.echeancier.refresh_from_db()
        paiement.refresh_from_db()

        self.assertEqual(self.echeancier.total_du, Decimal("1800000"))
        self.assertEqual(self.echeancier.frais_inscription_paye, Decimal("200000"))
        self.assertEqual(self.echeancier.tranche_1_payee, Decimal("400000"))
        self.assertEqual(self.echeancier.total_paye, Decimal("600000"))
        self.assertEqual(self.echeancier.solde_restant, Decimal("1200000"))
        self.assertEqual(paiement.annee_scolaire, "2025-2026")
        self.assertEqual(self.eleve._financial_transfer_info["credit_non_affecte"], 0)

    def test_transfert_nouvelle_annee_garde_historique_et_ne_reporte_pas_paiement(self):
        paiement = self.creer_paiement_valide("600000")

        self.eleve.classe = self.classe_annee_suivante
        self.eleve.save()

        self.echeancier.refresh_from_db()
        nouvel_echeancier = EcheancierPaiement.objects.get(
            eleve=self.eleve,
            annee_scolaire="2026-2027",
        )
        paiement.refresh_from_db()

        self.assertEqual(self.echeancier.annee_scolaire, "2025-2026")
        self.assertEqual(self.echeancier.total_du, Decimal("1500000"))
        self.assertEqual(nouvel_echeancier.nature_frais, "REINSCRIPTION")
        self.assertEqual(nouvel_echeancier.total_du, Decimal("1850000"))
        self.assertEqual(nouvel_echeancier.total_paye, Decimal("0"))
        self.assertEqual(paiement.annee_scolaire, "2025-2026")
        self.assertEqual(self.eleve.echeanciers.count(), 2)

    def test_transfert_avec_tarif_inferieur_signale_le_credit_sans_perdre_le_paiement(self):
        GrilleTarifaire.objects.filter(
            ecole=self.ecole,
            niveau="COLLEGE_8",
            annee_scolaire="2025-2026",
        ).update(
            frais_inscription=Decimal("100000"),
            tranche_1=Decimal("200000"),
            tranche_2=Decimal("100000"),
            tranche_3=Decimal("100000"),
        )
        self.creer_paiement_valide("600000")

        self.eleve.classe = self.nouvelle_classe
        self.eleve.save()
        self.echeancier.refresh_from_db()

        self.assertEqual(self.echeancier.total_du, Decimal("500000"))
        self.assertEqual(self.echeancier.total_paye, Decimal("500000"))
        self.assertEqual(self.echeancier.statut, "PAYE_COMPLET")
        self.assertEqual(
            self.eleve._financial_transfer_info["credit_non_affecte"],
            Decimal("100000"),
        )
        self.assertEqual(
            Paiement.objects.filter(eleve=self.eleve, statut="VALIDE").aggregate(
                total=Sum("montant")
            )["total"],
            Decimal("600000"),
        )

    def ajouter_remise(self, paiement, base='paiement_echeance'):
        from paiements.models import PaiementRemise, RemiseReduction
        from paiements.recalcul_remises import memoriser_regle_remise
        remise = RemiseReduction.objects.create(
            nom='Remise transfert', type_remise='POURCENTAGE', valeur=10,
            motif='AUTRE', date_debut=date(2025, 9, 1), date_fin=date(2026, 8, 31),
        )
        return PaiementRemise.objects.create(
            paiement=paiement, remise=remise, montant_remise=50000,
            regle_calcul=memoriser_regle_remise(remise, base, ['1']),
        )

    def test_transfert_recalcule_remise_sur_paiement_et_carnet(self):
        from paiements.carnet_paiement import construire_donnees_carnet
        paiement = self.creer_paiement_valide('600000')
        remise = self.ajouter_remise(paiement)
        self.eleve.classe = self.nouvelle_classe
        self.eleve.save()
        self.echeancier.refresh_from_db()
        remise.refresh_from_db()
        self.assertEqual(remise.montant_remise, 40000)
        self.assertEqual(self.echeancier.total_paye, 600000)
        self.assertEqual(self.echeancier.solde_restant, 1160000)
        self.assertEqual(self.eleve._financial_transfer_info['solde_restant'], 1160000)
        carnet = construire_donnees_carnet(paiement)
        self.assertEqual(carnet['total_remises'], 40000)
        self.assertEqual(carnet['reste'], 1160000)

    def test_transfert_recalcule_remise_sur_tranche_due(self):
        paiement = self.creer_paiement_valide('600000')
        remise = self.ajouter_remise(paiement, base='tranches_dues')
        self.eleve.classe = self.nouvelle_classe
        self.eleve.save()
        remise.refresh_from_db()
        self.echeancier.refresh_from_db()
        self.assertEqual(remise.montant_remise, 60000)
        self.assertEqual(self.echeancier.solde_restant, 1140000)

    def test_passage_a_vers_b_meme_niveau_conserve_montants(self):
        classe_b = Classe.objects.create(ecole=self.ecole, nom='7eme B',
            niveau=self.ancienne_classe.niveau, annee_scolaire='2025-2026')
        paiement = self.creer_paiement_valide('600000')
        remise = self.ajouter_remise(paiement)
        numero = paiement.numero_recu
        self.eleve.classe = classe_b
        self.eleve.save()
        self.echeancier.refresh_from_db()
        remise.refresh_from_db()
        paiement.refresh_from_db()
        self.assertEqual(self.echeancier.total_du, 1500000)
        self.assertEqual(self.echeancier.total_paye, 600000)
        self.assertEqual(remise.montant_remise, 50000)
        self.assertEqual(self.echeancier.solde_restant, 850000)
        self.assertEqual(paiement.numero_recu, numero)
        self.assertEqual(self.eleve.echeanciers.count(), 1)

    def test_changement_annee_ne_recalcule_pas_anciennes_remises(self):
        paiement = self.creer_paiement_valide('600000')
        remise = self.ajouter_remise(paiement)
        self.eleve.classe = self.classe_annee_suivante
        self.eleve.save()
        remise.refresh_from_db()
        self.assertEqual(remise.montant_remise, 50000)
        nouvel = self.eleve.echeanciers.get(annee_scolaire='2026-2027')
        self.assertEqual(nouvel.total_paye, 0)
        self.assertEqual(nouvel.total_remises_valides, 0)

    def test_erreur_recalcul_annule_transfert(self):
        from unittest.mock import patch
        self.creer_paiement_valide('600000')
        matricule = self.eleve.matricule
        with patch('paiements.services._synchroniser_couverture', side_effect=ValueError('Calcul impossible')):
            self.eleve.classe = self.nouvelle_classe
            with self.assertRaises(ValueError):
                self.eleve.save()
        self.eleve.refresh_from_db()
        self.echeancier.refresh_from_db()
        self.assertEqual(self.eleve.classe_id, self.ancienne_classe.pk)
        self.assertEqual(self.eleve.matricule, matricule)
        self.assertEqual(self.echeancier.total_du, 1500000)
