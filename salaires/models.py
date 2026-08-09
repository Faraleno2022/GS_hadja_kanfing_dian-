from django.db import models
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from decimal import Decimal
from datetime import datetime
from eleves.models import Classe, Ecole
from synchronisation.mixins import SyncTrackedModel


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


class Enseignant(SyncTrackedModel):
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
        erreurs = {}

        if self.est_taux_horaire and (self.taux_horaire is None or self.taux_horaire <= 0):
            erreurs['taux_horaire'] = (
                'Le taux horaire doit être strictement positif pour les enseignants du secondaire.'
            )

        if self.est_salaire_fixe and (self.salaire_fixe is None or self.salaire_fixe <= 0):
            erreurs['salaire_fixe'] = (
                f'Le salaire fixe doit être strictement positif pour les '
                f'{self.get_type_enseignant_display().lower()}.'
            )

        if self.heures_mensuelles is not None and self.heures_mensuelles < 0:
            erreurs['heures_mensuelles'] = 'Les heures mensuelles ne peuvent pas être négatives.'

        if erreurs:
            raise ValidationError(erreurs)

    def save(self, *args, **kwargs):
        exclusions = ['cree_par'] if self.cree_par_id is None else None
        self.full_clean(exclude=exclusions)
        return super().save(*args, **kwargs)
    
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
            
            # Un salaire horaire repose uniquement sur le pointage réel. Sans
            # heures réalisées, aucun montant n'est dû.
            heures = heures_realisees if heures_realisees is not None else Decimal('0')
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


class AffectationClasse(SyncTrackedModel):
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
        erreurs = {}

        if self.enseignant_id and self.enseignant.est_taux_horaire and (
            self.heures_par_semaine is None or self.heures_par_semaine <= 0
        ):
            erreurs['heures_par_semaine'] = (
                'Le nombre d\'heures par semaine doit être strictement positif '
                'pour les enseignants du secondaire.'
            )

        if self.heures_par_semaine is not None and self.heures_par_semaine < 0:
            erreurs['heures_par_semaine'] = 'Les heures par semaine ne peuvent pas être négatives.'

        if self.date_fin and self.date_fin < self.date_debut:
            erreurs['date_fin'] = 'La date de fin ne peut pas être antérieure à la date de début.'

        if self.classe_id and self.enseignant_id and self.classe.ecole_id != self.enseignant.ecole_id:
            erreurs['classe'] = 'La classe doit appartenir à la même école que l\'enseignant.'

        if erreurs:
            raise ValidationError(erreurs)

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)


class PeriodeSalaire(SyncTrackedModel):
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

    def clean(self):
        if self.nombre_semaines is None or self.nombre_semaines <= 0:
            raise ValidationError({
                'nombre_semaines': 'Le nombre de semaines doit être strictement positif.'
            })

    def save(self, *args, **kwargs):
        exclusions = ['cree_par'] if self.cree_par_id is None else None
        self.full_clean(exclude=exclusions)
        return super().save(*args, **kwargs)


class EtatSalaire(SyncTrackedModel):
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
    taux_horaire_applique = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name="Taux horaire appliqué",
        help_text="Taux figé au moment du calcul pour conserver l'historique de paie",
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

    def clean(self):
        erreurs = {}
        champs_positifs = {
            'salaire_base': self.salaire_base,
            'primes': self.primes,
            'deductions': self.deductions,
            'total_heures': self.total_heures,
            'taux_horaire_applique': self.taux_horaire_applique,
        }
        for champ, valeur in champs_positifs.items():
            if valeur is not None and valeur < 0:
                erreurs[champ] = 'Cette valeur ne peut pas être négative.'

        salaire_base = self.salaire_base or Decimal('0')
        primes = self.primes or Decimal('0')
        deductions = self.deductions or Decimal('0')
        if deductions > salaire_base + primes:
            erreurs['deductions'] = 'Les retenues ne peuvent pas dépasser le salaire brut.'

        if self.enseignant_id and self.periode_id:
            if self.enseignant.ecole_id != self.periode.ecole_id:
                erreurs['enseignant'] = 'L\'enseignant et la période doivent appartenir à la même école.'

        if erreurs:
            raise ValidationError(erreurs)

    def save(self, *args, **kwargs):
        # Calcul automatique du salaire net
        self.salaire_net = (
            (self.salaire_base or Decimal('0'))
            + (self.primes or Decimal('0'))
            - (self.deductions or Decimal('0'))
        )
        exclusions = ['calcule_par'] if self.calcule_par_id is None else None
        self.full_clean(exclude=exclusions)
        return super().save(*args, **kwargs)
    
    @property
    def peut_etre_valide(self):
        """Vérifie si l'état de salaire peut être validé"""
        return not self.valide and not self.periode.cloturee
    
    @property
    def peut_etre_paye(self):
        """Vérifie si l'état de salaire peut être marqué comme payé"""
        return self.valide and not self.paye


