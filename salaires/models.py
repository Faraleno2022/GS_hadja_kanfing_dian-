from django.db import models
from django.contrib.auth.models import User
from decimal import Decimal
from datetime import datetime
from eleves.models import Classe, Ecole


class TypeEnseignant(models.TextChoices):
    """Types d'enseignants avec modes de rémunération différents"""
    GARDERIE = 'GARDERIE', 'Garderie'
    MATERNELLE = 'MATERNELLE', 'Maternelle'
    PRIMAIRE = 'PRIMAIRE', 'Primaire'
    SECONDAIRE = 'SECONDAIRE', 'Secondaire (taux horaire)'
    ADMINISTRATEUR = 'ADMINISTRATEUR', 'Administrateur'


class StatutEnseignant(models.TextChoices):
    """Statut de l'enseignant"""
    ACTIF = 'ACTIF', 'Actif'
    CONGE = 'CONGE', 'En congé'
    SUSPENDU = 'SUSPENDU', 'Suspendu'
    DEMISSIONNAIRE = 'DEMISSIONNAIRE', 'Démissionnaire'


class Enseignant(models.Model):
    """Modèle représentant un enseignant"""
    
    # Informations personnelles
    nom = models.CharField(max_length=100, verbose_name="Nom")
    prenoms = models.CharField(max_length=150, verbose_name="Prénoms")
    telephone = models.CharField(max_length=20, blank=True, verbose_name="Téléphone")
    email = models.EmailField(blank=True, verbose_name="Email")
    adresse = models.TextField(blank=True, verbose_name="Adresse")
    
    # Informations professionnelles
    ecole = models.ForeignKey(Ecole, on_delete=models.CASCADE, verbose_name="École")
    type_enseignant = models.CharField(
        max_length=20, 
        choices=TypeEnseignant.choices,
        verbose_name="Type d'enseignant"
    )
    statut = models.CharField(
        max_length=20,
        choices=StatutEnseignant.choices,
        default=StatutEnseignant.ACTIF,
        verbose_name="Statut"
    )
    
    # Rémunération
    taux_horaire = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        null=True, 
        blank=True,
        verbose_name="Taux horaire (GNF)",
        help_text="Pour les enseignants du secondaire uniquement"
    )
    salaire_fixe = models.DecimalField(
        max_digits=12, 
        decimal_places=2, 
        null=True, 
        blank=True,
        verbose_name="Salaire fixe (GNF)",
        help_text="Pour garderie, maternelle, primaire et administrateurs"
    )
    heures_mensuelles = models.DecimalField(
        max_digits=6, 
        decimal_places=2, 
        null=True, 
        blank=True,
        verbose_name="Heures mensuelles",
        help_text="Nombre d'heures de travail prévues par mois (pour calcul précis du salaire)"
    )
    
    # Dates
    date_embauche = models.DateField(verbose_name="Date d'embauche")
    date_creation = models.DateTimeField(auto_now_add=True)
    date_modification = models.DateTimeField(auto_now=True)
    
    # Relations
    cree_par = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        related_name='enseignants_crees'
    )
    
    class Meta:
        verbose_name = "Enseignant"
        verbose_name_plural = "Enseignants"
        ordering = ['nom', 'prenoms']
    
    def __str__(self):
        return f"{self.nom} {self.prenoms}"
    
    @property
    def nom_complet(self):
        return f"{self.nom} {self.prenoms}"
    
    @property
    def est_taux_horaire(self):
        """Vérifie si l'enseignant est payé au taux horaire"""
        return self.type_enseignant == TypeEnseignant.SECONDAIRE
    
    @property
    def est_salaire_fixe(self):
        """Vérifie si l'enseignant a un salaire fixe"""
        return self.type_enseignant in [
            TypeEnseignant.GARDERIE,
            TypeEnseignant.MATERNELLE,
            TypeEnseignant.PRIMAIRE,
            TypeEnseignant.ADMINISTRATEUR
        ]
    
    def clean(self):
        from django.core.exceptions import ValidationError
        
        if self.est_taux_horaire and not self.taux_horaire:
            raise ValidationError({
                'taux_horaire': 'Le taux horaire est obligatoire pour les enseignants du secondaire.'
            })
        
        if self.est_salaire_fixe and not self.salaire_fixe:
            raise ValidationError({
                'salaire_fixe': f'Le salaire fixe est obligatoire pour les {self.get_type_enseignant_display().lower()}.'
            })
    
    def calculer_salaire_mensuel(self, heures_realisees=None):
        """
        Calcule le salaire mensuel de l'enseignant
        
        Args:
            heures_realisees: Nombre d'heures réellement travaillées (optionnel)
        
        Returns:
            Decimal: Salaire mensuel calculé
        """
        from decimal import Decimal
        
        if self.est_taux_horaire:
            # Pour les enseignants du secondaire (taux horaire)
            if not self.taux_horaire:
                return Decimal('0')
            
            # Utiliser les heures réalisées si fournies, sinon les heures mensuelles prévues
            heures = heures_realisees if heures_realisees is not None else (self.heures_mensuelles or Decimal('120'))
            return self.taux_horaire * heures
        
        elif self.est_salaire_fixe:
            # Pour les autres types (salaire fixe)
            return self.salaire_fixe or Decimal('0')
        
        return Decimal('0')
    
    def get_heures_mensuelles_defaut(self):
        """Retourne le nombre d'heures mensuelles par défaut selon le type d'enseignant"""
        from decimal import Decimal
        
        if self.type_enseignant == TypeEnseignant.SECONDAIRE:
            return Decimal('120')  # 120 heures par mois pour le secondaire
        else:
            return Decimal('160')  # 160 heures par mois pour les autres types
    
    @property
    def heures_mensuelles_effectives(self):
        """Retourne les heures mensuelles effectives (définies ou par défaut)"""
        return self.heures_mensuelles or self.get_heures_mensuelles_defaut()


