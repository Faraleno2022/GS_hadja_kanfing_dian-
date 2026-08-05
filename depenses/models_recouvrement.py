"""Modèles des nouveaux modules du menu Recouvrement (ex-Dépenses) :
Cuisine, Document, Versement et Informatique (abonnements élèves).
"""
from decimal import Decimal

from django.contrib.auth.models import User
from django.db import models
from django.utils import timezone

from eleves.models import Eleve
from synchronisation.mixins import SyncTrackedModel


class DepenseCuisine(SyncTrackedModel):
    """Dépense de la cuisine (achats, matériel, denrées, etc.)."""

    date = models.DateField(default=timezone.localdate, verbose_name="Date")
    designation = models.CharField(max_length=200, verbose_name="Désignation")
    montant = models.DecimalField(
        max_digits=12, decimal_places=0, default=Decimal('0'),
        verbose_name="Montant (GNF)"
    )
    observation = models.TextField(blank=True, verbose_name="Observation")

    cree_par = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='depenses_cuisine_creees'
    )
    date_creation = models.DateTimeField(auto_now_add=True)
    date_modification = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Dépense cuisine"
        verbose_name_plural = "Dépenses cuisine"
        ordering = ['-date', '-date_creation']

    def __str__(self):
        return f"{self.designation} - {self.montant:,.0f} GNF"


class DepenseDocument(SyncTrackedModel):
    """Dépense liée aux documents administratifs (impression, reliure, etc.)."""

    date = models.DateField(default=timezone.localdate, verbose_name="Date")
    designation = models.CharField(max_length=200, verbose_name="Désignation")
    montant = models.DecimalField(
        max_digits=12, decimal_places=0, default=Decimal('0'),
        verbose_name="Montant (GNF)"
    )
    observation = models.TextField(blank=True, verbose_name="Observation")

    cree_par = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='depenses_document_creees'
    )
    date_creation = models.DateTimeField(auto_now_add=True)
    date_modification = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Dépense document"
        verbose_name_plural = "Dépenses document"
        ordering = ['-date', '-date_creation']

    def __str__(self):
        return f"{self.designation} - {self.montant:,.0f} GNF"


class Versement(SyncTrackedModel):
    """Versement effectué par l'établissement (banque, trésor, etc.)."""

    date = models.DateField(default=timezone.localdate, verbose_name="Date")
    montant = models.DecimalField(
        max_digits=12, decimal_places=0, default=Decimal('0'),
        verbose_name="Montant (GNF)"
    )
    lieu_versement = models.CharField(max_length=200, verbose_name="Lieu de versement")
    observation = models.TextField(blank=True, verbose_name="Observation")

    cree_par = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='versements_crees'
    )
    date_creation = models.DateTimeField(auto_now_add=True)
    date_modification = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Versement"
        verbose_name_plural = "Versements"
        ordering = ['-date', '-date_creation']

    def __str__(self):
        return f"{self.lieu_versement} - {self.montant:,.0f} GNF"


class AbonnementInformatique(SyncTrackedModel):
    """Abonnement informatique par élève (accès salle info, logiciels, etc.)."""

    class Statut(models.TextChoices):
        ACTIF = 'ACTIF', 'Actif'
        EXPIRE = 'EXPIRE', 'Expiré'
        SUSPENDU = 'SUSPENDU', 'Suspendu'

    eleve = models.ForeignKey(Eleve, on_delete=models.CASCADE, related_name='abonnements_informatique')
    montant = models.DecimalField(
        max_digits=10, decimal_places=0, default=Decimal('0'),
        verbose_name="Montant d'abonnement (GNF)"
    )
    date_debut = models.DateField(default=timezone.localdate, verbose_name="Date de début")
    date_fin = models.DateField(db_index=True, verbose_name="Date de fin")
    statut = models.CharField(max_length=10, choices=Statut.choices, default=Statut.ACTIF, db_index=True)

    alerte_avant_jours = models.PositiveIntegerField(default=7, verbose_name="Alerte avant (jours)")
    observation = models.TextField(blank=True, verbose_name="Observation")

    cree_par = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='abonnements_informatique_crees'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Abonnement informatique"
        verbose_name_plural = "Abonnements informatique"
        ordering = ['-updated_at']
        indexes = [
            models.Index(fields=['eleve', 'statut']),
            models.Index(fields=['eleve', 'date_fin']),
            models.Index(fields=['statut', 'date_fin']),
        ]

    def __str__(self):
        return f"Informatique: {self.eleve} ({self.date_debut} → {self.date_fin})"

    @property
    def est_proche_expiration(self) -> bool:
        if not self.date_fin:
            return False
        today = timezone.localdate()
        delta = (self.date_fin - today).days
        return 0 <= delta <= (self.alerte_avant_jours or 7)

    @property
    def est_expire(self) -> bool:
        if not self.date_fin:
            return False
        return timezone.localdate() > self.date_fin

    @property
    def jours_restants(self) -> int:
        if not self.date_fin:
            return 0
        delta = (self.date_fin - timezone.localdate()).days
        return max(0, delta)
