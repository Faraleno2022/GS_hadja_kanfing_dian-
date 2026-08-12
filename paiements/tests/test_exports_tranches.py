from datetime import date
from decimal import Decimal
from io import BytesIO
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from openpyxl import load_workbook

from eleves.models import Classe, Ecole, Eleve, Responsable
from paiements.models import EcheancierPaiement


class ExportTranchesParClasseTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_superuser(
            username='admin-export-tranches',
            email='admin-export@example.com',
            password='mot-de-passe-test',
        )
        self.client.force_login(self.user)
        self.ecole = Ecole.objects.create(
            nom='École export',
            adresse='Conakry',
            telephone='+224620000001',
            directeur='Direction export',
        )
        self.classe = Classe.objects.create(
            ecole=self.ecole,
            nom='Classe export',
            niveau='COLLEGE_8',
            annee_scolaire='2025-2026',
        )
        responsable = Responsable.objects.create(
            prenom='Parent',
            nom='Export',
            relation='PERE',
            telephone='+224620000002',
        )
        self.eleve = Eleve.objects.create(
            matricule='EXP-001',
            prenom='Élève',
            nom='Export',
            sexe='F',
            date_naissance=date(2014, 1, 1),
            classe=self.classe,
            date_inscription=date(2025, 9, 1),
            responsable_principal=responsable,
        )
        EcheancierPaiement.objects.create(
            eleve=self.eleve,
            annee_scolaire='2025-2026',
            nature_frais=EcheancierPaiement.NATURE_REINSCRIPTION,
            frais_inscription_du=Decimal('30000'),
            frais_inscription_paye=Decimal('30000'),
            tranche_1_due=Decimal('500000'),
            tranche_1_payee=Decimal('100000'),
            tranche_2_due=Decimal('500000'),
            tranche_3_due=Decimal('500000'),
            date_echeance_inscription=date(2025, 9, 30),
            date_echeance_tranche_1=date(2026, 1, 10),
            date_echeance_tranche_2=date(2026, 3, 5),
            date_echeance_tranche_3=date(2026, 5, 5),
        )

    @property
    def filtres(self):
        return {'classe': self.classe.pk, 'annee_scolaire': '2025-2026'}

    def test_excel_separe_inscription_et_reinscription(self):
        response = self.client.get(
            reverse('paiements:export_tranches_par_classe_excel'),
            self.filtres,
        )

        self.assertEqual(response.status_code, 200)
        workbook = load_workbook(BytesIO(response.content), data_only=True)
        self.assertGreaterEqual(len(workbook.worksheets), 2)
        sheet = workbook.worksheets[1]
        self.assertEqual(sheet.cell(2, 2).value, 'Inscription payée')
        self.assertEqual(sheet.cell(2, 3).value, 'Réinscription payée')
        self.assertEqual(sheet.cell(3, 2).value, 0)
        self.assertEqual(sheet.cell(3, 3).value, 30000)
        self.assertEqual(sheet.cell(3, 8).value, 130000)

    def test_pdf_contient_la_colonne_reinscription(self):
        from reportlab.platypus import Table as ReportLabTable

        tables = []

        def capture_table(data, *args, **kwargs):
            tables.append(data)
            return ReportLabTable(data, *args, **kwargs)

        with patch('reportlab.platypus.Table', side_effect=capture_table):
            response = self.client.get(
                reverse('paiements:export_tranches_par_classe_pdf'),
                self.filtres,
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/pdf')
        header = [cell.getPlainText() for cell in tables[0][0]]
        self.assertEqual(header[1:3], ['Inscription payée', 'Réinscription payée'])
        self.assertEqual(tables[0][1][1:3], ['0', '30 000'])
