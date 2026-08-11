"""Tests de la corbeille, du journal des modifications et de l'export élèves.

Couvre les cas signalés en production :

* suppression d'une école depuis l'administration Django (erreur de contrainte) ;
* suppression d'un élève (admin et interface) → corbeille puis restauration ;
* suppression d'un paiement / échéancier depuis l'admin → corbeille ;
* modification d'un paiement journalisée avant / après ;
* export global des élèves au format du modèle d'importation ;
* planches de cartes imprimées à 8 cartes par feuille A4.
"""

from datetime import date
from decimal import Decimal

from django.conf import settings
from django.contrib.admin.sites import AdminSite
from django.contrib.auth.models import User
from django.test import RequestFactory, TestCase, override_settings

# La vérification de licence renvoie 403 hors installation activée : elle n'a
# pas sa place dans les tests fonctionnels.
MIDDLEWARE_SANS_LICENCE = [
    m for m in settings.MIDDLEWARE
    if 'licence_middleware' not in m
]

from bus.models import AbonnementBus, AbonnementCantine
from eleves.models import Classe, Ecole, Eleve, Responsable
from paiements.models import (
    EcheancierPaiement, ModePaiement, Paiement, TypePaiement,
)

from .models import CorbeilleElement, CorbeilleEleve, JournalModification


class _RequeteAdmin:
    """Petite fabrique de requêtes authentifiées pour les ModelAdmin."""

    def __init__(self, user):
        self.factory = RequestFactory()
        self.user = user

    def post(self, chemin='/admin/'):
        requete = self.factory.post(chemin)
        requete.user = self.user
        requete.session = {}
        requete._messages = _MessagesMuets()
        return requete


class _MessagesMuets:
    """Stockage de messages minimal (le middleware n'est pas monté ici)."""

    def __init__(self):
        self.messages = []

    def add(self, level, message, extra_tags=''):
        self.messages.append((level, str(message)))


def _creer_jeu_de_donnees(suffixe='1', rang=1):
    """Crée école + classe + élève + responsables cohérents pour un test.

    ``rang`` sert à fabriquer des numéros de téléphone guinéens distincts
    (le format ``+224XXXXXXXX`` est validé par le modèle et normalisé à l'import).
    """
    ecole = Ecole.objects.create(
        nom=f"École Test {suffixe}",
        adresse="Conakry",
        telephone="+224622000000",
        directeur="Directeur",
    )
    classe = Classe.objects.create(
        ecole=ecole, nom="6ème A", niveau="PRIMAIRE_6", annee_scolaire="2025-2026",
    )
    responsable = Responsable.objects.create(
        prenom="Mamadou", nom="Diallo", relation="PERE",
        telephone=f"+2246221{rang:05d}", adresse="Ratoma", email="papa@test.gn",
    )
    mere = Responsable.objects.create(
        prenom="Fatoumata", nom="Barry", relation="MERE",
        telephone=f"+2246222{rang:05d}", adresse="Ratoma",
    )
    eleve = Eleve.objects.create(
        matricule=f"MAT-{suffixe}-001", prenom="Aissatou", nom="Camara", sexe="F",
        date_naissance=date(2014, 5, 12), lieu_naissance="Kindia",
        classe=classe, date_inscription=date(2025, 9, 15), statut="ACTIF",
        responsable_principal=responsable, responsable_secondaire=mere,
    )
    return ecole, classe, eleve