class PresenceEnseignant(SyncTrackedModel):
    """Pointage de présence quotidienne des enseignants"""
    
    STATUT_CHOICES = [
        ('PRESENT', 'Présent'),
        ('ABSENT', 'Absent'),
        ('RETARD', 'Retard'),
        ('CONGE', 'Congé'),
        ('MALADIE', 'Maladie'),
        ('PERMISSION', 'Permission'),
    ]
    
    enseignant = models.ForeignKey(
        Enseignant,
        on_delete=models.CASCADE,
        related_name='presences',
        verbose_name="Enseignant"
    )
    date = models.DateField(verbose_name="Date")
    statut = models.CharField(
        max_length=20,
        choices=STATUT_CHOICES,
        default='PRESENT',
        verbose_name="Statut"
    )
    
    # Heures de pointage
    heure_arrivee = models.TimeField(
        null=True,
        blank=True,
        verbose_name="Heure d'arrivée"
    )
    heure_depart = models.TimeField(
        null=True,
        blank=True,
        verbose_name="Heure de départ"
    )
    
    # Heures travaillées
    heures_travaillees = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name="Heures travaillées",
        help_text="Calculé automatiquement ou saisi manuellement"
    )
    
    # Observations
    observations = models.TextField(
        blank=True,
        verbose_name="Observations",
        help_text="Motif d'absence, retard, etc."
    )
    
    # Justificatif
    justifie = models.BooleanField(
        default=False,
        verbose_name="Justifié",
        help_text="Absence ou retard justifié"
    )
    
    # Métadonnées
    date_creation = models.DateTimeField(auto_now_add=True)
    date_modification = models.DateTimeField(auto_now=True)
    pointe_par = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='pointages_effectues',
        verbose_name="Pointé par"
    )
    
    class Meta:
        verbose_name = "Présence enseignant"
        verbose_name_plural = "Présences enseignants"
        unique_together = ['enseignant', 'date']
        ordering = ['-date', 'enseignant__nom']
        indexes = [
            models.Index(fields=['enseignant', 'date']),
            models.Index(fields=['date', 'statut']),
        ]
    
    def __str__(self):
        return f"{self.enseignant.nom_complet} - {self.date} - {self.get_statut_display()}"
    
    def _calculer_heures_depuis_pointage(self):
        # Calcul automatique des heures travaillées si arrivée et départ fournis
        if self.heure_arrivee and self.heure_depart:
            from datetime import datetime, timedelta
            arrivee = datetime.combine(self.date, self.heure_arrivee)
            depart = datetime.combine(self.date, self.heure_depart)
            
            # Si départ avant arrivée, c'est le lendemain
            if depart < arrivee:
                depart += timedelta(days=1)
            
            delta = depart - arrivee
            # Toujours recalculer les heures travaillées
            self.heures_travaillees = Decimal(str(round(delta.total_seconds() / 3600, 2)))
        elif not self.heure_arrivee or not self.heure_depart:
            # Si pas d'heures d'arrivée/départ, mettre à 0 si non défini
            if self.heures_travaillees is None:
                self.heures_travaillees = Decimal('0')

    def clean(self):
        erreurs = {}
        if bool(self.heure_arrivee) != bool(self.heure_depart):
            erreurs['heure_depart'] = (
                "L'heure d'arrivée et l'heure de départ doivent être renseignées ensemble."
            )
        if self.heures_travaillees is not None:
            if self.heures_travaillees < 0:
                erreurs['heures_travaillees'] = 'Les heures travaillées ne peuvent pas être négatives.'
            elif self.heures_travaillees > 24:
                erreurs['heures_travaillees'] = 'Un pointage journalier ne peut pas dépasser 24 heures.'
            elif self.statut not in ('PRESENT', 'RETARD') and self.heures_travaillees > 0:
                erreurs['heures_travaillees'] = (
                    'Un statut non travaillé ne peut pas contenir des heures réalisées.'
                )
        if erreurs:
            raise ValidationError(erreurs)

    def save(self, *args, **kwargs):
        self._calculer_heures_depuis_pointage()
        exclusions = ['pointe_par'] if self.pointe_par_id is None else None
        self.full_clean(exclude=exclusions)
        return super().save(*args, **kwargs)
    
    @property
    def est_present(self):
        """Vérifie si l'enseignant était présent"""
        return self.statut == 'PRESENT'
    
    @property
    def est_absent_injustifie(self):
        """Vérifie si c'est une absence injustifiée"""
        return self.statut == 'ABSENT' and not self.justifie


class DetailHeuresClasse(SyncTrackedModel):
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

    def clean(self):
        erreurs = {}
        for champ in ('heures_prevues', 'heures_realisees', 'taux_horaire_applique'):
            valeur = getattr(self, champ)
            if valeur is not None and valeur < 0:
                erreurs[champ] = 'Cette valeur ne peut pas être négative.'
        if erreurs:
            raise ValidationError(erreurs)

    def save(self, *args, **kwargs):
        # Calcul automatique du montant
        self.montant = self.heures_realisees * self.taux_horaire_applique
        self.full_clean()
        return super().save(*args, **kwargs)
