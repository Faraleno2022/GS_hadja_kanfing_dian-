from django.core.paginator import Paginator
from django.template.loader import get_template
from django.test import SimpleTestCase


class PaymentReminderTemplateTests(SimpleTestCase):
    def test_late_students_template_can_be_loaded(self):
        template = get_template("paiements/eleves_en_retard.html")

        self.assertEqual(template.template.name, "paiements/eleves_en_retard.html")

    def test_late_students_template_renders_empty_state(self):
        page = Paginator([], 25).get_page(1)

        html = get_template("paiements/eleves_en_retard.html").render(
            {
                "titre_page": "Élèves en retard de paiement",
                "total_eleves_retard": 0,
                "eleves_data": [],
                "page_obj": page,
                "search": "",
                "classe_filtre": "",
            }
        )

        self.assertIn("Aucun élève en retard", html)