class SuppressionEcoleAdminTest(TestCase):
    """L'école et toute sa cascade doivent se supprimer sans erreur."""

    def setUp(self):
        self.admin = User.objects.create_superuser('admin_ecole', 'a@a.gn', 'x')
        self.requetes = _RequeteAdmin(self.admin)

    def test_suppression_ecole_avec_donnees_liees(self):
        from eleves.admin import EcoleAdmin

        ecole, classe, eleve = _creer_jeu_de_donnees('ec')
        type_p = TypePaiement.objects.create(nom="Scolarité EC")
        mode_p = ModePaiement.objects.create(nom="Espèces EC")
        Paiement.objects.create(
            eleve=eleve, type_paiement=type_p, mode_paiement=mode_p,
            montant=Decimal('250000'), date_paiement=date(2025, 10, 1),
        )
        AbonnementCantine.objects.create(
            eleve=eleve, montant=Decimal('50000'), date_debut=date(2025, 9, 1),
            date_expiration=date(2026, 6, 30),
        )

        model_admin = EcoleAdmin(Ecole, AdminSite())
        requete = self.requetes.post()

        # La page de confirmation ne doit pas exploser sur les objets liés
        lignes, model_count, perms, protected = model_admin.get_deleted_objects(
            [ecole], requete,
        )
        self.assertTrue(lignes)
        self.assertEqual(protected, [])

        model_admin.delete_model(requete, ecole)

        self.assertFalse(Ecole.objects.filter(pk=ecole.pk).exists())
        self.assertFalse(Classe.objects.filter(pk=classe.pk).exists())
        self.assertFalse(Eleve.objects.filter(pk=eleve.pk).exists())
        # Aucun message d'erreur remonté à l'utilisateur
        erreurs = [m for niveau, m in requete._messages.messages if 'impossible' in m.lower()]
        self.assertEqual(erreurs, [])


class CorbeilleEleveTest(TestCase):
    """Suppression d'un élève depuis l'admin puis restauration."""

    def setUp(self):
        self.admin = User.objects.create_superuser('admin_eleve', 'b@b.gn', 'x')
        self.requetes = _RequeteAdmin(self.admin)

    def test_suppression_admin_puis_restauration(self):
        from eleves.admin import EleveAdmin

        ecole, classe, eleve = _creer_jeu_de_donnees('el')
        type_p = TypePaiement.objects.create(nom="Scolarité EL")
        mode_p = ModePaiement.objects.create(nom="Espèces EL")
        Paiement.objects.create(
            eleve=eleve, type_paiement=type_p, mode_paiement=mode_p,
            montant=Decimal('300000'), date_paiement=date(2025, 10, 5),
        )
        AbonnementCantine.objects.create(
            eleve=eleve, montant=Decimal('60000'), date_debut=date(2025, 9, 1),
            date_expiration=date(2026, 6, 30),
        )

        model_admin = EleveAdmin(Eleve, AdminSite())
        requete = self.requetes.post()
        model_admin.delete_model(requete, eleve)

        self.assertFalse(Eleve.objects.filter(pk=eleve.pk).exists())
        entree = CorbeilleEleve.objects.get(matricule="MAT-el-001")
        self.assertEqual(entree.nb_paiements, 1)
        self.assertEqual(entree.supprime_par, self.admin)
        self.assertFalse(entree.restaure)

        from .audit import restaurer_eleve

        restaure, message = restaurer_eleve(entree, utilisateur=self.admin)
        self.assertIn('restauré', message)
        self.assertEqual(restaure.matricule, "MAT-el-001")
        self.assertEqual(restaure.classe_id, classe.pk)
        self.assertEqual(restaure.paiements.count(), 1)
        self.assertEqual(restaure.abonnements_cantine.count(), 1)
        self.assertEqual(
            restaure.responsable_principal.telephone,
            eleve.responsable_principal.telephone,
        )

        entree.refresh_from_db()
        self.assertTrue(entree.restaure)

    def test_suppression_interface_met_en_corbeille(self):
        from administration.audit import mettre_eleve_en_corbeille

        ecole, classe, eleve = _creer_jeu_de_donnees('ui')
        mettre_eleve_en_corbeille(eleve, utilisateur=self.admin, motif="Test interface")

        self.assertFalse(Eleve.objects.filter(matricule="MAT-ui-001").exists())
        entree = CorbeilleEleve.objects.get(matricule="MAT-ui-001")
        self.assertEqual(entree.motif, "Test interface")
        self.assertTrue(
            JournalModification.objects.filter(
                model_name='Eleve', action=JournalModification.ACTION_SUPPRESSION,
            ).exists()
        )


