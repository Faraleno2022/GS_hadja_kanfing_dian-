"""Exports « Tranches par classe »: accès, téléchargement et pourcentages."""
from datetime import date
from decimal import Decimal
from io import BytesIO
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse
from openpyxl import load_workbook

from eleves.models import Classe, Ecole, Eleve, Responsable
from paiements.models import (
    EcheancierPaiement,
    ModePaiement,
    Paiement,
    PaiementRemise,
    RemiseReduction,
    TypePaiement,
)
from paiements.tests.support import MIDDLEWARE_SANS_LICENCE
from utilisateurs.models import Profil


@override_settings(MIDDLEWARE=MIDDLEWARE_SANS_LICENCE)
class ExportTranchesParClasseTests(TestCase):
    def setUp(self):
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
            prenom='Awa',
            nom='Export',
            sexe='F',
            date_naissance=date(2014, 1, 1),
            classe=self.classe,
            date_inscription=date(2025, 9, 1),
            responsable_principal=responsable,
        )
        self.echeancier = EcheancierPaiement.objects.create(
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
        self.user = self._creer_utilisateur('comptable-export', 'COMPTABLE')
        self.client.force_login(self.user)

    def _creer_utilisateur(self, username, role, ecole=..., **permissions):
        user = get_user_model().objects.create_user(
            username=username, password='mot-de-passe-test'
        )
        # Le signal utilisateurs.signals crée déjà un profil (rôle COMPTABLE).
        profil, _ = Profil.objects.get_or_create(user=user)
        profil.role = role
        profil.ecole = self.ecole if ecole is ... else ecole
        for champ, valeur in permissions.items():
            setattr(profil, champ, valeur)
        profil.save()
        # Le profil créé par le signal reste en cache sur `user`: on relit
        # l'utilisateur pour ne pas réécrire l'ancien rôle par mégarde.
        return get_user_model().objects.get(pk=user.pk)

    def _appliquer_remise(self, pourcentage, montant):
        """Applique une remise « scolarité X% » telle que la crée l'écran de remise."""
        type_paiement = TypePaiement.objects.create(nom=f'Scolarité remise {pourcentage}')
        mode_paiement = ModePaiement.objects.create(nom=f'Espèces {pourcentage}')
        paiement = Paiement.objects.create(
            eleve=self.eleve,
            type_paiement=type_paiement,
            mode_paiement=mode_paiement,
            numero_recu=f'EXP-REM-{pourcentage}',
            montant=Decimal('100000'),
            annee_scolaire='2025-2026',
            date_paiement=date(2026, 2, 15),
            statut='VALIDE',
            cree_par=self.user,
            valide_par=self.user,
        )
        remise = RemiseReduction.objects.create(
            nom=f'Remise scolarité {pourcentage}%',
            type_remise='POURCENTAGE',
            valeur=Decimal(str(pourcentage)),
            motif='SOCIALE',
            date_debut=date(2025, 9, 1),
            date_fin=date(2026, 8, 31),
        )
        PaiementRemise.objects.create(
            paiement=paiement,
            remise=remise,
            montant_remise=Decimal(str(montant)),
        )
        return paiement

    @property
    def filtres(self):
        return {'classe': self.classe.pk, 'annee_scolaire': '2025-2026'}

    def _feuille_classe(self, response):
        workbook = load_workbook(BytesIO(response.content), data_only=True)
        return workbook.worksheets[1]

    def _tables_pdf(self):
        """Capture les tables passées à ReportLab pendant la génération."""
        from reportlab.platypus import Table as ReportLabTable

        tables = []

        def capture(data, *args, **kwargs):
            tables.append(data)
            return ReportLabTable(data, *args, **kwargs)

        return tables, patch('reportlab.platypus.Table', side_effect=capture)

    # ── Accès ─────────────────────────────────────────────────────────
    def test_directeur_peut_telecharger_le_pdf(self):
        self.client.force_login(self._creer_utilisateur('directeur-export', 'DIRECTEUR'))

        response = self.client.get(
            reverse('paiements:export_tranches_par_classe_pdf'), self.filtres
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/pdf')
        self.assertIn('tranches_par_classe_', response['Content-Disposition'])

    def test_secretaire_peut_telecharger_le_excel(self):
        self.client.force_login(self._creer_utilisateur('secretaire-export', 'SECRETAIRE'))

        response = self.client.get(
            reverse('paiements:export_tranches_par_classe_excel'), self.filtres
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn('spreadsheetml.sheet', response['Content-Type'])
        self.assertIn('.xlsx', response['Content-Disposition'])

    def test_enseignant_prive_de_rapports_est_refuse(self):
        self.client.force_login(self._creer_utilisateur(
            'prof-export', 'ENSEIGNANT',
            peut_consulter_rapports=False, peut_generer_rapports=False,
        ))

        response = self.client.get(
            reverse('paiements:export_tranches_par_classe_pdf'), self.filtres
        )

        self.assertEqual(response.status_code, 403)

    def test_enseignant_avec_droit_rapports_peut_telecharger(self):
        self.client.force_login(self._creer_utilisateur('prof-rapports', 'ENSEIGNANT'))

        response = self.client.get(
            reverse('paiements:export_tranches_par_classe_pdf'), self.filtres
        )

        self.assertEqual(response.status_code, 200)

    def test_compte_sans_ecole_n_exporte_aucune_classe(self):
        self.client.force_login(
            self._creer_utilisateur('comptable-sans-ecole', 'COMPTABLE', ecole=None)
        )

        response = self.client.get(
            reverse('paiements:export_tranches_par_classe_excel'), self.filtres
        )

        self.assertEqual(response.status_code, 200)
        workbook = load_workbook(BytesIO(response.content), data_only=True)
        self.assertEqual(len(workbook.worksheets), 1)
        self.assertEqual(workbook.worksheets[0].cell(3, 1).value,
                         'Aucune classe ne correspond aux filtres.')

    def test_anonyme_est_redirige_vers_la_connexion(self):
        self.client.logout()

        response = self.client.get(reverse('paiements:export_tranches_par_classe_pdf'))

        self.assertIn(response.status_code, (302, 301))

    # ── Pourcentages ──────────────────────────────────────────────────
    def test_excel_affiche_le_pourcentage_reellement_selectionne(self):
        self._appliquer_remise(50, 250000)

        response = self.client.get(
            reverse('paiements:export_tranches_par_classe_excel'), self.filtres
        )
        sheet = self._feuille_classe(response)

        self.assertEqual(sheet.cell(2, 9).value, 'Remise (GNF)')
        self.assertEqual(sheet.cell(2, 10).value, 'Remise (%)')
        self.assertEqual(sheet.cell(2, 12).value, '% payé')
        self.assertEqual(sheet.cell(3, 9).value, 250000)
        # 50% choisi par l'utilisateur, pas 250000/1530000 = 16,3%
        self.assertEqual(sheet.cell(3, 10).value, 50)
        self.assertEqual(sheet.cell(3, 11).value, 1530000 - 130000 - 250000)
        self.assertAlmostEqual(sheet.cell(3, 12).value, 24.84, places=2)

    def test_excel_cumule_les_taux_choisis_dans_la_colonne_pourcentage(self):
        self._appliquer_remise(50, 250000)
        self._appliquer_remise(10, 50000)

        response = self.client.get(
            reverse('paiements:export_tranches_par_classe_excel'), self.filtres
        )
        sheet = self._feuille_classe(response)

        self.assertEqual(sheet.cell(3, 9).value, 300000)
        self.assertEqual(sheet.cell(3, 10).value, '50 % + 10 %')

    def test_excel_laisse_la_colonne_pourcentage_vide_sans_remise(self):
        response = self.client.get(
            reverse('paiements:export_tranches_par_classe_excel'), self.filtres
        )
        sheet = self._feuille_classe(response)

        self.assertIsNone(sheet.cell(3, 10).value)
        self.assertEqual(sheet.cell(3, 9).value, 0)

    def test_pdf_place_chaque_pourcentage_dans_sa_colonne(self):
        self._appliquer_remise(50, 250000)
        tables, capture = self._tables_pdf()

        with capture:
            response = self.client.get(
                reverse('paiements:export_tranches_par_classe_pdf'), self.filtres
            )

        self.assertEqual(response.status_code, 200)
        entetes = [cellule.getPlainText().strip() for cellule in tables[0][0]]
        ligne = tables[0][1]
        self.assertEqual(len(ligne), len(entetes))
        self.assertEqual(entetes[9], 'Remise (%)')
        self.assertEqual(entetes[11], '% payé')
        self.assertEqual(ligne[8], '250 000')
        self.assertEqual(ligne[9], '50 %')
        self.assertEqual(ligne[11], '24,84 %')

    def test_pdf_separe_inscription_et_reinscription(self):
        tables, capture = self._tables_pdf()

        with capture:
            self.client.get(
                reverse('paiements:export_tranches_par_classe_pdf'), self.filtres
            )

        entetes = [cellule.getPlainText().strip() for cellule in tables[0][0]]
        self.assertEqual(entetes[1:3], ['Inscription payée', 'Réinscription payée'])
        self.assertEqual(tables[0][1][1:3], ['0', '30 000'])

    def test_pdf_ajoute_une_ligne_de_total_par_classe(self):
        tables, capture = self._tables_pdf()

        with capture:
            self.client.get(
                reverse('paiements:export_tranches_par_classe_pdf'), self.filtres
            )

        derniere = tables[0][-1]
        self.assertEqual(derniere[0].getPlainText().strip(), 'TOTAL CLASSE')
        self.assertEqual(derniere[6], '1 530 000')
        self.assertEqual(derniere[7], '130 000')
