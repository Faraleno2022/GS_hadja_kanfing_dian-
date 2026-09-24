from datetime import date
from io import BytesIO
from pathlib import Path
from tempfile import TemporaryDirectory

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from PIL import Image
from pypdf import PdfReader

from eleves.models import Ecole
from paiements.tests.support import MIDDLEWARE_SANS_LICENCE
from salaires.cartes_enseignants import construire_cartes_pdf
from salaires.forms import EnseignantForm
from salaires.models import Enseignant


@override_settings(MIDDLEWARE=MIDDLEWARE_SANS_LICENCE)
class CartesEnseignantsTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_superuser('carte-enseignant', 'carte@example.com', 'test')
        self.client.force_login(self.user)
        self.ecole = Ecole.objects.create(nom='Les Jardins de Kakimbo — Démonstration', adresse='Conakry', telephone='620000001', directeur='Direction')
        self.prof = Enseignant.objects.create(nom='CAMARA', prenoms='Mariam', ecole=self.ecole,
            type_enseignant='ADMINISTRATEUR', fonction='Directrice pédagogique', salaire_fixe=1500000,
            telephone='620000002', date_embauche=date(2026, 9, 1), cree_par=self.user)

    def donnees(self):
        return dict(nom=self.prof.nom, prenoms=self.prof.prenoms, ecole=self.ecole.pk, type_enseignant='ADMINISTRATEUR',
                    fonction=self.prof.fonction, salaire_fixe='1500000', date_embauche='2026-09-01', statut='ACTIF', mode_calcul_horaire='POINTAGE')

    def test_carte_individuelle_et_planche(self):
        response = self.client.get(reverse('salaires:carte_enseignant_pdf', args=[self.prof.pk]))
        self.assertEqual(response.status_code, 200)
        reader = PdfReader(BytesIO(response.content))
        self.assertEqual(len(reader.pages), 1)
        self.assertAlmostEqual(float(reader.pages[0].mediabox.width), 85.6 * 72 / 25.4, places=2)
        texte = reader.pages[0].extract_text()
        self.assertIn('CARTE ENSEIGNANT', texte)
        self.assertIn('MARIAM', texte)
        self.assertNotIn('1500000', texte)
        multiple = construire_cartes_pdf([self.prof] * 9, {self.ecole.pk: '2026-2027'})
        self.assertEqual(len(PdfReader(BytesIO(multiple)).pages), 2)
        folder = Path(__file__).resolve().parents[1] / 'tmp/pdfs/revision'
        folder.mkdir(parents=True, exist_ok=True)
        (folder / 'carte_enseignant.pdf').write_bytes(response.content)
        (folder / 'planche_enseignants.pdf').write_bytes(multiple)

    def test_photo_importee_et_salaire_inchange(self):
        image = BytesIO()
        Image.new('RGB', (100, 120), '#167d8d').save(image, format='PNG')
        photo = SimpleUploadedFile('portrait.png', image.getvalue(), content_type='image/png')
        with TemporaryDirectory() as media, override_settings(MEDIA_ROOT=media):
            data = self.donnees()
            data['photo'] = photo
            response = self.client.post(reverse('salaires:modifier_enseignant', args=[self.prof.pk]), data)
            self.assertEqual(response.status_code, 302)
            self.prof.refresh_from_db()
            self.assertTrue(self.prof.photo)
            self.assertEqual(self.prof.salaire_fixe, 1500000)
            result = self.client.get(reverse('salaires:carte_enseignant_pdf', args=[self.prof.pk]))
            self.assertEqual(result.status_code, 200)
            self.assertTrue(PdfReader(BytesIO(result.content)).pages[0].images)

    def test_fausse_image_refusee(self):
        form = EnseignantForm(self.donnees(), {'photo': SimpleUploadedFile('fausse.jpg', b'pas une image', content_type='image/jpeg')}, instance=self.prof, user=self.user)
        self.assertFalse(form.is_valid())
        self.assertIn('photo', form.errors)

    def test_camera_et_bouton_carte_disponibles(self):
        response = self.client.get(reverse('salaires:modifier_enseignant', args=[self.prof.pk]))
        self.assertContains(response, 'multipart/form-data')
        self.assertContains(response, 'data-open-camera-for="id_photo"')
        self.assertContains(response, 'getUserMedia')
        response = self.client.get(reverse('salaires:liste_enseignants'))
        self.assertContains(response, reverse('salaires:carte_enseignant_pdf', args=[self.prof.pk]))
        self.assertContains(response, reverse('salaires:cartes_enseignants_pdf'))

    def test_compte_sans_ecole_aucun_acces_aux_cartes(self):
        user = get_user_model().objects.create_user('sans-ecole-cartes', password='test')
        self.client.force_login(user)
        self.assertEqual(self.client.get(reverse('salaires:carte_enseignant_pdf', args=[self.prof.pk])).status_code, 404)
        self.assertEqual(self.client.get(reverse('salaires:cartes_enseignants_pdf')).status_code, 400)
