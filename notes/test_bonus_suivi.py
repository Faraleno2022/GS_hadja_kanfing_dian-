"""Bonus détaillés : calculs, recalculs, plafonds et accès par école."""
from datetime import date
from decimal import Decimal

from django.core.cache import cache
from django.test import TestCase, override_settings
from django.urls import reverse

from eleves.models import Ecole
from utilisateurs.models import Profil
from paiements.tests import test_school_filtering as fixtures
from paiements.tests.support import MIDDLEWARE_SANS_LICENCE
from .models import ClasseNote, MatiereNote, NoteMensuelle, NoteSuivi, Devoir, RemiseDevoir
from .calculs_moyennes import (
    bonus_suivi_batch, details_bonus_suivi_batch, calculer_moyenne_matiere,
    calculer_moyennes_classe_optimise,
)


@override_settings(MIDDLEWARE=MIDDLEWARE_SANS_LICENCE)
class BonusSuiviTests(TestCase):
    def setUp(self):
        fixtures.SchoolFilteringTests.setUp(self)
        cache.clear()
        Ecole.objects.filter(pk=self.ecole1.pk).update(bonus_suivi_actif=True)
        self.client.force_login(self.user1)
        self.annee = self.classe1.annee_scolaire
        self.cn = ClasseNote.objects.create(ecole=self.ecole1, nom=self.classe1.nom,
            niveau='COLLEGE_8', annee_scolaire=self.annee)
        self.matiere = MatiereNote.objects.create(classe=self.cn, nom='Français', code='FR', coefficient=2)
        self.note = NoteMensuelle.objects.create(eleve=self.eleve1, matiere=self.matiere,
            mois='OCTOBRE', annee_scolaire=self.annee, note=12)
        self.cours = self.suivi(14)
        self.suivi(18, type_note='ORALE')
        self.devoir = Devoir.objects.create(classe=self.cn, matiere=self.matiere,
            titre='Lecture du chapitre 2', date_donne=date(2024, 10, 1),
            date_remise=date(2024, 10, 8), compte_bonus=True)
        RemiseDevoir.objects.create(devoir=self.devoir, eleve=self.eleve1, note=16, statut='RENDU')
        self.url = reverse('notes:saisie_suivi')
        self.filtres = {'classe_id': self.cn.pk, 'matiere_id': self.matiere.pk,
            'mois': 'OCTOBRE', 'type_note': 'COURS', 'numero': 1}

    def suivi(self, note, **kwargs):
        params = dict(eleve=self.eleve1, matiere=self.matiere, mois='OCTOBRE',
            annee_scolaire=self.annee, type_note='COURS', numero=1, note=note)
        params.update(kwargs)
        return NoteSuivi.objects.create(**params)

    def ligne(self, response=None):
        r = response or self.client.get(self.url, self.filtres)
        self.assertEqual(r.status_code, 200)
        return r.context['lignes'][0]

    def moyenne(self):
        return calculer_moyennes_classe_optimise(
            [self.eleve1], [self.matiere], 'OCTOBRE',
        )[self.eleve1.pk]['moyenne_generale']

    def test_detail_et_bulletin_partagent_le_calcul(self):
        r = self.client.get(self.url, self.filtres)
        l = self.ligne(r)
        self.assertEqual(l['nombre_notes'], 3)
        self.assertEqual(l['moyenne_suivi'], 16)
        self.assertEqual(l['bonus_calcule'], Decimal('1.6'))
        self.assertEqual(l['note_avant'], 12)
        self.assertAlmostEqual(l['note_apres'], 13.6)
        self.assertAlmostEqual(l['gain_reel'], 1.6)
        bulletin = calculer_moyenne_matiere(self.eleve1, self.matiere, 'OCTOBRE')
        self.assertEqual(l['note_apres'], bulletin['moyenne_matiere'])
        self.assertAlmostEqual(l['note_apres'], self.moyenne())
        self.note.refresh_from_db()
        self.assertEqual(self.note.note, 12)
        for label in ('Avant bonus', 'Après bonus', 'Gain réel', 'Détail (3)', 'Lecture du chapitre 2'):
            self.assertContains(r, label)

    def test_chaque_note_y_compris_zero_a_le_meme_poids(self):
        self.suivi(0, numero=2)
        l = self.ligne()
        self.assertEqual(l['nombre_notes'], 4)
        self.assertEqual(l['moyenne_suivi'], 12)
        self.assertEqual(l['bonus_calcule'], Decimal('1.2'))

    def test_tous_les_types_et_numeros_restent_inclus(self):
        r = self.client.get(self.url, {**self.filtres, 'type_note': 'PARTICIPATION', 'numero': 7})
        self.assertEqual(self.ligne(r)['note'], '')
        self.assertEqual(self.ligne(r)['nombre_notes'], 3)
        self.assertAlmostEqual(self.ligne(r)['bonus'], 1.6)

    def test_gain_reel_zero_plafond_et_absence(self):
        for note, absent, apres, gain in [(0, False, 1.6, 1.6),
                (19, False, 20, 1), (20, False, 20, 0),
                (12, True, None, 0), (None, False, None, 0)]:
            with self.subTest(note=note, absent=absent):
                NoteMensuelle.objects.filter(pk=self.note.pk).update(note=note, absent=absent)
                l = self.ligne()
                self.assertEqual(l['note_apres'], apres)
                self.assertAlmostEqual(l['gain_reel'], gain)
        self.note.delete()
        self.assertIsNone(self.ligne()['note_apres'])
        self.assertEqual(self.ligne()['gain_reel'], 0)

    def test_desactive_montre_potentiel_sans_gain(self):
        Ecole.objects.filter(pk=self.ecole1.pk).update(bonus_suivi_actif=False)
        l = self.ligne()
        self.assertEqual(l['bonus_calcule'], Decimal('1.6'))
        self.assertEqual(l['bonus'], 0)
        self.assertEqual(l['note_apres'], 12)
        self.assertEqual(l['gain_reel'], 0)

    def test_sans_suivi_et_zero_suivi_sont_distincts(self):
        NoteSuivi.objects.all().delete()
        RemiseDevoir.objects.all().delete()
        l = self.ligne()
        self.assertEqual(l['nombre_notes'], 0)
        self.assertIsNone(l['moyenne_suivi'])
        self.assertEqual(l['note_apres'], 12)
        self.suivi(0)
        l = self.ligne()
        self.assertEqual(l['nombre_notes'], 1)
        self.assertEqual(l['moyenne_suivi'], 0)
        self.assertEqual(l['bonus'], 0)

    def test_plafond_du_bonus(self):
        NoteSuivi.objects.all().update(note=20)
        RemiseDevoir.objects.all().update(note=20)
        self.assertEqual(self.ligne()['bonus'], 2)

    def test_notes_et_devoirs_hors_base_exclus(self):
        self.suivi(0, mois='NOVEMBRE')
        self.suivi(0, annee_scolaire='2023-2024')
        autre = MatiereNote.objects.create(classe=self.cn, nom='Anglais', code='ANG')
        self.suivi(0, matiere=autre)
        for actif, note, remise in [(False, 0, date(2024, 10, 9)),
                (True, None, date(2024, 10, 9)), (True, 0, date(2024, 11, 9))]:
            d = Devoir.objects.create(classe=self.cn, matiere=self.matiere,
                titre='Exclu', date_donne=date(2024, 10, 1), date_remise=remise, compte_bonus=actif)
            RemiseDevoir.objects.create(devoir=d, eleve=self.eleve1, note=note)
        self.assertEqual(self.ligne()['nombre_notes'], 3)

    def test_modification_suppression_recalcule_bulletin_cache(self):
        self.assertAlmostEqual(self.moyenne(), 13.6)
        r = self.client.post(self.url, {**self.filtres, f'note_{self.eleve1.pk}': '20'}, follow=True)
        self.assertAlmostEqual(self.ligne(r)['bonus'], 1.8)
        self.assertAlmostEqual(self.moyenne(), 13.8)
        r = self.client.post(self.url, {**self.filtres, f'note_{self.eleve1.pk}': ''}, follow=True)
        self.assertEqual(self.ligne(r)['nombre_notes'], 2)
        self.assertAlmostEqual(self.moyenne(), 13.7)

    def test_numero_et_decimales_conserves(self):
        self.suivi(10, numero=12)
        r = self.client.post(self.url, {**self.filtres, 'numero': 12, f'note_{self.eleve1.pk}': '15,25'}, follow=True)
        self.assertContains(r, 'name="numero" value="12"')
        self.assertContains(r, 'value="15.25"')
        self.assertEqual(NoteSuivi.objects.get(type_note='COURS', numero=1).note, 14)
        self.assertEqual(NoteSuivi.objects.get(type_note='COURS', numero=12).note, Decimal('15.25'))

    def test_champ_non_envoye_ne_supprime_pas_note(self):
        self.assertEqual(self.client.post(self.url, self.filtres).status_code, 302)
        self.cours.refresh_from_db()
        self.assertEqual(self.cours.note, 14)

    def test_entrees_invalides_refusees_sans_modifier_notes(self):
        for value in ('NaN', 'Infinity', '-1', '21', 'abc'):
            r = self.client.post(self.url, {**self.filtres, f'note_{self.eleve1.pk}': value})
            self.assertEqual(r.status_code, 400)
        for field in ('mois', 'type_note'):
            r = self.client.post(self.url, {**self.filtres, field: 'INVALIDE', f'note_{self.eleve1.pk}': '0'})
            self.assertEqual(r.status_code, 400)
        self.cours.refresh_from_db()
        self.assertEqual(self.cours.note, 14)

    def test_acces_autre_ecole_et_sans_ecole_refuses(self):
        for ecole in (self.ecole2, None):
            Profil.objects.filter(user=self.user1).update(ecole=ecole)
            self.assertEqual(len(self.client.get(self.url).context['classes']), 0)
            for method in ('get', 'post'):
                r = getattr(self.client, method)(self.url, {**self.filtres, f'note_{self.eleve1.pk}': '0'})
                self.assertEqual(r.status_code, 404)
        self.cours.refresh_from_db()
        self.assertEqual(self.cours.note, 14)

    def test_matiere_autre_classe_refusee(self):
        cn = ClasseNote.objects.create(ecole=self.ecole1, nom='C2', niveau='COLLEGE_8', annee_scolaire=self.annee)
        mat = MatiereNote.objects.create(classe=cn, nom='Français', code='FR')
        self.assertEqual(self.client.get(self.url, {**self.filtres, 'matiere_id': mat.pk}).status_code, 404)

    def test_activation_par_ecole_en_calcul_lot(self):
        cn = ClasseNote.objects.create(ecole=self.ecole2, nom='C2', niveau='COLLEGE_8', annee_scolaire=self.annee)
        mat = MatiereNote.objects.create(classe=cn, nom='Français', code='FR')
        self.suivi(20, eleve=self.eleve2, matiere=mat)
        result = bonus_suivi_batch([self.eleve1.pk, self.eleve2.pk],
            [self.matiere.pk, mat.pk], ['OCTOBRE'], self.annee)
        self.assertAlmostEqual(result[(self.eleve1.pk, self.matiere.pk, 'OCTOBRE')], 1.6)
        self.assertNotIn((self.eleve2.pk, mat.pk, 'OCTOBRE'), result)

    def test_detail_en_lot_nombre_requetes_constant(self):
        with self.assertNumQueries(3):
            result = details_bonus_suivi_batch([self.eleve1.pk], [self.matiere.pk], ['OCTOBRE'], self.annee)
        self.assertEqual(result[(self.eleve1.pk, self.matiere.pk, 'OCTOBRE')]['nombre_notes'], 3)

    def test_bascule_recalcule_et_redirection_externe_refusee(self):
        self.assertAlmostEqual(self.moyenne(), 13.6)
        r = self.client.post(reverse('notes:toggle_bonus_suivi'), {'next': '//site-invalide.invalid'})
        self.assertEqual(r.url, self.url)
        self.assertEqual(self.ligne()['gain_reel'], 0)
        self.assertEqual(self.moyenne(), 12)
        self.client.post(reverse('notes:toggle_bonus_suivi'), {'next': self.url})
        self.assertAlmostEqual(self.ligne()['gain_reel'], 1.6)

    def test_titre_devoir_echappe_et_resume_impact(self):
        self.devoir.titre = '<script>alert("test")</script>'
        self.devoir.save()
        self.note.note = 19
        self.note.save()
        r = self.client.get(self.url, self.filtres)
        self.assertNotContains(r, self.devoir.titre)
        self.assertContains(r, '&lt;script&gt;')
        self.assertEqual(r.context['beneficiaires'], 1)
        self.assertEqual(r.context['plafonnes'], 1)
        self.assertEqual(r.context['sans_note_mensuelle'], 0)

    def test_retrait_devoir_du_bonus_invalide_bulletin_cache(self):
        RemiseDevoir.objects.filter(devoir=self.devoir).update(note=20)
        self.assertAlmostEqual(self.moyenne(), 13.73)
        r = self.client.post(reverse('notes:suivi_devoir', args=[self.devoir.pk]), {
            f'note_{self.eleve1.pk}': '20', f'statut_{self.eleve1.pk}': 'RENDU',
        })
        self.assertEqual(r.status_code, 302)
        self.assertEqual(self.ligne()['nombre_notes'], 2)
        self.assertAlmostEqual(self.moyenne(), 13.6)

    def test_suppression_devoir_invalide_bulletin_cache(self):
        RemiseDevoir.objects.filter(devoir=self.devoir).update(note=20)
        self.assertAlmostEqual(self.moyenne(), 13.73)
        r = self.client.post(reverse('notes:supprimer_devoir', args=[self.devoir.pk]))
        self.assertEqual(r.status_code, 302)
        self.assertEqual(self.ligne()['nombre_notes'], 2)
        self.assertAlmostEqual(self.moyenne(), 13.6)
