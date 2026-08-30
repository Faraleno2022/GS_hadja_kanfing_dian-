from decimal import Decimal

from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, RegexValidator
from django.db import IntegrityError, models
from django.utils import timezone
from eleves.models import Ecole, Eleve
from synchronisation.mixins import SyncTrackedModel


ANNEE_SCOLAIRE_VALIDATOR = RegexValidator(
    regex=r'^\d{4}-\d{4}$',
    message="L'année scolaire doit être au format AAAA-AAAA.",
)


class GrilleTarifaireBus(SyncTrackedModel):
    """Tarifs annuels du bus définis par une école et par zone."""

    ecole = models.ForeignKey(
        Ecole,
        on_delete=models.CASCADE,
        related_name='grilles_tarifaires_bus',
    )
    zone = models.CharField(
        max_length=100,
        verbose_name="Zone / circuit",
        help_text="Exemple : Ratoma, Sonfonia ou Circuit A.",
    )
    annee_scolaire = models.CharField(
        max_length=9,
        validators=[ANNEE_SCOLAIRE_VALIDATOR],
        db_index=True,
        verbose_name="Année scolaire",
    )
    tranche_1 = models.DecimalField(
        max_digits=10,
        decimal_places=0,
        validators=[MinValueValidator(Decimal('0'))],
        verbose_name="1ère tranche (GNF)",
    )
    tranche_2 = models.DecimalField(
        max_digits=10,
        decimal_places=0,
        validators=[MinValueValidator(Decimal('0'))],
        verbose_name="2ème tranche (GNF)",
    )
    tranche_3 = models.DecimalField(
        max_digits=10,
        decimal_places=0,
        validators=[MinValueValidator(Decimal('0'))],
        verbose_name="3ème tranche (GNF)",
    )
    date_echeance_tranche_1 = models.DateField(
        null=True, blank=True, verbose_name="Échéance de la 1ère tranche"
    )
    date_echeance_tranche_2 = models.DateField(
        null=True, blank=True, verbose_name="Échéance de la 2ème tranche"
    )
    date_echeance_tranche_3 = models.DateField(
        null=True, blank=True, verbose_name="Échéance de la 3ème tranche"
    )
    actif = models.BooleanField(default=True, db_index=True, verbose_name="Grille active")
    cree_par = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='grilles_bus_creees',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-annee_scolaire', 'zone']
        verbose_name = "Grille tarifaire bus"
        verbose_name_plural = "Grilles tarifaires bus"
        constraints = [
            models.UniqueConstraint(
                fields=['ecole', 'zone', 'annee_scolaire'],
                name='bus_grille_unique_ecole_zone_annee',
            ),
        ]
        indexes = [
            models.Index(fields=['ecole', 'annee_scolaire', 'actif']),
        ]

    def __str__(self):
        return f"{self.zone} - {self.annee_scolaire} ({self.ecole})"

    @property
    def montant_annuel(self):
        return (self.tranche_1 or 0) + (self.tranche_2 or 0) + (self.tranche_3 or 0)

    def montant_pour(self, periodicite):
        return {
            'T1': self.tranche_1,
            'T2': self.tranche_2,
            'T3': self.tranche_3,
        }.get(periodicite, Decimal('0'))

    def echeance_pour(self, periodicite):
        return {
            'T1': self.date_echeance_tranche_1,
            'T2': self.date_echeance_tranche_2,
            'T3': self.date_echeance_tranche_3,
        }.get(periodicite)


