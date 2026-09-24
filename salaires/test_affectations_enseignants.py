from datetime import date
from decimal import Decimal

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase, override_settings
from django.urls import reverse

from eleves.models import Classe, Ecole

from .forms import AffectationClasseForm, EnseignantForm
from .models import AffectationClasse, Enseignant, TypeEnseignant


LICENCE_MIDDLEWARE = 'ecole_moderne.licence_middleware.LicenceMiddleware'
TEST_MIDDLEWARE = tuple(
    middleware for middleware in settings.MIDDLEWARE
    if middleware != LICENCE_MIDDLEWARE
)


@override_settings(MIDDLEWARE=TEST_MIDDLEWARE)
class AffectationsEnseignantsTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_superuser(
            username='admin-affectations',
            email='admin-affectations@example.com',
            password='mot-de-passe-test',
        )
        self.ecole = Ecole.objects.create(
            nom='École des affectations',
            adresse='Conakry',
            telephone='+224610000010',
            directeur='Direction',
        )
        self.autre_ecole = Ecole.objects.create(
            nom='Autre école',
            adresse='Conakry',
            telephone='+224610000011',
            directeur='Autre direction',
        )
        self.maternelle = Classe.objects.create(
            ecole=self.ecole,
            nom='Grande section A',
            niveau='GRANDE_SECTION',
            annee_scolaire='2026-2027',
        )
        self.primaire = Classe.objects.create(
            ecole=self.ecole,
            nom='3ème année A',
            niveau='PRIMAIRE_3',
            annee_scolaire='2026-2027',
        )
        self.secondaire = Classe.objects.create(
            ecole=self.ecole,
            nom='8ème année A',
            niveau='COLLEGE_8',
            annee_scolaire='2026-2027',
        )
        self.classe_autre_ecole = Classe.objects.create(
            ecole=self.autre_ecole,
            nom='4ème année A',
            niveau='PRIMAIRE_4',
            annee_scolaire='2026-2027',
        )
        self.client.force_login(self.user)

    def donnees_enseignant(self, type_enseignant, **overrides):
        donnees = {
            'nom': 'CAMARA',
            'prenoms': 'Mariam',
            'telephone': '',
            'email': 'mariam@example.com',
            'adresse': '',
            'ecole': str(self.ecole.id),
            'type_enseignant': type_enseignant,
            'statut': 'ACTIF',
            'classe_principale': '',
            'fonction': '',
            'taux_horaire': '',
            'mode_calcul_horaire': 'POINTAGE',
            'salaire_fixe': '1500000',
            'heures_mensuelles': '',
            'date_embauche': '2026-09-01',
        }
        if type_enseignant == TypeEnseignant.SECONDAIRE:
            donnees['salaire_fixe'] = ''
            donnees['taux_horaire'] = '25000'
        donnees.update(overrides)
        return donnees

    def creer_secondaire(self):
        return Enseignant.objects.create(
            nom='DIALLO',
            prenoms='Ibrahima',
            ecole=self.ecole,
            type_enseignant=TypeEnseignant.SECONDAIRE,
            statut='ACTIF',
            taux_horaire=Decimal('25000'),
            date_embauche=date(2026, 9, 1),
            cree_par=self.user,
        )

    def test_primaire_exige_et_enregistre_une_classe_principale(self):
        sans_classe = EnseignantForm(
            self.donnees_enseignant(TypeEnseignant.PRIMAIRE),
            user=self.user,
        )
        self.assertFalse(sans_classe.is_valid())
        self.assertIn('classe_principale', sans_classe.errors)

        avec_classe = EnseignantForm(
            self.donnees_enseignant(
                TypeEnseignant.PRIMAIRE,
                classe_principale=str(self.primaire.id),
            ),
            user=self.user,
        )
        self.assertTrue(avec_classe.is_valid(), avec_classe.errors)
        enseignant = avec_classe.save(commit=False)
        enseignant.cree_par = self.user
        enseignant.save()
        self.assertEqual(enseignant.classe_principale, self.primaire)

    def test_maternelle_refuse_une_classe_primaire(self):
        formulaire = EnseignantForm(
            self.donnees_enseignant(
                TypeEnseignant.MATERNELLE,
                classe_principale=str(self.primaire.id),
            ),
            user=self.user,
        )
        self.assertFalse(formulaire.is_valid())
        self.assertIn('classe_principale', formulaire.errors)

    def test_administrateur_exige_et_enregistre_sa_fonction(self):
        sans_fonction = EnseignantForm(
            self.donnees_enseignant(TypeEnseignant.ADMINISTRATEUR),
            user=self.user,
        )
        self.assertFalse(sans_fonction.is_valid())
        self.assertIn('fonction', sans_fonction.errors)

        avec_fonction = EnseignantForm(
            self.donnees_enseignant(
                TypeEnseignant.ADMINISTRATEUR,
                fonction='Directrice pédagogique',
            ),
            user=self.user,
        )
        self.assertTrue(avec_fonction.is_valid(), avec_fonction.errors)

    def test_creation_secondaire_enchaine_sur_affectation(self):
        reponse = self.client.post(
            reverse('salaires:ajouter_enseignant'),
            self.donnees_enseignant(TypeEnseignant.SECONDAIRE),
        )
        enseignant = Enseignant.objects.get(nom='CAMARA')
        self.assertRedirects(
            reponse,
            reverse('salaires:ajouter_affectation', args=[enseignant.id]),
        )

    def test_affectation_secondaire_filtre_et_enregistre_les_classes(self):
        enseignant = self.creer_secondaire()
        formulaire = AffectationClasseForm(enseignant=enseignant)
        ids_disponibles = set(
            formulaire.fields['classe'].queryset.values_list('id', flat=True)
        )
        self.assertIn(self.secondaire.id, ids_disponibles)
        self.assertNotIn(self.primaire.id, ids_disponibles)

        reponse = self.client.post(
            reverse('salaires:ajouter_affectation', args=[enseignant.id]),
            {
                'classe': str(self.secondaire.id),
                'heures_par_semaine': '12',
                'matiere': 'Mathématiques',
                'date_debut': '2026-09-01',
                'date_fin': '',
                'actif': 'on',
            },
        )
        self.assertRedirects(
            reponse,
            reverse('salaires:detail_enseignant', args=[enseignant.id]),
        )
        self.assertTrue(
            AffectationClasse.objects.filter(
                enseignant=enseignant,
                classe=self.secondaire,
                matiere='Mathématiques',
                heures_par_semaine=Decimal('12'),
                actif=True,
            ).exists()
        )

    def test_detail_affiche_affectation_secondaire(self):
        enseignant = self.creer_secondaire()
        AffectationClasse.objects.create(
            enseignant=enseignant,
            classe=self.secondaire,
            heures_par_semaine=Decimal('8'),
            matiere='Physique',
            date_debut=date(2026, 9, 1),
            actif=True,
        )
        reponse = self.client.get(
            reverse('salaires:detail_enseignant', args=[enseignant.id])
        )
        self.secondaire.refresh_from_db()
        self.assertContains(reponse, self.secondaire.nom)
        self.assertContains(reponse, 'Affectations de classes du secondaire')

    def test_modele_refuse_une_classe_principale_d_une_autre_ecole(self):
        enseignant = Enseignant(
            nom='TOURE',
            prenoms='Aminata',
            ecole=self.ecole,
            type_enseignant=TypeEnseignant.PRIMAIRE,
            statut='ACTIF',
            classe_principale=self.classe_autre_ecole,
            salaire_fixe=Decimal('1200000'),
            date_embauche=date(2026, 9, 1),
            cree_par=self.user,
        )
        with self.assertRaises(ValidationError):
            enseignant.full_clean()
