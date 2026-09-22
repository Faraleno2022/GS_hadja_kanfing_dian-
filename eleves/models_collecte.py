"""Collecte publique : les propositions ne sont pas encore des élèves."""
import uuid

from django.conf import settings
from django.db import models
from django.utils import timezone

from .collecte_permissions import peut_gerer_collecte


class LienCollecteEleves(models.Model):
    token = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    ecole = models.ForeignKey('eleves.Ecole', on_delete=models.CASCADE, related_name='liens_collecte')
    classe = models.ForeignKey('eleves.Classe', on_delete=models.CASCADE, related_name='liens_collecte')
    annee_scolaire = models.CharField(max_length=9)
    destinataire = models.CharField(max_length=150, verbose_name="Enseignant destinataire")
    expire_le = models.DateTimeField(verbose_name="Valable jusqu'au")
    revoque_le = models.DateTimeField(null=True, blank=True)
    cree_par = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    cree_le = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-cree_le']
        indexes = [models.Index(fields=['ecole', 'cree_le'], name='collecte_ecole_date_idx')]

    @property
    def statut(self):
        if self.revoque_le:
            return 'Révoqué'
        if self.expire_le <= timezone.now():
            return 'Expiré'
        if (self.classe.ecole_id != self.ecole_id
                or self.classe.annee_scolaire != self.annee_scolaire
                or not self.cree_par or not peut_gerer_collecte(self.cree_par)):
            return 'Indisponible'
        if not self.cree_par.is_superuser and self.cree_par.profil.ecole_id != self.ecole_id:
            return 'Indisponible'
        return 'Actif'

    @property
    def est_actif(self):
        return self.statut == 'Actif'


class EnvoiCollecteEleves(models.Model):
    lien = models.ForeignKey(LienCollecteEleves, on_delete=models.CASCADE, related_name='envois')
    identifiant = models.UUIDField()
    auteur = models.CharField(max_length=150, verbose_name="Votre nom")
    recu_le = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-recu_le', '-pk']
        constraints = [
            models.UniqueConstraint(fields=['lien', 'identifiant'], name='collecte_envoi_unique')
        ]


class PropositionEleve(models.Model):
    class Statut(models.TextChoices):
        EN_ATTENTE = 'EN_ATTENTE', 'À vérifier'
        ACCEPTEE = 'ACCEPTEE', 'Acceptée'
        REFUSEE = 'REFUSEE', 'Refusée'

    envoi = models.ForeignKey(EnvoiCollecteEleves, on_delete=models.CASCADE, related_name='propositions')
    prenom = models.CharField(max_length=100, verbose_name="Prénom de l'élève")
    nom = models.CharField(max_length=100, verbose_name="Nom de l'élève")
    sexe = models.CharField(max_length=1, choices=[('M', 'Masculin'), ('F', 'Féminin')])
    date_naissance = models.DateField(null=True, blank=True, verbose_name="Date de naissance")
    lieu_naissance = models.CharField(max_length=100, blank=True, verbose_name="Lieu de naissance")
    prenom_responsable = models.CharField(max_length=100, blank=True, verbose_name="Prénom du responsable")
    nom_responsable = models.CharField(max_length=100, blank=True, verbose_name="Nom du responsable")
    telephone_responsable = models.CharField(max_length=20, blank=True, verbose_name="Téléphone du responsable")
    adresse = models.CharField(max_length=300, blank=True, verbose_name="Adresse")
    statut = models.CharField(max_length=12, choices=Statut.choices, default=Statut.EN_ATTENTE, db_index=True)
    eleve = models.ForeignKey('eleves.Eleve', on_delete=models.SET_NULL, null=True, blank=True)
    traite_par = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    traite_le = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['pk']

    @property
    def nom_complet(self):
        return f"{self.prenom} {self.nom}"