class AbonnementBus(SyncTrackedModel):
    class Statut(models.TextChoices):
        ACTIF = 'ACTIF', 'Actif'
        EXPIRE = 'EXPIRE', 'Expiré'
        SUSPENDU = 'SUSPENDU', 'Suspendu'

    class Periodicite(models.TextChoices):
        MENSUEL = 'MENSUEL', 'Mensuel'
        ANNUEL = 'ANNUEL', 'Annuel'
        TRANCHE_1 = 'T1', "1ère Tranche"
        TRANCHE_2 = 'T2', "2ème Tranche"
        TRANCHE_3 = 'T3', "3ème Tranche"

    eleve = models.ForeignKey(Eleve, on_delete=models.CASCADE, related_name='abonnements_bus')
    grille = models.ForeignKey(
        GrilleTarifaireBus,
        on_delete=models.SET_NULL,
        related_name='versements',
        null=True,
        blank=True,
        verbose_name="Grille tarifaire",
    )
    annee_scolaire = models.CharField(
        max_length=9,
        validators=[ANNEE_SCOLAIRE_VALIDATOR],
        blank=True,
        db_index=True,
        verbose_name="Année scolaire",
    )
    mode_paiement = models.ForeignKey(
        'paiements.ModePaiement',
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='paiements_bus',
        verbose_name="Mode de paiement",
    )
    numero_recu = models.CharField(
        max_length=20,
        unique=True,
        null=True,
        blank=True,
        verbose_name="Numéro de reçu",
    )
    reference_externe = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="Référence externe du paiement",
        help_text="Numéro du reçu externe, transaction Mobile Money, chèque, etc.",
    )
    montant = models.DecimalField(max_digits=10, decimal_places=0)
    periodicite = models.CharField(max_length=10, choices=Periodicite.choices, default=Periodicite.MENSUEL)
    date_debut = models.DateField(default=timezone.localdate)
    date_expiration = models.DateField(db_index=True)
    statut = models.CharField(max_length=10, choices=Statut.choices, default=Statut.ACTIF, db_index=True)

    # Alertes / relances
    alerte_avant_jours = models.PositiveIntegerField(default=7)
    derniere_relance = models.DateTimeField(null=True, blank=True)

    # Infos logistiques
    zone = models.CharField(max_length=100, blank=True)
    itineraire = models.CharField(max_length=200, blank=True)
    point_arret = models.CharField(max_length=150, blank=True)

    # Contact relance
    contact_parent = models.CharField(max_length=100, blank=True)

    observations = models.TextField(blank=True)

    cree_par = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='paiements_bus_crees',
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-updated_at']
        verbose_name = 'Abonnement bus'
        verbose_name_plural = 'Abonnements bus'
        indexes = [
            models.Index(fields=['eleve', 'statut']),
            models.Index(fields=['eleve', 'date_expiration']),
            models.Index(fields=['statut', 'date_expiration']),
            models.Index(fields=['eleve', 'grille', 'periodicite']),
        ]

    def __str__(self):
        return f"Bus: {self.eleve} ({self.get_periodicite_display()})"

    def save(self, *args, **kwargs):
        champs_automatiques = set()
        if self.grille_id:
            self.annee_scolaire = self.grille.annee_scolaire
            champs_automatiques.add('annee_scolaire')
            if not self.zone:
                self.zone = self.grille.zone
                champs_automatiques.add('zone')
        if not self.annee_scolaire and self.eleve_id:
            self.annee_scolaire = (
                getattr(getattr(self.eleve, 'classe', None), 'annee_scolaire', '') or ''
            )
            champs_automatiques.add('annee_scolaire')

        if not self.numero_recu:
            champs_automatiques.add('numero_recu')
            if kwargs.get('update_fields') is not None:
                kwargs['update_fields'] = set(kwargs['update_fields']) | champs_automatiques
            prefix = f"BUS{timezone.localdate().year}"
            for _ in range(10):
                dernier = (
                    AbonnementBus.objects
                    .filter(numero_recu__startswith=prefix)
                    .order_by('-numero_recu')
                    .first()
                )
                try:
                    sequence = int(dernier.numero_recu[-4:]) + 1 if dernier else 1
                except (TypeError, ValueError):
                    sequence = 1
                self.numero_recu = f"{prefix}{sequence:04d}"
                try:
                    return super().save(*args, **kwargs)
                except IntegrityError:
                    self.numero_recu = None
                    continue
            raise ValueError("Impossible de générer un numéro de reçu bus unique.")
        if kwargs.get('update_fields') is not None and champs_automatiques:
            kwargs['update_fields'] = set(kwargs['update_fields']) | champs_automatiques
        return super().save(*args, **kwargs)

    @property
    def est_proche_expiration(self) -> bool:
        if not self.date_expiration:
            return False
        today = timezone.localdate()
        delta = (self.date_expiration - today).days
        return 0 <= delta <= (self.alerte_avant_jours or 7)

    @property
    def est_expire(self) -> bool:
        if not self.date_expiration:
            return False
        return timezone.localdate() > self.date_expiration


