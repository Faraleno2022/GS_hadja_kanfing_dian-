from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse

from administration.models import CorbeilleElement
from eleves.models import Classe, Ecole, Eleve, Responsable
from paiements.models import (
    EcheancierPaiement,
    ModePaiement,
    Paiement,
    PaiementRemise,
    RemiseReduction,
    TypePaiement,
)
from paiements.tests.support import MIDDLEWARE_SANS_LICENCE


@override_settings(MIDDLEWARE=MIDDLEWARE_SANS_LICENCE)
class SuppressionPaiementCorbeilleTest(TestCase):
    def setUp(self):
        self.admin = get_user_model().objects.create_superuser(
            'admin_corbeille_paiement',
            'paiement@example.com',
            'secret',
        )
        self.ecole = Ecole.objects.create(
            nom='École Corbeille Paiement',
            adresse='Conakry',
            telephone='+224622400001',
            directeur='Direction',
        )
        self.classe = Classe.objects.create(
            ecole=self.ecole,
            nom='5ème Corbeille',
            niveau='PRIMAIRE_5',
            annee_scolaire='2025-2026',
        )
        responsable = Responsable.objects.create(
            prenom='Mamadou',
            nom='Diallo',
            relation='PERE',
            telephone='+224622400002',
            adresse='Conakry',
        )
        self.eleve = Eleve.objects.create(
            matricule='CORB-PAY-001',
            prenom='Aminata',
            nom='Camara',
            sexe='F',
            date_naissance=date(2014, 2, 3),
            lieu_naissance='Conakry',
            classe=self.classe,
            date_inscription=date(2025, 9, 1),
            responsable_principal=responsable,
        )
        self.type_paiement = TypePaiement.objects.create(nom='Scolarité Corbeille')
        self.mode_paiement = ModePaiement.objects.create(nom='Espèces Corbeille')
        self.echeancier = EcheancierPaiement.objects.create(
            eleve=self.eleve,
            annee_scolaire='2025-2026',
            frais_inscription_du=Decimal('100000'),
            tranche_1_due=Decimal('200000'),
            tranche_2_due=Decimal('200000'),
            tranche_3_due=Decimal('200000'),
            frais_inscription_paye=Decimal('100000'),
            tranche_1_payee=Decimal('50000'),
            date_echeance_inscription=date(2025, 9, 1),
            date_echeance_tranche_1=date(2025, 10, 1),
            date_echeance_tranche_2=date(2026, 1, 1),
            date_echeance_tranche_3=date(2026, 3, 1),
            statut='PAYE_PARTIEL',
        )
        self.paiement_a_supprimer = Paiement.objects.create(
            eleve=self.eleve,
            type_paiement=self.type_paiement,
            mode_paiement=self.mode_paiement,
            montant=Decimal('100000'),
            date_paiement=date(2025, 9, 2),
            statut='VALIDE',
            cree_par=self.admin,
            valide_par=self.admin,
        )
        self.autre_paiement = Paiement.objects.create(
            eleve=self.eleve,
            type_paiement=self.type_paiement,
            mode_paiement=self.mode_paiement,
            montant=Decimal('50000'),
            date_paiement=date(2025, 9, 3),
            statut='VALIDE',
            cree_par=self.admin,
            valide_par=self.admin,
        )
        remise = RemiseReduction.objects.create(
            nom='Remise corbeille',
            type_remise='MONTANT_FIXE',
            valeur=Decimal('10000'),
            motif='AUTRE',
            date_debut=date(2025, 9, 1),
            date_fin=date(2026, 6, 30),
            cree_par=self.admin,
        )
        PaiementRemise.objects.create(
            paiement=self.paiement_a_supprimer,
            remise=remise,
            montant_remise=Decimal('10000'),
        )
        self.client.force_login(self.admin)

    def test_suppression_et_restauration_conservent_recu_remise_et_echeancier(self):
        paiement_id = self.paiement_a_supprimer.pk
        numero_recu = self.paiement_a_supprimer.numero_recu
        url = reverse('paiements:supprimer_paiement', args=[paiement_id])

        confirmation = self.client.get(url)
        self.assertEqual(confirmation.status_code, 200)
        self.assertContains(confirmation, numero_recu)
        self.assertContains(confirmation, 'État de l\'échéancier')

        reponse = self.client.post(
            url,
            {'motif': 'Paiement saisi en double'},
            follow=True,
        )
        self.assertEqual(reponse.status_code, 200)
        self.assertFalse(Paiement.objects.filter(pk=paiement_id).exists())
        self.assertTrue(Paiement.objects.filter(pk=self.autre_paiement.pk).exists())
        self.assertFalse(PaiementRemise.objects.filter(paiement_id=paiement_id).exists())

        entree = CorbeilleElement.objects.get(
            app_label='paiements',
            model_name='Paiement',
            objet_id_origine=paiement_id,
        )
        self.assertEqual(entree.donnees['recu']['numero'], numero_recu)
        self.assertEqual(
            entree.donnees['echeancier']['tranche_1_payee'],
            '50000',
        )
        self.assertEqual(entree.nb_lignes_liees, 3)  # reçu + échéancier + remise

        self.echeancier.refresh_from_db()
        self.assertEqual(self.echeancier.frais_inscription_paye, Decimal('50000'))
        self.assertEqual(self.echeancier.tranche_1_payee, Decimal('0'))

        ancien_recu = self.client.get(
            reverse('paiements:generer_recu_pdf', args=[paiement_id])
        )
        self.assertEqual(ancien_recu.status_code, 404)

        restauration = self.client.post(
            reverse('administration:restaurer_element_corbeille', args=[entree.pk]),
            follow=True,
        )
        self.assertEqual(restauration.status_code, 200)

        paiement_restaure = Paiement.objects.get(numero_recu=numero_recu)
        self.assertEqual(paiement_restaure.pk, paiement_id)
        self.assertEqual(paiement_restaure.remises.count(), 1)
        self.echeancier.refresh_from_db()
        self.assertEqual(self.echeancier.frais_inscription_paye, Decimal('100000'))
        self.assertEqual(self.echeancier.tranche_1_payee, Decimal('50000'))

        recu_restaure = self.client.get(
            reverse('paiements:generer_recu_pdf', args=[paiement_restaure.pk])
        )
        self.assertEqual(recu_restaure.status_code, 200)
        self.assertEqual(recu_restaure['Content-Type'], 'application/pdf')


