import io

from django.contrib.auth.models import User
from django.test import RequestFactory, TestCase
from pypdf import PdfReader

from eleves.models import Classe, Ecole, Eleve
from notes.models import ClasseNote, MatiereNote
from notes.saisie_guineenne import classe_de_saisie
from notes.views import liste_saisie_pdf


class ClassesExportAuditTests(TestCase):
    def setUp(self):
        self.ecole = Ecole.objects.create(nom='École exports')
        self.classe = Classe.objects.create(ecole=self.ecole, nom='Petite section A', niveau='PETITE_SECTION', annee_scolaire='2026-2027')
        self.classe_note = ClasseNote.objects.create(id=61, ecole=self.ecole, nom=self.classe.nom, niveau='MATERNELLE', niveau_enseignement='MATERNELLE', annee_scolaire='2026-2027')
        self.matiere = MatiereNote.objects.create(classe=self.classe_note, nom='Éveil', code='EVEIL', coefficient=1)
        self.user = User.objects.create_user('audit-export-classe')
        profil = self.user.profil
        profil.ecole = self.ecole
        profil.role = 'ADMIN'
        profil.save()

    def test_identifiants_historiques_ne_selectionnent_pas_une_autre_ecole(self):
        autre = Ecole.objects.create(nom='École étrangère')
        mauvaise = Classe.objects.create(id=56, ecole=autre, nom='Autre classe', niveau='COLLEGE_7', annee_scolaire='2026-2027')
        Eleve.objects.create(classe=mauvaise, matricule='INTERDIT-56', nom='Secret', prenom='Autre', sexe='F')
        Eleve.objects.create(classe=self.classe, matricule='AUTORISE-61', nom='Diallo', prenom='Awa', sexe='F')
        request = RequestFactory().get('/notes/liste-saisie-pdf/', {'classe_id': 61, 'matiere_id': self.matiere.pk, 'periode': 'TRIMESTRE_1'})
        request.user = self.user
        response = liste_saisie_pdf(request)
        self.assertEqual(response.status_code, 200)
        contenu = '\n'.join(page.extract_text() for page in PdfReader(io.BytesIO(response.content)).pages)
        self.assertIn('AUTORISE-61', contenu)
        self.assertNotIn('INTERDIT-56', contenu)

    def test_classe_vide_ne_reprend_pas_les_eleves_de_lannee_precedente(self):
        ancienne = Classe.objects.create(ecole=self.ecole, nom=self.classe.nom, niveau=self.classe.niveau, annee_scolaire='2025-2026')
        Eleve.objects.create(classe=ancienne, matricule='ANCIEN', nom='Bah', prenom='Awa', sexe='F')
        self.assertEqual(classe_de_saisie(self.classe_note), self.classe)

    def test_absence_de_classe_correspondante_ne_prend_pas_la_section_b(self):
        self.classe.nom = 'Petite section B'
        self.classe.save()
        Eleve.objects.create(classe=self.classe, matricule='SECTION-B', nom='Bah', prenom='Awa', sexe='F')
        self.assertIsNone(classe_de_saisie(self.classe_note))
