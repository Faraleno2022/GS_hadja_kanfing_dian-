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
        for name in ('couleur_carte_scolaire', 'couleur_carte_retrait', 'couleur_carte_bus', 'couleur_carte_cantine'):
            self.assertContains(page, f'name="{name}"', count=1)
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


class VersoCartesRetraitBusTests(SimpleTestCase):
    """Verso des cartes de retrait et de bus : format, alignement, contenu."""

    def setUp(self):
        from reportlab.lib.units import mm

        self.mm = mm
        self.ecole = Ecole(nom="GROUPE SCOLAIRE HADJA KANFING DIANE")
        self.classe = Classe(nom="CM1 A", ecole=self.ecole, annee_scolaire="2026-2027")

    def _eleve(self, index, avec_second=True):
        from .models import Responsable

        principal = Responsable(prenom="Mamadou", nom=f"Diallo{index}", relation="PERE", telephone="+224620000000")
        second = (
            Responsable(prenom="Fatoumata", nom="Camara", relation="MERE", telephone="+224655111222")
            if avec_second else None
        )
        return Eleve(
            id=index, matricule=f"MAT{index:03d}", prenom="Aissatou", nom=f"Bah{index}",
            classe=self.classe, responsable_principal=principal, responsable_secondaire=second,
        )

    def _planche(self, elements, verso):
        """Génère une planche en relevant, page par page, les cadres des cartes et les textes."""
        from unittest import mock

        from django.http import HttpResponse
        from reportlab.pdfgen import canvas as rl_canvas

        from . import views

        mm = self.mm
        pages = [{"cadres": [], "textes": []}]

        class Enregistreur(rl_canvas.Canvas):
            def roundRect(self, x, y, w, h, r, stroke=1, fill=0):
                if abs(w - 85.6 * mm) < 0.01 and abs(h - 53.98 * mm) < 0.01 and stroke and not fill:
                    pages[-1]["cadres"].append((round(x / mm, 2), round(y / mm, 2)))
                return super().roundRect(x, y, w, h, r, stroke, fill)

            def drawString(self, x, y, text, *args, **kwargs):
                pages[-1]["textes"].append(text)
                return super().drawString(x, y, text, *args, **kwargs)

            def drawCentredString(self, x, y, text, *args, **kwargs):
                pages[-1]["textes"].append(text)
                return super().drawCentredString(x, y, text, *args, **kwargs)

            def showPage(self):
                super().showPage()
                pages.append({"cadres": [], "textes": []})

        with mock.patch.object(views.canvas, "Canvas", Enregistreur):
            views._generer_planche_cartes(
                HttpResponse(content_type="application/pdf"), elements,
                lambda c, e, x, y, w, h, f, fb: views._dessiner_ticket_retrait(c, e, x, y, w, h, f, fb),
                lambda c, e, x, y, w, h, f, fb: views._dessiner_ticket_verso(c, e, x, y, w, h, f, fb, verso),
            )
        return [page for page in pages if page["cadres"]]

    def test_carte_seule_et_planche_ont_le_meme_format(self):
        from . import views

        largeur, hauteur, _ = views._grille_cartes_a4()
        self.assertEqual(views._format_carte_cr80(), (largeur, hauteur))
        self.assertAlmostEqual(largeur / self.mm, 85.6)
        self.assertAlmostEqual(hauteur / self.mm, 53.98)

    def test_chaque_verso_tombe_au_dos_de_son_recto(self):
        from reportlab.lib.pagesizes import A4

        pages = self._planche([self._eleve(i) for i in range(1, 11)], "retrait")

        # Recto 1, verso 1, recto 2, verso 2
        self.assertEqual([len(p["cadres"]) for p in pages], [8, 8, 2, 2])
        largeur_page = A4[0] / self.mm
        for recto, verso in ((pages[0], pages[1]), (pages[2], pages[3])):
            for (xr, yr), (xv, yv) in zip(recto["cadres"], verso["cadres"]):
                self.assertAlmostEqual(yv, yr, places=2)
                self.assertAlmostEqual(xv, round(largeur_page - xr - 85.6, 2), places=1)

    def test_verso_affiche_ecole_et_deux_personnes_autorisees(self):
        pages = self._planche([self._eleve(1), self._eleve(2, avec_second=False)], "bus")
        textes = " | ".join(pages[1]["textes"])

        self.assertIn("HADJA KANFING", textes)
        self.assertIn("MAMADOU DIALLO1", textes)
        self.assertIn("FATOUMATA CAMARA", textes)
        self.assertIn("+224620000000", textes)
        self.assertIn("+224655111222", textes)
        self.assertIn("Non renseignee", textes)

    def test_nom_d_ecole_long_passe_sur_deux_lignes(self):
        from . import views

        font, font_bold = views._polices_cartes()
        largeur = 85.6 * self.mm - 6 * self.mm
        lignes, taille = views._ticket_lignes_titre(
            "GROUPE SCOLAIRE HADJA KANFING DIANE DE CONAKRY", font_bold, largeur, 12, 6, 10
        )
        self.assertEqual(len(lignes), 2)
        self.assertGreaterEqual(taille, 10)

        lignes, taille = views._ticket_lignes_titre("GS KANFING", font_bold, largeur, 12, 6, 10)
        self.assertEqual(lignes, ["GS KANFING"])
        self.assertEqual(taille, 12)
