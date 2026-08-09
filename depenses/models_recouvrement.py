"""Modules de recouvrement: cuisine, documents, versements et informatique.

Ces quatre modules partagent la même logique de saisie rapide: la date est
posée automatiquement le jour de l'enregistrement, l'utilisateur ne renseigne
que le libellé, le montant et une observation facultative.
"""

from decimal import Decimal

from django.contrib.auth.models import User
from django.db import models
from django.utils import timezone

from synchronisation.mixins import SyncTrackedModel


class LigneRecouvrement(SyncTrackedModel):
    """Socle commun aux écritures simples (cuisine, documents, versements)."""

    ecole = models.ForeignKey(
        'eleves.Ecole',
        on_delete=models.PROTECT,
        related_name='%(class)ss',
        verbose_name='Établissement',
    )
    date = models.DateField(
        default=timezone.localdate,
        db_index=True,
        verbose_name='Date',
        help_text="Renseignée automatiquement à l'enregistrement.",
    )
    montant = models.DecimalField(
        max_digits=12, decimal_places=0,
        default=Decimal('0'),
        verbose_name='Montant (GNF)',
    )
    observation = models.TextField(blank=True, verbose_name='Observation')
    cree_par = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='+', verbose_name='Enregistré par',
    )
    date_creation = models.DateTimeField(auto_now_add=True)

    class Meta:
        abstract = True
        ordering = ['-date', '-id']

    @property
    def libelle(self):
        """Libellé affiché dans les listes et les exports."""
        return getattr(self, self.CHAMP_LIBELLE, '')


class DepenseCuisine(LigneRecouvrement):
    """Dépense engagée pour la cuisine de l'établissement."""

    CHAMP_LIBELLE = 'designation'

    designation = models.CharField(max_length=200, verbose_name='Désignation')

    class Meta(LigneRecouvrement.Meta):
        abstract = False
        verbose_name = 'Dépense de cuisine'
        verbose_name_plural = 'Dépenses de cuisine'

    def __str__(self):
        return f"{self.date:%d/%m/%Y} - {self.designation} - {int(self.montant):,} GNF".replace(',', ' ')


class DepenseDocument(LigneRecouvrement):
    """Dépense liée aux documents (impressions, actes, fournitures administratives)."""

    CHAMP_LIBELLE = 'designation'

    designation = models.CharField(max_length=200, verbose_name='Désignation')

    class Meta(LigneRecouvrement.Meta):
        abstract = False
        verbose_name = 'Dépense de document'
        verbose_name_plural = 'Dépenses de documents'

    def __str__(self):
        return f"{self.date:%d/%m/%Y} - {self.designation} - {int(self.montant):,} GNF".replace(',', ' ')


class Versement(LigneRecouvrement):
    """Versement effectué par l'établissement (banque, direction, autre caisse)."""

    CHAMP_LIBELLE = 'lieu_versement'

    lieu_versement = models.CharField(max_length=200, verbose_name='Lieu de versement')

    class Meta(LigneRecouvrement.Meta):
        abstract = False
        verbose_name = 'Versement'
        verbose_name_plural = 'Versements'

    def __str__(self):
        return f"{self.date:%d/%m/%Y} - {self.lieu_versement} - {int(self.montant):,} GNF".replace(',', ' ')


class AbonnementInformatique(SyncTrackedModel):
    """Abonnement d'un élève à la salle informatique."""

    STATUT_CHOICES = [
        ('ACTIF', 'Actif'),
        ('SUSPENDU', 'Suspendu'),
        ('RESILIE', 'Résilié'),
    ]

    eleve = models.ForeignKey(
        'eleves.Eleve',
        on_delete=models.CASCADE,
        related_name='abonnements_informatique',
        verbose_name='Élève',
    )
    date = models.DateField(
        default=timezone.localdate,
        db_index=True,
        verbose_name="Date d'enregistrement",
        help_text="Renseignée automatiquement à l'enregistrement.",
    )
    montant = models.DecimalField(
        max_digits=12, decimal_places=0,
        default=Decimal('0'),
        verbose_name="Montant de l'abonnement (GNF)",
    )
    date_debut = models.DateField(default=timezone.localdate, verbose_name='Début')
    date_fin = models.DateField(db_index=True, verbose_name='Fin')
    alerte_avant_jours = models.PositiveIntegerField(
        default=7,
        verbose_name='Alerte avant (jours)',
        help_text="Nombre de jours avant la fin à partir duquel l'abonnement est signalé.",
    )
    statut = models.CharField(
        max_length=10, choices=STATUT_CHOICES, default='ACTIF',
        db_index=True, verbose_name='Statut',
    )
    observation = models.TextField(blank=True, verbose_name='Observation')
    cree_par = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='+', verbose_name='Enregistré par',
    )
    date_creation = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Abonnement informatique'
        verbose_name_plural = 'Abonnements informatiques'
        ordering = ['-date_fin', 'eleve__nom']

    def __str__(self):
        return f"{self.eleve} - jusqu'au {self.date_fin:%d/%m/%Y}"

    @property
    def jours_restants(self):
        """Jours avant la fin (négatif si la période est dépassée)."""
        return (self.date_fin - timezone.localdate()).days

    @property
    def est_expire(self):
        return self.statut == 'ACTIF' and self.date_fin < timezone.localdate()

    @property
    def est_proche_expiration(self):
        """Abonnement encore valide mais dans la fenêtre d'alerte."""
        if self.statut != 'ACTIF' or self.est_expire:
            return False
        return self.jours_restants <= self.alerte_avant_jours

    @property
    def statut_effectif(self):
        """Statut réel: un abonnement actif dont la date est passée est expiré."""
        if self.statut != 'ACTIF':
            return self.statut
        return 'EXPIRE' if self.est_expire else 'ACTIF'

    @property
    def libelle_statut(self):
        if self.statut_effectif == 'EXPIRE':
            return 'Expiré'
        return self.get_statut_display()
