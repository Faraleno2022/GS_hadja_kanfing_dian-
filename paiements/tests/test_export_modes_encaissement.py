from datetime import date
from decimal import Decimal
from io import BytesIO

from django.contrib.auth import get_user_model
from django.test import RequestFactory, TestCase, override_settings
from django.urls import reverse
from openpyxl import load_workbook

from eleves.models import Classe, Ecole, Eleve, Responsable
from paiements.models import (
    EcheancierPaiement,
    ModePaiement,
    Paiement,
    TypePaiement,
)
from paiements.export_modes_encaissement import collect_modes_encaissement_data
from paiements.views_modes_encaissement import collect_modes_students_data
from paiements.tests.support import MIDDLEWARE_SANS_LICENCE
from utilisateurs.models import Profil


@override_settings(MIDDLEWARE=MIDDLEWARE_SANS_LICENCE)
class ExportModesEncaissementTests(TestCase):
    def setUp(self):
        self.ecole = Ecole.objects.create(
            nom='École Encaissements',
            adresse='Conakry',
            telephone='+224620000001',
            directeur='Direction',
        )
        self.autre_ecole = Ecole.objects.create(
            nom='Autre École',
            adresse='Conakry',
            telephone='+224620000002',
            directeur='Autre direction',
        )
        self.classe = Classe.objects.create(
            nom='8e A',
            ecole=self.ecole,
            niveau='COLLEGE_8',
            annee_scolaire='2024-2025',
        )
        autre_classe = Classe.objects.create(
            nom='8e B',
            ecole=self.autre_ecole,
            niveau='COLLEGE_8',
            annee_scolaire='2024-2025',
        )
        responsable = Responsable.objects.create(
            prenom='Parent',
            nom='Test',
            relation='PERE',
            telephone='+224620000010',
            adresse='Conakry',
        )
        autre_responsable = Responsable.objects.create(
            prenom='Autre',
            nom='Parent',
            relation='MERE',
            telephone='+224620000011',
            adresse='Conakry',
        )
        self.eleve = Eleve.objects.create(
            nom='Camara',
            prenom='Aminata',
            matricule='ENC-001',
            classe=self.classe,
            sexe='F',
            date_naissance=date(2012, 1, 1),
            lieu_naissance='Conakry',
            date_inscription=date(2024, 9, 1),
            responsable_principal=responsable,
        )
        autre_eleve = Eleve.objects.create(
            nom='Diallo',
            prenom='Mamadou',
            matricule='ENC-002',
            classe=autre_classe,
            sexe='M',
            date_naissance=date(2012, 2, 1),
            lieu_naissance='Conakry',
            date_inscription=date(2024, 9, 1),
            responsable_principal=autre_responsable,
        )
        self.type_paiement = TypePaiement.objects.create(nom='Scolarité')
        self.especes = ModePaiement.objects.create(nom='Espèces')
        self.orange = ModePaiement.objects.create(nom='Orange Money')
        self.paiement_especes = Paiement.objects.create(
            eleve=self.eleve,
            type_paiement=self.type_paiement,
            mode_paiement=self.especes,
            montant=Decimal('30000'),
            annee_scolaire='2024-2025',
            date_paiement=date(2025, 1, 10),
            statut='VALIDE',
        )
        self.paiement_orange = Paiement.objects.create(
            eleve=self.eleve,
            type_paiement=self.type_paiement,
            mode_paiement=self.orange,
            montant=Decimal('70000'),
            annee_scolaire='2024-2025',
            date_paiement=date(2025, 1, 11),
            statut='VALIDE',
            reference_externe='OM-12345',
        )
        self.paiement_en_attente = Paiement.objects.create(
            eleve=self.eleve,
            type_paiement=self.type_paiement,
            mode_paiement=self.especes,
            montant=Decimal('500000'),
            annee_scolaire='2024-2025',
            date_paiement=date(2025, 1, 12),
            statut='EN_ATTENTE',
        )
        self.paiement_autre_ecole = Paiement.objects.create(
            eleve=autre_eleve,
            type_paiement=self.type_paiement,
            mode_paiement=self.especes,
            montant=Decimal('900000'),
            annee_scolaire='2024-2025',
            date_paiement=date(2025, 1, 10),
            statut='VALIDE',
        )
        self.echeancier = EcheancierPaiement.objects.create(
            eleve=self.eleve,
            annee_scolaire='2024-2025',
            frais_inscription_du=Decimal('50000'),
            tranche_1_due=Decimal('50000'),
            tranche_2_due=Decimal('50000'),
            tranche_3_due=Decimal('50000'),
            date_echeance_inscription=date(2024, 9, 30),
            date_echeance_tranche_1=date(2024, 11, 30),
            date_echeance_tranche_2=date(2025, 2, 28),
            date_echeance_tranche_3=date(2025, 5, 31),
        )

        User = get_user_model()
        self.user = User.objects.create_user(
            username='comptable-modes', password='mot-de-passe'
        )
        Profil.objects.update_or_create(
            user=self.user,
            defaults={
                'role': 'COMPTABLE',
                'ecole': self.ecole,
                'telephone': '+224620000020',
                'peut_consulter_rapports': True,
            },
        )
        self.user.refresh_from_db()
        self.client.force_login(self.user)
        self.params = {
            'du': '2025-01-01',
            'au': '2025-01-31',
            'annee_scolaire': '2024-2025',
        }

    def test_collecte_uniquement_les_encaissements_valides_de_lecole(self):
        request = RequestFactory().get('/', self.params)
        request.user = self.user
        data = collect_modes_encaissement_data(request)
        self.assertEqual(data['payment_count'], 2)
        self.assertEqual(data['total_amount'], Decimal('100000'))
        montants = {row['mode']: row['amount'] for row in data['rows']}
        self.assertEqual(montants, {'Espèces': Decimal('30000'), 'Orange Money': Decimal('70000')})
        students = collect_modes_students_data(request)
        self.assertEqual(students['summary']['student_count'], 1)
        self.assertEqual(students['summary']['balance'], Decimal('100000'))
        self.assertEqual(len(students['rows']), 2)

    def test_tableau_affiche_les_eleves_et_soldes_avec_filtres(self):
        url = reverse('paiements:modes_encaissement_tableau')
        response = self.client.get(url, self.params)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'paiements/modes_encaissement_soldes.html')
        self.assertContains(response, 'AMINATA CAMARA')
        self.assertEqual(response.context['summary']['student_count'], 1)
        self.assertEqual(response.context['summary']['balance'], Decimal('100000'))
        self.assertEqual(response.context['page_obj'].paginator.count, 2)
        filtered = self.client.get(url, {**self.params, 'mode_id': self.orange.pk})
        self.assertEqual(filtered.context['page_obj'].paginator.count, 1)
        row = filtered.context['rows'][0]
        self.assertEqual(row['mode'], 'Orange Money')
        self.assertEqual(row['period_amount'], Decimal('70000'))
        self.assertEqual(row['situation']['balance'], Decimal('100000'))
        settled = self.client.get(url, {**self.params, 'situation': 'solde'})
        self.assertEqual(settled.context['page_obj'].paginator.count, 0)
        self.assertEqual(settled.context['summary']['period_amount'], 0)

    def test_tableau_ajax_retourne_uniquement_les_resultats(self):
        response = self.client.get(reverse('paiements:modes_encaissement_tableau'),
                                   {**self.params, 'q': 'ENC-001'}, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'paiements/_modes_encaissement_soldes_resultats.html')
        self.assertContains(response, 'AMINATA CAMARA')
        self.assertNotContains(response, '<html')

    def test_export_excel_contient_les_montants_et_parts_valides(self):
        response = self.client.get(reverse('paiements:export_modes_encaissement_excel'), self.params)
        self.assertEqual(response.status_code, 200)
        self.assertIn('spreadsheetml', response['Content-Type'])
        workbook = load_workbook(BytesIO(response.content), data_only=True)
        summary = workbook["Modes d'encaissement"]
        values = {summary.cell(row, 1).value: (summary.cell(row, 2).value, summary.cell(row, 3).value, summary.cell(row, 4).value)
                  for row in range(6, summary.max_row + 1)}
        self.assertEqual(values['Espèces'], (1, 30000, 0.3))
        self.assertEqual(values['Orange Money'], (1, 70000, 0.7))
        self.assertEqual(values['TOTAL'], (2, 100000, 1))

    def test_ajouter_une_autre_annee_ne_change_pas_le_solde_historique(self):
        EcheancierPaiement.objects.create(
            eleve=self.eleve, annee_scolaire='2025-2026', frais_inscription_du=999999,
            date_echeance_inscription=date(2025, 9, 1), date_echeance_tranche_1=date(2025, 12, 1),
            date_echeance_tranche_2=date(2026, 3, 1), date_echeance_tranche_3=date(2026, 6, 1))
        response = self.client.get(reverse('paiements:modes_encaissement_tableau'), self.params)
        self.assertEqual(response.context['summary']['balance'], Decimal('100000'))
        for row in response.context['rows']:
            self.assertEqual(row['school_year'], '2024-2025')

    def test_filtre_annee_applique_aux_tableaux_et_aux_exports(self):
        request = RequestFactory().get('/', {**self.params, 'annee_scolaire': '2025-2026'})
        request.user = self.user
        self.assertEqual(collect_modes_encaissement_data(request)['total_amount'], 0)
        self.assertEqual(collect_modes_students_data(request)['summary']['period_amount'], 0)

    def test_export_pdf_est_genere_avec_le_bon_nom(self):
        response = self.client.get(
            reverse('paiements:export_modes_encaissement_pdf'), self.params
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/pdf')
        self.assertTrue(response.content.startswith(b'%PDF'))
        self.assertIn(
            'modes_encaissement_',
            response['Content-Disposition'],
        )

    def test_dates_invalides_sont_refusees(self):
        response = self.client.get(
            reverse('paiements:export_modes_encaissement_pdf'),
            {'du': '2025-02-01', 'au': '2025-01-01'},
        )

        self.assertEqual(response.status_code, 400)