@override_settings(MIDDLEWARE=MIDDLEWARE_SANS_LICENCE)
class SuppressionPaiementPermissionTest(TestCase):
    def setUp(self):
        self.ecole = Ecole.objects.create(
            nom='École Permission Paiement', adresse='Conakry',
            telephone='+224622410001', directeur='Direction',
        )
        autre_ecole = Ecole.objects.create(
            nom='Autre École Paiement', adresse='Conakry',
            telephone='+224622410002', directeur='Direction',
        )
        classe = Classe.objects.create(
            ecole=self.ecole, nom='Classe Permission', niveau='PRIMAIRE_4',
            annee_scolaire='2025-2026',
        )
        autre_classe = Classe.objects.create(
            ecole=autre_ecole, nom='Autre Classe', niveau='PRIMAIRE_4',
            annee_scolaire='2025-2026',
        )
        responsable = Responsable.objects.create(
            prenom='Alpha', nom='Parent', relation='PERE',
            telephone='+224622410003', adresse='Conakry',
        )
        autre_responsable = Responsable.objects.create(
            prenom='Beta', nom='Parent', relation='MERE',
            telephone='+224622410004', adresse='Conakry',
        )
        eleve = Eleve.objects.create(
            matricule='PERM-PAY-001', prenom='Alpha', nom='Élève', sexe='M',
            date_naissance=date(2014, 1, 1), lieu_naissance='Conakry',
            classe=classe, date_inscription=date(2025, 9, 1),
            responsable_principal=responsable,
        )
        autre_eleve = Eleve.objects.create(
            matricule='PERM-PAY-002', prenom='Beta', nom='Élève', sexe='F',
            date_naissance=date(2014, 1, 2), lieu_naissance='Conakry',
            classe=autre_classe, date_inscription=date(2025, 9, 1),
            responsable_principal=autre_responsable,
        )
        type_paiement = TypePaiement.objects.create(nom='Type Permission Paiement')
        mode = ModePaiement.objects.create(nom='Mode Permission Paiement')
        self.paiement = Paiement.objects.create(
            eleve=eleve, type_paiement=type_paiement, mode_paiement=mode,
            montant=Decimal('50000'), date_paiement=date(2025, 9, 2),
        )
        self.paiement_autre_ecole = Paiement.objects.create(
            eleve=autre_eleve, type_paiement=type_paiement, mode_paiement=mode,
            montant=Decimal('50000'), date_paiement=date(2025, 9, 2),
        )
        self.user = get_user_model().objects.create_user(
            'comptable_suppression', password='secret',
        )
        self.user.profil.role = 'COMPTABLE'
        self.user.profil.ecole = self.ecole
        self.user.profil.telephone = '+224622410005'
        self.user.profil.peut_supprimer_paiements = False
        self.user.profil.save()
        self.client.force_login(self.user)

    def test_permission_et_perimetre_ecole_sont_appliques(self):
        url = reverse('paiements:supprimer_paiement', args=[self.paiement.pk])
        self.assertEqual(self.client.get(url).status_code, 403)

        self.user.profil.peut_supprimer_paiements = True
        self.user.profil.save(update_fields=['peut_supprimer_paiements'])
        self.assertEqual(self.client.get(url).status_code, 200)

        url_autre = reverse(
            'paiements:supprimer_paiement',
            args=[self.paiement_autre_ecole.pk],
        )
        self.assertEqual(self.client.get(url_autre).status_code, 404)

        numero_recu = self.paiement.numero_recu
        self.assertEqual(self.client.post(url).status_code, 302)
        entree = CorbeilleElement.objects.get(
            app_label='paiements',
            model_name='Paiement',
            objet_id_origine=self.paiement.pk,
        )

        corbeille = self.client.get(
            reverse('administration:corbeille_elements'),
            {'type': 'Paiement'},
        )
        self.assertEqual(corbeille.status_code, 200)
        self.assertContains(corbeille, numero_recu)

        # La permission de paiement ne donne pas le droit de restaurer un
        # autre type d'élément de la corbeille.
        autre_entree = CorbeilleElement.objects.create(
            app_label='paiements',
            model_name='EcheancierPaiement',
            modele_libelle='Échéancier',
            objet_id_origine=999,
            objet_repr='Échéancier hors permission',
            ecole_nom=self.ecole.nom,
            donnees={'principal': {'id': 999}},
        )
        restauration_interdite = self.client.post(
            reverse(
                'administration:restaurer_element_corbeille',
                args=[autre_entree.pk],
            )
        )
        self.assertEqual(restauration_interdite.status_code, 404)

        restauration = self.client.post(
            reverse(
                'administration:restaurer_element_corbeille',
                args=[entree.pk],
            ),
            follow=True,
        )
        self.assertEqual(restauration.status_code, 200)
        self.assertTrue(Paiement.objects.filter(numero_recu=numero_recu).exists())
