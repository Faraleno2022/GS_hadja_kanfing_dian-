"""Un paiement partiel par tranche (ou type combiné) doit être accepté
immédiatement, sans confirmation ni second essai — cf. demande utilisateur
« l'application doit intelligemment accepter le paiement partiel par
tranche sans bloquer l'utilisateur »."""
from datetime import date
from decimal import Decimal

from django.conf import settings
from django.contrib.auth.models import User
from django.test import TestCase, override_settings
from django.urls import reverse

from eleves.models import Classe, Ecole, Eleve, Responsable
from paiements.models import EcheancierPaiement, ModePaiement, Paiement, TypePaiement

MIDDLEWARE_SANS_LICENCE = [
    m for m in settings.MIDDLEWARE if 'licence_middleware' not in m
]


@override_settings(MIDDLEWARE=MIDDLEWARE_SANS_LICENCE)
class PaiementPartielTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_superuser('caissier_partiel', 'p@p.gn', 'x')
        self.client.force_login(self.user)

        ecole = Ecole.objects.create(
            nom="École Partiel", adresse="Conakry",
            telephone="+224622500000", directeur="Directeur",
        )
        self.classe = Classe.objects.create(
            ecole=ecole, nom="6ème A", niveau="PRIMAIRE_6", annee_scolaire="2025-2026",
        )
        responsable = Responsable.objects.create(
            prenom="Mamadou", nom="Diallo", relation="PERE",
            telephone="+224622500001", adresse="Ratoma",
        )
        self.eleve = Eleve.objects.create(
            matricule="MAT-PARTIEL-001", prenom="Aissatou", nom="Camara", sexe="F",
            date_naissance=date(2014, 5, 12), lieu_naissance="Kindia",
            classe=self.classe, date_inscription=date(2025, 9, 15), statut="ACTIF",
            responsable_principal=responsable,
        )
        self.echeancier = EcheancierPaiement.objects.create(
            eleve=self.eleve, annee_scolaire="2025-2026",
            frais_inscription_du=Decimal('100000'),
            tranche_1_due=Decimal('200000'),
            tranche_2_due=Decimal('200000'),
            tranche_3_due=Decimal('200000'),
            date_echeance_inscription=date(2025, 9, 30),
            date_echeance_tranche_1=date(2025, 12, 31),
            date_echeance_tranche_2=date(2026, 3, 31),
            date_echeance_tranche_3=date(2026, 6, 30),
        )
        self.mode = ModePaiement.objects.create(nom="Espèces")

    def _payer(self, type_nom, montant):
        type_p = TypePaiement.objects.create(nom=type_nom)
        return self.client.post(
            reverse('paiements:ajouter_paiement'),
            {
                'eleve': self.eleve.pk,
                'type_paiement': type_p.pk,
                'mode_paiement': self.mode.pk,
                'montant': str(montant),
                'date_paiement': '2025-10-05',
                'observations': '',
                'reference_externe': '',
            },
            follow=True,
        )

    def test_partiel_sur_type_combine_est_accepte_immediatement(self):
        """Tranche 1 + Tranche 2 dues = 400000 ; on ne paie que 150000."""
        reponse = self._payer("Tranche 1 + Tranche 2", 150000)

        self.assertEqual(reponse.status_code, 200)
        # Pas de re-affichage du formulaire avec demande de confirmation :
        # la redirection vers le detail du paiement a bien eu lieu.
        self.assertEqual(reponse.redirect_chain[-1][1], 302)
        self.assertIn('/paiements/detail/', reponse.redirect_chain[-1][0])

        paiement = Paiement.objects.get(eleve=self.eleve, montant=150000)
        self.assertIsNotNone(paiement.pk)

        messages_texte = [str(m) for m in reponse.context['messages']]
        self.assertTrue(any('enregistré avec succès' in m for m in messages_texte))
        self.assertTrue(any('Paiement partiel' in m for m in messages_texte))
        self.assertFalse(any('confirmez' in m.lower() for m in messages_texte))

    def test_partiel_sur_inscription_seule_est_accepte_immediatement(self):
        """Frais d'inscription dus = 100000 ; on ne paie que 40000."""
        reponse = self._payer("Frais d'inscription", 40000)

        self.assertEqual(reponse.status_code, 200)
        paiement = Paiement.objects.filter(eleve=self.eleve, montant=40000).first()
        self.assertIsNotNone(paiement, "Le paiement partiel d'inscription doit être enregistré directement.")

    def test_partiel_sur_tranche_simple_reste_accepte(self):
        """Comportement déjà correct auparavant (tranche seule) : non régressé."""
        reponse = self._payer("Scolarité - 1ère tranche", 50000)

        self.assertEqual(reponse.status_code, 200)
        paiement = Paiement.objects.filter(eleve=self.eleve, montant=50000).first()
        self.assertIsNotNone(paiement)
