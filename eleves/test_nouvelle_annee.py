"""Création d'une nouvelle année scolaire (/eleves/nouvelle-annee/creer/)."""
from datetime import date
from decimal import Decimal

from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse

from eleves.models import Classe, Ecole, Eleve, Responsable
from notes.models import ClasseNote, Classement, MatiereNote, NoteMensuelle
from paiements.models import EcheancierPaiement

MIDDLEWARE_SANS_LICENCE = [m for m in settings.MIDDLEWARE if 'licence_middleware' not in m]


@override_settings(MIDDLEWARE=MIDDLEWARE_SANS_LICENCE)
class CreationNouvelleAnneeTest(TestCase):
    def setUp(self):
        self.ecole = Ecole.objects.create(
            nom='École Passage', adresse='Conakry', telephone='+224620555001', directeur='Direction',
        )
        self.admin = get_user_model().objects.create_superuser('admin-passage', 'p@p.gn', 'x')
        profil = self.admin.profil
        profil.ecole = self.ecole
        profil.save()

        self.classe_1 = Classe.objects.create(
            ecole=self.ecole, nom='1ÈRE ANNÉE A', niveau='PRIMAIRE_1', annee_scolaire='2025-2026',
        )
        Classe.objects.create(
            ecole=self.ecole, nom='2ÈME ANNÉE A', niveau='PRIMAIRE_2', annee_scolaire='2025-2026',
        )
        responsable = Responsable.objects.create(
            prenom='Parent', nom='Passage', relation='PERE', telephone='+224620555002', adresse='Conakry',
        )
        self.eleve = Eleve.objects.create(
            matricule='PAS-001', prenom='Aminata', nom='Camara', sexe='F',
            date_naissance=date(2018, 1, 1), classe=self.classe_1,
            date_inscription=date(2025, 9, 1), responsable_principal=responsable, statut='ACTIF',
        )

        self.classe_note = ClasseNote.objects.create(
            ecole=self.ecole, nom='1ÈRE ANNÉE A', niveau='PRIMAIRE_1',
            niveau_enseignement='PRIMAIRE', annee_scolaire='2025-2026',
        )
        self.matiere = MatiereNote.objects.create(
            classe=self.classe_note, nom='Mathématiques', code='MAT', coefficient=1,
        )
        # Classe supérieure configurée dans Notes : dupliquée vers la nouvelle année,
        # elle offre une matière « équivalente » vers laquelle l'ancien code déplaçait les notes.
        classe_note_2 = ClasseNote.objects.create(
            ecole=self.ecole, nom='2ÈME ANNÉE A', niveau='PRIMAIRE_2',
            niveau_enseignement='PRIMAIRE', annee_scolaire='2025-2026',
        )
        MatiereNote.objects.create(classe=classe_note_2, nom='Mathématiques', code='MAT', coefficient=1)
        self.note = NoteMensuelle.objects.create(
            eleve=self.eleve, matiere=self.matiere, mois='OCTOBRE',
            annee_scolaire='2025-2026', note=Decimal('8'),
        )
        Classement.objects.create(
            eleve=self.eleve, classe=self.classe_note, periode='ANNUEL_TRIM',
            annee_scolaire='2025-2026', moyenne_generale=Decimal('8'),
            total_points=Decimal('8'), total_coefficients=Decimal('1'),
            rang=1, rang_formate='1er/1', effectif=1,
        )
        self.ancien_echeancier = EcheancierPaiement.objects.create(
            eleve=self.eleve, annee_scolaire='2025-2026',
            frais_inscription_du=Decimal('0'), tranche_1_due=Decimal('100000'),
            tranche_2_due=Decimal('0'), tranche_3_due=Decimal('0'),
            date_echeance_inscription=date(2025, 9, 30), date_echeance_tranche_1=date(2026, 1, 10),
            date_echeance_tranche_2=date(2026, 3, 5), date_echeance_tranche_3=date(2026, 5, 5),
        )
        self.client.force_login(self.admin)

    def test_passage_conserve_les_notes_et_classements_de_l_annee_ecoulee(self):
        response = self.client.post(reverse('eleves:nouvelle_annee_creer'), {
            'annee_courante': '2025-2026', 'annee_nouvelle': '2026-2027',
            'dupliquer_notes_classes': '1', 'faire_passer_eleves': '1',
        })
        self.assertEqual(response.status_code, 302)

        self.eleve.refresh_from_db()
        self.assertEqual(self.eleve.classe.annee_scolaire, '2026-2027')
        self.assertEqual(self.eleve.classe.nom, '2ÈME ANNÉE A')

        # Les notes de l'année écoulée restent rattachées aux matières de cette année-là :
        # auparavant elles étaient déplacées vers la nouvelle année (bulletins vidés).
        self.note.refresh_from_db()
        self.assertEqual(self.note.matiere_id, self.matiere.pk)
        self.assertTrue(Classement.objects.filter(eleve=self.eleve, annee_scolaire='2025-2026').exists())

        self.assertTrue(EcheancierPaiement.objects.filter(pk=self.ancien_echeancier.pk).exists())
        self.assertTrue(EcheancierPaiement.objects.filter(eleve=self.eleve, annee_scolaire='2026-2027').exists())

    def test_grande_ecole_traitee_par_lots_enchaines(self):
        """Chaque requête traite un lot : aucune ne doit dépasser le délai du serveur."""
        from unittest.mock import patch

        deuxieme = Eleve.objects.create(
            matricule='PAS-002', prenom='Mamadou', nom='Diallo', sexe='M',
            date_naissance=date(2018, 2, 2), classe=self.classe_1,
            date_inscription=date(2025, 9, 1), responsable_principal=self.eleve.responsable_principal,
            statut='ACTIF',
        )
        Classement.objects.create(
            eleve=deuxieme, classe=self.classe_note, periode='ANNUEL_TRIM',
            annee_scolaire='2025-2026', moyenne_generale=Decimal('7'),
            total_points=Decimal('7'), total_coefficients=Decimal('1'),
            rang=2, rang_formate='2e/2', effectif=2,
        )
        url = reverse('eleves:nouvelle_annee_creer')
        with patch('eleves.views_nouvelle_annee.TAILLE_LOT_PASSAGE', 1):
            premiere = self.client.post(url, {
                'annee_courante': '2025-2026', 'annee_nouvelle': '2026-2027',
                'dupliquer_notes_classes': '1', 'faire_passer_eleves': '1',
            })
            self.assertEqual(premiere.status_code, 200)
            self.assertContains(premiere, '1 / 2')
            self.assertEqual(Eleve.objects.filter(classe__annee_scolaire='2026-2027').count(), 1)

            suite = self.client.post(url, {
                'annee_courante': '2025-2026', 'annee_nouvelle': '2026-2027', 'continuer': '1',
            })
        self.assertEqual(suite.status_code, 302)
        self.assertEqual(Eleve.objects.filter(classe__annee_scolaire='2026-2027').count(), 2)
        self.assertEqual(Classe.objects.filter(annee_scolaire='2026-2027').count(), 2)
        self.assertEqual(EcheancierPaiement.objects.filter(annee_scolaire='2026-2027').count(), 2)
        messages = [str(m) for m in suite.wsgi_request._messages]
        self.assertTrue(any('2 élève(s) passé(s)' in m for m in messages), messages)

    def test_reprise_sans_etat_ne_plante_pas(self):
        response = self.client.post(reverse('eleves:nouvelle_annee_creer'), {
            'annee_courante': '2025-2026', 'annee_nouvelle': '2026-2027', 'continuer': '1',
        })
        self.assertRedirects(response, reverse('eleves:nouvelle_annee_apercu'),
                             fetch_redirect_response=False)