class CorbeillePaiementAdminTest(TestCase):
    """Les suppressions admin de paiements / échéanciers passent par la corbeille."""

    def setUp(self):
        self.admin = User.objects.create_superuser('admin_paie', 'c@c.gn', 'x')
        self.requetes = _RequeteAdmin(self.admin)
        self.ecole, self.classe, self.eleve = _creer_jeu_de_donnees('pa')
        self.type_p = TypePaiement.objects.create(nom="Scolarité PA")
        self.mode_p = ModePaiement.objects.create(nom="Espèces PA")

    def test_paiement_supprime_va_en_corbeille_et_revient(self):
        from paiements.admin import PaiementAdmin

        paiement = Paiement.objects.create(
            eleve=self.eleve, type_paiement=self.type_p, mode_paiement=self.mode_p,
            montant=Decimal('150000'), date_paiement=date(2025, 11, 3),
        )
        numero = paiement.numero_recu

        model_admin = PaiementAdmin(Paiement, AdminSite())
        model_admin.delete_model(self.requetes.post(), paiement)

        self.assertFalse(Paiement.objects.filter(numero_recu=numero).exists())
        entree = CorbeilleElement.objects.get(model_name='Paiement')
        self.assertEqual(entree.supprime_par, self.admin)
        self.assertIn(self.eleve.matricule, entree.contexte)

        from .audit import restaurer_element

        objet, message = restaurer_element(entree, utilisateur=self.admin)
        self.assertEqual(objet.numero_recu, numero)
        self.assertEqual(objet.montant, Decimal('150000'))
        self.assertIn('restauré', message)

    def test_echeancier_supprime_va_en_corbeille(self):
        from paiements.admin import EcheancierPaiementAdmin

        echeancier = EcheancierPaiement.objects.create(
            eleve=self.eleve, annee_scolaire="2025-2026",
            frais_inscription_du=Decimal('100000'),
            date_echeance_inscription=date(2025, 9, 30),
            tranche_1_due=Decimal('200000'), date_echeance_tranche_1=date(2025, 10, 1),
            tranche_2_due=Decimal('200000'), date_echeance_tranche_2=date(2026, 1, 5),
            tranche_3_due=Decimal('200000'), date_echeance_tranche_3=date(2026, 4, 5),
        )

        model_admin = EcheancierPaiementAdmin(EcheancierPaiement, AdminSite())
        model_admin.delete_queryset(
            self.requetes.post(), EcheancierPaiement.objects.filter(pk=echeancier.pk),
        )

        self.assertFalse(EcheancierPaiement.objects.filter(pk=echeancier.pk).exists())
        self.assertTrue(CorbeilleElement.objects.filter(model_name='EcheancierPaiement').exists())


class JournalModificationTest(TestCase):
    """La corbeille mémoire enregistre l'avant / après de chaque changement."""

    def setUp(self):
        self.user = User.objects.create_superuser('admin_journal', 'd@d.gn', 'x')
        self.ecole, self.classe, self.eleve = _creer_jeu_de_donnees('jo')

    def test_modification_paiement_journalisee(self):
        type_p = TypePaiement.objects.create(nom="Scolarité JO")
        mode_p = ModePaiement.objects.create(nom="Espèces JO")
        paiement = Paiement.objects.create(
            eleve=self.eleve, type_paiement=type_p, mode_paiement=mode_p,
            montant=Decimal('100000'), date_paiement=date(2025, 10, 10),
        )
        JournalModification.objects.all().delete()

        paiement.montant = Decimal('180000')
        paiement.save()

        entree = JournalModification.objects.get(
            model_name='Paiement', action=JournalModification.ACTION_MODIFICATION,
        )
        self.assertIn('montant', entree.changements)
        self.assertEqual(entree.changements['montant']['avant'], '100000')
        self.assertEqual(entree.changements['montant']['apres'], '180000')

    def test_creation_eleve_journalisee(self):
        self.assertTrue(
            JournalModification.objects.filter(
                model_name='Eleve', action=JournalModification.ACTION_CREATION,
            ).exists()
        )