class AbonnementCantine(SyncTrackedModel):
    """Modèle pour gérer les abonnements à la cantine scolaire"""
    
    class Statut(models.TextChoices):
        ACTIF = 'ACTIF', 'Actif'
        EXPIRE = 'EXPIRE', 'Expiré'
        SUSPENDU = 'SUSPENDU', 'Suspendu'
    
    class Periodicite(models.TextChoices):
        JOURNALIER = 'JOURNALIER', 'Journalier'
        HEBDOMADAIRE = 'HEBDOMADAIRE', 'Hebdomadaire'
        MENSUEL = 'MENSUEL', 'Mensuel'
        TRIMESTRIEL = 'TRIMESTRIEL', 'Trimestriel'
        ANNUEL = 'ANNUEL', 'Annuel'
    
    class TypeRepas(models.TextChoices):
        DEJEUNER = 'DEJEUNER', 'Déjeuner uniquement'
        GOUTER = 'GOUTER', 'Goûter uniquement'
        COMPLET = 'COMPLET', 'Déjeuner + Goûter'
    
    eleve = models.ForeignKey(Eleve, on_delete=models.CASCADE, related_name='abonnements_cantine')
    montant = models.DecimalField(max_digits=10, decimal_places=0, verbose_name="Montant (GNF)")
    reference_externe = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="Référence externe du paiement",
        help_text="Numéro du reçu externe, transaction Mobile Money, chèque, etc.",
    )
    periodicite = models.CharField(max_length=15, choices=Periodicite.choices, default=Periodicite.MENSUEL)
    type_repas = models.CharField(max_length=10, choices=TypeRepas.choices, default=TypeRepas.DEJEUNER)
    
    date_debut = models.DateField(default=timezone.localdate, verbose_name="Date de début")
    date_expiration = models.DateField(db_index=True, verbose_name="Date d'expiration")
    statut = models.CharField(max_length=10, choices=Statut.choices, default=Statut.ACTIF, db_index=True)
    
    # Alertes / relances
    alerte_avant_jours = models.PositiveIntegerField(default=7, verbose_name="Alerte avant (jours)")
    derniere_relance = models.DateTimeField(null=True, blank=True, verbose_name="Dernière relance")
    
    # Régime alimentaire et allergies
    regime_alimentaire = models.CharField(
        max_length=100, 
        blank=True, 
        verbose_name="Régime alimentaire",
        help_text="Ex: Végétarien, Sans porc, Halal, etc."
    )
    allergies = models.TextField(blank=True, verbose_name="Allergies alimentaires")
    
    # Contact relance
    contact_parent = models.CharField(max_length=100, blank=True, verbose_name="Contact parent")
    
    observations = models.TextField(blank=True, verbose_name="Observations")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-updated_at']
        verbose_name = 'Abonnement cantine'
        verbose_name_plural = 'Abonnements cantine'
        indexes = [
            models.Index(fields=['eleve', 'statut']),
            models.Index(fields=['eleve', 'date_expiration']),
            models.Index(fields=['statut', 'date_expiration']),
        ]
    
    def __str__(self):
        return f"Cantine: {self.eleve} ({self.get_periodicite_display()})"
    
    @property
    def est_proche_expiration(self) -> bool:
        """Vérifie si l'abonnement est proche de l'expiration"""
        if not self.date_expiration:
            return False
        today = timezone.localdate()
        delta = (self.date_expiration - today).days
        return 0 <= delta <= (self.alerte_avant_jours or 7)
    
    @property
    def est_expire(self) -> bool:
        """Vérifie si l'abonnement est expiré"""
        if not self.date_expiration:
            return False
        return timezone.localdate() > self.date_expiration
    
    @property
    def jours_restants(self) -> int:
        """Retourne le nombre de jours restants avant expiration"""
        if not self.date_expiration:
            return 0
        today = timezone.localdate()
        delta = (self.date_expiration - today).days
        return max(0, delta)
