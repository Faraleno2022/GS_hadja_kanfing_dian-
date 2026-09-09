"""Non-regression des failles de securite confirmees en septembre 2026."""
import json
import time
from unittest.mock import patch
from django.test import TestCase, Client, override_settings
from django.urls import reverse
from django.core.cache import cache
from django.conf import settings
from django.utils.html import escape
from paiements.tests import test_school_filtering as fixtures
from paiements.tests.support import MIDDLEWARE_SANS_LICENCE
from synchronisation.models import SyncDevice
from utilisateurs.models import Profil
from eleves.models import Ecole

from ecole_moderne.middleware_config import production_middlewares
MW = production_middlewares(MIDDLEWARE_SANS_LICENCE)

@override_settings(MIDDLEWARE=MW, DEBUG=False, ALLOWED_HOSTS=['testserver'],
                   SECURE_SSL_REDIRECT=False, SECURE_CONTENT_TYPE_NOSNIFF=True,
                   SESSION_COOKIE_HTTPONLY=True, SESSION_COOKIE_SAMESITE='Strict',
                   CSRF_COOKIE_HTTPONLY=True, CSRF_COOKIE_SAMESITE='Strict',
                   CACHES={'default': {'BACKEND': 'django.core.cache.backends.locmem.LocMemCache'}})
