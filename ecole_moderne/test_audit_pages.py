"""Vérifier que les pages de consultation des modules restent accessibles."""
from django.contrib.auth.models import User
from django.core.cache import cache
from django.test import TestCase, override_settings
from django.urls import reverse

from eleves.models import Classe, Ecole, Eleve
from notes.models import ClasseNote, MatiereNote
from paiements.tests.support import MIDDLEWARE_SANS_LICENCE
from utilisateurs.services import attribuer_compte_principal


PAGES = '''bus:liste bus:liste_abonnements_cantine bus:tableau_bord_cantine
depenses:dashboard_bibliotheque depenses:dashboard_courantes depenses:dashboard_informatique
depenses:dashboard_logistique depenses:dashboard_salaires depenses:gestion_categories
depenses:gestion_categories_articles depenses:gestion_categories_livres
depenses:liste_abonnements_informatique depenses:liste_articles depenses:liste_articles_legacy
depenses:liste_biens depenses:liste_contributions_papier depenses:liste_depenses
depenses:liste_emprunts depenses:liste_inventaires depenses:liste_mouvements
depenses:liste_mouvements_legacy depenses:liste_reservations depenses:statistiques_bibliotheque
depenses:tableau_bord eleves:gestion_annees eleves:gestion_classes eleves:liste_eleves
eleves:statistiques_eleves notes:liste_activites notes:liste_devoirs notes:liste_saisie_pdf
notes:statistiques notes:tableau_bord notes:tableau_honneur
paiements:liste_eleves_impayes paiements:liste_eleves_soldes paiements:liste_paiements
paiements:gerer_rappels paiements:eleves_en_retard paiements:liste_relances paiements:rapport_comptable paiements:rapport_encaissements
paiements:rapport_remises paiements:rapport_retards paiements:statistiques_rappels paiements:tableau_bord
presence:rapport presence:rapport_excel presence:rapport_pdf rapports:liste_rapports
rapports:rapport_annuel rapports:rapport_hebdomadaire rapports:rapport_journalier
rapports:rapport_mensuel rapports:rapport_remises rapports:rapport_transport rapports:tableau_bord
salaires:gestion_periodes salaires:liste_avances salaires:liste_enseignants salaires:liste_presences
salaires:rapport_paiements salaires:rapport_presences salaires:tableau_bord'''.split()


@override_settings(MIDDLEWARE=MIDDLEWARE_SANS_LICENCE)
class PagesModulesAuditTests(TestCase):
    def setUp(self):
        cache.clear()
        user = User.objects.create_user('principal-pages-audit')
        ecole = Ecole.objects.create(nom='École parcours', etat='VALIDE', created_by=user)
        attribuer_compte_principal(user.profil, ecole)
        classe = Classe.objects.create(ecole=ecole, nom='1ère année A', niveau='PRIMAIRE_1', annee_scolaire='2026-2027')
        Eleve.objects.create(classe=classe, matricule='PAGES-001', prenom='Aminata', nom='Bah', sexe='F')
        classe_note = ClasseNote.objects.create(ecole=ecole, nom=classe.nom, niveau='PRIMAIRE_1', niveau_enseignement='PRIMAIRE', annee_scolaire='2026-2027')
        self.matiere = MatiereNote.objects.create(classe=classe_note, nom='Calcul', code='CAL', coefficient=1)
        self.classe = classe
        self.classe_note = classe_note
        self.client.force_login(user)

    def test_pages_de_consultation(self):
        for name in PAGES:
            with self.subTest(page=name):
                params = {}
                if name == 'notes:liste_saisie_pdf':
                    params = {'classe_id': self.classe_note.pk, 'matiere_id': self.matiere.pk, 'periode': 'TRIMESTRE_1'}
                elif name in ('presence:rapport_excel', 'presence:rapport_pdf'):
                    params = {'classe_id': self.classe.pk}
                response = self.client.get(reverse(name), params)
                self.assertIn(response.status_code, (200, 302))
