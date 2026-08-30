from importlib import import_module

from django.apps import apps
from django.conf import settings
from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from eleves.models import Classe, Ecole, GrilleTarifaire
from eleves.utils import valider_compte_utilisateur
from .models import Profil


def middleware_sans_licence():
    return [
        middleware
        for middleware in settings.MIDDLEWARE
        if middleware != 'ecole_moderne.licence_middleware.LicenceMiddleware'
    ]


class ComptesPrincipauxTests(TestCase):
    def creer_ecole(self, nom, telephone):
        return Ecole.objects.create(
            nom=nom,
            adresse='Conakry',
            telephone=telephone,
            directeur='Direction',
            etat='VALIDE',
        )

    def creer_principal(self, username, ecole):
        user = User.objects.create_user(username=username, password='PrincipalSolide2026!')
        profil = user.profil
        profil.role = 'DIRECTEUR'
        profil.telephone = '+224622000001'
        profil.ecole = ecole
        profil.est_compte_principal = True
        profil.peut_gerer_utilisateurs = True
        profil.peut_gerer_classes = True
        profil.peut_gerer_grilles_tarifaires = True
        profil.is_validated = True
        profil.actif = True
        profil.save()
        return user

    def setUp(self):
        self.ecole = self.creer_ecole('École principale', '+224622000001')
        self.autre_ecole = self.creer_ecole('Autre école', '+224622000002')
        self.principal = self.creer_principal('principal_ecole', self.ecole)
        self.autre_principal = self.creer_principal('principal_autre', self.autre_ecole)

    def test_principal_cree_un_sous_utilisateur_limite_a_son_ecole(self):
        self.client.force_login(self.principal)
        with self.settings(MIDDLEWARE=middleware_sans_licence()):
            response = self.client.post(reverse('utilisateurs:sous_utilisateur_create'), {
                'username': 'secretaire_ecole',
                'first_name': 'Aissatou',
                'last_name': 'Diallo',
                'email': 'aissatou@example.test',
                'telephone': '+224622000009',
                'role': 'SECRETAIRE',
                'password1': 'SousCompteSolide2026!',
                'password2': 'SousCompteSolide2026!',
                'allowed_menus': ['eleves', 'paiements'],
                'peut_ajouter_paiements': 'on',
            })

        self.assertRedirects(response, reverse('utilisateurs:sous_utilisateur_list'))
        profil = Profil.objects.select_related('user').get(user__username='secretaire_ecole')
        self.assertEqual(profil.ecole, self.ecole)
        self.assertEqual(profil.compte_principal, self.principal.profil)
        self.assertEqual(profil.allowed_menus, ['eleves', 'paiements'])
        self.assertTrue(profil.peut_ajouter_paiements)
        self.assertFalse(profil.est_compte_principal)
        self.assertFalse(profil.user.is_staff)

    def test_sous_utilisateur_ne_peut_pas_ouvrir_un_menu_non_autorise(self):
        child = User.objects.create_user(username='agent_eleves', password='SousCompteSolide2026!')
        profil = child.profil
        profil.role = 'SECRETAIRE'
        profil.telephone = '+224622000008'
        profil.ecole = self.ecole
        profil.compte_principal = self.principal.profil
        profil.allowed_menus = ['eleves']
        profil.is_validated = True
        profil.actif = True
        profil.save()
        self.client.force_login(child)

        with self.settings(MIDDLEWARE=middleware_sans_licence()):
            interdit = self.client.get(reverse('paiements:tableau_bord'))
            autorise = self.client.get(reverse('eleves:gestion_classes'))

        self.assertEqual(interdit.status_code, 403)
        self.assertContains(interdit, "Le menu", status_code=403)
        self.assertContains(interdit, "Paiements", status_code=403)
        self.assertEqual(autorise.status_code, 200)

    def test_un_principal_ne_modifie_pas_les_sous_utilisateurs_d_une_autre_ecole(self):
        child = User.objects.create_user(username='agent_autre', password='SousCompteSolide2026!')
        profil = child.profil
        profil.role = 'SECRETAIRE'
        profil.telephone = '+224622000007'
        profil.ecole = self.autre_ecole
        profil.compte_principal = self.autre_principal.profil
        profil.is_validated = True
        profil.actif = True
        profil.save()
        self.client.force_login(self.principal)

        with self.settings(MIDDLEWARE=middleware_sans_licence()):
            response = self.client.get(reverse('utilisateurs:sous_utilisateur_update', args=[profil.id]))

        self.assertEqual(response.status_code, 404)

    def test_les_droits_classes_et_grilles_restent_independants(self):
        child = User.objects.create_user(username='agent_classes', password='SousCompteSolide2026!')
        profil = child.profil
        profil.role = 'SECRETAIRE'
        profil.telephone = '+224622000006'
        profil.ecole = self.ecole
        profil.compte_principal = self.principal.profil
        profil.allowed_menus = ['eleves']
        profil.peut_gerer_classes = True
        profil.peut_gerer_grilles_tarifaires = False
        profil.is_validated = True
        profil.actif = True
        profil.save()
        self.client.force_login(child)
        config_url = reverse('eleves:configurer_ecole', args=[self.ecole.id])

        with self.settings(MIDDLEWARE=middleware_sans_licence()):
            self.client.post(config_url, {
                'action': 'add_classe',
                'classe_nom': '9ème C',
                'classe_niveau': 'COLLEGE_9',
                'classe_annee': '2026-2027',
                'classe_capacite': '35',
            })
            self.client.post(config_url, {
                'action': 'add_grille',
                'grille_niveau': 'COLLEGE_9',
                'grille_annee': '2026-2027',
                'grille_t1': '250000',
            })

        self.assertTrue(Classe.objects.filter(ecole=self.ecole, nom='9ÈME C').exists())
        self.assertFalse(GrilleTarifaire.objects.filter(ecole=self.ecole, niveau='COLLEGE_9').exists())

    def test_un_compte_en_lecture_seule_peut_modifier_son_mot_de_passe(self):
        child = User.objects.create_user(username='agent_lecture', password='AncienMotDePasse2026!')
        profil = child.profil
        profil.role = 'SECRETAIRE'
        profil.telephone = '+224622000005'
        profil.ecole = self.ecole
        profil.compte_principal = self.principal.profil
        profil.lecture_seule = True
        profil.is_validated = True
        profil.actif = True
        profil.save()
        self.client.force_login(child)

        with self.settings(MIDDLEWARE=middleware_sans_licence()):
            response = self.client.post(reverse('utilisateurs:password_change'), {
                'current_password': 'AncienMotDePasse2026!',
                'new_password': 'NouveauMotDePasse2026!',
                'confirm_password': 'NouveauMotDePasse2026!',
            })

        self.assertRedirects(response, reverse('utilisateurs:login'))
        child.refresh_from_db()
        self.assertTrue(child.check_password('NouveauMotDePasse2026!'))

    def test_superadmin_cree_uniquement_un_compte_principal_associe_a_une_ecole(self):
        ecole_sans_principal = self.creer_ecole('École à attribuer', '+224622000003')
        admin = User.objects.create_superuser('superadmin_test', 'admin@example.test', 'AdminSolide2026!')
        self.client.force_login(admin)

        with self.settings(MIDDLEWARE=middleware_sans_licence()):
            response = self.client.post(reverse('utilisateurs:creer_compte'), {
                'username': 'direction_nouvelle',
                'first_name': 'Direction',
                'last_name': 'École',
                'email': 'direction@example.test',
                'telephone': '+224622000004',
                'ecole': str(ecole_sans_principal.id),
                'password': 'DirectionSolide2026!',
                'password2': 'DirectionSolide2026!',
            })

        self.assertRedirects(response, reverse('utilisateurs:activation'))
        profil = Profil.objects.get(user__username='direction_nouvelle')
        self.assertTrue(profil.est_compte_principal)
        self.assertEqual(profil.role, 'DIRECTEUR')
        self.assertEqual(profil.ecole, ecole_sans_principal)
        self.assertTrue(profil.peut_gerer_utilisateurs)
        self.assertTrue(profil.peut_gerer_classes)
        self.assertTrue(profil.peut_gerer_grilles_tarifaires)

    def test_principal_gere_classes_et_grilles_d_une_ecole_validee(self):
        self.client.force_login(self.principal)
        config_url = reverse('eleves:configurer_ecole', args=[self.ecole.id])
        with self.settings(MIDDLEWARE=middleware_sans_licence()):
            classe_response = self.client.post(config_url, {
                'action': 'add_classe',
                'classe_nom': '7ème A',
                'classe_niveau': 'COLLEGE_7',
                'classe_annee': '2026-2027',
                'classe_capacite': '40',
            })
            grille_response = self.client.post(config_url, {
                'action': 'add_grille',
                'grille_niveau': 'COLLEGE_7',
                'grille_annee': '2026-2027',
                'grille_inscription': '100000',
                'grille_reinscription': '75000',
                'grille_t1': '500000',
                'grille_t2': '400000',
                'grille_t3': '300000',
            })

        self.assertRedirects(classe_response, config_url)
        self.assertRedirects(grille_response, config_url)
        classe = Classe.objects.get(ecole=self.ecole, nom='7ÈME A')
        grille = GrilleTarifaire.objects.get(ecole=self.ecole, niveau='COLLEGE_7')
        self.assertEqual(classe.capacite_max, 40)
        self.assertEqual(grille.frais_reinscription, 75000)

        classe_autre = Classe.objects.create(
            ecole=self.autre_ecole,
            nom='8ème B',
            niveau='COLLEGE_8',
            annee_scolaire='2026-2027',
        )
        with self.settings(MIDDLEWARE=middleware_sans_licence()):
            interdit = self.client.get(reverse('eleves:modifier_classe_configuration', args=[classe_autre.id]))
        self.assertEqual(interdit.status_code, 403)

    def test_menu_compte_contient_changement_mot_de_passe_et_gestion_deleguee(self):
        self.client.force_login(self.principal)
        with self.settings(MIDDLEWARE=middleware_sans_licence()):
            response = self.client.get(reverse('eleves:gestion_classes'))
        self.assertContains(response, reverse('utilisateurs:password_change'))
        self.assertContains(response, reverse('utilisateurs:sous_utilisateur_list'))
        self.assertContains(response, reverse('eleves:configurer_ecole', args=[self.ecole.id]))

    def test_validation_nouvelle_ecole_active_toutes_les_nouvelles_fonctions(self):
        user = User.objects.create_user(
            username='nouvelle_direction',
            password='NouvelleDirection2026!',
            is_active=False,
        )
        ecole = Ecole.objects.create(
            nom='Nouvelle école',
            adresse='Conakry',
            telephone='+224622000011',
            directeur='Nouvelle direction',
            created_by=user,
            etat='EN_ATTENTE',
        )

        profil = valider_compte_utilisateur(
            user,
            ecole,
            telephone='+224622000011',
            adresse='Conakry',
        )

        self.assertTrue(profil.est_compte_principal)
        self.assertEqual(profil.ecole, ecole)
        self.assertTrue(profil.peut_gerer_utilisateurs)
        self.assertTrue(profil.peut_gerer_classes)
        self.assertTrue(profil.peut_gerer_grilles_tarifaires)
        self.assertEqual(set(profil.allowed_menus), {
            'eleves', 'paiements', 'depenses', 'salaires',
            'bus', 'notes', 'rapports',
        })

        self.client.force_login(user)
        with self.settings(MIDDLEWARE=middleware_sans_licence()):
            response = self.client.get(reverse('eleves:gestion_classes'))
        self.assertContains(response, reverse('utilisateurs:sous_utilisateur_list'))
        self.assertContains(response, reverse('eleves:configurer_ecole', args=[ecole.id]))

    def test_signal_ecole_validee_repare_un_ancien_compte(self):
        ecole = Ecole.objects.create(
            nom='École historique signal',
            adresse='Conakry',
            telephone='+224622000012',
            directeur='Ancienne direction',
            etat='EN_ATTENTE',
        )
        user = User.objects.create_user(username='ancien_compte_signal', password='AncienCompte2026!')
        profil = user.profil
        profil.ecole = ecole
        profil.role = 'COMPTABLE'
        profil.est_compte_principal = False
        profil.allowed_menus = []
        profil.save()

        ecole.etat = 'VALIDE'
        ecole.save(update_fields=['etat'])

        profil.refresh_from_db()
        self.assertTrue(profil.est_compte_principal)
        self.assertEqual(profil.role, 'DIRECTEUR')
        self.assertTrue(profil.peut_gerer_classes)
        self.assertTrue(profil.peut_gerer_grilles_tarifaires)

    def test_migration_repare_ecole_historique_sans_directeur(self):
        ecole = Ecole.objects.create(
            nom='École historique migration',
            adresse='Conakry',
            telephone='+224622000013',
            directeur='Ancienne direction',
            etat='EN_ATTENTE',
        )
        principal_user = User.objects.create_user(username='ancien_comptable', password='AncienCompte2026!')
        principal = principal_user.profil
        principal.ecole = ecole
        principal.role = 'COMPTABLE'
        principal.est_compte_principal = False
        principal.allowed_menus = []
        principal.save()

        agent_user = User.objects.create_user(username='ancien_agent', password='AncienAgent2026!')
        agent = agent_user.profil
        agent.ecole = ecole
        agent.role = 'SECRETAIRE'
        agent.est_compte_principal = False
        agent.allowed_menus = []
        agent.save()

        migration = import_module(
            'utilisateurs.migrations.0016_reparer_comptes_principaux_ecoles'
        )
        migration.reparer_comptes_principaux(apps, None)

        principal.refresh_from_db()
        agent.refresh_from_db()
        self.assertTrue(principal.est_compte_principal)
        self.assertEqual(principal.role, 'DIRECTEUR')
        self.assertTrue(principal.peut_gerer_utilisateurs)
        self.assertTrue(principal.peut_gerer_classes)
        self.assertEqual(agent.compte_principal, principal)
        self.assertEqual(set(agent.allowed_menus), set(principal.allowed_menus))