class SecurityTests(TestCase):
    def setUp(self):
        fixtures.SchoolFilteringTests.setUp(self)
        self.user1.refresh_from_db()
        self.user2.refresh_from_db()
        Profil.objects.filter(user__in=[self.user1, self.user2]).update(is_validated=True)
        cache.clear()
        self.login(self.user1)

    def login(self, user, client=None):
        user.refresh_from_db()
        client = client or self.client
        client.force_login(user)
        session = client.session
        session['phone_verified'] = True
        session['phone_verified_at'] = time.time()
        session.save()
        return client

    def admin(self, user=None):
        user = user or self.user1
        Profil.objects.filter(user=user).update(role='ADMIN', is_validated=True)
        self.login(user)

    def headers(self, active=True):
        device = SyncDevice(ecole=self.ecole1, nom='Audit sécurité fictif', actif=active)
        device.definir_token('FAKE-security-test-only')
        device.save()
        return {'HTTP_X_SYNC_DEVICE': str(device.device_id),
                'HTTP_X_SYNC_TOKEN': 'FAKE-security-test-only'}

    def push(self, model, obj, payload, headers=None, operation='UPDATE'):
        return self.client.post(reverse('synchronisation:push'), json.dumps({'changes': [{
            'model': model, 'object_uuid': str(obj.sync_uuid),
            'operation': operation, 'payload': payload,
        }]}), content_type='application/json', **(headers or self.headers()))

    def toggle(self, target, field, value='true', client=None):
        return (client or self.client).post(reverse('utilisateurs:ajax_toggle_permission'), {
            'comptable_id': target.profil.pk, 'permission_name': field, 'value': value,
        })

    def test_permission_legitime_autorisee(self):
        Profil.objects.filter(user=self.user1).update(peut_gerer_utilisateurs=True)
        self.login(self.user1)
        r = self.toggle(self.user1, 'peut_supprimer_paiements')
        self.assertTrue(r.json()['success'])
        self.user1.refresh_from_db()
        self.assertTrue(self.user1.profil.peut_supprimer_paiements)

    def test_permission_ecole_etrangere_refusee(self):
        self.admin()
        r = self.toggle(self.user2, 'peut_supprimer_paiements')
        self.assertFalse(r.json()['success'])
        self.user2.refresh_from_db()
        self.assertFalse(self.user2.profil.peut_supprimer_paiements)

    def test_permission_sans_habilitation_refusee(self):
        Profil.objects.filter(user=self.user1).update(peut_gerer_utilisateurs=False, est_compte_principal=False)
        self.login(self.user1)
        self.assertEqual(self.toggle(self.user1, 'peut_supprimer_paiements').status_code, 403)

    def test_permission_ne_permet_pas_changement_ecole(self):
        self.assertEqual(self.ecole1.pk, 1, 'Précondition : école cible ID 1')
        Profil.objects.filter(user=self.user2).update(peut_gerer_utilisateurs=True)
        self.login(self.user2)
        before = self.client.get(reverse('paiements:detail_paiement', args=[self.paiement1.pk]))
        self.assertNotEqual(before.status_code, 200)
        r = self.toggle(self.user2, 'ecole_id')
        self.user2.refresh_from_db()
        after = self.client.get(reverse('paiements:detail_paiement', args=[self.paiement1.pk]))
        self.assertEqual(self.user2.profil.ecole_id, self.ecole2.pk,
            f"Champ ecole_id accepté={r.json().get('success')}; reçu autre école avant={before.status_code}, après={after.status_code}")

    def test_permission_ne_permet_pas_auto_promotion(self):
        Profil.objects.filter(user=self.user1).update(peut_gerer_utilisateurs=True, est_compte_principal=False)
        self.login(self.user1)
        r = self.toggle(self.user1, 'est_compte_principal')
        self.user1.refresh_from_db()
        self.assertFalse(self.user1.profil.est_compte_principal,
            f"Promotion compte principal acceptée={r.json().get('success')}")

    def test_admin_sans_ecole_ne_peut_pas_exporter_autres_ecoles(self):
        self.admin()
        Profil.objects.filter(user=self.user1).update(ecole=None)
        r = self.client.get(reverse('utilisateurs:export_permissions_csv'))
        self.assertNotIn(self.user2.username.encode(), r.content,
                         f"Export global accessible sans école, HTTP {r.status_code}")

    def test_admin_sans_ecole_ne_peut_pas_modifier_autres_ecoles(self):
        self.admin()
        Profil.objects.filter(user=self.user1).update(ecole=None)
        self.client.post(reverse('utilisateurs:bulk_update_permissions'), {
            'action': 'allow_all', 'comptable_ids': [self.user2.profil.pk],
        })
        self.user2.refresh_from_db()
        self.assertFalse(self.user2.profil.peut_supprimer_paiements)

    def test_csrf_formulaire_classique_bloque(self):
        self.admin()
        c = self.login(self.user1, Client(enforce_csrf_checks=True))
        r = self.toggle(self.user2, 'peut_supprimer_paiements', client=c)
        self.assertEqual(r.status_code, 403)

    def test_csrf_enregistrement_poste_bloque(self):
        self.admin()
        c = self.login(self.user1, Client(enforce_csrf_checks=True))
        before = SyncDevice.objects.count()
        r = c.post(reverse('synchronisation:register_device'),
                   json.dumps({'nom': 'Poste de test CSRF'}),
                   content_type='text/plain', HTTP_ORIGIN='https://origine-non-autorisee.invalid')
        self.assertEqual(SyncDevice.objects.count(), before,
                         f"Session sans jeton CSRF : HTTP {r.status_code}, appareil créé")
        self.assertEqual(r.status_code, 403)

    def test_enregistrement_poste_avec_csrf_autorise(self):
        self.admin()
        c = self.login(self.user1, Client(enforce_csrf_checks=True))
        c.get(reverse('synchronisation:device_setup'))
        self.assertIn('csrftoken', c.cookies)
        r = c.post(reverse('synchronisation:register_device'),
                   json.dumps({'nom': 'Poste légitime'}),
                   content_type='application/json', HTTP_X_CSRFTOKEN=c.cookies['csrftoken'].value)
        self.assertEqual(r.status_code, 201)

    @override_settings(MYSCHOOL_SYNC_ADMIN_TOKEN='FAKE-test-admin-token')
    def test_enregistrement_poste_jeton_admin_autorise(self):
        c = Client(enforce_csrf_checks=True)
        r = c.post(reverse('synchronisation:register_device'),
                   json.dumps({'nom': 'Poste API', 'ecole_id': self.ecole1.pk}),
                   content_type='application/json', HTTP_X_SYNC_ADMIN_TOKEN='FAKE-test-admin-token')
        self.assertEqual(r.status_code, 201)

    def test_enregistrement_poste_anonyme_refuse(self):
        c = Client()
        self.assertEqual(c.post(reverse('synchronisation:register_device'),
                         '{}', content_type='application/json').status_code, 403)

    def test_sync_sans_jeton_refuse(self):
        self.assertEqual(self.client.get(reverse('synchronisation:pull')).status_code, 401)

    def test_sync_mauvais_jeton_refuse(self):
        h = self.headers()
        h['HTTP_X_SYNC_TOKEN'] = 'FAKE-wrong-token'
        self.assertEqual(self.client.get(reverse('synchronisation:pull'), **h).status_code, 403)

    def test_sync_poste_desactive_refuse(self):
        self.assertEqual(self.client.get(reverse('synchronisation:pull'), **self.headers(active=False)).status_code, 403)

    def test_sync_ecole_ne_peut_pas_se_valider(self):
        Ecole.objects.filter(pk=self.ecole1.pk).update(etat='REJETE')
        r = self.push('eleves.Ecole', self.ecole1, {'etat': 'VALIDE'})
        self.ecole1.refresh_from_db()
        self.assertEqual(self.ecole1.etat, 'REJETE',
                         f"Validation réservée au superadmin acceptée={r.json().get('accepted_count')}")

    def test_sync_modification_etrangere_refusee(self):
        original = self.eleve2.nom
        r = self.push('eleves.Eleve', self.eleve2, {'nom': 'CHANGEMENT INTERDIT'})
        self.eleve2.refresh_from_db()
        self.assertEqual(r.json()['accepted_count'], 0)
        self.assertEqual(self.eleve2.nom, original)

    def test_sync_suppression_etrangere_refusee(self):
        r = self.push('eleves.Eleve', self.eleve2, {}, operation='DELETE')
        self.assertEqual(r.json()['accepted_count'], 0)
        self.assertTrue(type(self.eleve2).objects.filter(pk=self.eleve2.pk).exists())

    def test_sync_relation_etrangere_refusee(self):
        r = self.push('eleves.Eleve', self.eleve1, {'classe': {'sync_uuid': str(self.classe2.sync_uuid)}})
        self.eleve1.refresh_from_db()
        self.assertEqual(r.json()['accepted_count'], 0)
        self.assertEqual(self.eleve1.classe_id, self.classe1.pk)

    def test_sync_paiement_negatif_refuse(self):
        r = self.push('paiements.Paiement', self.paiement1, {'montant': '-1'})
        self.paiement1.refresh_from_db()
        self.assertEqual(r.json()['accepted_count'], 0)
        self.assertGreaterEqual(self.paiement1.montant, 0)

    def test_sync_json_liste_refuse(self):
        r = self.client.post(reverse('synchronisation:push'), '[]',
                             content_type='application/json', **self.headers())
        self.assertEqual(r.status_code, 400)

    def test_sync_lot_trop_long_refuse(self):
        r = self.client.post(reverse('synchronisation:push'), json.dumps({'changes': [{}] * 1001}),
                             content_type='application/json', **self.headers())
        self.assertEqual(r.status_code, 400)

    def test_compte_revoque_perd_acces_session_existante(self):
        url = reverse('paiements:detail_paiement', args=[self.paiement1.pk])
        self.assertEqual(self.client.get(url).status_code, 200)
        Profil.objects.filter(user=self.user1).update(is_validated=False, actif=False)
        self.assertNotEqual(self.client.get(url).status_code, 200,
                            'Le profil désactivé/non validé conserve sa session et son accès au reçu')

    def test_lecture_seule_bloque_modification(self):
        Profil.objects.filter(user=self.user1).update(lecture_seule=True, peut_gerer_utilisateurs=True)
        self.login(self.user1)
        self.toggle(self.user1, 'peut_supprimer_paiements')
        self.user1.refresh_from_db()
        self.assertFalse(self.user1.profil.peut_supprimer_paiements)

    def test_paiement_anonyme_refuse(self):
        self.assertEqual(Client().get(reverse('paiements:detail_paiement', args=[self.paiement1.pk])).status_code, 302)

    def test_nom_eleve_html_echappe(self):
        marker = '<img src=x onerror="AUDIT_SENTINEL">'
        type(self.eleve1).objects.filter(pk=self.eleve1.pk).update(nom=marker)
        r = self.client.get(reverse('paiements:detail_paiement', args=[self.paiement1.pk]))
        self.assertEqual(r.status_code, 200)
        body = r.content.decode()
        self.assertNotIn(marker, body)
        self.assertIn(escape(marker), body)

    def test_entetes_securite_presents(self):
        r = self.client.get(reverse('paiements:detail_paiement', args=[self.paiement1.pk]))
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r['X-Content-Type-Options'], 'nosniff')
        self.assertIn(r['X-Frame-Options'], ['DENY', 'SAMEORIGIN'])
        self.assertIn('Content-Security-Policy', r)

    def test_session_inactive_30_minutes_est_refusee(self):
        session = self.client.session
        session['last_activity'] = time.time() - 1900
        session.save()
        r = self.client.get(reverse('paiements:detail_paiement', args=[self.paiement1.pk]))
        self.assertNotEqual(r.status_code, 200, "L'expiration prévue à 30 minutes n'est pas appliquée")

    def test_session_sans_verification_telephone_est_refusee(self):
        session = self.client.session
        session['phone_verified'] = False
        session.pop('phone_verified_at', None)
        session.save()
        r = self.client.get(reverse('paiements:detail_paiement', args=[self.paiement1.pk]))
        self.assertNotEqual(r.status_code, 200, "La vérification de session attendue est contournée")

    def test_compte_django_desactive_perd_acces(self):
        type(self.user1).objects.filter(pk=self.user1.pk).update(is_active=False)
        r = self.client.get(reverse('paiements:detail_paiement', args=[self.paiement1.pk]))
        self.assertEqual(r.status_code, 302)

    def test_sauvegarde_locale_inaccessible_en_ligne(self):
        import os
        with patch.dict(os.environ, {'OFFLINE_MODE': '0'}):
            r = self.client.get(reverse('sauvegarde_telecharger'), {'chemin': 'fichier-fictif.zip'})
        self.assertEqual(r.status_code, 403)

    def test_sauvegarde_refuse_fichier_non_reference(self):
        import os
        from pathlib import Path
        sentinel = Path(settings.MEDIA_ROOT) / 'audit-ne-pas-servir.txt'
        sentinel.parent.mkdir(parents=True, exist_ok=True)
        sentinel.write_text('DONNEE FICTIVE', encoding='utf-8')
        type(self.user1).objects.filter(pk=self.user1.pk).update(is_staff=True)
        self.login(self.user1)
        with patch.dict(os.environ, {'OFFLINE_MODE': '1'}), patch(
                'ecole_moderne.sauvegarde_views.moteur.lister_archives_disponibles', return_value=[]):
            r = self.client.get(reverse('sauvegarde_telecharger'), {'chemin': str(sentinel)})
        self.assertIn(r.status_code, (403, 404))
        self.assertNotIn(b"DONNEE FICTIVE", r.content)

    def test_injection_sql_recherche_ne_lit_pas_autre_ecole(self):
        r = self.client.get(reverse('paiements:liste_paiements'), {'recherche': "' OR 1=1 --"})
        self.assertIn(r.status_code, (200, 403))
        self.assertNotIn(self.eleve2.matricule.encode(), r.content)
        self.assertTrue(type(self.paiement2).objects.filter(pk=self.paiement2.pk).exists())

    def test_api_permissions_refuse_tous_les_champs_de_structure(self):
        Profil.objects.filter(user=self.user1).update(peut_gerer_utilisateurs=True)
        self.login(self.user1)
        before = Profil.objects.filter(user=self.user1).values().get()
        for field in ('id', 'user_id', 'ecole_id', 'role', 'is_validated', 'actif',
                      'est_compte_principal', 'compte_principal_id', 'allowed_menus'):
            with self.subTest(field=field):
                r = self.toggle(self.user1, field)
                self.assertEqual(r.status_code, 400)
                self.assertEqual(Profil.objects.filter(user=self.user1).values().get(), before)

    def test_jeton_admin_invalide_ne_desactive_pas_csrf(self):
        self.admin()
        c = self.login(self.user1, Client(enforce_csrf_checks=True))
        with override_settings(MYSCHOOL_SYNC_ADMIN_TOKEN='FAKE-correct-token'):
            r = c.post(reverse('synchronisation:register_device'), '{}',
                       content_type='application/json', HTTP_X_SYNC_ADMIN_TOKEN='FAKE-wrong-token')
        self.assertEqual(r.status_code, 403)
        self.assertFalse(SyncDevice.objects.exists())

    def test_sync_accepte_validation_authentique_du_serveur(self):
        from synchronisation.engine import build_change_instance
        Ecole.objects.filter(pk=self.ecole1.pk).update(etat='EN_ATTENTE')
        build_change_instance('eleves.Ecole', self.ecole1.sync_uuid,
                              {'etat': 'VALIDE'}, ecole=self.ecole1, trusted=True)
        self.ecole1.refresh_from_db()
        self.assertEqual(self.ecole1.etat, 'VALIDE')

    def test_sync_accepte_modification_ecole_sans_changer_validation(self):
        r = self.push('eleves.Ecole', self.ecole1,
                      {'etat': self.ecole1.etat, 'nom': 'Ecole renommee'})
        self.assertEqual(r.json()['accepted_count'], 1)
        self.ecole1.refresh_from_db()
        self.assertEqual(self.ecole1.nom, 'ECOLE RENOMMEE')

    def test_retrait_validation_seul_revoque_session(self):
        Profil.objects.filter(user=self.user1).update(is_validated=False)
        r = self.client.get(reverse('paiements:detail_paiement', args=[self.paiement1.pk]))
        self.assertEqual(r.status_code, 302)
        self.assertNotIn('_auth_user_id', self.client.session)

    def test_desactivation_profil_seule_revoque_session(self):
        Profil.objects.filter(user=self.user1).update(actif=False)
        r = self.client.get(reverse('paiements:detail_paiement', args=[self.paiement1.pk]))
        self.assertEqual(r.status_code, 302)
        self.assertNotIn('_auth_user_id', self.client.session)

    def test_session_timestamp_invalide_refuse_sans_erreur_500(self):
        session = self.client.session
        session['last_activity'] = 'date-invalide'
        session.save()
        r = self.client.get(reverse('paiements:detail_paiement', args=[self.paiement1.pk]))
        self.assertEqual(r.status_code, 302)

    def test_verification_telephone_expiree_impose_reverification(self):
        session = self.client.session
        session['phone_verified_at'] = time.time() - 9 * 3600
        session.save()
        r = self.client.get(reverse('paiements:detail_paiement', args=[self.paiement1.pk]))
        self.assertEqual(r.status_code, 302)
        self.assertTrue(r.url.startswith(reverse('utilisateurs:verify_phone')))

    def test_ordre_production_et_idempotence_configuration(self):
        from ecole_moderne.middleware_config import SESSION_SECURITY
        self.assertEqual(production_middlewares(MW), MW)
        for predecessor in ('django.contrib.sessions.middleware.SessionMiddleware',
                            'django.contrib.auth.middleware.AuthenticationMiddleware',
                            'notes.middleware_acces_enseignants.AccesEnseignantMiddleware',
                            'utilisateurs.middleware.ProfilAccessMiddleware'):
            self.assertLess(MW.index(predecessor), MW.index(SESSION_SECURITY))

    def test_ancien_statut_sur_pc_ne_bloque_pas_les_autres_modifications(self):
        Ecole.objects.filter(pk=self.ecole1.pk).update(etat='VALIDE')
        r = self.push('eleves.Ecole', self.ecole1,
                      {'etat': 'EN_ATTENTE', 'nom': 'Nouveau nom'})
        self.assertEqual(r.json()['accepted_count'], 1)
        self.ecole1.refresh_from_db()
        self.assertEqual(self.ecole1.etat, 'VALIDE')
        self.assertEqual(self.ecole1.nom, 'NOUVEAU NOM')

    def test_verification_telephone_refuse_redirection_externe(self):
        r = self.client.get(reverse('utilisateurs:verify_phone'),
                            {'next': '//site-non-autorise.invalid/'})
        self.assertEqual(r.status_code, 302)
        self.assertEqual(r.url, reverse('eleves:liste_eleves'))

    def test_verification_telephone_post_conserve_destination_locale(self):
        session = self.client.session
        session['phone_verified'] = False
        session.save()
        destination = reverse('paiements:detail_paiement', args=[self.paiement1.pk])
        r = self.client.post(reverse('utilisateurs:verify_phone'),
                             {'telephone': self.user1.profil.telephone, 'next': destination})
        self.assertEqual(r.status_code, 302)
        self.assertEqual(r.url, destination)
        self.assertTrue(self.client.session['phone_verified'])
