from datetime import date
from decimal import Decimal
import pandas as pd
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase, override_settings
from django.urls import reverse
from eleves.models import Ecole, Classe, Eleve
from eleves.import_eleves import ImportElevesProcessor
from paiements.models import Paiement, TypePaiement, ModePaiement
from paiements.tests.support import MIDDLEWARE_SANS_LICENCE


@override_settings(MIDDLEWARE=MIDDLEWARE_SANS_LICENCE)
class ImportVerrouilleTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_superuser('import-admin', 'admin@example.com', 'test')
        self.client.force_login(self.user)
        self.ecole = Ecole.objects.create(nom='Ecole import', adresse='Conakry', telephone='620111111', directeur='Direction')
        self.a = Classe.objects.create(ecole=self.ecole, nom='Petite section A', niveau='PETITE_SECTION', annee_scolaire='2026-2027')
        self.b = Classe.objects.create(ecole=self.ecole, nom='Petite section B', niveau=self.a.niveau, annee_scolaire=self.a.annee_scolaire)
        self.autre = Classe.objects.create(ecole=self.ecole, nom='Autre niveau', niveau='COLLEGE_7', annee_scolaire=self.a.annee_scolaire)
        self.eleve = Eleve.objects.create(matricule='IMPORT-001', nom='Diallo', prenom='Aminata', sexe='F', date_naissance=date(2022, 1, 1), classe=self.a, import_verrouille=True)
        self.url = reverse('eleves:repartir_importes')

    def paiement(self, statut='EN_ATTENTE', montant='10000', annee='2026-2027'):
        return Paiement.objects.create(eleve=self.eleve, type_paiement=TypePaiement.objects.create(nom='Inscription'), mode_paiement=ModePaiement.objects.create(nom='Especes'), montant=montant, statut=statut, annee_scolaire=annee, numero_recu='TEST-001', date_paiement=date(2026, 9, 6), cree_par=self.user)

    def test_import_verrouille_et_import_historique(self):
        for verrouiller in (True, False):
            stats = ImportElevesProcessor(pd.DataFrame([{'Matricule': 'LOT-' + str(verrouiller), 'Nom': 'Camara', 'Prénom': 'Moussa' + str(verrouiller), 'Sexe': 'M'}]), self.a.pk, verrouiller=verrouiller).importer()
            self.assertEqual(stats['crees'], 1)
            eleve = Eleve.objects.get(matricule='LOT-' + str(verrouiller))
            self.assertEqual(eleve.import_verrouille, verrouiller)
            self.assertEqual(eleve.statut, 'ATTENTE_PAIEMENT' if verrouiller else 'ACTIF')

    def test_verrou_pedagogique_et_modification_statut(self):
        self.assertFalse(Eleve.pedagogiques.filter(pk=self.eleve.pk).exists())
        self.eleve.statut = 'ACTIF'
        self.eleve.save(update_fields=['statut'])
        self.eleve.refresh_from_db()
        self.assertEqual(self.eleve.statut, 'ATTENTE_PAIEMENT')

    def test_premier_paiement_valide_deverrouille(self):
        paiement = self.paiement()
        self.eleve.refresh_from_db()
        self.assertTrue(self.eleve.import_verrouille)
        paiement.statut = 'REJETE'
        paiement.save()
        self.eleve.refresh_from_db()
        self.assertTrue(self.eleve.import_verrouille)
        paiement.statut = 'VALIDE'
        paiement.save()
        self.eleve.refresh_from_db()
        self.assertFalse(self.eleve.import_verrouille)
        self.assertEqual(self.eleve.statut, 'ACTIF')
        self.assertTrue(Eleve.pedagogiques.filter(pk=self.eleve.pk).exists())

    def test_paiement_autre_annee_ne_deverrouille_pas(self):
        self.paiement(statut='VALIDE', annee='2025-2026')
        self.eleve.refresh_from_db()
        self.assertTrue(self.eleve.import_verrouille)

    def test_paiement_nul_ne_deverrouille_pas(self):
        with self.assertRaises(ValidationError):
            self.paiement(statut='VALIDE', montant='0')
        self.eleve.refresh_from_db()
        self.assertTrue(self.eleve.import_verrouille)

    def test_grille_classes_compatibles(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        eleve = list(response.context['page_obj'])[0]
        self.assertEqual({c.pk for c in eleve.classes_proposees}, {self.a.pk, self.b.pk})

    def test_affectation_et_premier_paiement(self):
        matricule = self.eleve.matricule
        response = self.client.post(self.url, {'eleve_id': self.eleve.pk, 'classe_id': self.b.pk, 'action': 'payer'})
        self.assertRedirects(response, reverse('paiements:ajouter_paiement_eleve', args=[self.eleve.pk]), fetch_redirect_response=False)
        self.eleve.refresh_from_db()
        self.assertEqual(self.eleve.classe_id, self.b.pk)
        self.assertEqual(self.eleve.matricule, matricule)
        self.assertTrue(self.eleve.import_verrouille)

    def test_refuse_classe_incompatible_et_identifiant_invalide(self):
        for classe in (self.autre.pk, 'invalide'):
            self.assertEqual(self.client.post(self.url, {'eleve_id': self.eleve.pk, 'classe_id': classe}).status_code, 404)
        self.eleve.refresh_from_db()
        self.assertEqual(self.eleve.classe_id, self.a.pk)

    def test_refuse_affectation_si_paiement_en_attente(self):
        self.paiement()
        self.client.post(self.url, {'eleve_id': self.eleve.pk, 'classe_id': self.b.pk})
        self.eleve.refresh_from_db()
        self.assertEqual(self.eleve.classe_id, self.a.pk)

    def test_refuse_utilisateur_sans_permission(self):
        user = get_user_model().objects.create_user('sans-permission')
        user.profil.role = 'ENSEIGNANT'
        user.profil.is_validated = True
        user.profil.save(update_fields=['role', 'is_validated'])
        self.client.force_login(user)
        self.assertEqual(self.client.get(self.url).status_code, 403)

    def test_presence_ignore_verrouille_puis_accepte_apres_validation(self):
        from presence.models import PresenceJournaliere
        url = reverse('presence:pointage')
        data = {'classe_id': self.a.pk, 'date': '2026-09-06', f'statut_{self.eleve.pk}': 'ABSENT'}
        self.client.post(url, data)
        self.assertFalse(PresenceJournaliere.objects.filter(eleve=self.eleve).exists())
        self.paiement(statut='VALIDE')
        self.client.post(url, data)
        self.assertTrue(PresenceJournaliere.objects.filter(eleve=self.eleve).exists())

    def test_bulletin_direct_refuse_eleve_verrouille(self):
        from notes.models import ClasseNote
        classe_note = ClasseNote.objects.create(ecole=self.ecole, nom=self.a.nom, niveau='MATERNELLE', annee_scolaire=self.a.annee_scolaire)
        url = reverse('notes:saisie_bulletin_maternelle', args=[self.eleve.pk, classe_note.pk, 'TRIMESTRE_1'])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)

    def test_formulaire_paiement_propose_eleve_verrouille(self):
        from paiements.forms import PaiementForm
        form = PaiementForm()
        self.assertTrue(form.fields['eleve'].queryset.filter(pk=self.eleve.pk).exists())

    def test_import_web_redirige_vers_repartition(self):
        from django.core.files.uploadedfile import SimpleUploadedFile
        fichier = SimpleUploadedFile('eleves.csv', 'Matricule,Prénom,Nom,Sexe\nWEB-001,Awa,Diallo,F\n'.encode('utf-8'), content_type='text/csv')
        response = self.client.post(reverse('eleves:importer_eleves'), {'classe_id': self.a.pk, 'verrouiller': 'on', 'generer_matricules': 'on', 'fichier': fichier})
        self.assertRedirects(response, self.url, fetch_redirect_response=False)
        self.assertTrue(Eleve.objects.get(matricule='WEB-001').import_verrouille)

    def test_erreur_allocation_annule_deverrouillage(self):
        from unittest.mock import patch
        from paiements.views import _valider_paiement_impl
        paiement = self.paiement()
        with patch('paiements.views.ensure_echeancier_for_eleve'), patch('paiements.views._assert_payment_fits_annual_balance'), patch('paiements.views._allocate_payment_to_echeancier', side_effect=ValueError('Allocation impossible')):
            with self.assertRaises(ValueError):
                _valider_paiement_impl(paiement, self.user)
        self.eleve.refresh_from_db()
        paiement.refresh_from_db()
        self.assertTrue(self.eleve.import_verrouille)
        self.assertEqual(paiement.statut, 'EN_ATTENTE')

    def test_ecole_et_annee_incompatibles_refusees(self):
        ecole = Ecole.objects.create(nom='Autre ecole', adresse='Conakry', telephone='620111112', directeur='Direction')
        for nom, school, annee in [('Autre ecole', ecole, self.a.annee_scolaire), ('Annee precedente', self.ecole, '2025-2026')]:
            classe = Classe.objects.create(ecole=school, nom=nom, niveau=self.a.niveau, annee_scolaire=annee)
            response = self.client.post(self.url, {'eleve_id': self.eleve.pk, 'classe_id': classe.pk})
            self.assertEqual(response.status_code, 404)

    def test_compte_autre_ecole_ne_voit_pas_eleve(self):
        ecole = Ecole.objects.create(nom='Autre ecole', adresse='Conakry', telephone='620111112', directeur='Direction')
        user = get_user_model().objects.create_user('comptable-autre')
        user.profil.ecole = ecole
        user.profil.is_validated = True
        user.profil.save(update_fields=['ecole', 'is_validated'])
        self.client.force_login(user)
        self.assertEqual(self.client.get(self.url).context['page_obj'].paginator.count, 0)
        self.assertEqual(self.client.post(self.url, {'eleve_id': self.eleve.pk, 'classe_id': self.b.pk}).status_code, 404)

    def test_fiche_et_paiement_restent_accessibles(self):
        self.assertEqual(self.client.get(reverse('eleves:detail_eleve', args=[self.eleve.pk])).status_code, 200)
        self.assertEqual(self.client.get(reverse('paiements:ajouter_paiement_eleve', args=[self.eleve.pk])).status_code, 200)
