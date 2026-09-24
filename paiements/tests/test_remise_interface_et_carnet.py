from datetime import date
from decimal import Decimal
from io import BytesIO

from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from pypdf import PdfReader

from eleves.models import Classe, Ecole, Eleve, Responsable
from paiements.models import (
    EcheancierPaiement,
    ModePaiement,
    Paiement,
    PaiementRemise,
    RemiseReduction,
    TypePaiement,
)


LICENCE_MIDDLEWARE = 'ecole_moderne.licence_middleware.LicenceMiddleware'
TEST_MIDDLEWARE = tuple(
    middleware for middleware in settings.MIDDLEWARE
    if middleware != LICENCE_MIDDLEWARE
)


@override_settings(MIDDLEWARE=TEST_MIDDLEWARE)
class RemiseInterfaceEtCarnetTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_superuser(
            username='admin-remise-carnet',
            email='remise-carnet@example.com',
            password='mot-de-passe-test',
        )
        self.client.force_login(self.user)
        self.ecole = Ecole.objects.create(
            nom='École du carnet',
            adresse='Conakry',
            telephone='+224620000121',
            directeur='Fondateur Test',
        )
        self.classe = Classe.objects.create(
            ecole=self.ecole,
            nom='1ère année',
            niveau='PRIMAIRE_1',
            annee_scolaire='2026-2027',
        )
        responsable = Responsable.objects.create(
            prenom='Parent',
            nom='Carnet',
            relation='PERE',
            telephone='+224620000122',
        )
        self.eleve = Eleve.objects.create(
            matricule='CAR-001',
            prenom='Fara',
            nom='Leno',
            sexe='M',
            date_naissance=date(2018, 1, 1),
            classe=self.classe,
            date_inscription=date(2026, 7, 1),
            responsable_principal=responsable,
        )
        self.echeancier = EcheancierPaiement.objects.create(
            eleve=self.eleve,
            annee_scolaire='2026-2027',
            frais_inscription_du=Decimal('50000'),
            tranche_1_due=Decimal('500000'),
            tranche_2_due=Decimal('500000'),
            tranche_3_due=Decimal('500000'),
            date_echeance_inscription=date(2026, 7, 1),
            date_echeance_tranche_1=date(2026, 7, 1),
            date_echeance_tranche_2=date(2027, 1, 1),
            date_echeance_tranche_3=date(2027, 3, 1),
        )
        self.type_paiement = TypePaiement.objects.create(
            nom='Inscription + Tranche 1 - carnet'
        )
        self.mode = ModePaiement.objects.create(nom='Espèces - carnet')
        self.paiement = Paiement.objects.create(
            eleve=self.eleve,
            type_paiement=self.type_paiement,
            mode_paiement=self.mode,
            montant=Decimal('550000'),
            date_paiement=date(2026, 8, 23),
            annee_scolaire='2026-2027',
            statut='EN_ATTENTE',
            cree_par=self.user,
        )

    def test_formulaire_affiche_chaque_tranche_une_seule_fois(self):
        response = self.client.get(reverse(
            'paiements:appliquer_remise', args=[self.paiement.pk]
        ))
        self.assertEqual(response.status_code, 200)
        html = response.content.decode('utf-8')

        for numero in (1, 2, 3):
            self.assertIn(f'id="tranche_{numero}"', html)
            self.assertIn(f'value="{numero}"', html)
        self.assertEqual(html.count('<strong>1ère tranche</strong>'), 1)
        self.assertEqual(html.count('<strong>2ème tranche</strong>'), 1)
        self.assertEqual(html.count('<strong>3ème tranche</strong>'), 1)
        self.assertIn('value="TRANCHE"', html)
        self.assertIn('value="ECHEANCE"', html)
        self.assertNotIn('value="tranches_dues"', html)
        self.assertNotIn('value="paiement_echeance"', html)

    def test_pourcentage_est_calcule_sur_la_tranche_selectionnee(self):
        response = self.client.post(
            reverse('paiements:appliquer_remise', args=[self.paiement.pk]),
            {
                'montant_original': '550000',
                'pourcentage_scolarite': '5',
                'tranches': ['1'],
                'base_calcul': 'TRANCHE',
                'motif': 'GESTE_COMMERCIAL',
            },
        )
        self.assertEqual(response.status_code, 302)
        lien = PaiementRemise.objects.get(paiement=self.paiement)
        self.assertEqual(lien.montant_base, Decimal('500000'))
        self.assertEqual(lien.montant_remise, Decimal('25000'))
        self.assertEqual(lien.montant_tranche_1, Decimal('25000'))
        self.assertEqual(lien.montant_tranche_2, Decimal('0'))
        self.assertEqual(lien.montant_tranche_3, Decimal('0'))
        self.paiement.refresh_from_db()
        self.assertEqual(self.paiement.montant, Decimal('550000'))

    def test_carnet_pdf_contient_les_colonnes_et_le_solde(self):
        self.paiement.statut = 'VALIDE'
        self.paiement.date_validation = timezone.now()
        self.paiement.valide_par = self.user
        self.paiement.save()
        remise = RemiseReduction.objects.create(
            nom='Remise carnet 5%',
            type_remise='POURCENTAGE',
            valeur=Decimal('5'),
            motif='GESTE_COMMERCIAL',
            date_debut=date(2026, 1, 1),
            date_fin=date(2027, 12, 31),
        )
        PaiementRemise.objects.create(
            paiement=self.paiement,
            remise=remise,
            montant_remise=Decimal('25000'),
            montant_base=Decimal('500000'),
            montant_tranche_1=Decimal('25000'),
            applique_tranche_1=True,
            base_calcul='TRANCHE',
            motif='GESTE_COMMERCIAL',
        )

        response = self.client.get(reverse(
            'paiements:generer_carnet_paiement_pdf', args=[self.paiement.pk]
        ))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/pdf')
        self.assertIn('carnet_paiement_CAR-001_2026-2027.pdf', response['Content-Disposition'])
        texte = ' '.join(
            ' '.join((page.extract_text() or '').split())
            for page in PdfReader(BytesIO(response.content)).pages
        ).replace('\xa0', ' ')
        for libelle in (
            'Mois', 'Date', 'Montant', 'Reste à payer',
            'Signature comptable', 'Signature fondateur', 'Signature parent',
        ):
            self.assertIn(libelle, texte)
        self.assertIn('975 000 GNF', texte)

