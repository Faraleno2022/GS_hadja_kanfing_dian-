import uuid
from decimal import Decimal

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Sum
from django.utils import timezone

from synchronisation.mixins import SyncTrackedModel


class FournitureScolaire(SyncTrackedModel):
    """Produit scolaire acheté puis revendu par un établissement."""

    CATEGORIE_CHOICES = [
        ('CAHIER_PAPIER', 'Cahiers et papier'),
        ('ECRITURE', 'Stylos et écriture'),
        ('MANUEL', 'Manuels et livres'),
        ('GEOMETRIE', 'Géométrie et dessin'),
        ('SAC', 'Sacs et cartables'),
        ('UNIFORME', 'Uniformes'),
        ('ACCESSOIRE', 'Accessoires scolaires'),
        ('AUTRE', 'Autre'),
    ]
    UNITE_CHOICES = [
        ('PIECE', 'Pièce'),
        ('PAQUET', 'Paquet'),
        ('BOITE', 'Boîte'),
        ('DOUZAINE', 'Douzaine'),
        ('CARTON', 'Carton'),
    ]

    ecole = models.ForeignKey(
        'eleves.Ecole',
        on_delete=models.PROTECT,
        related_name='fournitures_scolaires',
        verbose_name='Établissement',
    )
    reference = models.CharField(
        max_length=50,
        blank=True,
        verbose_name='Référence',
        help_text='Laissez vide pour générer une référence automatiquement.',
    )
    nom = models.CharField(max_length=200, verbose_name='Produit')
    categorie = models.CharField(
        max_length=30,
        choices=CATEGORIE_CHOICES,
        default='AUTRE',
        verbose_name='Catégorie',
    )
    unite = models.CharField(
        max_length=20,
        choices=UNITE_CHOICES,
        default='PIECE',
        verbose_name='Unité',
    )
    description = models.TextField(blank=True, verbose_name='Description')

    quantite_stock = models.PositiveIntegerField(
        default=0,
        verbose_name='Quantité mise en stock',
    )
    stock_minimum = models.PositiveIntegerField(
        default=0,
        verbose_name='Seuil d’alerte',
    )
    prix_achat_unitaire = models.DecimalField(
        max_digits=15,
        decimal_places=0,
        default=Decimal('0'),
        verbose_name="Prix d'achat unitaire (GNF)",
    )
    prix_vente_unitaire = models.DecimalField(
        max_digits=15,
        decimal_places=0,
        default=Decimal('0'),
        verbose_name='Prix de vente unitaire (GNF)',
    )

    actif = models.BooleanField(default=True, verbose_name='Actif')
    cree_par = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='fournitures_scolaires_creees',
        verbose_name='Créé par',
    )
    date_creation = models.DateTimeField(auto_now_add=True)
    date_modification = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Fourniture scolaire'
        verbose_name_plural = 'Fournitures scolaires'
        ordering = ['nom', 'reference']
        constraints = [
            models.UniqueConstraint(
                fields=['ecole', 'reference'],
                name='uniq_fourniture_ref_ecole',
            ),
        ]
        indexes = [
            models.Index(fields=['ecole', 'actif'], name='dep_four_ecole_actif_idx'),
            models.Index(fields=['ecole', 'nom'], name='dep_four_ecole_nom_idx'),
        ]

    def __str__(self):
        return f'{self.reference} - {self.nom}'

    def clean(self):
        super().clean()
        self.reference = (self.reference or '').strip().upper()
        if self.prix_achat_unitaire is not None and self.prix_achat_unitaire < 0:
            raise ValidationError({'prix_achat_unitaire': 'Le prix ne peut pas être négatif.'})
        if self.prix_vente_unitaire is not None and self.prix_vente_unitaire < 0:
            raise ValidationError({'prix_vente_unitaire': 'Le prix ne peut pas être négatif.'})
        if self.pk and self.quantite_stock < self.quantite_vendue:
            raise ValidationError({
                'quantite_stock': (
                    f'Le stock ne peut pas être inférieur aux {self.quantite_vendue} '
                    'unités déjà vendues.'
                )
            })

    @property
    def quantite_vendue(self):
        if not self.pk:
            return 0
        return self.ventes.aggregate(total=Sum('quantite'))['total'] or 0

    @property
    def quantite_restante(self):
        return max(0, (self.quantite_stock or 0) - self.quantite_vendue)

    @property
    def valeur_stock_initial(self):
        return Decimal(self.quantite_stock or 0) * Decimal(self.prix_achat_unitaire or 0)

    @property
    def chiffre_affaires(self):
        if not self.pk:
            return Decimal('0')
        return self.ventes.aggregate(total=Sum('montant_total'))['total'] or Decimal('0')

    @property
    def solde(self):
        cout_vendu = Decimal(self.quantite_vendue) * Decimal(self.prix_achat_unitaire or 0)
        return self.chiffre_affaires - cout_vendu

    @property
    def alerte_stock(self):
        return self.quantite_restante <= (self.stock_minimum or 0)