class AffectationClasse(models.Model):
    """Affectation d'un enseignant à une classe"""
    
    enseignant = models.ForeignKey(
        Enseignant, 
        on_delete=models.CASCADE, 
        related_name='affectations',
        verbose_name="Enseignant"
    )
    classe = models.ForeignKey(
        Classe, 
        on_delete=models.CASCADE,
        verbose_name="Classe"
    )
    
    # Pour les enseignants du secondaire (taux horaire)
    heures_par_semaine = models.DecimalField(
        max_digits=5, 
        decimal_places=2, 
        null=True, 
        blank=True,
        verbose_name="Heures par semaine",
        help_text="Nombre d'heures d'enseignement par semaine dans cette classe"
    )
    
    # Matière enseignée (optionnel)
    matiere = models.CharField(
        max_length=100, 
        blank=True,
        verbose_name="Matière",
        help_text="Matière enseignée dans cette classe"
    )
    
    # Dates
    date_debut = models.DateField(verbose_name="Date de début")
    date_fin = models.DateField(null=True, blank=True, verbose_name="Date de fin")
    
    # Statut
    actif = models.BooleanField(default=True, verbose_name="Actif")
    
    date_creation = models.DateTimeField(auto_now_add=True)
    date_modification = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Affectation de classe"
        verbose_name_plural = "Affectations de classes"
        unique_together = ['enseignant', 'classe', 'date_debut']
        ordering = ['-date_debut']
    
    def __str__(self):
        return f"{self.enseignant.nom_complet} - {self.classe.nom}"
    
    def clean(self):
        from django.core.exceptions import ValidationError
        
        if self.enseignant.est_taux_horaire and not self.heures_par_semaine:
            raise ValidationError({
                'heures_par_semaine': 'Le nombre d\'heures par semaine est obligatoire pour les enseignants du secondaire.'
            })
        
        if self.date_fin and self.date_fin < self.date_debut:
            raise ValidationError({
                'date_fin': 'La date de fin ne peut pas être antérieure à la date de début.'
            })


class PeriodeSalaire(models.Model):
    """Période de calcul des salaires (mois)"""
    
    mois = models.IntegerField(
        choices=[(i, f"{i:02d}") for i in range(1, 13)],
        verbose_name="Mois"
    )
    annee = models.IntegerField(verbose_name="Année")
    ecole = models.ForeignKey(Ecole, on_delete=models.CASCADE, verbose_name="École")
    
    # Paramètres de la période
    nombre_semaines = models.DecimalField(
        max_digits=4, 
        decimal_places=2, 
        default=Decimal('4.33'),
        verbose_name="Nombre de semaines",
        help_text="Nombre moyen de semaines dans le mois (défaut: 4.33)"
    )
    
    # Statut
    cloturee = models.BooleanField(
        default=False, 
        verbose_name="Clôturée",
        help_text="Une fois clôturée, la période ne peut plus être modifiée"
    )
    
    # Dates
    date_creation = models.DateTimeField(auto_now_add=True)
    date_cloture = models.DateTimeField(null=True, blank=True)
    
    cree_par = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True,
        related_name='periodes_salaire_creees'
    )
    cloturee_par = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='periodes_salaire_cloturees'
    )
    
    class Meta:
        verbose_name = "Période de salaire"
        verbose_name_plural = "Périodes de salaire"
        unique_together = ['mois', 'annee', 'ecole']
        ordering = ['-annee', '-mois']
    
    def __str__(self):
        mois_noms = [
            '', 'Janvier', 'Février', 'Mars', 'Avril', 'Mai', 'Juin',
            'Juillet', 'Août', 'Septembre', 'Octobre', 'Novembre', 'Décembre'
        ]
        return f"{mois_noms[self.mois]} {self.annee} - {self.ecole.nom}"
    
    @property
    def nom_periode(self):
        mois_noms = [
            '', 'Janvier', 'Février', 'Mars', 'Avril', 'Mai', 'Juin',
            'Juillet', 'Août', 'Septembre', 'Octobre', 'Novembre', 'Décembre'
        ]
        return f"{mois_noms[self.mois]} {self.annee}"