class ExportElevesTest(TestCase):
    """L'export global doit respecter le format du modèle d'importation."""

    COLONNES_ATTENDUES = [
        'École', 'Classe', 'Année scolaire', 'Matricule', 'Prénom', 'Nom', 'Sexe',
        'Date de Naissance', 'Lieu de Naissance', 'Nom du Père/Tuteur',
        'Prénom du Père/Tuteur', 'Téléphone Principal', 'Adresse', 'Nom de la Mère',
        'Prénom de la Mère', 'Téléphone Secondaire', 'Email',
    ]

    def test_colonnes_et_contenu(self):
        from eleves.import_eleves import exporter_tous_les_eleves

        ecole, classe, eleve = _creer_jeu_de_donnees('ex')
        df = exporter_tous_les_eleves()

        self.assertEqual(list(df.columns), self.COLONNES_ATTENDUES)
        ligne = df[df['Matricule'] == eleve.matricule].iloc[0]
        self.assertEqual(ligne['École'], ecole.nom)
        self.assertEqual(ligne['Classe'], classe.nom)
        self.assertEqual(ligne['Année scolaire'], classe.annee_scolaire)
        # Le modèle normalise l'identité en majuscules à l'enregistrement
        self.assertEqual(ligne['Prénom'], eleve.prenom)
        self.assertEqual(ligne['Nom'], eleve.nom)
        self.assertEqual(ligne['Sexe'], 'F')
        self.assertEqual(ligne['Date de Naissance'], '12/05/2014')
        self.assertEqual(ligne['Lieu de Naissance'], eleve.lieu_naissance)
        self.assertEqual(ligne['Nom du Père/Tuteur'], eleve.responsable_principal.nom)
        self.assertEqual(ligne['Prénom du Père/Tuteur'], eleve.responsable_principal.prenom)
        self.assertEqual(ligne['Nom de la Mère'], eleve.responsable_secondaire.nom)
        self.assertEqual(ligne['Prénom de la Mère'], eleve.responsable_secondaire.prenom)
        self.assertEqual(ligne['Téléphone Principal'], eleve.responsable_principal.telephone)
        self.assertEqual(ligne['Téléphone Secondaire'], eleve.responsable_secondaire.telephone)
        self.assertEqual(ligne['Email'], 'papa@test.gn')

    @override_settings(MIDDLEWARE=MIDDLEWARE_SANS_LICENCE)
    def test_telechargement_depuis_la_liste_des_eleves(self):
        """Le bouton « Exporter tous les élèves » renvoie bien le classeur."""
        import io

        import pandas as pd
        from django.urls import reverse

        _creer_jeu_de_donnees('dl')
        self.client.force_login(User.objects.create_superuser('admin_dl', 'x@x.gn', 'x'))

        reponse = self.client.get(reverse('eleves:exporter_tous_eleves_template'))
        self.assertEqual(reponse.status_code, 200)
        self.assertIn('spreadsheetml', reponse['Content-Type'])
        self.assertIn('attachment; filename="export_eleves_', reponse['Content-Disposition'])

        df = pd.read_excel(io.BytesIO(reponse.content))
        self.assertEqual(list(df.columns), self.COLONNES_ATTENDUES)
        self.assertEqual(len(df), 1)

    @override_settings(MIDDLEWARE=MIDDLEWARE_SANS_LICENCE)
    def test_reimport_du_fichier_exporte(self):
        """Le fichier exporté se réimporte tel quel (transfert vers un autre poste)."""
        import io

        from django.core.files.uploadedfile import SimpleUploadedFile
        from django.urls import reverse

        from eleves.import_eleves import exporter_tous_les_eleves

        ecole, classe, eleve = _creer_jeu_de_donnees('ri')
        nom_classe, nom_ecole = classe.nom, ecole.nom
        df = exporter_tous_les_eleves()

        tampon = io.BytesIO()
        df.to_excel(tampon, index=False)
        contenu = tampon.getvalue()

        # On efface l'élève et sa classe : l'import doit tout recréer à partir
        # des seules colonnes École / Classe / Année scolaire du fichier.
        Eleve.objects.filter(pk=eleve.pk).delete()
        Classe.objects.filter(pk=classe.pk).delete()
        self.assertFalse(Eleve.objects.filter(matricule='MAT-ri-001').exists())

        # force_login : django-axes exige une requête pour authenticate()
        self.client.force_login(User.objects.create_superuser('admin_import', 'e@e.gn', 'x'))

        reponse = self.client.post(
            reverse('eleves:importer_eleves'),
            {
                'repartition_auto': 'on',
                'fichier': SimpleUploadedFile(
                    'export.xlsx', contenu,
                    content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                ),
            },
            follow=True,
        )

        contexte = reponse.context or {}
        messages_recus = [str(m) for m in contexte.get('messages', [])]
        self.assertTrue(
            Eleve.objects.filter(matricule='MAT-ri-001').exists(),
            msg=(
                f"Import échoué (status={reponse.status_code}, "
                f"chain={reponse.redirect_chain}) : {messages_recus} "
                f"{reponse.content[:500]}"
            ),
        )
        recree = Eleve.objects.get(matricule='MAT-ri-001')
        self.assertEqual(recree.classe.nom, nom_classe)
        self.assertEqual(recree.classe.ecole.nom, nom_ecole)
        self.assertEqual(recree.classe.annee_scolaire, '2025-2026')
        self.assertEqual(
            recree.responsable_principal.telephone,
            eleve.responsable_principal.telephone,
        )


