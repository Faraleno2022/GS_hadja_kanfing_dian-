from datetime import date

from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import SimpleTestCase, TestCase
from django.urls import reverse

from .couleurs_cartes import palette_carte
from .forms import CouleursCartesEcoleForm, EleveForm
from .models import Classe, Ecole, Eleve, GrilleTarifaire


class ClasseNiveauxMaternelleTests(SimpleTestCase):
    NIVEAUX_MATERNELLE_ATTENDUS = {
        "GARDERIE": "Garderie",
        "TOUTE_PETITE_SECTION": "Toute petite section",
        "PETITE_SECTION": "Petite section",
        "MOYENNE_SECTION": "Moyenne section",
        "GRANDE_SECTION": "Grande section",
        "MATERNELLE": "Maternelle (ancienne appellation)",
    }

    def test_le_formulaire_classe_propose_toutes_les_sections_maternelles(self):
        niveaux = dict(Classe._meta.get_field("niveau").choices)

        for code, libelle in self.NIVEAUX_MATERNELLE_ATTENDUS.items():
            self.assertEqual(niveaux[code], libelle)

    def test_la_grille_tarifaire_propose_les_memes_sections_maternelles(self):
        niveaux = dict(GrilleTarifaire._meta.get_field("niveau").choices)

        for code, libelle in self.NIVEAUX_MATERNELLE_ATTENDUS.items():
            self.assertEqual(niveaux[code], libelle)


class EleveFormAgeMaternelleTests(TestCase):
    def setUp(self):
        self.ecole = Ecole.objects.create(
            nom="École maternelle",
            adresse="Conakry",
            telephone="+224622000010",
            directeur="Direction",
            etat="VALIDE",
        )
        self.garderie = Classe.objects.create(
            ecole=self.ecole,
            nom="Garderie A",
            niveau="GARDERIE",
            annee_scolaire="2026-2027",
        )

    def _donnees_eleve(self, date_naissance):
        return {
            "prenom": "FATOUMATA",
            "nom": "DIALLO",
            "sexe": "F",
            "date_naissance": date_naissance.isoformat(),
            "classe": self.garderie.pk,
            "date_inscription": date.today().isoformat(),
            "statut": "ACTIF",
        }

    def test_garderie_accepte_un_eleve_de_plus_de_trois_ans(self):
        aujourd_hui = date.today()
        naissance = date(aujourd_hui.year - 6, aujourd_hui.month, 1)

        form = EleveForm(data=self._donnees_eleve(naissance))

        self.assertTrue(form.is_valid(), form.errors)

    def test_garderie_refuse_un_age_superieur_a_dix_ans(self):
        aujourd_hui = date.today()
        naissance = date(aujourd_hui.year - 11, aujourd_hui.month, 1)

        form = EleveForm(data=self._donnees_eleve(naissance))

        self.assertFalse(form.is_valid())
        self.assertIn("date_naissance", form.errors)
        self.assertIn("10 ans", form.errors["date_naissance"][0])


class CouleursCartesEcoleTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_superuser(
            username="admin_couleurs_cartes",
            email="cartes@test.local",
            password="secret",
        )
        self.client.force_login(self.user)
        self.ecole = Ecole.objects.create(
            nom="École couleurs",
            adresse="Conakry",
            telephone="+224622000011",
            directeur="Direction",
            etat="VALIDE",
        )

    def _middleware_sans_licence(self):
        return [
            middleware
            for middleware in settings.MIDDLEWARE
            if middleware != "ecole_moderne.licence_middleware.LicenceMiddleware"
        ]

    def test_valeurs_par_defaut_et_palette_derivee(self):
        self.assertEqual(self.ecole.couleur_carte_scolaire, "#1746A2")
        self.assertEqual(self.ecole.couleur_carte_retrait, "#0F766E")
        self.assertEqual(self.ecole.couleur_carte_bus, "#2563EB")
        self.assertEqual(self.ecole.couleur_carte_cantine, "#B45309")

        self.ecole.couleur_carte_bus = "#123456"
        palette = palette_carte(self.ecole, "bus")

        self.assertEqual(palette["primary"], "#123456")
        self.assertRegex(palette["soft"], r"^#[0-9A-F]{6}$")
        self.assertIn(palette["header_text"], ("#111827", "#FFFFFF"))

    def test_formulaire_refuse_une_couleur_invalide(self):
        form = CouleursCartesEcoleForm(
            data={
                "couleur_carte_scolaire": "bleu",
                "couleur_carte_retrait": "#0F766E",
                "couleur_carte_bus": "#2563EB",
                "couleur_carte_cantine": "#B45309",
            },
            instance=self.ecole,
        )

        self.assertFalse(form.is_valid())
        self.assertIn("couleur_carte_scolaire", form.errors)

    def test_parametres_ecole_enregistrent_les_quatre_couleurs(self):
        url = reverse("eleves:configurer_ecole", args=[self.ecole.pk])
        with self.settings(MIDDLEWARE=self._middleware_sans_licence()):
            page = self.client.get(url)
            response = self.client.post(
                url,
                {
                    "action": "update_card_colors",
                    "couleur_carte_scolaire": "#102030",
                    "couleur_carte_retrait": "#204060",
                    "couleur_carte_bus": "#306090",
                    "couleur_carte_cantine": "#4080A0",
                },
            )

        self.assertEqual(page.status_code, 200)
        self.assertContains(page, "Couleurs des cartes imprimées")
        self.assertContains(
            page,
            'class="form-control form-control-color w-100"',
            count=4,
        )
        self.assertRedirects(response, url)
        self.ecole.refresh_from_db()
        self.assertEqual(self.ecole.couleur_carte_scolaire, "#102030")
        self.assertEqual(self.ecole.couleur_carte_retrait, "#204060")
        self.assertEqual(self.ecole.couleur_carte_bus, "#306090")
        self.assertEqual(self.ecole.couleur_carte_cantine, "#4080A0")


class NouvelElevePaiementWorkflowTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_superuser(
            username="admin_workflow",
            email="workflow@test.local",
            password="secret",
        )
        self.client.force_login(self.user)
        self.ecole = Ecole.objects.create(
            nom="École parcours",
            adresse="Conakry",
            telephone="+224622000001",
            email="workflow@ecole.local",
            directeur="Direction",
            etat="VALIDE",
        )
        self.classe = Classe.objects.create(
            ecole=self.ecole,
            nom="1ère année A",
            niveau="PRIMAIRE_1",
            annee_scolaire="2026-2027",
            capacite_max=40,
        )

    def test_ajout_eleve_affiche_le_choix_paiement_ou_nouvel_eleve(self):
        middleware_sans_licence = [
            middleware
            for middleware in settings.MIDDLEWARE
            if middleware != "ecole_moderne.licence_middleware.LicenceMiddleware"
        ]
        with self.settings(MIDDLEWARE=middleware_sans_licence):
            response = self.client.post(
                reverse("eleves:ajouter_eleve"),
                {
                    "prenom": "MARIAMA",
                    "nom": "DIALLO",
                    "sexe": "F",
                    "classe": self.classe.pk,
                    "statut": "ACTIF",
                },
            )

        self.assertEqual(response.status_code, 302)
        eleve = Eleve.objects.get(prenom="MARIAMA", nom="DIALLO")
        self.assertEqual(
            response.url,
            f"{reverse('eleves:ajouter_eleve')}?eleve_ajoute={eleve.pk}&classe_id={self.classe.pk}",
        )
        self.assertNotIn("nouvel_eleve_paiement_id", self.client.session)

        with self.settings(MIDDLEWARE=middleware_sans_licence):
            choix = self.client.get(response.url)
        self.assertEqual(choix.status_code, 200)
        self.assertContains(choix, "Ajouter un paiement")
        self.assertContains(choix, "Continuer l'ajout des élèves")
        self.assertContains(choix, eleve.matricule)
        self.assertContains(
            choix,
            f"{reverse('paiements:ajouter_paiement_eleve', kwargs={'eleve_id': eleve.pk})}?origine=ajout_eleve",
        )

        with self.settings(MIDDLEWARE=middleware_sans_licence):
            paiement = self.client.get(
                reverse(
                    "paiements:ajouter_paiement_eleve",
                    kwargs={"eleve_id": eleve.pk},
                ),
                {"origine": "ajout_eleve"},
            )
        self.assertEqual(paiement.status_code, 200)
        self.assertEqual(
            self.client.session.get("nouvel_eleve_paiement_id"),
            eleve.pk,
        )

    def test_continuer_ajout_quitte_le_parcours_de_paiement(self):
        session = self.client.session
        session["nouvel_eleve_paiement_id"] = 123
        session.save()

        middleware_sans_licence = [
            middleware
            for middleware in settings.MIDDLEWARE
            if middleware != "ecole_moderne.licence_middleware.LicenceMiddleware"
        ]
        with self.settings(MIDDLEWARE=middleware_sans_licence):
            response = self.client.get(
                reverse("eleves:ajouter_eleve"),
                {"classe_id": self.classe.pk, "continuer": "1"},
            )

        self.assertEqual(response.status_code, 200)
        self.assertNotIn("nouvel_eleve_paiement_id", self.client.session)
        self.assertEqual(response.context["form"].fields["classe"].initial, self.classe.pk)
