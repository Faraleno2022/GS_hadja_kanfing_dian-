"""Régressions de saisie, d'isolation des écoles et des exports."""
import io
import json
from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth.models import User
from django.contrib.messages.storage.fallback import FallbackStorage
from django.contrib.sessions.middleware import SessionMiddleware
from django.core.cache import cache
from django.http import Http404, HttpResponse
from django.test import RequestFactory, TestCase
from pypdf import PdfReader

from eleves.models import Classe, Ecole, Eleve
from .models import ClasseNote, CompositionNote, MatiereNote, NoteMensuelle
from .views import saisie_notes_simple, sauvegarder_notes_guineen


class AuditSaisieNotesTests(TestCase):
    def setUp(self):
        cache.clear()
        self.factory = RequestFactory()
        self.ecole = Ecole.objects.create(nom='École audit', adresse='Conakry', telephone='620000001', directeur='Direction')
        self.classe = Classe.objects.create(ecole=self.ecole, nom='1ère année A', niveau='PRIMAIRE_1', annee_scolaire='2026-2027')
        self.classe_note = ClasseNote.objects.create(ecole=self.ecole, nom=self.classe.nom, niveau='PRIMAIRE_1', niveau_enseignement='PRIMAIRE', annee_scolaire='2026-2027')
        self.matiere = MatiereNote.objects.create(classe=self.classe_note, nom='Calcul', code='CAL', coefficient=1)
        self.eleve = Eleve.objects.create(classe=self.classe, matricule='AUDIT-1', nom='Diallo', prenom='Aminata', sexe='F', statut='ACTIF')
        self.user = User.objects.create_user(username='audit-notes')
        profil = self.user.profil
        profil.ecole = self.ecole
        profil.role = 'ENSEIGNANT'
        profil.est_compte_principal = False
        profil.peut_gerer_notes = True
        profil.save()
        self.payload = {'eleve_id': self.eleve.pk, 'matiere_id': self.matiere.pk, 'annee_scolaire': '2026-2027'}

    def request(self, method='get', data=None):
        if method == 'post':
            request = self.factory.post('/notes/sauvegarder/', json.dumps(data), content_type='application/json')
        else:
            request = self.factory.get('/notes/saisie-simple/', data or {})
        request.user = self.user
        SessionMiddleware(lambda req: None).process_request(request)
        request._messages = FallbackStorage(request)
        return request

    def save_notes(self, **data):
        return sauvegarder_notes_guineen(self.request('post', {**self.payload, **data}))

    def test_saisie_simple_affiche_les_eleves_de_la_classe(self):
        response = saisie_notes_simple(self.request(data={'classe_id': self.classe_note.pk, 'eleve_id': self.eleve.pk, 'matiere_id': self.matiere.pk}))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'AMINATA')

    def test_selection_eleve_reste_dans_la_classe(self):
        autre = Classe.objects.create(ecole=self.ecole, nom='1ère année B', niveau='PRIMAIRE_1', annee_scolaire='2026-2027')
        self.eleve.classe = autre
        self.eleve.save()
        with patch('notes.views.render', return_value=HttpResponse()) as render:
            saisie_notes_simple(self.request(data={'classe_id': self.classe_note.pk, 'eleve_id': self.eleve.pk}))
        self.assertIsNone(render.call_args.args[2]['eleve_selectionne'])

    def test_selection_identifiant_invalide_ne_provoque_pas_500(self):
        self.assertEqual(saisie_notes_simple(self.request(data={'classe_id': 'abc'})).status_code, 400)

    def test_refus_note_hors_limite_ne_modifie_aucune_note(self):
        note = NoteMensuelle.objects.create(eleve=self.eleve, matiere=self.matiere, mois='OCTOBRE', annee_scolaire='2026-2027', note=4)
        response = self.save_notes(notes_mois={'OCTOBRE': 8, 'NOVEMBRE': 11})
        self.assertEqual(response.status_code, 400)
        note.refresh_from_db()
        self.assertEqual(note.note, Decimal('4'))
        self.assertEqual(NoteMensuelle.objects.count(), 1)

    def test_composition_invalide_annule_aussi_les_notes_mensuelles(self):
        self.assertEqual(self.save_notes(notes_mois={'OCTOBRE': 8}, compositions={'composition1': 11}).status_code, 400)
        self.assertFalse(NoteMensuelle.objects.exists())
        self.assertFalse(CompositionNote.objects.exists())

    def test_json_malforme_et_notes_non_numeriques_sont_refuses(self):
        for value in ('texte', 'NaN', 'Infinity', -1, True, {'note': 3, 'absent': 'false'}):
            with self.subTest(value=value):
                self.assertEqual(self.save_notes(notes_mois={'OCTOBRE': value}).status_code, 400)
        for value in ([], None, 'abc'):
            with self.subTest(value=value):
                self.assertEqual(sauvegarder_notes_guineen(self.request('post', value)).status_code, 400)
        self.assertFalse(NoteMensuelle.objects.exists())

    def test_periodes_et_annee_invalides_sont_refusees(self):
        for data in ({'notes_mois': {'JUILLET': 5}}, {'compositions': {'composition4': 5}}, {'annee_scolaire': '2025-2026', 'notes_mois': {'OCTOBRE': 5}}, {'notes_mois': []}):
            with self.subTest(data=data):
                self.assertEqual(self.save_notes(**data).status_code, 400)
        self.assertFalse(NoteMensuelle.objects.exists())

    def test_saisie_valide_et_absence(self):
        response = self.save_notes(notes_mois={'OCTOBRE': '8,5', 'NOVEMBRE': {'absent': True}}, compositions={'composition1': 9})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(json.loads(response.content)['saved'], 3)
        self.assertEqual(NoteMensuelle.objects.get(mois='OCTOBRE').note, Decimal('8.5'))
        self.assertTrue(NoteMensuelle.objects.get(mois='NOVEMBRE').absent)

    def test_secondaire_enregistre_des_semestres(self):
        self.classe.nom = self.classe_note.nom = '7ème année A'
        self.classe.niveau = self.classe_note.niveau = 'COLLEGE_7'
        self.classe_note.niveau_enseignement = 'SECONDAIRE'
        self.classe.save()
        self.classe_note.save()
        self.assertEqual(self.save_notes(compositions={'composition1': 18}).status_code, 200)
        self.assertEqual(CompositionNote.objects.get().periode, 'SEMESTRE_1')
        self.assertEqual(self.save_notes(compositions={'composition3': 18}).status_code, 400)
        with patch('notes.views.render', return_value=HttpResponse()) as render:
            saisie_notes_simple(self.request(data={'classe_id': self.classe_note.pk}))
        self.assertEqual(render.call_args.args[2]['system_type'], 'semestre')

    def test_absence_permission_refuse_lecriture(self):
        self.user.profil.peut_gerer_notes = False
        self.user.profil.save()
        self.assertEqual(self.save_notes(notes_mois={'OCTOBRE': 5}).status_code, 403)
        self.assertFalse(NoteMensuelle.objects.exists())

    def test_utilisateur_sans_ecole_ne_peut_pas_ecrire(self):
        self.user.profil.ecole = None
        self.user.profil.save()
        self.assertEqual(self.save_notes(notes_mois={'OCTOBRE': 5}).status_code, 404)
        self.assertFalse(NoteMensuelle.objects.exists())

    def test_matiere_autre_classe_ou_autre_ecole_est_refusee(self):
        autre = ClasseNote.objects.create(ecole=self.ecole, nom='1ère année B', niveau='PRIMAIRE_1', niveau_enseignement='PRIMAIRE', annee_scolaire='2026-2027')
        self.matiere.classe = autre
        self.matiere.save()
        self.assertEqual(self.save_notes(notes_mois={'OCTOBRE': 5}).status_code, 400)
        autre.ecole = Ecole.objects.create(nom='Autre école')
        autre.save()
        self.assertEqual(self.save_notes(notes_mois={'OCTOBRE': 5}).status_code, 404)
        self.assertFalse(NoteMensuelle.objects.exists())

    def test_export_complet_pdf_est_lisible(self):
        from .export_notes_complet import exporter_notes_complet_pdf
        response = exporter_notes_complet_pdf(self.request(data={'classe_id': self.classe_note.pk}))
        self.assertEqual(response.status_code, 200)
        self.assertIn('CALCUL', ''.join(page.extract_text() for page in PdfReader(io.BytesIO(response.content)).pages).upper())

    def test_exports_refusent_une_autre_ecole(self):
        from .export_notes_complet import exporter_notes_complet_excel, exporter_notes_complet_pdf
        self.user.profil.ecole = Ecole.objects.create(nom='Autre école')
        self.user.profil.save()
        for view in (exporter_notes_complet_pdf, exporter_notes_complet_excel):
            with self.subTest(view=view.__name__), self.assertRaises(Http404):
                view(self.request(data={'classe_id': self.classe_note.pk}))

    def test_bulletin_intelligent_affiche_la_page(self):
        from .bulletin_intelligent import bulletin_intelligent_view
        response = bulletin_intelligent_view(self.request(), self.eleve.pk, self.classe_note.pk, 'TRIMESTRE_1')
        self.assertEqual(response.status_code, 200)

    def test_echec_base_annule_lensemble_de_la_saisie(self):
        with patch.object(CompositionNote.objects, 'update_or_create', side_effect=RuntimeError('Échec simulé')):
            with self.assertRaises(RuntimeError):
                self.save_notes(notes_mois={'OCTOBRE': 7}, compositions={'composition1': 8})
        self.assertFalse(NoteMensuelle.objects.exists())

