from datetime import date, time
from decimal import Decimal
from unittest.mock import patch

from django.conf import settings
from django.test import TestCase, override_settings
from django.urls import reverse

from eleves.models import Classe, Ecole, Eleve, Responsable
from paiements.models import ModePaiement, Paiement, TypePaiement

from .models import (
    ActiviteJournaliere,
    ClasseNote,
    CreneauEmploiDuTemps,
    MatiereNote,
    NoteMensuelle,
    NoteSuivi,
)
from .rapport_scolaire import _make_token


MIDDLEWARE_SANS_LICENCE = [
    middleware
    for middleware in settings.MIDDLEWARE
    if middleware != 'ecole_moderne.licence_middleware.LicenceMiddleware'
]


@override_settings(MIDDLEWARE=MIDDLEWARE_SANS_LICENCE)
class RapportScolaireDocumentsParentTests(TestCase):
    def setUp(self):
        self.annee = '2026-2027'
        self.ecole = Ecole.objects.create(
            nom='École des Parents',
            adresse='Conakry',
            telephone='+224620500001',
            directeur='Direction générale',
            etat='VALIDE',
        )
        self.classe = Classe.objects.create(
            ecole=self.ecole,
            nom='6ème Année A',
            niveau='PRIMAIRE_6',
            annee_scolaire=self.annee,
        )
        self.responsable = Responsable.objects.create(
            prenom='Mamadou',
            nom='Diallo',
            relation='PERE',
            telephone='+224620500002',
            adresse='Conakry',
        )
        self.eleve = Eleve.objects.create(
            matricule='PAR-001',
            prenom='Aminata',
            nom='Diallo',
            sexe='F',
            classe=self.classe,
            responsable_principal=self.responsable,
            statut='ACTIF',
        )
        self.classe_note = ClasseNote.objects.create(
            ecole=self.ecole,
            nom=self.classe.nom,
            niveau=self.classe.niveau,
            niveau_enseignement='PRIMAIRE',
            annee_scolaire=self.annee,
            actif=True,
        )
        self.matiere = MatiereNote.objects.create(
            classe=self.classe_note,
            nom='Français',
            code='FR',
            coefficient=Decimal('2'),
        )
        NoteMensuelle.objects.create(
            eleve=self.eleve,
            matiere=self.matiere,
            mois='OCTOBRE',
            annee_scolaire=self.annee,
            note=Decimal('15'),
        )
        NoteSuivi.objects.create(
            eleve=self.eleve,
            matiere=self.matiere,
            mois='OCTOBRE',
            annee_scolaire=self.annee,
            type_note='PARTICIPATION',
            numero=1,
            note=Decimal('16'),
            date=date(2026, 10, 8),
            observation='Participation active',
        )
        NoteSuivi.objects.create(
            eleve=self.eleve,
            matiere=self.matiere,
            mois='OCTOBRE',
            annee_scolaire=self.annee,
            type_note='ORALE',
            numero=1,
            note=Decimal('14'),
            date=date(2026, 10, 9),
        )
        ActiviteJournaliere.objects.create(
            classe=self.classe_note,
            eleve=self.eleve,
            date=date(2026, 10, 10),
            type_activite='RETARD',
            titre='Retard du matin',
            description='Arrivée après le début du premier cours.',
        )
        CreneauEmploiDuTemps.objects.create(
            classe=self.classe_note,
            jour='LUNDI',
            heure_debut=time(8, 0),
            heure_fin=time(9, 0),
            matiere=self.matiere,
            salle='A1',
        )
        type_paiement = TypePaiement.objects.create(nom='Scolarité parent test')
        mode_paiement = ModePaiement.objects.create(nom='Espèces parent test')
        self.paiement = Paiement.objects.create(
            eleve=self.eleve,
            type_paiement=type_paiement,
            mode_paiement=mode_paiement,
            montant=Decimal('250000'),
            annee_scolaire=self.annee,
            date_paiement=date(2026, 10, 5),
            statut='VALIDE',
        )
        self.token = _make_token(self.eleve.pk)

    def document_url(self, document_type, format_document='pdf'):
        return reverse(
            'rapport_scolaire_document',
            args=[document_type, format_document],
        )

    def test_detail_affiche_tous_les_documents_de_lenfant(self):
        response = self.client.get(
            reverse('rapport_scolaire_detail'),
            {'token': self.token},
        )

        self.assertEqual(response.status_code, 200)
        for libelle in (
            'Bulletins de notes',
            'Carnet de paiement',
            'Lettre de recommandation',
            'Participation en classe',
            'Vie scolaire',
            'Notes de suivi',
            'Livret scolaire',
            'Emploi du temps de la classe',
        ):
            self.assertContains(response, libelle)
        self.assertContains(
            response,
            reverse(
                'notes:bulletin_public_pdf',
                args=[self.eleve.pk, self.classe_note.pk, 'OCTOBRE'],
            ),
        )
        self.assertContains(response, self.document_url('carnet-paiement'))
        self.assertContains(response, self.document_url('emploi-du-temps', 'excel'))
        self.assertContains(response, 'PDF (1)')
        self.assertContains(response, 'PDF (2)')

    def test_documents_pdf_sont_telechargeables_avec_le_token_parent(self):
        for document_type in (
            'carnet-paiement',
            'lettre-recommandation',
            'participation-classe',
            'vie-scolaire',
            'notes-suivi',
        ):
            with self.subTest(document_type=document_type):
                response = self.client.get(
                    self.document_url(document_type),
                    {'token': self.token},
                )
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response['Content-Type'], 'application/pdf')
                self.assertTrue(response.content.startswith(b'%PDF'))

    def test_livret_et_emploi_du_temps_sont_telechargeables(self):
        with patch(
            'notes.livret_scolaire._collecter_parcours_eleve',
            return_value=[],
        ):
            livret = self.client.get(
                self.document_url('livret-scolaire'),
                {'token': self.token},
            )
        emploi_pdf = self.client.get(
            self.document_url('emploi-du-temps'),
            {'token': self.token},
        )
        emploi_excel = self.client.get(
            self.document_url('emploi-du-temps', 'excel'),
            {'token': self.token},
        )

        self.assertEqual(livret.status_code, 200)
        self.assertTrue(livret.content.startswith(b'%PDF'))
        self.assertEqual(emploi_pdf.status_code, 200)
        self.assertTrue(emploi_pdf.content.startswith(b'%PDF'))
        self.assertEqual(emploi_excel.status_code, 200)
        self.assertEqual(
            emploi_excel['Content-Type'],
            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        )
        self.assertTrue(emploi_excel.content.startswith(b'PK'))

    def test_token_invalide_est_refuse(self):
        response = self.client.get(
            self.document_url('notes-suivi'),
            {'token': 'token-invalide'},
        )
        self.assertEqual(response.status_code, 404)

    def test_token_dun_enfant_ne_donne_pas_le_recu_dun_autre(self):
        autre = Eleve.objects.create(
            matricule='PAR-002',
            prenom='Ibrahima',
            nom='Bah',
            sexe='M',
            classe=self.classe,
            statut='ACTIF',
        )
        autre_paiement = Paiement.objects.create(
            eleve=autre,
            type_paiement=self.paiement.type_paiement,
            mode_paiement=self.paiement.mode_paiement,
            montant=Decimal('100000'),
            annee_scolaire=self.annee,
            date_paiement=date(2026, 10, 6),
            statut='VALIDE',
        )

        response = self.client.get(
            reverse('rapport_scolaire_recu_pdf', args=[autre_paiement.pk]),
            {'token': self.token},
        )
        self.assertEqual(response.status_code, 404)
