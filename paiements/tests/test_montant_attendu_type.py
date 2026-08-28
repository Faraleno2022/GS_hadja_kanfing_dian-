"""Montant exact attendu selon le type de paiement.

La règle est écrite une seule fois (``montant_attendu_pour_type``) et sert à la
fois à proposer le montant à la saisie et à le valider à l'enregistrement. Ces
tests verrouillent cette unicité: un montant proposé par l'écran ne doit jamais
être refusé par le même écran.
"""

from datetime import date, timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from eleves.models import Ecole, Classe, Responsable, Eleve
from paiements.allocation import (
    INSCRIPTION,
    TRANCHE_1,
    TRANCHE_2,
    TRANCHE_3,
    montant_attendu_pour_type,
    scope_for_type,
)
from paiements.models import (
    EcheancierPaiement,
    ModePaiement,
    Paiement,
    TypePaiement,
)
from paiements.tests.support import TEST_MIDDLEWARE


class ScopeParTypeTests(TestCase):
    """Ce que chaque libellé de type annonce couvrir."""

    def test_types_courants(self):
        cas = {
            "Réinscription + Tranche 1": (INSCRIPTION, TRANCHE_1),
            "Inscription + Tranche 1": (INSCRIPTION, TRANCHE_1),
            "Frais d'inscription + Annuel": (
                INSCRIPTION, TRANCHE_1, TRANCHE_2, TRANCHE_3,
            ),
            "Frais d'inscription + 1ère tranche + 2ème tranche": (
                INSCRIPTION, TRANCHE_1, TRANCHE_2,
            ),
            "Tranche 1 + Tranche 2": (TRANCHE_1, TRANCHE_2),
            "Tranche 2 + Tranche 3": (TRANCHE_2, TRANCHE_3),
            "Tranche 3": (TRANCHE_3,),
            "Scolarité": (TRANCHE_1, TRANCHE_2, TRANCHE_3),
        }
        for libelle, attendu in cas.items():
            with self.subTest(libelle=libelle):
                self.assertEqual(scope_for_type(libelle), attendu)

    def test_une_tranche_nommee_empeche_la_lecture_annuelle(self):
        """« Scolarité - 2ème tranche » ne vise que T2, pas toute l'année."""
        self.assertEqual(scope_for_type("Scolarité - 2ème tranche"), (TRANCHE_2,))
        self.assertEqual(scope_for_type("Scolarité - 1ère tranche"), (TRANCHE_1,))

    def test_libelle_non_standard_ne_donne_aucun_montant(self):
        self.assertEqual(scope_for_type("Divers"), ())
        montant, detail = montant_attendu_pour_type("Divers", {TRANCHE_1: 100}, {})
        self.assertEqual(montant, Decimal("0"))
        self.assertEqual(detail, [])

    def test_ce_qui_est_deja_couvert_est_retranche(self):
        dues = {INSCRIPTION: 30000, TRANCHE_1: 400000}
        payes = {INSCRIPTION: 30000, TRANCHE_1: 150000}
        montant, detail = montant_attendu_pour_type(
            "Réinscription + Tranche 1", dues, payes
        )
        # L'inscription est soldée: il ne reste que le solde de T1
        self.assertEqual(montant, Decimal("250000"))
        self.assertEqual(
            detail, [(INSCRIPTION, Decimal("0")), (TRANCHE_1, Decimal("250000"))]
        )


