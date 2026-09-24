from decimal import Decimal

from django.core.exceptions import ValidationError
from django.test import TestCase

from .forms import BienEtablissementForm
from .models_logistique import BienEtablissement


class StockHistoriqueAuditTests(TestCase):
    def setUp(self):
        self.bien = BienEtablissement.objects.create(code_bien='AUDIT-STOCK', nom='Tables', type_bien='TABLE', localisation='Salle', quantite_achetee=10, quantite_utilisee=2, quantite_endommagee=3, prix_achat_unitaire=10000)

    def test_anciens_degats_sont_deduits_sans_double_compter_les_miroirs(self):
        self.assertEqual(self.bien.quantite_disponible, 5)
        self.bien.quantite_gatee = 3
        self.assertEqual(self.bien.quantite_disponible, 5)

    def test_degats_historiques_comptent_dans_la_validation(self):
        self.bien.quantite_utilisee = 8
        with self.assertRaises(ValidationError):
            self.bien.full_clean()

    def test_modification_permet_de_corriger_les_degats_historiques(self):
        form = BienEtablissementForm(instance=self.bien)
        self.assertEqual(form.initial['quantite_gatee'], 3)
        data = {name: getattr(self.bien, name) for name in form.Meta.fields}
        data.update(quantite_gatee=1, date_acquisition='', photo='', observations='')
        form = BienEtablissementForm(data, instance=self.bien)
        self.assertTrue(form.is_valid(), form.errors)
        form.save()
        self.bien.refresh_from_db()
        self.assertEqual(self.bien.quantite_endommagee, 1)
        self.assertEqual(self.bien.quantite_disponible, 7)

    def test_enregistrement_partiel_actualise_la_valeur(self):
        self.bien.quantite_achetee = 12
        self.bien.save(update_fields=['quantite_achetee'])
        self.bien.refresh_from_db()
        self.assertEqual(self.bien.valeur_acquisition, Decimal('120000'))
