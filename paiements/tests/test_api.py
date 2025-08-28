from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model


class PaiementsApiTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(username="tester", password="pass1234")
        self.client.login(username="tester", password="pass1234")

    def test_api_paiements_list_empty_ok(self):
        url = reverse("paiements:api_paiements_list")
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp["Content-Type"], "application/json")
        data = resp.json()
        self.assertIn("results", data)
        self.assertIsInstance(data["results"], list)

    def test_api_paiement_detail_404(self):
        url = reverse("paiements:api_paiement_detail", kwargs={"pk": 999999})
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 404)
