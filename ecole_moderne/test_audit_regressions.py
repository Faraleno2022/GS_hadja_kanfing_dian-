"""Non-régression des anomalies confirmées par l'audit de septembre 2026."""
import json
from datetime import date
from decimal import Decimal
from unittest.mock import patch

from django.test import TestCase, override_settings
from django.urls import reverse
from django.core.cache import cache

from paiements.tests import test_school_filtering as fixtures
from paiements.tests.support import MIDDLEWARE_SANS_LICENCE
from eleves.models import Classe, Responsable
from paiements.models import Paiement, Relance
from notes.models import ClasseNote
from rapports.views import collecter_donnees_journalieres
from synchronisation.models import SyncDevice

@override_settings(MIDDLEWARE=MIDDLEWARE_SANS_LICENCE)
class AuditRegressions(TestCase):
    def setUp(self):
        fixtures.SchoolFilteringTests.setUp(self)
        self.user1.refresh_from_db()
        self.user2.refresh_from_db()
        cache.clear()
        self.client.force_login(self.user1)

    def admin(self):
        profil = self.user1.profil
        profil.role = 'ADMIN'
        profil.is_validated = True
        profil.save()
        self.user1.refresh_from_db()
        self.client.force_login(self.user1)

    def classe_note(self):
        return ClasseNote.objects.create(
            ecole=self.ecole1, nom=self.classe1.nom, niveau='PRIMAIRE_1',
            niveau_enseignement='PRIMAIRE', annee_scolaire='2024-2025',
        )

    def depense(self):
        from depenses.models import Depense, CategorieDepense, Fournisseur
        return Depense.objects.create(
            numero_facture='AUDIT-DEPENSE', libelle='Dépense école B',
            description='Fictive', type_depense='FONCTIONNEMENT',
            categorie=CategorieDepense.objects.create(nom='Audit', code='AUD'),
            fournisseur=Fournisseur.objects.create(nom='Fournisseur fictif', type_fournisseur='ENTREPRISE'),
            montant_ht=Decimal('10000'), taux_tva=Decimal('18'),
            date_facture=date(2024, 9, 10), date_echeance=date(2024, 9, 30),
            statut='VALIDEE', cree_par=self.user2,
        )

    def sync_headers(self):
        device = SyncDevice(ecole=self.ecole1, nom='Audit fictif')
        device.definir_token('audit-token-local')
        device.save()
        return {'HTTP_X_SYNC_DEVICE': str(device.device_id), 'HTTP_X_SYNC_TOKEN': 'audit-token-local'}

    def test_grille_tarifaire_accepte_annee_valide(self):
        from eleves.forms import GrilleTarifaireForm
        form = GrilleTarifaireForm(data={'annee_scolaire': '2026-2027'})
        form.is_valid()
        self.assertNotIn('annee_scolaire', form.errors)


    def test_saisie_notes_guineennes_accessible(self):
        self.admin()
        response = self.client.get(reverse('notes:saisie_notes_guineen'))
        self.assertEqual(response.status_code, 200)


    def test_bulletin_intelligent_html_accessible(self):
        self.admin()
        classe = self.classe_note()
        response = self.client.get(reverse('notes:bulletin_intelligent', args=[self.eleve1.pk, classe.pk, 'TRIMESTRE_1']))
        self.assertEqual(response.status_code, 200)


    def test_cantine_refuse_autre_ecole(self):
        from abonnements.models import AbonnementCantine, PresenceCantine
        self.admin()
        abonnement = AbonnementCantine.objects.create(
            eleve=self.eleve2, duree='MENSUEL', montant=50000,
            date_debut=date(2024, 9, 1), date_fin=date(2024, 9, 30), cree_par=self.user2,
        )
        from abonnements.views import _filter_qs_by_school
        from django.test import RequestFactory
        request = RequestFactory().get('/abonnements/cantine/')
        request.user = self.user1
        self.assertNotIn(abonnement, _filter_qs_by_school(AbonnementCantine.objects.all(), request))
        response = self.client.post(reverse('abonnements:enregistrer_presence'), {
            'abonnement_id': abonnement.pk, 'date': '2024-09-10', 'present': 'true',
        })
        self.assertEqual(response.status_code, 403)
        self.assertFalse(response.json()['success'])
        self.assertFalse(PresenceCantine.objects.filter(abonnement=abonnement, enregistre_par=self.user1).exists())


    def test_carte_scolaire_refuse_autre_ecole(self):
        self.admin()
        response = self.client.get(reverse('eleves:carte_scolaire_pdf', args=[self.eleve2.pk]))
        self.assertEqual(response.status_code, 302)
        self.assertNotEqual(response.get('Content-Type'), 'application/pdf')


    def test_chatbot_ecarte_documents_autre_ecole(self):
        from chatbot.models import Matiere, DocumentCours
        from chatbot.views import _filter_documents_by_school
        self.admin()
        matiere = Matiere.objects.create(nom='Audit calcul')
        document = DocumentCours.objects.create(
            matiere=matiere, titre='Audit geometrie confidentiel',
            contenu_extrait='La geometrie du document confidentiel de l école B.',
            uploaded_by=self.user2, fichier='audit-fictif.pdf',
        )
        self.assertFalse(_filter_documents_by_school(DocumentCours.objects.all(), self.ecole1).filter(pk=document.pk).exists())
        def reponse_locale(question, resultats):
            return {'reponse': ' '.join(r['passage'] for r in resultats),
                    'documents': [r['document'] for r in resultats],
                    'confiance': 'haute', 'suggestions': []}
        with patch('chatbot.views.generer_reponse', side_effect=reponse_locale):
            response = self.client.post(reverse('chatbot:api_envoyer'),
                                        json.dumps({'message': 'geometrie confidentiel'}),
                                        content_type='application/json')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['documents'], [])


    def test_sync_refuse_modification_autre_ecole(self):
        response = self.client.post('/api/v1/sync/push/', json.dumps({'changes': [{
            'model': 'eleves.Eleve', 'object_uuid': str(self.eleve2.sync_uuid),
            'operation': 'UPDATE', 'payload': {'nom': 'MODIFICATION AUDIT'},
        }]}), content_type='application/json', **self.sync_headers())
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['accepted_count'], 0)
        self.eleve2.refresh_from_db()
        self.assertNotEqual(self.eleve2.nom, 'MODIFICATION AUDIT')


    def test_snapshot_ecarte_parents_autre_ecole(self):
        response = self.client.get('/api/v1/sync/pull/?initial=1', **self.sync_headers())
        self.assertEqual(response.status_code, 200)
        parents = [r for r in response.json()['changes'] if r['model'] == 'eleves.Responsable']
        self.assertNotIn(str(self.resp2.sync_uuid), [r['object_uuid'] for r in parents])


    def test_rapport_journalier_respecte_date(self):
        donnees = collecter_donnees_journalieres(date(2024, 9, 12), user=self.user1)
        self.assertEqual(donnees['ecoles'][self.ecole1.pk]['paiements']['montant_total'], 0)
        Paiement.objects.create(eleve=self.eleve1, type_paiement=self.type_insc,
                                mode_paiement=self.mode_espece, montant=20000,
                                date_paiement=date(2024, 10, 1), statut='VALIDE')
        donnees = collecter_donnees_journalieres(date(2024, 9, 12), user=self.user1)
        self.assertEqual(donnees['ecoles'][self.ecole1.pk]['paiements']['montant_total'], 0)


    def test_rapport_journalier_exclut_paiement_en_attente(self):
        self.paiement1.statut = 'EN_ATTENTE'
        self.paiement1.save()
        donnees = collecter_donnees_journalieres(date(2024, 9, 10), user=self.user1)
        self.assertEqual(donnees['ecoles'][self.ecole1.pk]['paiements']['montant_total'], 0)


    def test_rapport_conserve_nature_inscription(self):
        donnees = collecter_donnees_journalieres(date(2024, 9, 10), user=self.user1)
        paiement = donnees['ecoles'][self.ecole1.pk]['paiements']
        self.assertEqual(paiement['frais_inscription'], 30000)
        self.assertEqual(paiement['scolarite'], 0)


    def test_rapport_ecarte_depenses_etrangeres(self):
        depense = self.depense()
        donnees = collecter_donnees_journalieres(date(2024, 9, 10), user=self.user1)
        self.assertEqual(donnees['depenses_globales']['montant_total'], 0)


    def test_depense_zero_recalcule_tva_et_ttc(self):
        depense = self.depense()
        from depenses.forms import DepenseForm
        form = DepenseForm(data={'montant_ht': '0', 'date_facture': '2024-09-10', 'description': 'Correction'}, instance=depense)
        self.assertFalse(form.is_valid())
        self.assertIn('montant_ht', form.errors)
        depense.montant_ht = 0
        depense.save(update_fields=['montant_ht'])
        depense.refresh_from_db()
        self.assertEqual(depense.montant_ht, 0)
        self.assertEqual(depense.montant_ttc, 0)
        self.assertEqual(depense.montant_tva, 0)


    def test_rappels_accessibles_au_comptable(self):
        profil = self.user1.profil
        profil.peut_consulter_rapports = True
        profil.peut_ajouter_paiements = True
        profil.peut_modifier_paiements = True
        profil.save()
        response = self.client.get(reverse('paiements:gerer_rappels'))
        self.assertEqual(response.status_code, 200)
        self.assertFalse(hasattr(profil, 'can_view_payments'))
        self.assertFalse(hasattr(profil, 'can_manage_payments'))


    def test_apercu_rappel_refuse_autre_ecole(self):
        self.admin()
        response = self.client.get(reverse('paiements:apercu_message_rappel', args=[self.eleve2.pk]))
        self.assertEqual(response.status_code, 404)


    def test_generation_rappels_limitee_ecole(self):
        self.admin()
        response = self.client.post(reverse('paiements:creer_rappels_automatiques'), {'canal': 'SMS', 'limite': '100'})
        self.assertEqual(response.status_code, 302)
        self.assertFalse(Relance.objects.filter(eleve=self.eleve2, cree_par=self.user1).exists())


    def test_sync_recalcule_echeancier(self):
        response = self.client.post('/api/v1/sync/push/', json.dumps({'changes': [{
            'model': 'paiements.Paiement', 'object_uuid': str(self.paiement1.sync_uuid),
            'operation': 'UPDATE', 'payload': {'montant': '10000'},
        }]}), content_type='application/json', **self.sync_headers())
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['accepted_count'], 1)
        self.paiement1.refresh_from_db()
        self.echeancier1.refresh_from_db()
        self.assertEqual(self.paiement1.montant, 10000)
        self.assertEqual(self.echeancier1.frais_inscription_paye, 10000)


    def test_sync_refuse_json_malforme(self):
        headers = self.sync_headers()
        for payload in ('[]', '42', '"texte"', 'null', '{'):
            with self.subTest(payload=payload):
                response = self.client.post('/api/v1/sync/push/', payload, content_type='application/json', **headers)
                self.assertEqual(response.status_code, 400)
        response = self.client.post('/api/v1/sync/push/', json.dumps({'changes':[{'operation':42,'model':[]}]}), content_type='application/json', **headers)
        self.assertEqual(response.json()['rejected_count'], 1)


    def test_pages_restaurees_accessibles(self):
        self.admin()
        for route in ('abonnements:tableau_bord', 'abonnements:liste_cantine',
                      'abonnements:creer_cantine', 'abonnements:presences_cantine',
                      'paiements:eleves_en_retard', 'paiements:statistiques_rappels'):
            with self.subTest(route=route):
                self.assertEqual(self.client.get(reverse(route)).status_code, 200)
        self.user1.is_superuser = True
        self.user1.save()
        self.user2.profil.is_validated = False
        self.user2.profil.save()
        self.assertEqual(self.client.get(reverse('utilisateurs:rejeter_compte', args=[self.user2.pk])).status_code, 200)


    def test_rangs_limitent_classe_a_ecole(self):
        from notes.utils_rangs import calculer_rangs_classe_periode
        from eleves.models import Eleve
        classe_b = Classe.objects.create(id=56, ecole=self.ecole2, nom='Classe externe',
                                         niveau='PRIMAIRE_1', annee_scolaire='2024-2025')
        externe = Eleve.objects.create(classe=classe_b, nom='EXTERNE', prenom='Audit', matricule='AUD-56')
        classe_note = ClasseNote.objects.create(
            id=61, ecole=self.ecole1, nom='Classe propre', niveau='PRIMAIRE_1',
            niveau_enseignement='PRIMAIRE', annee_scolaire='2024-2025',
        )
        rangs = calculer_rangs_classe_periode(classe_note, 'OCTOBRE', use_cache=False)
        self.assertNotIn(externe.pk, rangs)


    def test_snapshot_pagine_plus_de_5000(self):
        from synchronisation.engine import snapshot_page_for_ecole
        from synchronisation.models import SyncOwnership
        parents = Responsable.objects.bulk_create([
            Responsable(nom=f'Parent {n}', prenom='Audit', telephone='000000000', relation='PERE')
            for n in range(5001)
        ])
        SyncOwnership.objects.bulk_create([
            SyncOwnership(ecole=self.ecole1, model_label='eleves.Responsable', object_uuid=p.sync_uuid)
            for p in parents
        ])
        cursor = None
        uuids = []
        while True:
            page, cursor, watermark = snapshot_page_for_ecole(self.ecole1, cursor)
            self.assertLessEqual(len(page), 500)
            uuids.extend(row['object_uuid'] for row in page if row['model']=='eleves.Responsable')
            if not cursor:
                break
        self.assertEqual(len(uuids), 5002)
        self.assertEqual(len(uuids), len(set(uuids)))
        self.assertNotIn(str(self.resp2.sync_uuid), uuids)


    def test_sync_refuse_suppression_autre_ecole(self):
        from eleves.models import Eleve
        response = self.client.post('/api/v1/sync/push/', json.dumps({'changes': [{
            'model': 'eleves.Eleve', 'object_uuid': str(self.eleve2.sync_uuid),
            'operation': 'DELETE', 'payload': {},
        }]}), content_type='application/json', **self.sync_headers())
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['accepted_count'], 0)
        self.assertTrue(Eleve.objects.filter(pk=self.eleve2.pk).exists())


    def test_admin_ecole_ne_supprime_pas_autre_compte(self):
        from django.contrib.auth.models import User
        self.admin()
        self.user2.profil.is_validated = True
        self.user2.profil.save()
        with patch('django.core.mail.send_mail'):
            response = self.client.post(reverse('utilisateurs:rejeter_compte', args=[self.user2.pk]),
                                        {'raison': 'Audit fictif'})
        self.assertEqual(response.status_code, 403)
        self.assertTrue(User.objects.filter(pk=self.user2.pk).exists())


    def test_configuration_production_importable(self):
        import importlib
        with patch.dict('os.environ', {'PROJECT_BASE_DIR': str(__import__('pathlib').Path('tmp/audit-project').resolve())}):
            configuration = importlib.import_module('ecole_moderne.settings_production')
        self.assertFalse(configuration.DEBUG)
        self.assertTrue(configuration.CSRF_COOKIE_SECURE)


    def test_couleurs_cartes_enregistrees(self):
        self.user1.is_superuser = True
        self.user1.save()
        url = reverse('eleves:configurer_ecole', args=[self.ecole1.pk])
        couleurs = {'couleur_carte_scolaire': '#102030', 'couleur_carte_retrait': '#204060',
                    'couleur_carte_bus': '#306090', 'couleur_carte_cantine': '#4080A0'}
        response = self.client.post(url, {'action':'update_card_colors', **couleurs})
        self.assertEqual(response.status_code, 302)
        self.ecole1.refresh_from_db()
        for field, value in couleurs.items():
            self.assertEqual(getattr(self.ecole1, field), value)


    def test_sync_refuse_relations_etrangeres_et_uuid_inconnu(self):
        from uuid import uuid4
        headers = self.sync_headers()
        changes = [
            {'model': 'eleves.Eleve', 'object_uuid': str(self.eleve1.sync_uuid), 'operation': 'UPDATE',
             'payload': {'classe': {'sync_uuid': str(self.classe2.sync_uuid), 'pk': self.classe1.pk}}},
            {'model': 'eleves.Eleve', 'object_uuid': str(self.eleve1.sync_uuid), 'operation': 'UPDATE',
             'payload': {'responsable_principal': {'sync_uuid': str(self.resp2.sync_uuid)}}},
            {'model': 'eleves.Eleve', 'object_uuid': str(self.eleve1.sync_uuid), 'operation': 'UPDATE',
             'payload': {'classe': {'sync_uuid': str(uuid4()), 'pk': self.classe1.pk}}},
            {'model': 'eleves.Ecole', 'object_uuid': str(uuid4()), 'operation': 'CREATE',
             'payload': {'nom': 'Autre école'}},
            {'model': 'paiements.TypePaiement', 'object_uuid': str(self.type_insc.sync_uuid), 'operation': 'UPDATE',
             'payload': {'nom': 'Type partagé modifié'}},
        ]
        response = self.client.post('/api/v1/sync/push/', json.dumps({'changes': changes}), content_type='application/json', **headers)
        self.assertEqual(response.json()['accepted_count'], 0, response.json())
        self.assertEqual(response.json()['rejected_count'], len(changes))
        self.eleve1.refresh_from_db()
        self.assertEqual(self.eleve1.classe_id, self.classe1.pk)
        self.assertEqual(self.eleve1.responsable_principal_id, self.resp1.pk)

    def test_sync_creation_parent_puis_eleve_et_suppression_paiement(self):
        from uuid import uuid4
        from eleves.models import Eleve
        parent_uuid, eleve_uuid = uuid4(), uuid4()
        headers = self.sync_headers()
        changes = [
            {'model': 'eleves.Responsable', 'object_uuid': str(parent_uuid), 'operation': 'CREATE',
             'payload': {'nom': 'Nouveau parent', 'prenom': 'Test', 'telephone': '000000000', 'relation': 'PERE'}},
            {'model': 'eleves.Eleve', 'object_uuid': str(eleve_uuid), 'operation': 'CREATE',
             'payload': {'nom': 'Nouveau', 'prenom': 'Élève', 'matricule': 'SYNC-NEW',
                         'classe': {'sync_uuid': str(self.classe1.sync_uuid)},
                         'responsable_principal': {'sync_uuid': str(parent_uuid)}}},
            {'model': 'paiements.Paiement', 'object_uuid': str(self.paiement1.sync_uuid), 'operation': 'DELETE', 'payload': {}},
        ]
        response = self.client.post('/api/v1/sync/push/', json.dumps({'changes': changes}), content_type='application/json', **headers)
        self.assertEqual(response.json()['accepted_count'], 3, response.json())
        self.assertEqual(Eleve.objects.get(sync_uuid=eleve_uuid).responsable_principal.sync_uuid, parent_uuid)
        self.echeancier1.refresh_from_db()
        self.assertEqual(self.echeancier1.frais_inscription_paye, 0)

    def test_sync_paiement_deplace_recalcule_anciens_et_nouveaux_soldes(self):
        from eleves.models import Eleve
        from paiements.models import EcheancierPaiement
        cible = Eleve.objects.create(classe=self.classe1, nom='Cible', prenom='Test', matricule='CIBLE-SYNC')
        echeancier = EcheancierPaiement.objects.create(
            eleve=cible, annee_scolaire='2024-2025', frais_inscription_du=30000,
            date_echeance_inscription=date(2024,9,1), date_echeance_tranche_1=date(2024,10,1),
            date_echeance_tranche_2=date(2025,1,1), date_echeance_tranche_3=date(2025,4,1),
        )
        response = self.client.post('/api/v1/sync/push/', json.dumps({'changes':[{
            'model':'paiements.Paiement', 'object_uuid':str(self.paiement1.sync_uuid), 'operation':'UPDATE',
            'payload':{'eleve':{'sync_uuid':str(cible.sync_uuid)}},
        }]}), content_type='application/json', **self.sync_headers())
        self.assertEqual(response.json()['accepted_count'], 1, response.json())
        self.echeancier1.refresh_from_db(); echeancier.refresh_from_db()
        self.assertEqual(self.echeancier1.frais_inscription_paye, 0)
        self.assertEqual(echeancier.frais_inscription_paye, 30000)

    def test_sync_snapshot_ecarte_depenses_et_rapports_etrangers(self):
        from synchronisation.engine import snapshot_changes_for_ecole
        from rapports.models import TypeRapport, Rapport
        depense = self.depense()
        type_rapport = TypeRapport.objects.create(nom='Audit', categorie='FINANCIER', cree_par=self.user2)
        rapport = Rapport.objects.create(type_rapport=type_rapport, titre='Privé B',
                                        periode_debut=date(2024,9,1), periode_fin=date(2024,9,30), genere_par=self.user2)
        rows = snapshot_changes_for_ecole(self.ecole1)
        uuids = {r['object_uuid'] for r in rows}
        self.assertNotIn(str(depense.sync_uuid), uuids)
        self.assertNotIn(str(rapport.sync_uuid), uuids)

    def test_snapshot_curseur_lie_a_ecole_et_modifications_web_visibles(self):
        from synchronisation.engine import snapshot_page_for_ecole
        from synchronisation.models import SyncChange
        _, cursor, _ = snapshot_page_for_ecole(self.ecole2, page_size=1)
        response = self.client.get('/api/v1/sync/pull/', {'initial':'1', 'snapshot_version':'2', 'snapshot_cursor':cursor}, **self.sync_headers())
        self.assertEqual(response.status_code, 400)
        since = SyncChange.objects.order_by('-pk').first().pk
        self.eleve1.nom = 'Modification web'
        self.eleve1.save()
        response = self.client.get('/api/v1/sync/pull/', {'since_id':since}, **self.sync_headers())
        self.assertTrue(any(row['object_uuid']==str(self.eleve1.sync_uuid) and row['payload'].get('nom', '').casefold()=='modification web' for row in response.json()['changes']))

    def test_client_reprend_snapshot_sur_plusieurs_cycles(self):
        from uuid import uuid4
        from synchronisation.client import pull_changes
        from synchronisation.models import SyncCheckpoint
        device_id = str(uuid4())
        pages = [
            {'ok':True,'changes':[],'next_snapshot_cursor':'page-2','latest_change_id':10},
            {'ok':True,'changes':[],'next_snapshot_cursor':None,'latest_change_id':10},
            {'ok':True,'changes':[],'latest_change_id':12,'has_more':False},
        ]
        with patch('synchronisation.client._get_json', side_effect=pages) as transport, patch('synchronisation.client.MAX_CYCLES_PAR_APPEL',1):
            pull_changes('https://sync.invalid',device_id,'test',self.ecole1)
            checkpoint=SyncCheckpoint.objects.get(device_id=device_id)
            self.assertFalse(checkpoint.initial_complete)
            self.assertEqual(checkpoint.snapshot_cursor,'page-2')
            pull_changes('https://sync.invalid',device_id,'test',self.ecole1)
            self.assertEqual(transport.call_args.kwargs['params']['snapshot_cursor'],'page-2')
            checkpoint.refresh_from_db()
            self.assertTrue(checkpoint.initial_complete)
            pull_changes('https://sync.invalid',device_id,'test',self.ecole1)
            self.assertEqual(transport.call_args.kwargs['params']['since_id'],10)
        checkpoint.refresh_from_db()
        self.assertEqual(checkpoint.last_change_id,12)

    def test_client_lot_echoue_sans_avancer_curseur(self):
        from uuid import uuid4
        from synchronisation.client import pull_changes, SyncTransportError
        from synchronisation.models import SyncCheckpoint, SyncChange
        device_id=str(uuid4())
        checkpoint=SyncCheckpoint.objects.create(device_id=device_id,initial_complete=True,last_change_id=3)
        response={'ok':True,'changes':[{'id':4,'model_label':'eleves.Eleve','object_uuid':str(self.eleve1.sync_uuid),'operation':'UPDATE','payload':{'nom':'Sans effet'}}],'latest_change_id':4}
        with patch('synchronisation.client._get_json',return_value=response):
            with self.assertRaises(SyncTransportError):
                pull_changes('https://sync.invalid',device_id,'test',self.ecole1,apply_change=lambda change: (_ for _ in ()).throw(ValueError('Essai')))
        checkpoint.refresh_from_db()
        self.assertEqual(checkpoint.last_change_id,3)
        self.assertFalse(SyncChange.objects.filter(payload__server_change_id=4).exists())
        self.eleve1.refresh_from_db()
        self.assertNotEqual(self.eleve1.nom,'Sans effet')

    def test_rapport_periode_ne_reprend_pas_autres_dates_ni_ecoles(self):
        from rapports.utils import collecter_donnees_periode
        self.depense()
        donnees=collecter_donnees_periode(date(2024,10,15),date(2024,10,16),'PERSONNALISE',user=self.user1)
        self.assertEqual(donnees['depenses_globales']['montant_total'],0)
        self.assertEqual(donnees['ecoles'][self.ecole1.pk]['paiements']['montant_total'],0)

    def test_rapport_ventile_tarif_variable_et_deux_versements(self):
        from rapports.utils import ventiler_encaissements
        self.echeancier1.frais_inscription_du=50000
        self.echeancier1.save()
        second=Paiement.objects.create(eleve=self.eleve1,type_paiement=self.type_insc,mode_paiement=self.mode_espece,
                                       montant=70000,statut='VALIDE',date_paiement=date(2024,9,12))
        result=ventiler_encaissements(Paiement.objects.filter(pk__in=[self.paiement1.pk,second.pk]))
        self.assertEqual(result['frais_inscription'],50000)
        self.assertEqual(result['scolarite'],50000)

    def test_rappels_modification_etrangere_refusee(self):
        self.admin()
        relance=Relance.objects.create(eleve=self.eleve2,canal='SMS',message='Privé',solde_estime=100000,cree_par=self.user2)
        for route in ('paiements:marquer_rappel_envoye','paiements:supprimer_rappel'):
            response=self.client.post(reverse(route,args=[relance.pk]), '{}',content_type='application/json')
            self.assertEqual(response.status_code,404)
        relance.refresh_from_db()
        self.assertEqual(relance.statut,'ENREGISTREE')

    def test_superadmin_ne_rejette_pas_compte_valide(self):
        self.user1.is_superuser=True; self.user1.save()
        self.user2.profil.is_validated=True; self.user2.profil.save()
        response=self.client.post(reverse('utilisateurs:rejeter_compte',args=[self.user2.pk]),{'raison':'Essai'})
        self.assertEqual(response.status_code,404)

    def test_cantine_presence_autorisee_dans_ecole(self):
        from abonnements.models import AbonnementCantine, PresenceCantine
        self.admin()
        abonnement=AbonnementCantine.objects.create(eleve=self.eleve1,duree='MENSUEL',montant=50000,
                                                    date_debut=date(2024,9,1),date_fin=date(2024,9,30),cree_par=self.user1)
        response=self.client.post(reverse('abonnements:enregistrer_presence'),{
            'abonnement_id':abonnement.pk,'date':'2024-09-10','present':'true'})
        self.assertTrue(response.json()['success'])
        self.assertTrue(PresenceCantine.objects.get(abonnement=abonnement).present)

    def test_bulletins_exports_et_ecole_de_classe(self):
        self.admin()
        classe=self.classe_note()
        for route, content in (('notes:bulletin_intelligent_pdf','application/pdf'),
                               ('notes:bulletin_intelligent_excel','application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')):
            response=self.client.get(reverse(route,args=[self.eleve1.pk,classe.pk,'TRIMESTRE_1']))
            self.assertEqual(response.status_code,200)
            self.assertEqual(response['Content-Type'],content)
        classe.ecole=self.ecole2; classe.save()
        response=self.client.get(reverse('notes:bulletin_intelligent',args=[self.eleve1.pk,classe.pk,'TRIMESTRE_1']))
        self.assertEqual(response.status_code,404)
