from django.contrib.auth.models import User
from django.template import Context, Template
from django.test import TestCase
from django.urls import reverse

from eleves.models import Ecole

from .charte_graphique import (
    CHARTE_PAR_DEFAUT,
    couleur_contraste,
    get_charte_notes,
)
from .forms import CharteDocumentsNotesForm
from .models import ThemeBulletin


class CharteGraphiqueNotesTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='direction-charte', password='secret')
        self.ecole = Ecole.objects.create(
            nom='École aux couleurs test',
            adresse='Conakry',
            telephone='+224620400001',
            directeur='Direction',
            created_by=self.user,
        )

    def test_palette_par_defaut_sans_theme(self):
        palette = get_charte_notes(self.ecole)
        self.assertEqual(palette['couleur_primaire'], CHARTE_PAR_DEFAUT['couleur_primaire'])
        self.assertEqual(palette['texte_sur_header'], '#FFFFFF')

    def test_theme_actif_de_lecole_est_prioritaire(self):
        ThemeBulletin.objects.create(
            nom='Charte test', ecole=self.ecole, actif=True, par_defaut=True,
            couleur_primaire='#123456', couleur_fond_header='#F5E942',
        )

        palette = get_charte_notes(self.ecole)

        self.assertEqual(palette['couleur_primaire'], '#123456')
        self.assertEqual(palette['couleur_fond_header'], '#F5E942')
        self.assertEqual(palette['texte_sur_header'], '#111827')

    def test_contraste_automatique(self):
        self.assertEqual(couleur_contraste('#000000'), '#FFFFFF')
        self.assertEqual(couleur_contraste('#FFFFFF'), '#111827')

    def test_formulaire_refuse_une_couleur_invalide(self):
        data = dict(CHARTE_PAR_DEFAUT)
        data['couleur_primaire'] = 'bleu'
        form = CharteDocumentsNotesForm(data=data)
        self.assertFalse(form.is_valid())
        self.assertIn('couleur_primaire', form.errors)

    def test_balise_template_expose_la_palette_de_lecole(self):
        ThemeBulletin.objects.create(
            nom='Charte modèle', ecole=self.ecole, actif=True,
            couleur_primaire='#654321',
        )
        rendered = Template(
            "{% load note_theme %}{% charte_notes as palette %}{{ palette.couleur_primaire }}"
        ).render(Context({'ecole': self.ecole}))
        self.assertEqual(rendered, '#654321')

    def test_compte_createur_peut_enregistrer_la_charte_depuis_configuration(self):
        self.client.force_login(self.user)
        data = dict(CHARTE_PAR_DEFAUT)
        data.update({
            'action': 'update_notes_branding',
            'couleur_primaire': '#1746A2',
            'couleur_secondaire': '#0F766E',
            'couleur_accent': '#B45309',
        })

        response = self.client.post(
            reverse('eleves:configurer_ecole', args=[self.ecole.pk]),
            data,
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        theme = ThemeBulletin.objects.get(ecole=self.ecole, par_defaut=True)
        self.assertTrue(theme.actif)
        self.assertEqual(theme.couleur_primaire, '#1746A2')
        self.assertContains(response, 'Charte graphique des documents Notes')
