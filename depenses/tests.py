from datetime import date
from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from eleves.models import Classe, Ecole, Eleve
from utilisateurs.models import Profil

from .forms import BienEtablissementForm, ContributionRamePapierForm
from .models_logistique import BienEtablissement, ContributionRamePapier


class LogistiqueSimplifieeTests(TestCase):
    def setUp(self):
        license_patcher = patch(
            'ecole_moderne.licence_middleware._check_license_cached',
            return_value={'valid': True, 'trial': False, 'days_left': 999},
        )
        integrity_patcher = patch(
            'ecole_moderne.licence_middleware._check_integrity_cached',
            return_value={'valid': True, 'reason': ''},
        )
        license_patcher.start()
        integrity_patcher.start()
        self.addCleanup(license_patcher.stop)
        self.addCleanup(integrity_patcher.stop)

        self.ecole = Ecole.objects.create(
            nom='École Logistique',
            adresse='Conakry',
            telephone='+224620100001',
            directeur='Direction',
            code_prefixe='LOG',
        )
        self.autre_ecole = Ecole.objects.create(
            nom='Autre école',
            adresse='Conakry',
            telephone='+224620100002',
            directeur='Direction B',
            code_prefixe='AUT',
        )
        self.classe = Classe.objects.create(
            ecole=self.ecole,
            nom='6e A',
            niveau='PRIMAIRE_6',
            annee_scolaire='2026-2027',
        )
        self.autre_classe = Classe.objects.create(
            ecole=self.autre_ecole,
            nom='6e B',
            niveau='PRIMAIRE_6',
            annee_scolaire='2026-2027',
        )
        self.eleve = Eleve.objects.create(
            matricule='LOG-001',
            prenom='Aminata',
            nom='Camara',
            sexe='F',
            classe=self.classe,
            statut='ACTIF',
        )
        self.autre_eleve = Eleve.objects.create(
            matricule='AUT-001',
            prenom='Mamadou',
            nom='Diallo',
            sexe='M',
            classe=self.autre_classe,
            statut='ACTIF',
        )
        User = get_user_model()
        self.user = User.objects.create_user('logisticien', password='test-pass')
        Profil.objects.update_or_create(
            user=self.user,
            defaults={
                'role': 'COMPTABLE',
                'telephone': '+224620100003',
                'ecole': self.ecole,
            },
        )
        self.user = User.objects.get(pk=self.user.pk)
        self.client.force_login(self.user)

    def test_ajout_bien_calcule_disponible_et_valeur(self):
        response = self.client.post(reverse('depenses:creer_bien'), {
            'code_bien': '',
            'nom': 'Tables élèves',
            'type_bien': 'TABLE',
            'marque': 'Locale',
            'quantite_achetee': '40',
            'prix_achat_unitaire': '250000',
            'quantite_utilisee': '30',
            'quantite_endommagee': '3',
            'date_acquisition': '2026-08-02',
            'localisation': 'Magasin',
            'etat': 'BON',
            'observations': '',
        })

        self.assertRedirects(response, reverse('depenses:liste_biens'))
        bien = BienEtablissement.objects.get(nom='Tables élèves')
        self.assertEqual(bien.ecole, self.ecole)
        self.assertEqual(bien.quantite_disponible, 7)
        self.assertEqual(bien.valeur_achat, Decimal('10000000'))
        self.assertEqual(bien.valeur_acquisition, Decimal('10000000'))
        self.assertTrue(bien.code_bien.startswith('BIEN-LOG/'))

    def test_quantites_incoherentes_sont_refusees(self):
        form = BienEtablissementForm(data={
            'nom': 'Marqueurs',
            'type_bien': 'MARQUEUR',
            'quantite_achetee': 10,
            'prix_achat_unitaire': 5000,
            'quantite_utilisee': 8,
            'quantite_endommagee': 4,
            'etat': 'BON',
        })

        self.assertFalse(form.is_valid())
        self.assertIn('quantite_endommagee', form.errors)

    def test_contribution_rames_et_recherche_eleve(self):
        response = self.client.post(reverse('depenses:ajouter_contribution_rame'), {
            'eleve': self.eleve.pk,
            'mode_contribution': 'RAMES',
            'nombre_paquets': '3',
            'montant_paye': '',
            'date_contribution': '2026-08-02',
            'observations': 'Reçu au secrétariat',
        })

        self.assertRedirects(response, reverse('depenses:liste_contributions_rames'))
        contribution = ContributionRamePapier.objects.get(eleve=self.eleve)
        self.assertEqual(contribution.ecole, self.ecole)
        self.assertEqual(contribution.annee_scolaire, '2026-2027')
        self.assertEqual(contribution.nombre_paquets, 3)
        self.assertEqual(contribution.montant_paye, 0)

        page = self.client.get(reverse('depenses:liste_contributions_rames'), {'q': 'LOG-001'})
        self.assertContains(page, 'AMINATA')
        self.assertEqual(page.context['resume']['total_paquets'], 3)

    def test_contribution_en_argent_et_dashboard(self):
        response = self.client.post(reverse('depenses:ajouter_contribution_rame'), {
            'eleve': self.eleve.pk,
            'mode_contribution': 'ARGENT',
            'nombre_paquets': '',
            'montant_paye': '150000',
            'date_contribution': '2026-08-02',
            'observations': '',
        })
        self.assertRedirects(response, reverse('depenses:liste_contributions_rames'))

        dashboard = self.client.get(reverse('depenses:dashboard_logistique'))
        self.assertEqual(dashboard.status_code, 200)
        self.assertEqual(dashboard.context['resume_rames']['total_argent'], Decimal('150000'))
        self.assertEqual(dashboard.context['resume_rames']['eleves_contributeurs'], 1)

    def test_donnees_autre_ecole_non_visibles_et_non_modifiables(self):
        autre_bien = BienEtablissement.objects.create(
            ecole=self.autre_ecole,
            code_bien='AUT-BIEN-001',
            nom='Bien secret',
            type_bien='TABLE',
            localisation='Autre école',
        )
        autre_contribution = ContributionRamePapier.objects.create(
            ecole=self.autre_ecole,
            eleve=self.autre_eleve,
            annee_scolaire='2026-2027',
            mode_contribution='RAMES',
            nombre_paquets=2,
            date_contribution=date(2026, 8, 2),
        )

        dashboard = self.client.get(reverse('depenses:dashboard_logistique'))
        self.assertNotContains(dashboard, 'Bien secret')
        self.assertEqual(
            self.client.get(reverse('depenses:modifier_bien', args=[autre_bien.pk])).status_code,
            404,
        )
        self.assertEqual(
            self.client.get(
                reverse('depenses:modifier_contribution_rame', args=[autre_contribution.pk])
            ).status_code,
            404,
        )

    def test_formulaire_ne_propose_que_les_eleves_de_la_meme_ecole(self):
        form = ContributionRamePapierForm(user=self.user)
        self.assertIn(self.eleve, form.fields['eleve'].queryset)
        self.assertNotIn(self.autre_eleve, form.fields['eleve'].queryset)
