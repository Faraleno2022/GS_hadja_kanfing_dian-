from django.test import TestCase, override_settings
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.conf import settings
from datetime import date
from unittest.mock import patch

from eleves.models import Ecole, Classe, Eleve, Responsable
from paiements.models import Paiement, TypePaiement, ModePaiement
from paiements.tests.support import TEST_MIDDLEWARE
from utilisateurs.models import Profil


@override_settings(MIDDLEWARE=TEST_MIDDLEWARE)
class SchoolFilteringTests(TestCase):
    def setUp(self):
        license_patcher = patch(
            'ecole_moderne.licence_middleware._check_license_cached',
            return_value={
                'valid': True,
                'trial': False,
                'days_left': 999,
            },
        )
        integrity_patcher = patch(
            'ecole_moderne.licence_middleware._check_integrity_cached',
            return_value={'valid': True, 'reason': ''},
        )
        license_patcher.start()
        integrity_patcher.start()
        self.addCleanup(license_patcher.stop)
        self.addCleanup(integrity_patcher.stop)

        # Schools (provide required fields)
        self.ecole1 = Ecole.objects.create(
            nom="Ecole A",
            adresse="Adresse A",
            telephone="+224620000001",
            directeur="Dir A",
        )
        self.ecole2 = Ecole.objects.create(
            nom="Ecole B",
            adresse="Adresse B",
            telephone="+224620000002",
            directeur="Dir B",
        )
        # Classes (provide required niveau + annee_scolaire)
        self.classe1 = Classe.objects.create(nom="C1", ecole=self.ecole1, niveau="PRIMAIRE_1", annee_scolaire="2024-2025")
        self.classe2 = Classe.objects.create(nom="C2", ecole=self.ecole2, niveau="PRIMAIRE_1", annee_scolaire="2024-2025")

        # Responsables
        self.resp1 = Responsable.objects.create(prenom="P1", nom="R1", relation="PERE", telephone="+224620000011", adresse="Adr1")
        self.resp2 = Responsable.objects.create(prenom="P2", nom="R2", relation="PERE", telephone="+224620000012", adresse="Adr2")

        # Students (provide all required fields)
        self.eleve1 = Eleve.objects.create(
            nom="Alpha",
            prenom="A",
            matricule="A-001",
            classe=self.classe1,
            sexe='M',
            date_naissance=date(2015, 1, 1),
            lieu_naissance="Conakry",
            date_inscription=date(2024, 9, 1),
            responsable_principal=self.resp1,
        )
        self.eleve2 = Eleve.objects.create(
            nom="Bravo",
            prenom="B",
            matricule="B-001",
            classe=self.classe2,
            sexe='F',
            date_naissance=date(2015, 2, 2),
            lieu_naissance="Conakry",
            date_inscription=date(2024, 9, 1),
            responsable_principal=self.resp2,
        )
        # Payment metadata
        self.type_insc = TypePaiement.objects.create(nom="Frais d'inscription")
        self.mode_espece = ModePaiement.objects.create(nom="Espèces")
        # Payments
        self.paiement1 = Paiement.objects.create(
            eleve=self.eleve1,
            type_paiement=self.type_insc,
            mode_paiement=self.mode_espece,
            montant=30000,
            statut='VALIDE',
            date_paiement=date(2024, 9, 10),
        )
        self.paiement2 = Paiement.objects.create(
            eleve=self.eleve2,
            type_paiement=self.type_insc,
            mode_paiement=self.mode_espece,
            montant=30000,
            statut='VALIDE',
            date_paiement=date(2024, 9, 11),
        )
        self.echeancier1 = EcheancierPaiement.objects.create(
            eleve=self.eleve1,
            annee_scolaire="2024-2025",
            frais_inscription_du=30000,
            tranche_1_due=100000,
            tranche_2_due=0,
            tranche_3_due=0,
            frais_inscription_paye=30000,
            date_echeance_inscription=date(2024, 9, 1),
            date_echeance_tranche_1=date(2024, 10, 1),
            date_echeance_tranche_2=date(2025, 1, 1),
            date_echeance_tranche_3=date(2025, 4, 1),
        )
        self.echeancier2 = EcheancierPaiement.objects.create(
            eleve=self.eleve2,
            annee_scolaire="2024-2025",
            frais_inscription_du=30000,
            tranche_1_due=100000,
            tranche_2_due=0,
            tranche_3_due=0,
            frais_inscription_paye=30000,
            date_echeance_inscription=date(2024, 9, 1),
            date_echeance_tranche_1=date(2024, 10, 1),
            date_echeance_tranche_2=date(2025, 1, 1),
            date_echeance_tranche_3=date(2025, 4, 1),
        )
        # Users
        User = get_user_model()
        self.user1 = User.objects.create_user(username="u1", password="pass12345")
        self.user2 = User.objects.create_user(username="u2", password="pass12345")
        Profil.objects.update_or_create(
            user=self.user1,
            defaults={
                'role': 'COMPTABLE',
                'ecole': self.ecole1,
                'telephone': "+224620000021",
                'peut_consulter_rapports': True,
            },
        )
        Profil.objects.update_or_create(
            user=self.user2,
            defaults={
                'role': 'COMPTABLE',
                'ecole': self.ecole2,
                'telephone': "+224620000022",
                'peut_consulter_rapports': True,
            },
        )

    def login1(self):
        self.client.logout()
        self.client.force_login(self.user1)

    def login2(self):
        self.client.logout()
        self.client.force_login(self.user2)

    def test_api_paiements_list_filtered_by_school(self):
        self.login1()
        url = reverse("paiements:api_paiements_list")
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        ids = [r["id"] for r in data.get("results", [])]
        self.assertIn(self.paiement1.id, ids)
        self.assertNotIn(self.paiement2.id, ids)

    def test_api_paiement_detail_for_other_school_is_404(self):
        self.login1()
        url = reverse("paiements:api_paiement_detail", kwargs={"pk": self.paiement2.id})
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 404)

    def test_ajax_eleve_info_other_school_is_404(self):
        self.login1()
        url = reverse("paiements:ajax_eleve_info")
        resp = self.client.get(url, {"matricule": self.eleve2.matricule})
        self.assertEqual(resp.status_code, 404)

    def test_ajax_eleve_info_own_school_ok(self):
        self.login1()
        url = reverse("paiements:ajax_eleve_info")
        resp = self.client.get(url, {"matricule": self.eleve1.matricule})
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data.get("success"))
        self.assertEqual(data.get("eleve", {}).get("id"), self.eleve1.id)

    def test_annuler_remise_paiement_other_school_is_404(self):
        """Un comptable ne peut pas annuler les remises d'un paiement d'une autre école."""
        self.login1()  # user1 -> ecole1
        url = reverse("paiements:annuler_remise_paiement", kwargs={"paiement_id": self.paiement2.id})
        resp = self.client.post(url)
        self.assertEqual(resp.status_code, 404)

    def test_annuler_remise_paiement_unique_other_school_is_404(self):
        """Même avec un remise_id arbitraire, l'accès à un paiement d'une autre école doit renvoyer 404."""
        self.login1()  # user1 -> ecole1
        # Pas besoin de créer une remise réelle: la vue vérifie d'abord l'accès au paiement
        url = reverse("paiements:annuler_remise_paiement_unique", kwargs={"paiement_id": self.paiement2.id, "remise_id": 999})
        resp = self.client.post(url)
        self.assertEqual(resp.status_code, 404)

    # --- Nouvelles vérifications des vues HTML protégées par require_school_object ---
    def test_detail_paiement_other_school_is_404(self):
        self.login1()
        url = reverse("paiements:detail_paiement", kwargs={"paiement_id": self.paiement2.id})
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 404)

    def test_detail_paiement_lists_all_payments_for_same_student(self):
        second_payment = Paiement.objects.create(
            eleve=self.eleve1,
            type_paiement=self.type_insc,
            mode_paiement=self.mode_espece,
            montant=45000,
            statut='EN_ATTENTE',
            date_paiement=date(2024, 10, 10),
        )
        self.login1()
        url = reverse("paiements:detail_paiement", kwargs={"paiement_id": self.paiement1.id})
        resp = self.client.get(url)

        self.assertEqual(resp.status_code, 200)
        listed_ids = list(resp.context['paiements_eleve'].values_list('id', flat=True))
        self.assertEqual(listed_ids, [second_payment.id, self.paiement1.id])
        self.assertNotIn(self.paiement2.id, listed_ids)
        self.assertEqual(resp.context['historique_resume']['nombre'], 2)
        self.assertContains(resp, second_payment.numero_recu)

    def test_generer_recu_pdf_other_school_is_404(self):
        self.login1()
        url = reverse("paiements:generer_recu_pdf", kwargs={"paiement_id": self.paiement2.id})
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 404)

    def test_echeancier_eleve_other_school_is_404(self):
        self.login1()
        url = reverse("paiements:echeancier_eleve", kwargs={"eleve_id": self.eleve2.id})
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 404)

    def test_relancer_eleve_other_school_is_404(self):
        self.login1()
        url = reverse("paiements:relancer_eleve", kwargs={"eleve_id": self.eleve2.id})
        # La vue est réservée au POST (elle crée une relance et notifie). Un GET
        # serait rejeté en 405 avant même le contrôle d'école : on poste donc
        # pour vérifier réellement la protection d'accès inter-écoles.
        resp = self.client.post(url)
        self.assertEqual(resp.status_code, 404)

    def test_impayes_utilisent_echeancier_et_restent_limites_a_ecole(self):
        self.login1()

        with self.sans_middleware_licence():
            response = self.client.get(reverse("paiements:liste_eleves_impayes"))

        self.assertEqual(response.status_code, 200)
        eleves_affiches = [
            ligne["eleve"].pk for ligne in response.context["eleves_avec_soldes"]
        ]
        self.assertEqual(eleves_affiches, [self.eleve1.pk])

    def test_eleves_soldes_restent_limites_a_ecole(self):
        self.echeancier1.tranche_1_payee = 100000
        self.echeancier1.save(update_fields=["tranche_1_payee"])
        self.echeancier2.tranche_1_payee = 100000
        self.echeancier2.save(update_fields=["tranche_1_payee"])
        self.login1()

        with self.sans_middleware_licence():
            response = self.client.get(
                reverse("paiements:liste_eleves_soldes"),
                {"annee": "2024-2025"},
            )

        self.assertEqual(response.status_code, 200)
        eleves_affiches = [
            echeancier.eleve_id for echeancier in response.context["page_obj"]
        ]
        self.assertEqual(eleves_affiches, [self.eleve1.pk])

    def test_relances_sont_affichees_en_temps_reel_pour_ecole(self):
        relance1 = Relance.objects.create(
            eleve=self.eleve1,
            canal="SMS",
            message="Relance école A",
            solde_estime=100000,
        )
        Relance.objects.create(
            eleve=self.eleve2,
            canal="SMS",
            message="Relance école B",
            solde_estime=100000,
        )
        self.login1()

        with self.sans_middleware_licence():
            response = self.client.get(reverse("paiements:liste_relances"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            [relance.pk for relance in response.context["page_obj"]],
            [relance1.pk],
        )

    def test_eleves_a_relancer_sont_listes_meme_sans_historique(self):
        self.login1()

        with self.sans_middleware_licence():
            response = self.client.get(reverse("paiements:liste_relances"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["total_a_relancer"], 1)
        self.assertEqual(response.context["page_obj"].paginator.count, 0)
        self.assertEqual(
            [
                echeancier.eleve_id
                for echeancier in response.context["a_relancer_page_obj"]
            ],
            [self.eleve1.pk],
        )
        self.assertContains(response, "Jamais relancé")
        self.assertNotContains(response, self.eleve2.matricule)

    def test_rapport_remises_couvre_annee_active_et_filtre_ecole(self):
        remise = RemiseReduction.objects.create(
            nom="Remise test",
            type_remise="MONTANT_FIXE",
            valeur=5000,
            motif="AUTRE",
            date_debut=date(2024, 9, 1),
            date_fin=date(2025, 8, 31),
            actif=True,
        )
        remise_ecole1 = PaiementRemise.objects.create(
            paiement=self.paiement1,
            remise=remise,
            montant_remise=5000,
        )
        PaiementRemise.objects.create(
            paiement=self.paiement2,
            remise=remise,
            montant_remise=5000,
        )
        self.login1()

        with self.sans_middleware_licence():
            response = self.client.get(reverse("rapports:rapport_remises"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["date_debut"], date(2024, 9, 1))
        self.assertEqual(
            [item.pk for item in response.context["remises_appliquees"]],
            [remise_ecole1.pk],
        )
