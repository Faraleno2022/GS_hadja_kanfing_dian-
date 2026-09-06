from datetime import date
from decimal import Decimal
from io import BytesIO

from django.contrib.auth import get_user_model
from django.test import SimpleTestCase, TestCase, override_settings
from django.urls import reverse
from openpyxl import load_workbook

from eleves.models import Classe, Ecole, Eleve, GrilleTarifaire, Responsable
from paiements.allocation import payment_type_plan
from paiements.models import (
    EcheancierPaiement,
    ModePaiement,
    Paiement,
    PaiementRemise,
    RemiseReduction,
    TypePaiement,
)
from paiements.tests.support import MIDDLEWARE_SANS_LICENCE
from paiements.views import _allocate_combined_payment, ensure_echeancier_for_eleve


class PaymentTypePlanTests(SimpleTestCase):
    def test_variantes_de_libelles_sont_reconnues(self):
        scenarios = (
            ("Réinscription + Tranche 1", "reinscription", (1,)),
            ("REINSCRIPTION + 1ere tranche + 2ème tranche", "reinscription", (1, 2)),
            ("Frais d'inscription + Annuel", "inscription", (1, 2, 3)),
            ("Scolarité - T2", None, (2,)),
            ("Scolarité annuelle", None, (1, 2, 3)),
            ("Première tranche + troisième tranche", None, (1, 3)),
            ("Deuxième tranche", None, (2,)),
        )
        for label, kind, tranches in scenarios:
            with self.subTest(label=label):
                plan = payment_type_plan(label)
                self.assertEqual(plan["registration_kind"], kind)
                self.assertEqual(plan["tranches"], tranches)

    def test_libelles_combines_et_plages_sont_additifs(self):
        """Chaque poste nommé s'ajoute : rien n'est perdu ni inventé."""
        scenarios = (
            # (libellé, admission facturée, tranches facturées)
            ("Inscription + Tranche 1 + Tranche 3", True, (1, 3)),
            ("Tranches 1 à 3", False, (1, 2, 3)),
            ("T1-T3", False, (1, 2, 3)),
            ("Réinscription + tranches 1 et 2", True, (1, 2)),
            ("Tranche deux", False, (2,)),
            ("2ème trimestre", False, (2,)),
            ("Frais d'admission", True, ()),
            # Un poste nommé prime sur l'élargissement au reste de l'année.
            ("Solde tranche 2", False, (2,)),
            # Les retraits explicites enlèvent un poste au lieu d'en ajouter.
            ("Scolarité sans inscription", False, (1, 2, 3)),
            ("Annuel sauf tranche 3", False, (1, 2)),
            # Aucun poste de l'échéancier : la saisie reste manuelle.
            ("Cantine", False, ()),
            ("Transport scolaire mensuel", False, ()),
        )
        for label, admission, tranches in scenarios:
            with self.subTest(label=label):
                plan = payment_type_plan(label)
                self.assertEqual(plan["include_registration"], admission)
                self.assertEqual(plan["tranches"], tranches)

    def test_solde_seul_couvre_toute_l_annee(self):
        plan = payment_type_plan("Solde")

        self.assertTrue(plan["covers_balance"])
        self.assertTrue(plan["include_registration"])
        self.assertEqual(plan["tranches"], (1, 2, 3))