class EtatSalaire(models.Model):
    """État de salaire d'un enseignant pour une période donnée"""
    
    enseignant = models.ForeignKey(
        Enseignant, 
        on_delete=models.CASCADE, 
        related_name='etats_salaire',
        verbose_name="Enseignant"
    )
    periode = models.ForeignKey(
        PeriodeSalaire, 
        on_delete=models.CASCADE, 
        related_name='etats_salaire',
        verbose_name="Période"
    )
    
    # Calculs pour enseignants au taux horaire
    total_heures = models.DecimalField(
        max_digits=8, 
        decimal_places=2, 
        null=True, 
        blank=True,
        verbose_name="Total heures",
        help_text="Total des heures enseignées dans le mois"
    )
    
    # Montants
    salaire_base = models.DecimalField(
        max_digits=12, 
        decimal_places=2,
        verbose_name="Salaire de base"
    )
    primes = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        default=Decimal('0'),
        verbose_name="Primes"
    )
    deductions = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        default=Decimal('0'),
        verbose_name="Déductions"
    )
    salaire_net = models.DecimalField(
        max_digits=12, 
        decimal_places=2,
        verbose_name="Salaire net"
    )
    
    # Statut
    valide = models.BooleanField(
        default=False, 
        verbose_name="Validé",
        help_text="État de salaire validé et prêt pour paiement"
    )
    paye = models.BooleanField(
        default=False, 
        verbose_name="Payé"
    )
    
    # Dates
    date_calcul = models.DateTimeField(auto_now_add=True)
    date_validation = models.DateTimeField(null=True, blank=True)
    date_paiement = models.DateTimeField(null=True, blank=True)
    
    # Utilisateurs
    calcule_par = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True,
        related_name='etats_salaire_calcules'
    )
    valide_par = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='etats_salaire_valides'
    )
    
    # Observations
    observations = models.TextField(
        blank=True,
        verbose_name="Observations"
    )
    
    class Meta:
        verbose_name = "État de salaire"
        verbose_name_plural = "États de salaire"
        unique_together = ['enseignant', 'periode']
        ordering = ['-periode__annee', '-periode__mois', 'enseignant__nom']
    
    def __str__(self):
        return f"{self.enseignant.nom_complet} - {self.periode.nom_periode}"
    
    def save(self, *args, **kwargs):
        # Calcul automatique du salaire net
        self.salaire_net = self.salaire_base + self.primes - self.deductions
        super().save(*args, **kwargs)
    
    @property
    def peut_etre_valide(self):
        """Vérifie si l'état de salaire peut être validé"""
        return not self.valide and not self.periode.cloturee
    
    @property
    def peut_etre_paye(self):
        """Vérifie si l'état de salaire peut être marqué comme payé"""
        return self.valide and not self.paye


class DetailHeuresClasse(models.Model):
    """Détail des heures par classe pour un état de salaire"""
    
    etat_salaire = models.ForeignKey(
        EtatSalaire, 
        on_delete=models.CASCADE, 
        related_name='details_heures',
        verbose_name="État de salaire"
    )
    affectation_classe = models.ForeignKey(
        AffectationClasse, 
        on_delete=models.CASCADE,
        verbose_name="Affectation classe"
    )
    
    heures_prevues = models.DecimalField(
        max_digits=6, 
        decimal_places=2,
        verbose_name="Heures prévues",
        help_text="Heures prévues selon l'affectation"
    )
    heures_realisees = models.DecimalField(
        max_digits=6, 
        decimal_places=2,
        verbose_name="Heures réalisées",
        help_text="Heures effectivement enseignées"
    )
    
    taux_horaire_applique = models.DecimalField(
        max_digits=10, 
        decimal_places=2,
        verbose_name="Taux horaire appliqué"
    )
    
    montant = models.DecimalField(
        max_digits=10, 
        decimal_places=2,
        verbose_name="Montant"
    )
    
    class Meta:
        verbose_name = "Détail heures par classe"
        verbose_name_plural = "Détails heures par classe"
        unique_together = ['etat_salaire', 'affectation_classe']
    
    def __str__(self):
        return f"{self.etat_salaire.enseignant.nom_complet} - {self.affectation_classe.classe.nom}"
    
    def save(self, *args, **kwargs):
        # Calcul automatique du montant
        self.montant = self.heures_realisees * self.taux_horaire_applique
        super().save(*args, **kwargs)