@override_settings(MIDDLEWARE=MIDDLEWARE_SANS_LICENCE)
class SuppressionEleveInterfaceTest(TestCase):
    """Depuis /eleves/, confirmer la suppression envoie l'élève à la corbeille."""

    def setUp(self):
        self.user = User.objects.create_superuser('admin_ui', 'f@f.gn', 'x')
        self.client.force_login(self.user)
        self.ecole, self.classe, self.eleve = _creer_jeu_de_donnees('iu')

    def test_confirmation_envoie_en_corbeille(self):
        from django.urls import reverse

        reponse = self.client.post(
            reverse('eleves:supprimer_eleve', args=[self.eleve.pk]),
            {'type_suppression': 'corbeille', 'mise_en_corbeille': 'on',
             'suppression_definitive': ''},
            follow=True,
        )
        self.assertEqual(reponse.status_code, 200)

        self.assertFalse(Eleve.objects.filter(pk=self.eleve.pk).exists())
        entree = CorbeilleEleve.objects.get(matricule=self.eleve.matricule)
        self.assertEqual(entree.supprime_par, self.user)
        self.assertFalse(entree.restaure)

        # Restauration depuis la page corbeille de l'application
        reponse = self.client.post(
            reverse('administration:restaurer_eleve_corbeille', args=[entree.pk]),
            follow=True,
        )
        self.assertEqual(reponse.status_code, 200)
        self.assertTrue(Eleve.objects.filter(matricule=self.eleve.matricule).exists())

    def test_page_corbeille_accessible(self):
        from django.urls import reverse

        for nom in ('administration:corbeille_eleves',
                    'administration:corbeille_elements',
                    'administration:journal_modifications'):
            with self.subTest(vue=nom):
                self.assertEqual(self.client.get(reverse(nom)).status_code, 200)


@override_settings(MIDDLEWARE=MIDDLEWARE_SANS_LICENCE)
class ModificationPaiementViewTest(TestCase):
    """La page de correction d'un paiement écrit bien dans la corbeille mémoire."""

    def setUp(self):
        self.user = User.objects.create_superuser('admin_modif', 'g@g.gn', 'x')
        self.client.force_login(self.user)
        self.ecole, self.classe, self.eleve = _creer_jeu_de_donnees('mp')
        self.type_p = TypePaiement.objects.create(nom="Scolarité MP")
        self.mode_p = ModePaiement.objects.create(nom="Espèces MP")
        self.paiement = Paiement.objects.create(
            eleve=self.eleve, type_paiement=self.type_p, mode_paiement=self.mode_p,
            montant=Decimal('120000'), date_paiement=date(2025, 10, 20),
        )

    def test_correction_montant_et_journal(self):
        from django.urls import reverse

        url = reverse('paiements:modifier_paiement', args=[self.paiement.pk])
        self.assertEqual(self.client.get(url).status_code, 200)

        JournalModification.objects.all().delete()
        reponse = self.client.post(url, {
            'type_paiement': self.type_p.pk,
            'mode_paiement': self.mode_p.pk,
            'montant': '175000',
            'date_paiement': '2025-10-21',
            'reference_externe': '',
            'observations': 'Tranche oubliée lors de la saisie',
            'motif_modification': 'Montant saisi incomplet le jour même',
        }, follow=True)
        self.assertEqual(reponse.status_code, 200)

        self.paiement.refresh_from_db()
        self.assertEqual(self.paiement.montant, Decimal('175000'))
        self.assertEqual(self.paiement.date_paiement, date(2025, 10, 21))

        entree = JournalModification.objects.filter(model_name='Paiement').first()
        self.assertIsNotNone(entree, "Aucune trace dans la corbeille mémoire")
        self.assertEqual(entree.commentaire, 'Montant saisi incomplet le jour même')
        self.assertEqual(entree.utilisateur, self.user)
        self.assertEqual(entree.changements['montant']['avant'], '120000')
        self.assertEqual(entree.changements['montant']['apres'], '175000')

    def test_motif_obligatoire(self):
        from django.urls import reverse

        reponse = self.client.post(
            reverse('paiements:modifier_paiement', args=[self.paiement.pk]),
            {
                'type_paiement': self.type_p.pk,
                'mode_paiement': self.mode_p.pk,
                'montant': '200000',
                'date_paiement': '2025-10-20',
                'motif_modification': '',
            },
        )
        self.assertEqual(reponse.status_code, 200)
        self.paiement.refresh_from_db()
        self.assertEqual(self.paiement.montant, Decimal('120000'))