@override_settings(MIDDLEWARE=TEST_MIDDLEWARE)
class MontantSuggereEndpointTests(TestCase):
    """L'écran propose le reste exact, et l'accepte ensuite sans confirmation."""

    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_superuser(
            username="admin", email="admin@example.com", password="pass1234"
        )
        self.client.force_login(self.user)

        self.ecole = Ecole.objects.create(
            nom="Ecole Test",
            adresse="Addr",
            telephone="+224123456789",
            email="ecole@test.com",
            directeur="Dir",
        )
        self.classe = Classe.objects.create(
            ecole=self.ecole,
            nom="7ème année",
            niveau="COLLEGE_7",
            annee_scolaire="2024-2025",
            capacite_max=40,
        )
        self.responsable = Responsable.objects.create(
            prenom="Jean", nom="Doe", relation="PERE",
            telephone="+224123456789", email="p@example.com", adresse="Addr",
        )
        self.eleve = Eleve.objects.create(
            matricule="TEMP-300",
            prenom="Awa", nom="Diallo", sexe="F",
            date_naissance=date(2012, 5, 4), lieu_naissance="Ville",
            classe=self.classe, date_inscription=timezone.now().date(),
            statut="ACTIF", responsable_principal=self.responsable,
        )
        self.today = timezone.now().date()
        self.echeancier = EcheancierPaiement.objects.create(
            eleve=self.eleve,
            annee_scolaire="2024-2025",
            frais_inscription_du=Decimal("30000"),
            tranche_1_due=Decimal("700000"),
            tranche_2_due=Decimal("500000"),
            tranche_3_due=Decimal("0"),
            date_echeance_inscription=self.today,
            date_echeance_tranche_1=self.today + timedelta(days=30),
            date_echeance_tranche_2=self.today + timedelta(days=60),
            date_echeance_tranche_3=self.today + timedelta(days=90),
        )
        self.mode = ModePaiement.objects.create(nom="Espèces")
        self.type = TypePaiement.objects.create(nom="Réinscription + Tranche 1")
        self.url_suggestion = reverse("paiements:ajax_montant_suggere")

    def _suggestion(self):
        resp = self.client.post(
            self.url_suggestion,
            {"eleve_id": self.eleve.id, "type_id": self.type.id},
        )
        self.assertEqual(resp.status_code, 200)
        return resp.json()

    def test_le_montant_propose_est_le_reste_des_postes_vises(self):
        data = self._suggestion()
        self.assertTrue(data["ok"])
        # 30 000 de réinscription + 700 000 de T1, T2 n'est pas visée
        self.assertEqual(data["suggested"], 730000)

    def test_le_detail_nomme_les_postes_couverts(self):
        data = self._suggestion()
        postes = data["breakdown"]["postes"]
        self.assertEqual(
            [(p["label"], p["montant"]) for p in postes],
            [("Réinscription", 30000), ("1ère tranche", 700000)],
        )

    def test_le_montant_propose_est_accepte_sans_confirmation(self):
        """L'invariant: proposer puis refuser le même montant est impossible."""
        suggested = self._suggestion()["suggested"]

        resp = self.client.post(
            reverse("paiements:ajouter_paiement"),
            {
                "eleve": self.eleve.id,
                "type_paiement": self.type.id,
                "mode_paiement": self.mode.id,
                "montant": str(suggested),
                "date_paiement": self.today.isoformat(),
                "observations": "",
                "reference_externe": "",
            },
        )
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(Paiement.objects.count(), 1)

    def test_consulter_une_reinscription_sans_grille_ne_efface_pas_la_dette(self):
        """Régression: l'échéancier était remis à zéro faute de grille.

        Le calcul du montant passe par ``ensure_echeancier_for_eleve`` avec
        ``prefer_reinscription``. Sans grille correspondante, les montants dus
        étaient écrasés par des zéros — la dette de l'élève disparaissait à la
        simple sélection du type.
        """
        self._suggestion()

        self.echeancier.refresh_from_db()
        self.assertEqual(self.echeancier.frais_inscription_du, Decimal("30000"))
        self.assertEqual(self.echeancier.tranche_1_due, Decimal("700000"))
        self.assertEqual(self.echeancier.tranche_2_due, Decimal("500000"))

    def test_la_suggestion_tient_compte_des_versements_deja_faits(self):
        Paiement.objects.create(
            eleve=self.eleve,
            type_paiement=self.type,
            mode_paiement=self.mode,
            montant=Decimal("30000"),
            date_paiement=self.today,
            statut="VALIDE",
            annee_scolaire="2024-2025",
            numero_recu="",
        )
        # La réinscription est soldée: il ne reste que T1
        self.assertEqual(self._suggestion()["suggested"], 700000)
