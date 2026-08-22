"""Rapports professionnels : comptabilité et recouvrement.

Ces tests verrouillent ce qui rendait l'ancien rapport inutilisable en usage
officiel : une date d'arrêt qui ne pilotait pas les retards, une définition du
retard divergente du moteur de paiement, un périmètre de classe absent du
document et un accès non protégé.
"""

from datetime import date, timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import RequestFactory, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from eleves.models import Classe, Ecole, Eleve, Responsable
from paiements.allocation import INSCRIPTION, TRANCHE_1, TRANCHE_2, TRANCHE_3
from paiements.models import (
    EcheancierPaiement,
    ModePaiement,
    Paiement,
    PaiementRemise,
    Relance,
    RemiseReduction,
    TypePaiement,
)
from paiements.rapports_professionnels import (
    _excel_workbook,
    build_recovery_pdf,
    collect_accounting_data,
    collect_recovery_data,
)
from paiements.tests.support import TEST_MIDDLEWARE


@override_settings(MIDDLEWARE=TEST_MIDDLEWARE)
class RapportsProfessionnelsTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_superuser(
            username="compta", email="compta@example.com", password="pass1234",
            first_name="Awa", last_name="Camara",
        )
        self.client.force_login(self.user)
        self.factory = RequestFactory()

        self.ecole = Ecole.objects.create(
            nom="École Test", adresse="Conakry", telephone="+224600000000",
            email="ecole@test.com", directeur="Directeur",
        )
        self.classe = Classe.objects.create(
            ecole=self.ecole, nom="7ème A", niveau="COLLEGE_7",
            annee_scolaire="2024-2025", capacite_max=40,
        )
        self.autre_classe = Classe.objects.create(
            ecole=self.ecole, nom="8ème B", niveau="COLLEGE_8",
            annee_scolaire="2024-2025", capacite_max=40,
        )
        self.responsable = Responsable.objects.create(
            prenom="Jean", nom="Doe", relation="PERE",
            telephone="+224620000000", email="p@example.com", adresse="Addr",
        )

        self.today = timezone.localdate()
        self.mode = ModePaiement.objects.create(nom="Espèces")
        self.type_paiement = TypePaiement.objects.create(nom="Scolarité")

        self.eleve = self._eleve("Alice", "Sow", self.classe)
        self.echeancier = self._echeancier(self.eleve)
        # Une élève de l'autre classe, pour vérifier le cloisonnement.
        self.eleve_autre = self._eleve("Bintou", "Barry", self.autre_classe)
        self._echeancier(self.eleve_autre)

    # -- helpers ----------------------------------------------------------
    def _eleve(self, prenom, nom, classe):
        return Eleve.objects.create(
            matricule=f"TEMP-{prenom.upper()}",
            prenom=prenom, nom=nom, sexe="F",
            date_naissance=date(2012, 5, 4), lieu_naissance="Conakry",
            classe=classe, date_inscription=self.today, statut="ACTIF",
            responsable_principal=self.responsable,
        )

    def _echeancier(self, eleve):
        return EcheancierPaiement.objects.create(
            eleve=eleve, annee_scolaire="2024-2025",
            frais_inscription_du=Decimal("30000"),
            tranche_1_due=Decimal("400000"),
            tranche_2_due=Decimal("300000"),
            tranche_3_due=Decimal("200000"),
            date_echeance_inscription=self.today - timedelta(days=120),
            date_echeance_tranche_1=self.today - timedelta(days=45),
            date_echeance_tranche_2=self.today + timedelta(days=15),
            date_echeance_tranche_3=self.today + timedelta(days=90),
        )

    def _paiement(self, eleve, montant, jour, statut="VALIDE", recu=None, type_paiement=None):
        return Paiement.objects.create(
            eleve=eleve, type_paiement=type_paiement or self.type_paiement,
            mode_paiement=self.mode,
            numero_recu=recu or f"R{Paiement.objects.count() + 1:04d}",
            montant=Decimal(str(montant)), date_paiement=jour,
            annee_scolaire="2024-2025", statut=statut,
            cree_par=self.user, valide_par=self.user if statut == "VALIDE" else None,
        )

    def _request(self, **params):
        request = self.factory.get("/", params)
        request.user = self.user
        request.session = {}
        return request

    def _appliquer_remise_soldante(self):
        type_annuel = TypePaiement.objects.create(nom="Inscription + Tranche 1")
        paiement = self._paiement(
            self.eleve, 830000, self.today, type_paiement=type_annuel,
        )
        remise = RemiseReduction.objects.create(
            nom="Remise solde annuel", type_remise="MONTANT_FIXE",
            valeur=Decimal("100000"), motif="SOCIALE",
            date_debut=self.today - timedelta(days=30),
            date_fin=self.today + timedelta(days=30), actif=True,
        )
        PaiementRemise.objects.create(
            paiement=paiement, remise=remise, montant_remise=Decimal("100000"),
            applique_tranche_3=True, montant_tranche_3=Decimal("100000"),
            base_calcul="TRANCHE", montant_base=Decimal("200000"),
            motif="GESTE_COMMERCIAL",
        )

    # -- comptabilité -----------------------------------------------------
    def test_comptabilite_separe_encaisse_remise_et_brut(self):
        paiement = self._paiement(self.eleve, 100000, self.today)
        remise = RemiseReduction.objects.create(
            nom="Fratrie", type_remise="MONTANT_FIXE", valeur=Decimal("20000"),
            motif="FRATRIE", date_debut=self.today - timedelta(days=30),
            date_fin=self.today + timedelta(days=180), actif=True,
        )
        PaiementRemise.objects.create(
            paiement=paiement, remise=remise, montant_remise=Decimal("20000"),
            applique_tranche_1=True, montant_tranche_1=Decimal("20000"),
            base_calcul="TRANCHE", montant_base=Decimal("400000"),
            motif="GESTE_COMMERCIAL", deduite_du_paiement=True,
        )

        data = collect_accounting_data(self._request(classe_id=self.classe.pk))
        self.assertEqual(data["validated_count"], 1)
        self.assertEqual(data["total_cash"], Decimal("100000"))
        self.assertEqual(data["total_discount"], Decimal("20000"))
        self.assertEqual(data["total_deducted"], Decimal("20000"))
        # Le brut reconstitue ce qui a été facturé avant déduction.
        self.assertEqual(data["total_gross"], Decimal("120000"))
        self.assertEqual(data["total_coverage"], Decimal("120000"))

    def test_comptabilite_compte_tous_les_statuts_mais_n_encaisse_que_les_valides(self):
        self._paiement(self.eleve, 100000, self.today)
        self._paiement(self.eleve, 50000, self.today, statut="EN_ATTENTE")
        self._paiement(self.eleve, 25000, self.today, statut="REJETE")

        data = collect_accounting_data(self._request(classe_id=self.classe.pk))
        self.assertEqual(data["payment_count"], 3)
        self.assertEqual(data["validated_count"], 1)
        self.assertEqual(data["total_cash"], Decimal("100000"))
        self.assertEqual(data["by_status"]["EN_ATTENTE"]["count"], 1)
        self.assertEqual(data["by_status"]["REJETE"]["amount"], Decimal("25000"))

    def test_comptabilite_respecte_les_bornes_de_periode(self):
        self._paiement(self.eleve, 100000, self.today - timedelta(days=10))
        self._paiement(self.eleve, 70000, self.today)

        data = collect_accounting_data(self._request(
            classe_id=self.classe.pk,
            du=(self.today - timedelta(days=2)).isoformat(),
            au=self.today.isoformat(),
        ))
        self.assertEqual(data["validated_count"], 1)
        self.assertEqual(data["total_cash"], Decimal("70000"))

    def test_le_perimetre_de_classe_est_ecrit_dans_le_document(self):
        data = collect_accounting_data(self._request(classe_id=self.classe.pk))
        self.assertEqual(data["scope_label"], f"Classe : {self.classe.nom}")
        self.assertTrue(data["reference"].startswith("RC-"))
        self.assertIn("7", data["reference"])

    def test_classe_hors_perimetre_est_exclue(self):
        self._paiement(self.eleve_autre, 500000, self.today)
        data = collect_accounting_data(self._request(classe_id=self.classe.pk))
        self.assertEqual(data["validated_count"], 0)
        self.assertEqual(data["total_cash"], Decimal("0"))

    # -- recouvrement -----------------------------------------------------
    def test_recouvrement_solde_et_retard_suivent_le_moteur(self):
        # Type « Scolarité » : les 130 000 vont sur les tranches, jamais sur
        # l'inscription. T1 reste donc due à hauteur de 270 000.
        self._paiement(self.eleve, 130000, self.today - timedelta(days=50))

        data = collect_recovery_data(self._request(classe_id=self.classe.pk))
        self.assertEqual(data["total_due"], Decimal("930000"))
        self.assertEqual(data["total_cash"], Decimal("130000"))
        self.assertEqual(data["total_balance"], Decimal("800000"))
        # Seules l'inscription (30 000) et T1 (270 000) sont échues.
        self.assertEqual(data["total_overdue"], Decimal("300000"))
        self.assertEqual(data["overdue_count"], 1)
        # T2 échoit dans 15 jours : elle alimente les échéances à 30 jours.
        self.assertEqual(data["total_upcoming"], Decimal("300000"))

    def test_une_echeance_du_jour_meme_n_est_pas_en_retard(self):
        """Le moteur n'exige une échéance qu'à partir du lendemain."""
        self.echeancier.date_echeance_inscription = self.today
        self.echeancier.date_echeance_tranche_1 = self.today
        self.echeancier.date_echeance_tranche_2 = self.today + timedelta(days=30)
        self.echeancier.save()

        data = collect_recovery_data(self._request(classe_id=self.classe.pk))
        self.assertEqual(data["total_overdue"], Decimal("0"))
        self.assertEqual(data["overdue_count"], 0)

    def test_la_date_d_arret_pilote_aussi_les_retards(self):
        """Une situation arrêtée avant l'échéance ne montre aucun retard."""
        cutoff = self.today - timedelta(days=60)
        data = collect_recovery_data(self._request(
            classe_id=self.classe.pk, au=cutoff.isoformat(),
        ))
        self.assertEqual(data["cutoff"], cutoff)
        self.assertTrue(data["historical_cutoff"])
        # À cette date, seule l'inscription (échue à J-120) est exigible.
        self.assertEqual(data["total_overdue"], Decimal("30000"))

    def test_un_paiement_posterieur_a_la_date_d_arret_est_ignore(self):
        self._paiement(self.eleve, 430000, self.today)
        cutoff = self.today - timedelta(days=10)
        data = collect_recovery_data(self._request(
            classe_id=self.classe.pk, au=cutoff.isoformat(),
        ))
        self.assertEqual(data["total_cash"], Decimal("0"))
        self.assertEqual(data["total_balance"], Decimal("930000"))

    def test_balance_agee_classe_le_retard_par_anciennete(self):
        data = collect_recovery_data(self._request(classe_id=self.classe.pk))
        # Inscription échue depuis 120 jours, T1 depuis 45 jours.
        self.assertEqual(data["aging"]["31-60 jours"]["amount"], Decimal("400000"))
        self.assertEqual(data["aging"]["Plus de 90 jours"]["amount"], Decimal("30000"))
        self.assertEqual(data["aging"]["1-30 jours"]["count"], 0)

    def test_ventilation_par_poste(self):
        # Ce type couvre l'admission puis déborde sur les tranches.
        type_admission = TypePaiement.objects.create(nom="Inscription + Tranche 1")
        self._paiement(
            self.eleve, 130000, self.today - timedelta(days=50),
            type_paiement=type_admission,
        )
        data = collect_recovery_data(self._request(classe_id=self.classe.pk))
        buckets = data["bucket_summary"]
        self.assertEqual(buckets[INSCRIPTION]["cash"], Decimal("30000"))
        self.assertEqual(buckets[INSCRIPTION]["balance"], Decimal("0"))
        self.assertEqual(buckets[TRANCHE_1]["cash"], Decimal("100000"))
        self.assertEqual(buckets[TRANCHE_1]["balance"], Decimal("300000"))
        self.assertEqual(buckets[TRANCHE_2]["balance"], Decimal("300000"))
        self.assertEqual(buckets[TRANCHE_3]["balance"], Decimal("200000"))

    def test_une_remise_peut_solder_et_reste_explicitement_signalee(self):
        self._appliquer_remise_soldante()

        data = collect_recovery_data(self._request(classe_id=self.classe.pk))
        student = data["student_rows"][0]

        self.assertEqual(data["total_discount"], Decimal("100000"))
        self.assertEqual(data["total_balance"], Decimal("0"))
        self.assertEqual(data["settled_count"], 1)
        self.assertEqual(data["settled_with_discount_count"], 1)
        self.assertEqual(student["status"], "Soldé avec remise")
        self.assertIn("Remise appliquée : 100 000 GNF", student["precision"])
        self.assertAlmostEqual(float(student["discount_rate"]), 10.7527, places=4)

    def test_excel_recouvrement_detaille_montant_taux_et_precision_remise(self):
        from io import BytesIO

        from openpyxl import load_workbook

        self._appliquer_remise_soldante()
        response = self.client.get(
            reverse("paiements:export_recouvrement_excel"),
            {"classe_id": self.classe.pk},
        )

        workbook = load_workbook(BytesIO(response.content), data_only=True)
        sheet = workbook["Portefeuille élèves"]
        headers = [cell.value for cell in sheet[5]]
        row = dict(zip(headers, [cell.value for cell in sheet[6]]))

        self.assertEqual(row["Encaissé"], 830000)
        self.assertEqual(row["Remises"], 100000)
        self.assertAlmostEqual(row["Remise (%)"], 10.8, places=1)
        self.assertEqual(row["Solde"], 0)
        self.assertEqual(row["Situation"], "Soldé avec remise")
        self.assertIn("Remise appliquée : 100 000 GNF", row["Précision remise"])

    def test_pdf_recouvrement_contient_les_remises_par_eleve(self):
        from unittest.mock import patch

        from reportlab.platypus import Table

        self._appliquer_remise_soldante()
        data = collect_recovery_data(self._request(classe_id=self.classe.pk))

        with patch('reportlab.platypus.SimpleDocTemplate.build') as build_pdf:
            build_recovery_pdf(data)

        elements = build_pdf.call_args.args[0]
        detail = next(
            element for element in elements
            if isinstance(element, Table)
            and element._cellvalues
            and all(hasattr(cell, 'getPlainText') for cell in element._cellvalues[0])
            and 'Situation / précision' in [
                cell.getPlainText() for cell in element._cellvalues[0]
            ]
        )
        headers = [cell.getPlainText() for cell in detail._cellvalues[0]]
        row = dict(zip(headers, detail._cellvalues[1]))
        self.assertEqual(row['Remise'].getPlainText(), '100 000')
        self.assertEqual(row['Remise %'].getPlainText(), '10.8 %')
        self.assertIn('Soldé avec remise', row['Situation / précision'].getPlainText())
        self.assertIn('Remise appliquée : 100 000 GNF', row['Situation / précision'].getPlainText())

    def test_logo_ecole_est_present_sur_pdf_excel_et_filigrane(self):
        from pathlib import Path
        from unittest.mock import MagicMock, patch

        from django.conf import settings

        logo_path = str(Path(settings.BASE_DIR) / 'static' / 'logos' / 'logo.png')
        data = collect_recovery_data(self._request(classe_id=self.classe.pk))

        with patch(
            'paiements.rapports_professionnels._get_logo_path',
            return_value=logo_path,
        ):
            with patch('reportlab.platypus.SimpleDocTemplate.build') as build_pdf:
                build_recovery_pdf(data)

            canvas = MagicMock()
            callback = build_pdf.call_args.kwargs['onFirstPage']
            callback(canvas, MagicMock())
            self.assertGreaterEqual(canvas.drawImage.call_count, 2)

            workbook = _excel_workbook(data, 'recovery')
            self.assertTrue(workbook.worksheets)
            self.assertTrue(all(sheet._images for sheet in workbook.worksheets))

    def test_relances_posterieures_a_la_date_d_arret_sont_exclues(self):
        Relance.objects.create(
            eleve=self.eleve, canal="SMS", message="Rappel", statut="ENVOYEE",
            solde_estime=Decimal("900000"), cree_par=self.user,
        )
        cutoff = self.today - timedelta(days=1)
        data = collect_recovery_data(self._request(
            classe_id=self.classe.pk, au=cutoff.isoformat(),
        ))
        self.assertEqual(len(data["period_relances"]), 0)
        self.assertEqual(data["student_rows"][0]["reminder_count"], 0)

        data = collect_recovery_data(self._request(classe_id=self.classe.pk))
        self.assertEqual(len(data["period_relances"]), 1)
        self.assertEqual(data["reminder_by_channel"]["SMS"]["sent"], 1)

    def test_filtres_invalides_sont_refuses(self):
        with self.assertRaises(ValueError):
            collect_recovery_data(self._request(du="01/02/2025"))
        with self.assertRaises(ValueError):
            collect_recovery_data(self._request(
                du=self.today.isoformat(),
                au=(self.today - timedelta(days=5)).isoformat(),
            ))
        with self.assertRaises(ValueError):
            collect_recovery_data(self._request(classe_id="abc"))
        with self.assertRaises(ValueError):
            collect_recovery_data(self._request(annee_scolaire="2024"))

    # -- rendu et accès ---------------------------------------------------
    def test_exports_pdf_et_excel(self):
        self._paiement(self.eleve, 130000, self.today - timedelta(days=50))
        Relance.objects.create(
            eleve=self.eleve, canal="WHATSAPP", message="Rappel", statut="ENVOYEE",
            solde_estime=Decimal("800000"), cree_par=self.user,
        )
        cas = [
            ("paiements:export_comptabilite_pdf", "application/pdf", b"%PDF"),
            ("paiements:export_recouvrement_pdf", "application/pdf", b"%PDF"),
            ("paiements:export_comptabilite_excel", "spreadsheetml", b"PK"),
            ("paiements:export_recouvrement_excel", "spreadsheetml", b"PK"),
        ]
        for nom, content_type, entete in cas:
            with self.subTest(export=nom):
                resp = self.client.get(reverse(nom), {"classe_id": self.classe.pk})
                self.assertEqual(resp.status_code, 200)
                self.assertIn(content_type, resp["Content-Type"])
                self.assertTrue(resp.content.startswith(entete))
                self.assertIn("attachment; filename=", resp["Content-Disposition"])

    def test_rapport_vide_reste_generable(self):
        for nom in ("paiements:export_comptabilite_pdf", "paiements:export_recouvrement_pdf"):
            with self.subTest(export=nom):
                resp = self.client.get(reverse(nom), {"classe_id": self.autre_classe.pk})
                self.assertEqual(resp.status_code, 200)
                self.assertTrue(resp.content.startswith(b"%PDF"))

    def test_date_invalide_renvoie_400(self):
        resp = self.client.get(
            reverse("paiements:export_recouvrement_pdf"), {"du": "hier"},
        )
        self.assertEqual(resp.status_code, 400)

    def test_acces_refuse_sans_permission_de_consulter_les_rapports(self):
        User = get_user_model()
        agent = User.objects.create_user(username="agent", password="pass1234")
        profil = getattr(agent, "profil", None)
        if profil is None:
            self.skipTest("Aucun profil utilisateur associé automatiquement.")
        profil.peut_consulter_rapports = False
        profil.save()

        self.client.force_login(agent)
        resp = self.client.get(reverse("paiements:export_recouvrement_pdf"))
        self.assertNotEqual(resp.status_code, 200)