class VenteFourniture(SyncTrackedModel):
    """Vente d'une quantité d'un produit scolaire."""

    ecole = models.ForeignKey(
        'eleves.Ecole',
        on_delete=models.PROTECT,
        related_name='ventes_fournitures',
        verbose_name='Établissement',
    )
    numero_vente = models.CharField(
        max_length=30,
        unique=True,
        blank=True,
        verbose_name='N° vente',
    )
    produit = models.ForeignKey(
        FournitureScolaire,
        on_delete=models.PROTECT,
        related_name='ventes',
        verbose_name='Produit',
    )
    quantite = models.PositiveIntegerField(verbose_name='Quantité vendue')
    prix_vente_unitaire = models.DecimalField(
        max_digits=15,
        decimal_places=0,
        verbose_name='Prix de vente unitaire (GNF)',
    )
    montant_total = models.DecimalField(
        max_digits=18,
        decimal_places=0,
        default=Decimal('0'),
        editable=False,
        verbose_name='Montant total (GNF)',
    )
    client = models.CharField(
        max_length=200,
        blank=True,
        verbose_name='Client / Acheteur',
    )
    date_vente = models.DateField(default=timezone.localdate, verbose_name='Date de vente')
    observations = models.TextField(blank=True, verbose_name='Observations')
    cree_par = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='ventes_fournitures_creees',
        verbose_name='Créé par',
    )
    date_creation = models.DateTimeField(auto_now_add=True)
    date_modification = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Vente de fourniture'
        verbose_name_plural = 'Ventes de fournitures'
        ordering = ['-date_vente', '-date_creation']
        indexes = [
            models.Index(fields=['ecole', 'date_vente'], name='dep_vente_ecole_date_idx'),
            models.Index(fields=['produit', 'date_vente'], name='dep_vente_prod_date_idx'),
        ]

    def __str__(self):
        return f'{self.numero_vente} - {self.produit.nom} ({self.quantite})'

    def clean(self):
        super().clean()
        if self.quantite is not None and self.quantite <= 0:
            raise ValidationError({'quantite': 'La quantité vendue doit être supérieure à zéro.'})
        if self.prix_vente_unitaire is not None and self.prix_vente_unitaire <= 0:
            raise ValidationError({
                'prix_vente_unitaire': 'Le prix de vente doit être supérieur à zéro.'
            })
        if self.produit_id and self.ecole_id and self.produit.ecole_id != self.ecole_id:
            raise ValidationError({'produit': "Ce produit n'appartient pas à cet établissement."})
        if self.produit_id and self.quantite:
            deja_vendu = (
                self.produit.ventes.exclude(pk=self.pk).aggregate(total=Sum('quantite'))['total']
                or 0
            )
            disponible = max(0, self.produit.quantite_stock - deja_vendu)
            if self.quantite > disponible:
                raise ValidationError({
                    'quantite': f'Stock restant insuffisant : {disponible} disponible(s).'
                })

    def save(self, *args, **kwargs):
        if not self.numero_vente:
            self.numero_vente = f"VTE-{timezone.localdate():%Y%m%d}-{uuid.uuid4().hex[:8].upper()}"
        if self.produit_id and not self.ecole_id:
            self.ecole_id = self.produit.ecole_id
        self.montant_total = (
            Decimal(self.quantite or 0) * Decimal(self.prix_vente_unitaire or 0)
        )
        super().save(*args, **kwargs)

    @property
    def marge(self):
        cout = Decimal(self.quantite or 0) * Decimal(self.produit.prix_achat_unitaire or 0)
        return self.montant_total - cout
