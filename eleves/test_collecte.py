"""Collecte enseignants : lien public limité, réception et validation par l'école."""
from datetime import timedelta
import uuid
from unittest.mock import patch

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.http import HttpResponse
from django.test import Client, RequestFactory, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from paiements.tests.support import MIDDLEWARE_SANS_LICENCE
from paiements.models import Paiement, ModePaiement, TypePaiement
from .models import Classe, Ecole, Eleve, Responsable
from .models_collecte import LienCollecteEleves, EnvoiCollecteEleves, PropositionEleve
from .services_collecte import decider_proposition


@override_settings(MIDDLEWARE=MIDDLEWARE_SANS_LICENCE)
class CollecteElevesTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.ecole = Ecole.objects.create(nom='École collecte', adresse='Conakry',
            telephone='620111111', directeur='Direction')
        cls.autre_ecole = Ecole.objects.create(nom='Autre école', adresse='Conakry',
            telephone='620111112', directeur='Direction')
        cls.classe = Classe.objects.create(ecole=cls.ecole, nom='Petite section A',
            niveau='PETITE_SECTION', annee_scolaire='2026-2027')
        cls.autre_classe = Classe.objects.create(ecole=cls.autre_ecole, nom='Autre classe',
            niveau='PETITE_SECTION', annee_scolaire='2026-2027')
        cls.user = cls.utilisateur('direction', cls.ecole)
        cls.autre_user = cls.utilisateur('autre-direction', cls.autre_ecole)
        cls.lien = LienCollecteEleves.objects.create(ecole=cls.ecole, classe=cls.classe,
            annee_scolaire=cls.classe.annee_scolaire, destinataire='Mme Diallo',
            expire_le=timezone.now() + timedelta(days=7), cree_par=cls.user)

    @classmethod
    def utilisateur(cls, nom, ecole, **overrides):
        user = get_user_model().objects.create_user(nom, password='test')
        profil = user.profil
        values = dict(ecole=ecole, role='ADMIN', is_validated=True, actif=True,
            telephone='', allowed_menus=['eleves'])
        values.update(overrides)
        for key, value in values.items():
            setattr(profil, key, value)
        profil.save()
        return user

    def setUp(self):
        cache.clear()
        self.client.force_login(self.user)
        self.public = Client()
        self.url = reverse('collecte_eleves_public', args=[self.lien.token])
        self.gestion = reverse('eleves:gestion_collecte')
        self.detail = reverse('eleves:detail_collecte', args=[self.lien.pk])

    def donnees(self, nombre=1, **overrides):
        data = dict(auteur='Mme Diallo', identifiant=str(uuid.uuid4()))
        data.update({
            'eleves-TOTAL_FORMS': str(nombre), 'eleves-INITIAL_FORMS': '0',
            'eleves-MIN_NUM_FORMS': '1', 'eleves-MAX_NUM_FORMS': '50',
        })
        for i in range(nombre):
            data.update({f'eleves-{i}-prenom': f'Aminata {i}',
                         f'eleves-{i}-nom': 'Camara', f'eleves-{i}-sexe': 'F'})
        data.update(overrides)
        return data

    def proposition(self, **overrides):
        envoi = EnvoiCollecteEleves.objects.create(lien=self.lien,
            identifiant=uuid.uuid4(), auteur='Mme Diallo')
        data = dict(envoi=envoi, prenom='Aminata', nom='Camara', sexe='F')
        data.update(overrides)
        return PropositionEleve.objects.create(**data)

    def accepter(self, proposition, **overrides):
        data = dict(action='accepter', propositions=[proposition.pk], verrouiller='on')
        data.update(overrides)
        return self.client.post(self.detail, data)

    def test_bouton_gestion_et_creation_lien_classe(self):
        self.assertContains(self.client.get(reverse('eleves:liste_eleves')), 'Collecte enseignants')
        response = self.client.get(self.gestion)
        self.assertEqual(list(response.context['form'].fields['classe'].queryset), [self.classe])
        response = self.client.post(self.gestion, {
            'classe': self.classe.pk, 'destinataire': 'Monsieur Barry',
            'expire_le': (timezone.now() + timedelta(hours=2)).strftime('%Y-%m-%dT%H:%M'),
        })
        self.assertEqual(response.status_code, 302)
        nouveau = LienCollecteEleves.objects.latest('pk')
        self.assertNotEqual(nouveau.token, self.lien.token)
        self.assertEqual(nouveau.ecole_id, self.ecole.pk)
        self.assertEqual(nouveau.cree_par_id, self.user.pk)
        self.assertContains(self.client.get(response.url), 'Copier le lien')

    def test_creation_lien_refuse_classe_etrangere_et_dates_invalides(self):
        for classe, expire in (
            (self.autre_classe.pk, timezone.now() + timedelta(days=1)),
            (self.classe.pk, timezone.now() - timedelta(hours=1)),
            (self.classe.pk, timezone.now() + timedelta(days=370)),
        ):
            with self.subTest(classe=classe, expire=expire):
                response = self.client.post(self.gestion, {'classe': classe, 'destinataire': 'Enseignant',
                    'expire_le': expire.strftime('%Y-%m-%dT%H:%M')})
                self.assertEqual(response.status_code, 400)
        self.assertEqual(LienCollecteEleves.objects.count(), 1)

    def test_anonyme_envoie_plusieurs_eleves_sans_creer_dossiers(self):
        response = self.public.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.classe.nom)
        self.assertContains(response, 'csrfmiddlewaretoken')
        self.assertEqual(self.public.post(self.url, self.donnees(2)).status_code, 302)
        self.assertEqual(PropositionEleve.objects.count(), 2)
        self.assertFalse(Eleve.objects.exists())
        self.assertFalse(Responsable.objects.exists())
        response = self.client.get(self.detail)
        self.assertContains(response, 'Aminata 0')
        self.assertContains(response, 'Mme Diallo')
        self.assertEqual(self.client.get(self.gestion).context['attente'], 2)

    def test_aucun_acces_public_aux_eleves_existants_et_aux_autres_envois(self):
        Eleve.objects.create(prenom='Confidentiel', nom='Existant', sexe='M', classe=self.classe)
        proposition = self.proposition(prenom='PropositionConfidentielle')
        response = self.public.get(self.url)
        self.assertNotContains(response, 'Confidentiel')
        self.assertNotContains(response, proposition.prenom)
        self.assertIn('no-store', response.headers['Cache-Control'])
        self.assertEqual(response.headers['Referrer-Policy'], 'strict-origin')
        self.assertIn('noindex', response.headers['X-Robots-Tag'])
        self.assertEqual(self.public.get(self.detail).status_code, 302)

    def test_classe_statut_et_matricule_imposes_cote_serveur(self):
        response = self.public.post(self.url, self.donnees(**{
            'classe': self.autre_classe.pk, 'statut': 'ACCEPTEE',
            'eleves-0-classe': self.autre_classe.pk, 'eleves-0-statut': 'ACCEPTEE',
            'eleves-0-matricule': 'FAUX', 'eleves-0-eleve': 99,
        }))
        self.assertEqual(response.status_code, 302)
        proposition = PropositionEleve.objects.get()
        self.assertEqual(proposition.statut, 'EN_ATTENTE')
        self.accepter(proposition)
        proposition.refresh_from_db()
        self.assertEqual(proposition.eleve.classe_id, self.classe.pk)
        self.assertNotEqual(proposition.eleve.matricule, 'FAUX')

    def test_double_envoi_meme_identifiant_est_idempotent(self):
        data = self.donnees(2)
        for _ in range(2):
            self.assertEqual(self.public.post(self.url, data).status_code, 302)
        self.assertEqual(EnvoiCollecteEleves.objects.count(), 1)
        self.assertEqual(PropositionEleve.objects.count(), 2)

    def test_donnees_invalides_annulent_tout_envoi(self):
        for field, value in (
            ('prenom', ''), ('nom', 'x' * 101), ('sexe', 'X'),
            ('date_naissance', '2100-01-01'), ('telephone_responsable', 'invalide'),
        ):
            with self.subTest(field=field):
                response = self.public.post(self.url, self.donnees(2, **{f'eleves-1-{field}': value}))
                self.assertEqual(response.status_code, 400)
                self.assertFalse(EnvoiCollecteEleves.objects.exists())
        self.assertFalse(PropositionEleve.objects.exists())

    def test_formset_absent_vide_et_surdimensionne_refuse(self):
        for data in ({'auteur': 'Mme Diallo'}, self.donnees(0), self.donnees(51),
                     self.donnees(**{'eleves-TOTAL_FORMS': '999999'})):
            self.assertEqual(self.public.post(self.url, data).status_code, 400)
        self.assertFalse(EnvoiCollecteEleves.objects.exists())

    def test_telephone_facultatif_et_normalisation(self):
        for numero in ('', '622 123 456'):
            data = self.donnees(**{'eleves-0-prenom_responsable': 'Ibrahima',
                'eleves-0-nom_responsable': 'Camara', 'eleves-0-telephone_responsable': numero})
            self.assertEqual(self.public.post(self.url, data).status_code, 302)
        self.assertEqual(list(PropositionEleve.objects.values_list('telephone_responsable', flat=True)),
            ['', '+224622123456'])

    def test_csrf_https_exige_jeton_et_origine_et_accepte_formulaire(self):
        client = Client(enforce_csrf_checks=True)
        self.assertEqual(client.get(self.url, secure=True).status_code, 200)
        data = self.donnees()
        self.assertEqual(client.post(self.url, data, secure=True).status_code, 403)
        data['csrfmiddlewaretoken'] = client.cookies['csrftoken'].value
        self.assertEqual(client.post(self.url, data, secure=True,
            HTTP_ORIGIN='https://exterieur.invalid').status_code, 403)
        self.assertEqual(client.post(self.url, data, secure=True,
            HTTP_REFERER='https://testserver/').status_code, 302)
        self.assertEqual(PropositionEleve.objects.count(), 1)

    def test_lien_inconnu_expire_et_revoque_refusent_get_et_post(self):
        self.assertEqual(self.public.get(reverse('collecte_eleves_public', args=[uuid.uuid4()])).status_code, 404)
        for changements in (
            {'expire_le': timezone.now() - timedelta(seconds=1)},
            {'expire_le': timezone.now() + timedelta(days=2), 'revoque_le': timezone.now()},
        ):
            LienCollecteEleves.objects.filter(pk=self.lien.pk).update(**changements)
            self.assertEqual(self.public.get(self.url).status_code, 410)
            self.assertEqual(self.public.post(self.url, self.donnees()).status_code, 410)
        self.assertFalse(EnvoiCollecteEleves.objects.exists())

    def test_revocation_formulaire_deja_ouvert_bloque_envoi_et_conserve_reception(self):
        proposition = self.proposition()
        self.public.get(self.url)
        self.assertEqual(self.client.post(self.detail, {'action': 'revoquer'}).status_code, 302)
        self.assertEqual(self.public.post(self.url, self.donnees()).status_code, 410)
        self.assertContains(self.client.get(self.detail), proposition.prenom)
        self.accepter(proposition)
        proposition.refresh_from_db()
        self.assertEqual(proposition.statut, 'ACCEPTEE')

    def test_modification_echeance_et_revocation_irreversible(self):
        expire = timezone.now() + timedelta(hours=1)
        self.client.post(self.detail, {'action': 'expiration', 'expire_le': expire.strftime('%Y-%m-%dT%H:%M')})
        self.lien.refresh_from_db()
        self.assertLess(abs((self.lien.expire_le - expire).total_seconds()), 60)
        self.assertEqual(self.client.post(self.detail, {'action': 'expiration', 'expire_le': 'invalide'}).status_code, 400)
        self.client.post(self.detail, {'action': 'revoquer'})
        self.client.post(self.detail, {'action': 'expiration', 'expire_le':
            (timezone.now() + timedelta(days=3)).strftime('%Y-%m-%dT%H:%M')})
        self.lien.refresh_from_db()
        self.assertIsNotNone(self.lien.revoque_le)
        self.assertEqual(self.public.get(self.url).status_code, 410)

    def test_lien_coupe_si_createur_revoque_ou_change_ecole(self):
        for champs in ({'actif': False}, {'ecole': self.autre_ecole}):
            profil = self.user.profil
            profil.actif = True
            profil.ecole = self.ecole
            for key, value in champs.items():
                setattr(profil, key, value)
            profil.save()
            self.assertEqual(self.public.post(self.url, self.donnees()).status_code, 410)

    def test_lien_coupe_si_annee_ou_ecole_classe_change(self):
        for champs in ({'annee_scolaire': '2027-2028'}, {'ecole': self.autre_ecole}):
            Classe.objects.filter(pk=self.classe.pk).update(annee_scolaire='2026-2027', ecole=self.ecole)
            Classe.objects.filter(pk=self.classe.pk).update(**champs)
            self.assertEqual(self.public.get(self.url).status_code, 410)

    def test_accepter_cree_dossier_trace_verrouille_et_deverrouille_apres_paiement(self):
        proposition = self.proposition()
        self.assertEqual(self.accepter(proposition).status_code, 302)
        proposition.refresh_from_db()
        eleve = proposition.eleve
        self.assertTrue(eleve.import_verrouille)
        self.assertEqual(eleve.statut, 'ATTENTE_PAIEMENT')
        self.assertEqual(proposition.traite_par_id, self.user.pk)
        self.assertEqual(eleve.cree_par_id, self.user.pk)
        self.assertTrue(eleve.matricule)
        self.assertFalse(Eleve.pedagogiques.filter(pk=eleve.pk).exists())
        self.assertTrue(eleve.historique.filter(action='CREATION').exists())
        paiement = Paiement.objects.create(eleve=eleve, montant=10000, statut='EN_ATTENTE',
            annee_scolaire=self.classe.annee_scolaire, date_paiement=timezone.localdate(),
            type_paiement=TypePaiement.objects.create(nom='Inscription'),
            mode_paiement=ModePaiement.objects.create(nom='Espèces'))
        eleve.refresh_from_db()
        self.assertTrue(eleve.import_verrouille)
        paiement.statut = 'VALIDE'
        paiement.save()
        eleve.refresh_from_db()
        self.assertFalse(eleve.import_verrouille)

    def test_accepter_sans_verrou_est_choix_explicite(self):
        proposition = self.proposition()
        self.accepter(proposition, verrouiller='')
        proposition.refresh_from_db()
        self.assertFalse(proposition.eleve.import_verrouille)
        self.assertEqual(proposition.eleve.statut, 'ACTIF')

    def test_double_validation_ne_cree_pas_deux_eleves(self):
        proposition = self.proposition()
        self.accepter(proposition)
        self.accepter(proposition)
        self.assertEqual(Eleve.objects.count(), 1)

    def test_refus_ne_cree_pas_eleve_et_ne_peut_pas_etre_revalide(self):
        proposition = self.proposition()
        self.client.post(self.detail, {'action': 'refuser', 'propositions': [proposition.pk]})
        self.accepter(proposition)
        proposition.refresh_from_db()
        self.assertEqual(proposition.statut, 'REFUSEE')
        self.assertFalse(Eleve.objects.exists())

    def test_homonyme_detecte_malgre_accents_espaces_et_confirme_explicitement(self):
        Eleve.objects.create(classe=self.classe, prenom='Sékou  Oumar', nom='Camara', sexe='M')
        proposition = self.proposition(prenom='Sekou Oumar')
        self.assertContains(self.client.get(self.detail), 'Homonyme à vérifier')
        self.accepter(proposition)
        self.assertEqual(Eleve.objects.count(), 1)
        self.accepter(proposition, confirmer_homonymes='on')
        self.assertEqual(Eleve.objects.count(), 2)

    def test_doublons_meme_lot_n_creent_pas_deux_dossiers(self):
        a, b = self.proposition(), self.proposition()
        self.client.post(self.detail, {'action': 'accepter', 'propositions': [a.pk, b.pk], 'verrouiller': 'on'})
        self.assertEqual(Eleve.objects.count(), 1)
        self.assertEqual(PropositionEleve.objects.filter(statut='EN_ATTENTE').count(), 1)

    def test_corriger_proposition_avant_creation(self):
        proposition = self.proposition()
        url = reverse('eleves:verifier_proposition', args=[proposition.pk])
        self.assertEqual(self.client.get(url).status_code, 200)
        data = {'action': 'enregistrer', 'prenom': 'Fatoumata', 'nom': 'Bah', 'sexe': 'F'}
        self.assertEqual(self.client.post(url, data).status_code, 302)
        self.assertFalse(Eleve.objects.exists())
        data['action'] = 'accepter'
        data['verrouiller'] = 'on'
        self.assertEqual(self.client.post(url, data).status_code, 302)
        proposition.refresh_from_db()
        self.assertEqual(proposition.eleve.prenom, 'FATOUMATA')
        self.assertEqual(proposition.eleve.nom, 'BAH')

    def test_correction_invalide_ne_modifie_pas_proposition(self):
        proposition = self.proposition()
        url = reverse('eleves:verifier_proposition', args=[proposition.pk])
        self.assertEqual(self.client.post(url, {'action': 'accepter', 'prenom': '', 'nom': 'Test', 'sexe': 'F'}).status_code, 400)
        proposition.refresh_from_db()
        self.assertEqual(proposition.prenom, 'Aminata')
        self.assertFalse(Eleve.objects.exists())

    def test_parent_ne_reutilise_pas_parent_autre_ecole(self):
        parent = Responsable.objects.create(prenom='Ibrahima', nom='Camara', relation='PERE',
            telephone='+224622123456', adresse='Conakry')
        Eleve.objects.create(prenom='Autre', nom='Enfant', sexe='M', classe=self.autre_classe, responsable_principal=parent)
        proposition = self.proposition(prenom_responsable='Ibrahima', nom_responsable='Camara',
            telephone_responsable='+224622123456')
        self.accepter(proposition)
        proposition.refresh_from_db()
        self.assertNotEqual(proposition.eleve.responsable_principal_id, parent.pk)
        self.assertEqual(proposition.eleve.responsable_principal.telephone, '+224622123456')

    def test_autre_ecole_ne_lit_ni_ne_traite_proposition_ou_lien(self):
        proposition = self.proposition()
        self.client.force_login(self.autre_user)
        self.assertNotContains(self.client.get(self.gestion), 'Mme Diallo')
        for url in (self.detail, reverse('eleves:verifier_proposition', args=[proposition.pk])):
            self.assertEqual(self.client.get(url).status_code, 404)
            self.assertEqual(self.client.post(url, {'action': 'revoquer'}).status_code, 404)
        self.assertFalse(Eleve.objects.exists())

    def test_ids_autre_collecte_refuses_en_validation_lot(self):
        autre = LienCollecteEleves.objects.create(ecole=self.autre_ecole, classe=self.autre_classe,
            annee_scolaire='2026-2027', destinataire='Autre', expire_le=timezone.now()+timedelta(days=1), cree_par=self.autre_user)
        envoi = EnvoiCollecteEleves.objects.create(lien=autre, identifiant=uuid.uuid4(), auteur='Autre')
        proposition = PropositionEleve.objects.create(envoi=envoi, prenom='Moussa', nom='Bah', sexe='M')
        self.assertEqual(self.accepter(proposition).status_code, 400)
        self.assertFalse(Eleve.objects.exists())

    def test_sans_permission_lecture_seule_et_sans_ecole_ne_gerent_pas(self):
        for nom, values in (
            ('enseignant', {'role': 'ENSEIGNANT', 'peut_importer_eleves': False}),
            ('lecteur', {'lecture_seule': True}), ('sans-ecole', {'ecole': None}),
        ):
            user = self.utilisateur(nom, values.pop('ecole', self.ecole), **values)
            self.client.force_login(user)
            self.assertEqual(self.client.get(self.gestion).status_code, 403)

    def test_quota_par_lien_est_persistant_et_double_envoi_reste_idempotent(self):
        data = self.donnees()
        self.public.post(self.url, data)
        EnvoiCollecteEleves.objects.bulk_create([
            EnvoiCollecteEleves(lien=self.lien, identifiant=uuid.uuid4(), auteur='Test') for _ in range(29)
        ])
        self.assertEqual(self.public.post(self.url, data).status_code, 302)
        response = self.public.post(self.url, self.donnees())
        self.assertEqual(response.status_code, 429)
        self.assertEqual(response.headers['Retry-After'], '3600')
        self.assertEqual(PropositionEleve.objects.count(), 1)

    def test_limite_globale_lien_ne_cree_pas_envoi_partiel(self):
        proposition = self.proposition()
        PropositionEleve.objects.bulk_create([
            PropositionEleve(envoi=proposition.envoi, prenom=f'E{i}', nom='Test', sexe='M')
            for i in range(999)
        ])
        self.assertEqual(self.public.post(self.url, self.donnees()).status_code, 429)
        self.assertEqual(EnvoiCollecteEleves.objects.count(), 1)
        self.assertEqual(PropositionEleve.objects.count(), 1000)

    def test_erreur_creation_annule_parent_et_conserve_proposition(self):
        proposition = self.proposition(prenom_responsable='Parent', nom_responsable='Test')
        with patch('eleves.services_collecte.Eleve.objects.create', side_effect=IntegrityError('collision')):
            with self.assertRaises(ValidationError):
                decider_proposition(proposition.pk, self.user, 'accepter')
        proposition.refresh_from_db()
        self.assertEqual(proposition.statut, 'EN_ATTENTE')
        self.assertFalse(Eleve.objects.exists())
        self.assertFalse(Responsable.objects.exists())

    def test_classe_modifiee_ne_permet_pas_creation_autre_ecole(self):
        proposition = self.proposition()
        Classe.objects.filter(pk=self.classe.pk).update(ecole=self.autre_ecole)
        self.accepter(proposition)
        self.assertFalse(Eleve.objects.exists())

    def test_vue_echappe_le_texte_enseignant(self):
        self.proposition(prenom='<script>alert(1)</script>')
        response = self.client.get(self.detail)
        self.assertContains(response, '&lt;script&gt;')
        self.assertNotContains(response, '<script>alert(1)</script>')

    def test_public_fonctionne_avec_session_non_validee_et_lecture_seule(self):
        user = self.utilisateur('visiteur-session', self.autre_ecole,
            is_validated=False, lecture_seule=True, telephone='+224622123456')
        self.public.force_login(user)
        self.assertEqual(self.public.get(self.url).status_code, 200)
        self.assertEqual(self.public.post(self.url, self.donnees()).status_code, 302)

    def test_public_ignore_session_enseignant_sans_elargir_acces_prive(self):
        from notes.middleware_acces_enseignants import AccesEnseignantMiddleware
        request = RequestFactory().get(self.url)
        request.user = self.user
        middleware = AccesEnseignantMiddleware(lambda r: HttpResponse('public'))
        with patch('notes.middleware_acces_enseignants.AccesEnseignantTemporaire.objects.filter') as filtres:
            self.assertEqual(middleware(request).content, b'public')
            filtres.assert_not_called()

    def test_middleware_session_n_impose_pas_verification_telephone_sur_lien(self):
        from ecole_moderne.security_middleware import SessionSecurityMiddleware
        request = RequestFactory().get(self.url)
        request.user = self.user
        request.session = {'last_activity': 0}
        self.assertIsNone(SessionSecurityMiddleware(lambda r: HttpResponse()).process_request(request))

    def test_formulaire_public_ne_depend_pas_licence_du_poste(self):
        from ecole_moderne.licence_middleware import LicenceMiddleware
        request = RequestFactory().get(self.url)
        middleware = LicenceMiddleware(lambda r: HttpResponse('public'))
        with patch('ecole_moderne.licence_middleware._check_license_cached', side_effect=AssertionError):
            self.assertEqual(middleware(request).content, b'public')

    def test_classe_changee_n_expose_pas_homonyme_autre_ecole(self):
        proposition = self.proposition()
        Classe.objects.filter(pk=self.classe.pk).update(ecole=self.autre_ecole)
        Eleve.objects.create(prenom=proposition.prenom, nom=proposition.nom,
            sexe='F', classe=self.classe)
        self.assertNotContains(self.client.get(self.detail), 'Homonyme à vérifier')
        response = self.client.get(reverse('eleves:verifier_proposition', args=[proposition.pk]))
        self.assertEqual(response.context['homonymes'], [])

    def test_echec_validation_conserve_choix_de_verrouillage(self):
        proposition = self.proposition()
        response = self.client.post(reverse('eleves:verifier_proposition', args=[proposition.pk]), {
            'action': 'accepter', 'prenom': '', 'nom': 'Camara', 'sexe': 'F',
            'confirmer_homonymes': 'on',
        })
        self.assertEqual(response.status_code, 400)
        self.assertFalse(response.context['verrouiller'])
        self.assertTrue(response.context['confirmer_homonymes'])