@override_settings(MIDDLEWARE=MIDDLEWARE_SANS_LICENCE)
class PlancheCartesA4Test(TestCase):
    """Toutes les planches de cartes doivent tenir 8 cartes par feuille A4."""

    NB_ELEVES = 9  # 9 cartes → 2 pages si la grille est bien de 8 par page

    def setUp(self):
        self.user = User.objects.create_superuser('admin_cartes', 'h@h.gn', 'x')
        self.client.force_login(self.user)
        self.ecole = Ecole.objects.create(
            nom="École Cartes", adresse="Conakry",
            telephone="+224622000000", directeur="Directeur",
        )
        self.classe = Classe.objects.create(
            ecole=self.ecole, nom="CM2 A", niveau="PRIMAIRE_6",
            annee_scolaire="2025-2026",
        )
        for i in range(self.NB_ELEVES):
            responsable = Responsable.objects.create(
                prenom=f"Parent{i}", nom="Sow", relation="PERE",
                telephone=f"+2246239{i:05d}", adresse="Ratoma",
            )
            eleve = Eleve.objects.create(
                matricule=f"CARTE-{i:03d}", prenom=f"Eleve{i}", nom="Bah", sexe="M",
                date_naissance=date(2013, 3, 4), lieu_naissance="Conakry",
                classe=self.classe, date_inscription=date(2025, 9, 1), statut="ACTIF",
                responsable_principal=responsable,
            )
            AbonnementBus.objects.create(
                eleve=eleve, montant=Decimal('80000'),
                date_debut=date(2025, 9, 1), date_expiration=date(2026, 6, 30),
            )
            AbonnementCantine.objects.create(
                eleve=eleve, montant=Decimal('90000'),
                date_debut=date(2025, 9, 1), date_expiration=date(2026, 6, 30),
            )

    def _nombre_de_pages(self, reponse):
        import io

        from pypdf import PdfReader

        self.assertEqual(reponse.status_code, 200, msg=str(reponse.get('Location', '')))
        self.assertEqual(reponse['Content-Type'], 'application/pdf')
        return len(PdfReader(io.BytesIO(reponse.content)).pages)

    def test_huit_cartes_par_page_a4(self):
        from django.urls import reverse

        vues = [
            'eleves:tickets_retrait_classe_pdf',
            'eleves:tickets_bus_classe_pdf',
            'eleves:cartes_cantine_classe_pdf',
            'eleves:cartes_scolaires_classe_pdf',
        ]
        for nom in vues:
            with self.subTest(planche=nom):
                reponse = self.client.get(reverse(nom, args=[self.classe.pk]))
                # 9 cartes réparties 8 + 1 → exactement 2 pages
                self.assertEqual(self._nombre_de_pages(reponse), 2)

    def test_format_page_a4(self):
        import io

        from django.urls import reverse
        from pypdf import PdfReader

        reponse = self.client.get(
            reverse('eleves:cartes_cantine_classe_pdf', args=[self.classe.pk])
        )
        page = PdfReader(io.BytesIO(reponse.content)).pages[0]
        largeur = float(page.mediabox.width)
        hauteur = float(page.mediabox.height)
        # A4 = 595 x 842 points (±1 pt d'arrondi)
        self.assertAlmostEqual(largeur, 595.27, delta=1)
        self.assertAlmostEqual(hauteur, 841.89, delta=1)
