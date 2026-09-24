from datetime import date
from decimal import Decimal

from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse

from eleves.models import Classe, Ecole

from .models import (
    AvanceSalaire,
    CategoriePaie,
    Enseignant,
    EtatSalaire,
    ParametrePaie,
    PeriodeSalaire,
    TypeEnseignant,
)
from .montant_lettres import montant_en_lettres
from .services import (
    acomptes_periode,
    calculer_etat_salaire,
    masse_salariale,
)


LICENCE_MIDDLEWARE = 'ecole_moderne.licence_middleware.LicenceMiddleware'
TEST_MIDDLEWARE = tuple(m for m in settings.MIDDLEWARE if m != LICENCE_MIDDLEWARE)


class MontantEnLettresTests(TestCase):
    def test_montants_du_classeur(self):
        self.assertEqual(
            montant_en_lettres(1600000), 'Un million six cent mille francs guinéens'
        )
        self.assertEqual(
            montant_en_lettres(20917500),
            'Vingt millions neuf cent dix-sept mille cinq cents francs guinéens',
        )
        self.assertEqual(montant_en_lettres(71), 'Soixante et onze francs guinéens')
        self.assertEqual(montant_en_lettres(80000), 'Quatre-vingt mille francs guinéens')


@override_settings(MIDDLEWARE=TEST_MIDDLEWARE)
class PrimesEtDocumentsPaieTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_superuser(
            username='paie-docs', email='paie-docs@example.com', password='x-test-123',
        )
        self.ecole = Ecole.objects.create(
            nom='Groupe Scolaire Test', adresse='Diécké',
            telephone='+224620000000', directeur='Direction',
        )
        self.classe = Classe.objects.create(
            ecole=self.ecole, nom='CE2', niveau='PRIMAIRE_3', annee_scolaire='2025-2026',
        )
        self.periode = PeriodeSalaire.objects.create(
            mois=5, annee=2026, ecole=self.ecole, cree_par=self.user,
        )
        ParametrePaie.objects.create(
            ecole=self.ecole,
            taux_anciennete_par_an=Decimal('10000'),
            taux_eloignement_par_km=Decimal('2000'),
            prime_craie_par_eleve=Decimal('500'),
            prime_par_heure_revision=Decimal('10000'),
            prime_professeur_principal=Decimal('50000'),
        )
        self.client.force_login(self.user)

    def creer_directeur(self):
        return Enseignant.objects.create(
            nom='BAMBA', prenoms='Hamed', matricule='0499120', ecole=self.ecole,
            type_enseignant=TypeEnseignant.ADMINISTRATEUR, fonction='DG',
            salaire_fixe=Decimal('600000'), date_embauche=date(2021, 1, 1),
            prime_fonction=Decimal('800000'), prime_performance=Decimal('50000'),
            prime_exceptionnelle=Decimal('80000'), distance_km=Decimal('15'),
            cree_par=self.user,
        )

    def test_primes_calculees_selon_le_bareme(self):
        directeur = self.creer_directeur()
        etat, _ = calculer_etat_salaire(directeur, self.periode, self.user)

        self.assertEqual(etat.prime_fonction, Decimal('800000.00'))
        self.assertEqual(etat.prime_anciennete, Decimal('50000.00'))  # 2026-2021 = 5 ans
        self.assertEqual(etat.prime_eloignement, Decimal('30000.00'))  # 15 km × 2000
        self.assertEqual(etat.prime_performance, Decimal('50000.00'))
        self.assertEqual(etat.prime_exceptionnelle, Decimal('80000.00'))
        self.assertEqual(etat.primes, Decimal('1010000.00'))
        self.assertEqual(etat.salaire_net, Decimal('1610000.00'))

    def test_prime_de_craie_du_primaire_suit_l_effectif(self):
        from eleves.models import Eleve, Responsable

        enseignant = Enseignant.objects.create(
            nom='GAMY', prenoms='Fréderic', ecole=self.ecole,
            type_enseignant=TypeEnseignant.PRIMAIRE, classe_principale=self.classe,
            salaire_fixe=Decimal('550000'), date_embauche=date(2026, 1, 1),
            cree_par=self.user,
        )
        responsable = Responsable.objects.create(
            prenom='Parent', nom='Test', relation='PERE',
            telephone='+224622100001', adresse='Diécké',
        )
        for index, statut in enumerate(('ACTIF', 'ACTIF', 'ACTIF', 'EXCLU')):
            Eleve.objects.create(
                matricule=f'CRAIE-{index}', prenom='Test', nom=f'Eleve{index}',
                sexe='M', classe=self.classe, statut=statut,
                responsable_principal=responsable,
            )

        etat, _ = calculer_etat_salaire(enseignant, self.periode, self.user)

        self.assertEqual(etat.effectif_classe, 3)
        self.assertEqual(etat.prime_craie, Decimal('1500.00'))

    def test_secondaire_revision_et_professeur_principal(self):
        prof = Enseignant.objects.create(
            nom='DIALLO', prenoms='Kadiatou', ecole=self.ecole,
            type_enseignant=TypeEnseignant.SECONDAIRE, taux_horaire=Decimal('13500'),
            mode_calcul_horaire='MENSUEL', heures_mensuelles=Decimal('40'),
            date_embauche=date(2026, 1, 1), professeur_principal=True,
            cree_par=self.user,
        )
        etat, _ = calculer_etat_salaire(prof, self.periode, self.user)
        etat.heures_revision = Decimal('3')
        etat.save()
        etat, _ = calculer_etat_salaire(prof, self.periode, self.user)

        self.assertEqual(etat.salaire_base, Decimal('540000.00'))
        self.assertEqual(etat.prime_fonction, Decimal('50000.00'))
        self.assertEqual(etat.prime_craie, Decimal('30000.00'))
        self.assertEqual(etat.salaire_net, Decimal('620000.00'))

    def test_primes_saisies_manuellement_survivent_au_recalcul(self):
        directeur = self.creer_directeur()
        etat, _ = calculer_etat_salaire(directeur, self.periode, self.user)

        response = self.client.post(
            reverse('salaires:ajuster_etat_salaire', args=[etat.id]),
            {
                'salaire_base': '600000', 'prime_fonction': '100000',
                'prime_exceptionnelle': '25000', 'deductions': '0',
                'observations': 'Prime ramenée',
            },
        )
        self.assertEqual(response.status_code, 302)
        etat, _ = calculer_etat_salaire(directeur, self.periode, self.user)

        self.assertTrue(etat.primes_ajustees)
        self.assertEqual(etat.primes, Decimal('125000.00'))
        self.assertEqual(etat.prime_anciennete, Decimal('0.00'))

    def test_masse_salariale_et_acomptes(self):
        directeur = self.creer_directeur()
        AvanceSalaire.objects.create(
            enseignant=directeur, periode_prevue=self.periode,
            date_avance=date(2026, 5, 5), montant=Decimal('100000'), motif='Bon 1', cree_par=self.user,
        )
        AvanceSalaire.objects.create(
            enseignant=directeur, periode_prevue=self.periode,
            date_avance=date(2026, 5, 15), montant=Decimal('50000'), motif='Bon 2', cree_par=self.user,
        )
        calculer_etat_salaire(directeur, self.periode, self.user)

        sections, totaux = masse_salariale(self.periode)
        self.assertEqual([s['categorie'] for s in sections], [CategoriePaie.DIRECTION])
        self.assertEqual(totaux['total_brut'], Decimal('1610000.00'))
        self.assertEqual(totaux['total_avances'], Decimal('150000.00'))
        self.assertEqual(totaux['total_net'], Decimal('1460000.00'))

        lignes, total = acomptes_periode(self.periode)
        self.assertEqual(total, Decimal('150000'))
        self.assertEqual(lignes[0]['bons'][:3], [Decimal('100000'), Decimal('50000'), None])

    def test_documents_pdf_et_pages(self):
        directeur = self.creer_directeur()
        etat, _ = calculer_etat_salaire(directeur, self.periode, self.user)

        for nom in (
            'etat_salaire_detaille_pdf', 'masse_salariale_pdf', 'acomptes_pdf',
            'emargement_pdf', 'bulletins_paie_pdf',
        ):
            response = self.client.get(reverse(f'salaires:{nom}', args=[self.periode.id]))
            self.assertEqual(response.status_code, 200, nom)
            self.assertTrue(response.content.startswith(b'%PDF'), nom)

        response = self.client.get(reverse('salaires:fiche_paie_pdf', args=[etat.id]))
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.content.startswith(b'%PDF'))

        response = self.client.get(
            reverse('salaires:documents_paie'), {'periode': self.periode.id}
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Masse salariale')
        self.assertContains(response, 'Un million six cent dix mille francs guinéens')

        response = self.client.get(reverse('salaires:parametres_paie'))
        # Le superadministrateur de test n'a pas d'école rattachée.
        self.assertIn(response.status_code, (200, 302))

    def test_ancien_total_de_primes_conserve(self):
        directeur = self.creer_directeur()
        etat = EtatSalaire.objects.create(
            enseignant=directeur, periode=self.periode,
            salaire_base=Decimal('600000'), primes=Decimal('70000'),
            salaire_net=Decimal('0'), calcule_par=self.user,
        )
        self.assertEqual(etat.prime_exceptionnelle, Decimal('70000'))
        self.assertEqual(etat.salaire_net, Decimal('670000.00'))