@override_settings(MIDDLEWARE=MIDDLEWARE_SANS_LICENCE)
class InscriptionReinscriptionIntegrationTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_superuser(
            username="admin_admission",
            email="admin-admission@example.com",
            password=None,
        )
        self.client.force_login(self.user)

        self.ecole = Ecole.objects.create(
            nom="École ventilation admission",
            adresse="Conakry",
            telephone="+224620000101",
            directeur="Direction",
        )
        self.classe = Classe.objects.create(
            ecole=self.ecole,
            nom="6ème test",
            niveau="PRIMAIRE_6",
            annee_scolaire="2024-2025",
        )
        self.grille = GrilleTarifaire.objects.create(
            ecole=self.ecole,
            niveau=self.classe.niveau,
            annee_scolaire="2024-2025",
            frais_inscription=Decimal("30000"),
            frais_reinscription=Decimal("20000"),
            tranche_1=Decimal("100000"),
            tranche_2=0,
            tranche_3=0,
        )
        self.responsable = Responsable.objects.create(
            prenom="Parent",
            nom="Test",
            relation="PERE",
            telephone="+224620000102",
            adresse="Conakry",
        )
        self.eleve_inscription = self._create_eleve("ADM-I", "Inscrit")
        self.eleve_reinscription = self._create_eleve("ADM-R", "Réinscrit")
        self.echeancier_inscription = self._create_echeancier(
            self.eleve_inscription,
            EcheancierPaiement.NATURE_INSCRIPTION,
            Decimal("30000"),
        )
        self.echeancier_reinscription = self._create_echeancier(
            self.eleve_reinscription,
            EcheancierPaiement.NATURE_REINSCRIPTION,
            Decimal("20000"),
        )
        self.type_reinscription_t1 = TypePaiement.objects.create(
            nom="Réinscription + Tranche 1"
        )
        self.mode = ModePaiement.objects.create(nom="Espèces admission")

    def _create_eleve(self, matricule, prenom):
        return Eleve.objects.create(
            matricule=matricule,
            prenom=prenom,
            nom="Test",
            sexe="F",
            date_naissance=date(2015, 1, 1),
            lieu_naissance="Conakry",
            classe=self.classe,
            date_inscription=date(2024, 9, 1),
            responsable_principal=self.responsable,
        )

    def _create_echeancier(self, eleve, nature, frais):
        return EcheancierPaiement.objects.create(
            eleve=eleve,
            annee_scolaire="2024-2025",
            nature_frais=nature,
            frais_inscription_du=frais,
            tranche_1_due=Decimal("100000"),
            tranche_2_due=0,
            tranche_3_due=0,
            date_echeance_inscription=date(2024, 9, 30),
            date_echeance_tranche_1=date(2025, 1, 10),
            date_echeance_tranche_2=date(2025, 3, 5),
            date_echeance_tranche_3=date(2025, 4, 6),
        )

    def test_nature_reinscription_est_persistee_meme_si_les_tarifs_sont_identiques(self):
        self.grille.frais_inscription = Decimal("20000")
        self.grille.save(update_fields=["frais_inscription"])

        echeancier = ensure_echeancier_for_eleve(
            self.eleve_inscription,
            registration_kind="reinscription",
        )
        echeancier.refresh_from_db()

        self.assertEqual(
            echeancier.nature_frais,
            EcheancierPaiement.NATURE_REINSCRIPTION,
        )
        self.assertEqual(echeancier.frais_inscription_du, Decimal("20000"))
        self.assertEqual(echeancier.libelle_frais_admission, "Frais de réinscription")

    def test_reinscription_plus_t1_est_repartie_dans_le_bon_ordre(self):
        paiement = Paiement.objects.create(
            eleve=self.eleve_reinscription,
            type_paiement=self.type_reinscription_t1,
            mode_paiement=self.mode,
            montant=Decimal("120000"),
            date_paiement=date(2024, 9, 30),
            statut="VALIDE",
            numero_recu="REC-ADM-R",
        )

        allocation = _allocate_combined_payment(
            paiement,
            self.echeancier_reinscription,
        )
        self.echeancier_reinscription.refresh_from_db()

        self.assertEqual(allocation["inscription"], Decimal("20000"))
        self.assertEqual(allocation["tranche_1"], Decimal("100000"))
        self.assertEqual(allocation["tranche_2"], Decimal("0"))
        self.assertEqual(
            self.echeancier_reinscription.nature_frais,
            EcheancierPaiement.NATURE_REINSCRIPTION,
        )

    def test_suggestion_reinscription_est_exacte_et_sans_effet_de_bord(self):
        response = self.client.post(
            reverse("paiements:ajax_montant_suggere"),
            {
                "eleve_id": self.eleve_inscription.pk,
                "type_id": self.type_reinscription_t1.pk,
            },
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["suggested"], 120000)
        self.assertEqual(payload["breakdown"]["fi_restant"], 20000)
        self.assertEqual(
            payload["breakdown"]["frais_admission_label"],
            "Réinscription",
        )
        self.echeancier_inscription.refresh_from_db()
        self.assertEqual(
            self.echeancier_inscription.nature_frais,
            EcheancierPaiement.NATURE_INSCRIPTION,
        )
        self.assertEqual(
            self.echeancier_inscription.frais_inscription_du,
            Decimal("30000"),
        )

    def test_suggestion_ne_cree_pas_un_echeancier(self):
        eleve_sans_echeancier = self._create_eleve("ADM-S", "Sans échéancier")
        count_before = EcheancierPaiement.objects.count()

        response = self.client.post(
            reverse("paiements:ajax_montant_suggere"),
            {
                "eleve_id": eleve_sans_echeancier.pk,
                "type_id": self.type_reinscription_t1.pk,
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["suggested"], 120000)
        self.assertEqual(EcheancierPaiement.objects.count(), count_before)
        self.assertFalse(
            EcheancierPaiement.objects.filter(eleve=eleve_sans_echeancier).exists()
        )

    def test_liste_separe_strictement_inscription_et_reinscription(self):
        response = self.client.get(
            reverse("paiements:liste_paiements"),
            {"annee": "2024-2025"},
        )

        self.assertEqual(response.status_code, 200)
        totals = response.context["totaux_du"]
        self.assertEqual(totals["du_sco_net"], 200000)
        self.assertEqual(totals["frais_inscription_total"], 30000)
        self.assertEqual(totals["frais_reinscription_total"], 20000)
        self.assertEqual(totals["du_global_net"], 250000)
        self.assertEqual(totals["frais_reinscription_pct"], 40.0)

        rows = response.context["totaux_du_detail_classes"]
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["frais_inscription_total"], 30000)
        self.assertEqual(rows[0]["frais_reinscription_total"], 20000)
        self.assertEqual(rows[0]["du_global_net"], 250000)

    def test_export_excel_conserve_la_meme_ventilation(self):
        response = self.client.get(reverse("paiements:export_recap_par_classe_excel"))

        self.assertEqual(response.status_code, 200)
        workbook = load_workbook(BytesIO(response.content), data_only=True)
        values = list(workbook.active.iter_rows(min_row=2, max_row=2, values_only=True))[0]
        self.assertEqual(values[4], 30000)
        self.assertEqual(values[5], 20000)
        self.assertEqual(values[6], 40.0)
        self.assertEqual(values[7], 250000)

    def test_plusieurs_remises_ne_multiplient_pas_les_montants_dus(self):
        paiement = Paiement.objects.create(
            eleve=self.eleve_inscription,
            type_paiement=self.type_reinscription_t1,
            mode_paiement=self.mode,
            montant=Decimal("50000"),
            date_paiement=date(2024, 10, 1),
            statut="VALIDE",
            numero_recu="REC-REMISES",
        )
        for index, montant in enumerate((Decimal("5000"), Decimal("10000")), start=1):
            remise = RemiseReduction.objects.create(
                nom=f"Remise {index}",
                type_remise="MONTANT_FIXE",
                valeur=montant,
                motif="AUTRE",
                date_debut=date(2024, 9, 1),
                date_fin=date(2025, 8, 31),
            )
            PaiementRemise.objects.create(
                paiement=paiement,
                remise=remise,
                montant_remise=montant,
            )

        response = self.client.get(
            reverse("paiements:liste_paiements"),
            {"annee": "2024-2025"},
        )

        totals = response.context["totaux_du"]
        self.assertEqual(totals["du_sco_net"], 185000)
        self.assertEqual(totals["frais_inscription_total"], 30000)
        self.assertEqual(totals["frais_reinscription_total"], 20000)
        self.assertEqual(totals["du_global_net"], 235000)

    def test_echeancier_affiche_le_libelle_reinscription(self):
        response = self.client.get(
            reverse(
                "paiements:echeancier_eleve",
                kwargs={"eleve_id": self.eleve_reinscription.pk},
            )
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Frais de réinscription")

    def _versements_recap(self):
        for index, (eleve, statut) in enumerate((
            (self.eleve_inscription, 'VALIDE'),
            (self.eleve_inscription, 'VALIDE'),
            (self.eleve_inscription, 'EN_ATTENTE'),
            (self.eleve_inscription, 'REJETE'),
            (self.eleve_reinscription, 'VALIDE'),
        )):
            Paiement.objects.create(
                eleve=eleve, type_paiement=self.type_reinscription_t1,
                mode_paiement=self.mode, montant=10000, statut=statut,
                annee_scolaire='2024-2025', date_paiement=date(2024, 10, 1),
                numero_recu=f'RECAP-MULTI-{index}',
            )

    def test_recap_plusieurs_versements_compte_chaque_du_une_fois(self):
        self._versements_recap()
        # Deux élèves avec la même scolarité : SUM(DISTINCT montant) serait faux.
        response = self.client.get(reverse('paiements:liste_paiements'), {'annee': '2024-2025'})
        self.assertEqual(response.status_code, 200)
        totals = response.context['totaux_du']
        self.assertEqual(totals['eleves_count'], 2)
        self.assertEqual(totals['du_sco_net'], 200000)
        self.assertEqual(totals['du_global_net'], 250000)
        row = response.context['totaux_du_detail_classes'][0]
        self.assertEqual(row['eleves_count'], 2)
        self.assertEqual(row['du_sco_net'], 200000)
        self.assertEqual(row['du_global_net'], 250000)
        self.assertEqual(response.context['totaux']['montant_total_valide'], 30000)

    def test_recherche_recap_ne_multiplie_pas_les_dus(self):
        self._versements_recap()
        for query, count, due in [('Test', 2, 250000), ('RECAP-MULTI', 2, 250000), ('ADM-I', 1, 130000)]:
            with self.subTest(query=query):
                response = self.client.get(reverse('paiements:liste_paiements'), {'q': query, 'annee': '2024-2025'})
                self.assertEqual(response.context['totaux_du']['du_global_net'], due)
                rows = response.context['totaux_du_detail_classes']
                self.assertEqual(sum(row['du_global_net'] for row in rows), due)
                self.assertEqual(sum(row['eleves_count'] for row in rows), count)

    def test_export_recap_plusieurs_versements_et_remises(self):
        self._versements_recap()
        for index, montant in enumerate([5000, 10000]):
            remise = RemiseReduction.objects.create(
                nom=f'Remise multi {index}', type_remise='MONTANT_FIXE', valeur=montant,
                motif='AUTRE', date_debut=date(2024, 9, 1), date_fin=date(2025, 8, 31),
            )
            PaiementRemise.objects.create(
                paiement=Paiement.objects.get(numero_recu=f'RECAP-MULTI-{index}'),
                remise=remise, montant_remise=montant,
            )
        for query in ('', 'Test'):
            with self.subTest(query=query):
                response = self.client.get(reverse('paiements:export_recap_par_classe_excel'), {'q': query})
                self.assertEqual(response.status_code, 200)
                workbook = load_workbook(BytesIO(response.content), data_only=True)
                rows = list(workbook.active.iter_rows(min_row=2, values_only=True))
                self.assertEqual(len(rows), 1)
                self.assertEqual(rows[0][2], 2)
                self.assertEqual(rows[0][3], 185000)
                self.assertEqual(rows[0][4:6], (30000, 20000))
                self.assertEqual(rows[0][7], 235000)
                screen = self.client.get(reverse('paiements:liste_paiements'), {'q': query})
                self.assertEqual(screen.context['totaux_du_detail_classes'][0]['du_global_net'], rows[0][7])

    def test_transfert_recap_ne_compte_pas_eleve_dans_deux_classes(self):
        self._versements_recap()
        classe_b = Classe.objects.create(ecole=self.ecole, nom='6eme B', niveau=self.classe.niveau,
                                        annee_scolaire='2024-2025')
        self.eleve_inscription.classe = classe_b
        self.eleve_inscription.save()
        response = self.client.get(reverse('paiements:liste_paiements'))
        rows = {row['classe_id']: row for row in response.context['totaux_du_detail_classes']}
        self.assertEqual(rows[self.classe.pk]['eleves_count'], 1)
        self.assertEqual(rows[self.classe.pk]['du_global_net'], 120000)
        self.assertEqual(rows[classe_b.pk]['eleves_count'], 1)
        self.assertEqual(rows[classe_b.pk]['du_global_net'], 130000)
        self.assertEqual(response.context['totaux_du']['du_global_net'], 250000)

    def test_tableau_bord_classe_ne_multiplie_pas_le_du(self):
        self._versements_recap()
        response = self.client.get(reverse('paiements:tableau_bord'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['finance_direction']['total_du'], 250000)
        rows = response.context['classes_a_risque']
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]['eleves_count'], 2)
        self.assertEqual(rows[0]['total_du'], 250000)

    def test_rapport_et_export_tranches_comptent_chaque_eleve_une_fois(self):
        from django.test import RequestFactory
        from paiements.rapports_professionnels import collect_recovery_data
        from paiements.views_tranches import _tranche_export_rows
        self._versements_recap()
        request = RequestFactory().get('/paiements/liste/', {
            'classe_id': self.classe.pk, 'annee_scolaire': '2024-2025',
        })
        request.user = self.user
        data = collect_recovery_data(request)
        self.assertEqual(data['schedule_count'], 2)
        self.assertEqual(data['total_due'], 250000)
        self.assertEqual(data['total_cash'], 30000)
        self.assertEqual(sum(row['due'] for row in data['class_summary'].values()), 250000)
        rows = _tranche_export_rows(self.classe, '2024-2025')
        self.assertEqual(len(rows), 2)
        self.assertEqual(sum(row['total_due'] for row in rows), 250000)
        self.assertEqual(sum(row['total_paid'] for row in rows), 30000)
