"""Séparation stricte des frais d'inscription et de réinscription.

Un élève ne paie qu'un seul frais d'admission : soit une inscription (nouvel
élève), soit une réinscription (élève qui revient). Les deux natures partagent
le même poste dans l'échéancier (``frais_inscription_du``) et se distinguent
par ``nature_frais``. Les rapports ne doivent donc jamais compter le même
montant dans les deux colonnes.
"""

from datetime import date

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse

from eleves.models import Classe, Ecole, Eleve, Responsable
from paiements.models import EcheancierPaiement
from paiements.tests.support import TEST_MIDDLEWARE
from utilisateurs.models import Profil


@override_settings(MIDDLEWARE=TEST_MIDDLEWARE)
class RepartitionInscriptionReinscriptionTests(TestCase):
    def setUp(self):
        self.ecole = Ecole.objects.create(
            nom="École Répartition", adresse="Conakry",
            telephone="+224620100031", directeur="Direction",
        )
        self.classe = Classe.objects.create(
            nom="6ÈME ANNÉE", ecole=self.ecole, niveau="PRIMAIRE_6",
            annee_scolaire="2025-2026",
        )
        self.responsable = Responsable.objects.create(
            nom="Diallo", prenom="Mariama", telephone="+224620100032",
            relation="PERE",
        )

        # Nouvel élève : frais d'inscription de 30 000.
        self.nouvel_eleve = self._creer_eleve("MAT-INSC-1", "Camara", "Awa")
        self._creer_echeancier(self.nouvel_eleve, 30000, 'INSCRIPTION')

        # Élève qui revient : frais de réinscription de 20 000.
        self.ancien_eleve = self._creer_eleve("MAT-REINSC-1", "Bah", "Ibrahima")
        self._creer_echeancier(self.ancien_eleve, 20000, 'REINSCRIPTION')

        User = get_user_model()
        self.comptable = User.objects.create_user(
            username="comptable_repartition", password="pass12345",
        )
        Profil.objects.update_or_create(
            user=self.comptable,
            defaults={
                'role': 'COMPTABLE', 'ecole': self.ecole,
                'telephone': "+224620100033",
                'peut_consulter_rapports': True, 'is_validated': True,
            },
        )
        self.client.force_login(self.comptable)

    def _creer_eleve(self, matricule, nom, prenom):
        return Eleve.objects.create(
            nom=nom, prenom=prenom, matricule=matricule, classe=self.classe,
            sexe='M', date_naissance=date(2015, 1, 1),
            lieu_naissance="Conakry", date_inscription=date(2025, 9, 1),
            responsable_principal=self.responsable,
        )

    def _creer_echeancier(self, eleve, frais_admission, nature):
        return EcheancierPaiement.objects.create(
            eleve=eleve, annee_scolaire="2025-2026",
            frais_inscription_du=frais_admission,
            nature_frais=nature,
            tranche_1_due=100000, tranche_2_due=0, tranche_3_due=0,
            frais_inscription_paye=0,
            tranche_1_payee=0, tranche_2_payee=0, tranche_3_payee=0,
            date_echeance_inscription=date(2025, 9, 1),
            date_echeance_tranche_1=date(2025, 10, 1),
            date_echeance_tranche_2=date(2026, 1, 1),
            date_echeance_tranche_3=date(2026, 4, 1),
        )

    def test_colonnes_inscription_et_reinscription_ne_se_recouvrent_pas(self):
        response = self.client.get(reverse('paiements:liste_paiements'))
        self.assertEqual(response.status_code, 200)

        totaux = response.context['totaux_du']
        # La colonne Inscription ne doit contenir que les vraies inscriptions.
        self.assertEqual(totaux['frais_inscription_total'], 30000)
        self.assertEqual(totaux['frais_reinscription_total'], 20000)
        # Le total dû reste complet : scolarité + les deux natures d'admission.
        self.assertEqual(totaux['du_global_net'], 200000 + 30000 + 20000)
        # Part de la réinscription dans l'ensemble des frais d'admission.
        self.assertAlmostEqual(totaux['frais_reinscription_pct'], 40.0, places=2)

    def test_detail_par_classe_ne_double_compte_pas(self):
        response = self.client.get(reverse('paiements:liste_paiements'))
        self.assertEqual(response.status_code, 200)

        lignes = response.context['totaux_du_detail_classes']
        self.assertEqual(len(lignes), 1)
        ligne = lignes[0]
        self.assertEqual(ligne['frais_inscription_total'], 30000)
        self.assertEqual(ligne['frais_reinscription_total'], 20000)
        self.assertEqual(ligne['du_global_net'], 200000 + 30000 + 20000)
        self.assertAlmostEqual(ligne['frais_reinscription_pct'], 40.0, places=2)

    def test_export_excel_recap_ne_double_compte_pas(self):
        from io import BytesIO

        from openpyxl import load_workbook

        response = self.client.get(reverse('paiements:export_recap_par_classe_excel'))
        self.assertEqual(response.status_code, 200)

        workbook = load_workbook(BytesIO(response.content))
        sheet = workbook.active
        entetes = [cell.value for cell in sheet[1]]
        ligne = dict(zip(entetes, [cell.value for cell in sheet[2]]))

        self.assertEqual(ligne['Inscription'], 30000)
        self.assertEqual(ligne['Réinscription'], 20000)
        self.assertEqual(ligne['Total dû net'], 200000 + 30000 + 20000)
        self.assertAlmostEqual(float(ligne['Réinscription %']), 40.0, places=2)

    def test_classe_entierement_en_reinscription_laisse_inscription_a_zero(self):
        EcheancierPaiement.objects.filter(eleve=self.nouvel_eleve).update(
            nature_frais='REINSCRIPTION', frais_inscription_du=20000,
        )

        response = self.client.get(reverse('paiements:liste_paiements'))
        totaux = response.context['totaux_du']

        self.assertEqual(totaux['frais_inscription_total'], 0)
        self.assertEqual(totaux['frais_reinscription_total'], 40000)
        self.assertAlmostEqual(totaux['frais_reinscription_pct'], 100.0, places=2)
        self.assertEqual(totaux['du_global_net'], 200000 + 40000)
