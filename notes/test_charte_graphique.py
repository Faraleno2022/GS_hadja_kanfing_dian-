import io

from django.contrib.auth.models import User
from django.contrib.messages.storage.fallback import FallbackStorage
from django.contrib.sessions.middleware import SessionMiddleware
from django.test import RequestFactory, TestCase
from pypdf import PdfReader

from eleves.models import Ecole
from ecole_moderne.branding import get_school_branding
from utilisateurs.context_processors import user_context

from .models import ThemeBulletin
from .views_branding import build_brand_preview_pdf, charte_graphique


class CharteGraphiqueTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.ecole = Ecole.objects.create(
            nom='École Couleurs',
            adresse='Conakry',
            telephone='+224620100099',
            directeur='Direction',
        )
        self.principal = User.objects.create_user(username='principal-charte', password='secret')
        profil = self.principal.profil
        profil.ecole = self.ecole
        profil.role = 'DIRECTEUR'
        profil.est_compte_principal = True
        profil.is_validated = True
        profil.actif = True
        profil.save()

    def _request(self, method='get', data=None, user=None):
        request = getattr(self.factory, method)('/notes/charte-graphique/', data=data or {})
        SessionMiddleware(lambda req: None).process_request(request)
        request.session.save()
        request.user = user or self.principal
        request._messages = FallbackStorage(request)
        return request

    @staticmethod
    def _payload():
        return {
            'nom': 'Charte verte et or',
            'couleur_primaire': '#14532d',
            'couleur_secondaire': '#ca8a04',
            'couleur_accent': '#be123c',
            'couleur_texte_principal': '#172033',
            'couleur_texte_secondaire': '#64748b',
            'couleur_fond_header': '#14532d',
            'couleur_fond_tableau': '#ecfdf5',
            'couleur_fond_carte': '#ffffff',
            'couleur_carte_primaire': '#2563eb',
            'couleur_carte_succes': '#15803d',
            'couleur_carte_attention': '#facc15',
            'couleur_carte_danger': '#dc2626',
            'couleur_bordure': '#86efac',
            'couleur_mention_tb': '#15803d',
            'couleur_mention_bien': '#2563eb',
            'couleur_mention_ab': '#ca8a04',
            'couleur_mention_passable': '#ea580c',
            'couleur_mention_insuffisant': '#dc2626',
            'action': 'save',
        }

    def test_compte_principal_enregistre_la_charte_de_son_ecole(self):
        response = charte_graphique(self._request('post', self._payload()))

        self.assertEqual(response.status_code, 302)
        theme = ThemeBulletin.objects.get(ecole=self.ecole, actif=True)
        self.assertTrue(theme.par_defaut)
        self.assertEqual(theme.couleur_primaire, '#14532d')
        self.assertEqual(theme.couleur_carte_attention, '#facc15')

    def test_ecran_affiche_les_cartes_et_l_apercu_document(self):
        response = charte_graphique(self._request('get'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Charte graphique')
        self.assertContains(response, 'Aperçu des cartes')
        self.assertContains(response, 'Aperçu d’un document')
        self.assertContains(response, 'id_couleur_carte_primaire')

    def test_palette_html_et_pdf_provient_de_la_meme_charte(self):
        charte_graphique(self._request('post', self._payload()))

        branding = get_school_branding(self.ecole)
        context = user_context(self._request('get'))

        self.assertEqual(branding['primary'], '#14532d')
        self.assertEqual(branding['card_warning'], '#facc15')
        self.assertEqual(context['school_branding']['primary'], '#14532d')
        self.assertEqual(context['school_branding']['card_warning_text'], '#111827')

    def test_une_seule_charte_reste_active_par_ecole(self):
        first = ThemeBulletin.objects.create(
            nom='Première', ecole=self.ecole, actif=True, par_defaut=True,
        )
        second = ThemeBulletin.objects.create(
            nom='Deuxième', ecole=self.ecole, actif=True, par_defaut=True,
            couleur_primaire='#7c3aed',
        )

        first.refresh_from_db()
        self.assertFalse(first.actif)
        self.assertFalse(first.par_defaut)
        self.assertTrue(second.actif)
        self.assertTrue(second.par_defaut)

    def test_un_sous_utilisateur_ne_peut_pas_modifier_la_charte(self):
        user = User.objects.create_user(username='lecture-charte', password='secret')
        profil = user.profil
        profil.ecole = self.ecole
        profil.role = 'ENSEIGNANT'
        profil.is_validated = True
        profil.save()

        response = charte_graphique(self._request('post', self._payload(), user=user))

        self.assertEqual(response.status_code, 403)
        self.assertFalse(ThemeBulletin.objects.filter(ecole=self.ecole).exists())

    def test_apercu_pdf_est_lisible_et_identifie_ecole(self):
        charte_graphique(self._request('post', self._payload()))
        theme = ThemeBulletin.objects.get(ecole=self.ecole, actif=True)

        pdf_bytes = build_brand_preview_pdf(self.ecole, theme=theme)
        reader = PdfReader(io.BytesIO(pdf_bytes))
        text = '\n'.join(page.extract_text() or '' for page in reader.pages)

        self.assertTrue(pdf_bytes.startswith(b'%PDF'))
        self.assertEqual(len(reader.pages), 1)
        self.assertIn('ÉCOLE COULEURS', text)
        self.assertIn('BULLETIN DE NOTES', text)
