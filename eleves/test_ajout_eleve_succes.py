from types import SimpleNamespace
from unittest.mock import patch

from django.http import HttpResponse
from django.test import RequestFactory, SimpleTestCase
from django.urls import reverse

from .views import ajout_eleve_succes


class AjoutEleveSuccesTests(SimpleTestCase):
    def setUp(self):
        self.factory = RequestFactory()

    @patch('eleves.views.render')
    @patch('eleves.views.get_object_or_404')
    @patch('eleves.views.filter_by_user_school')
    def test_propose_paiement_ou_nouvel_eleve(
        self,
        filter_by_user_school_mock,
        get_object_or_404_mock,
        render_mock,
    ):
        eleve = SimpleNamespace(
            id=42,
            prenom='ALPHONS',
            nom='THÉA',
            matricule='CL8-002',
            classe_id=8,
        )
        filter_by_user_school_mock.return_value = object()
        get_object_or_404_mock.return_value = eleve
        render_mock.return_value = HttpResponse(status=200)

        request = self.factory.get('/eleves/ajouter/succes/42/')
        request.user = SimpleNamespace(is_authenticated=True)

        response = ajout_eleve_succes(request, eleve_id=42)

        self.assertEqual(response.status_code, 200)
        template_name = render_mock.call_args.args[1]
        context = render_mock.call_args.args[2]
        self.assertEqual(template_name, 'eleves/ajout_eleve_succes.html')
        self.assertEqual(
            context['paiement_url'],
            reverse('paiements:ajouter_paiement_eleve', kwargs={'eleve_id': 42}),
        )
        self.assertEqual(
            context['continuer_url'],
            f"{reverse('eleves:ajouter_eleve')}?classe_id=8",
        )
