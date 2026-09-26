from django.db import models
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from decimal import Decimal, ROUND_HALF_UP
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


NIVEAUX_GARDERIE = {'GARDERIE'}
NIVEAUX_MATERNELLE = {
    'TOUTE_PETITE_SECTION',
    'PETITE_SECTION',
    'MOYENNE_SECTION',
    'GRANDE_SECTION',
    'MATERNELLE',
}
NIVEAUX_PRIMAIRE = {
    'PRIMAIRE_1', 'PRIMAIRE_2', 'PRIMAIRE_3',
    'PRIMAIRE_4', 'PRIMAIRE_5', 'PRIMAIRE_6',
}
NIVEAUX_SECONDAIRE = {
    'COLLEGE_7', 'COLLEGE_8', 'COLLEGE_9', 'COLLEGE_10',
    'LYCEE_11', 'LYCEE_12', 'TERMINALE',
}

NIVEAUX_PAR_TYPE_ENSEIGNANT = {
    TypeEnseignant.GARDERIE: NIVEAUX_GARDERIE,
    TypeEnseignant.MATERNELLE: NIVEAUX_MATERNELLE,
    TypeEnseignant.PRIMAIRE: NIVEAUX_PRIMAIRE,
    TypeEnseignant.SECONDAIRE: NIVEAUX_SECONDAIRE,
}


class StatutEnseignant(models.TextChoices):
    """Statut de l'enseignant"""
    ACTIF = 'ACTIF', 'Actif'
    CONGE = 'CONGE', 'En congé'
    SUSPENDU = 'SUSPENDU', 'Suspendu'
    DEMISSIONNAIRE = 'DEMISSIONNAIRE', 'Démissionnaire'


class ModeCalculHoraire(models.TextChoices):
    """Source des heures utilisées pour payer un enseignant du secondaire."""

    POINTAGE = 'POINTAGE', 'Pointage arrivée / départ'
    MENSUEL = 'MENSUEL', 'Total mensuel global'
    MANUEL = 'MANUEL', "Saisie manuelle sur l'état"
    HEBDOMADAIRE = 'HEBDO', 'Emploi du temps hebdomadaire (L à S)'


JOURS_SEMAINE_PAIE = (
    ('lundi', 'L', 'Lundi'),
    ('mardi', 'M', 'Mardi'),
    ('mercredi', 'M', 'Mercredi'),
    ('jeudi', 'J', 'Jeudi'),
    ('vendredi', 'V', 'Vendredi'),
    ('samedi', 'S', 'Samedi'),
)


def _heures_jour(libelle):
    return models.DecimalField(
        max_digits=4,
        decimal_places=2,
        default=Decimal('0'),
        verbose_name=f"Heures du {libelle.lower()}",
        validators=[MinValueValidator(Decimal('0')), MaxValueValidator(Decimal('24'))],
    )


def _occurrences_jour(libelle):
    return models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        verbose_name=f"Nombre de {libelle.lower()}s travaillés",
        validators=[MaxValueValidator(6)],
    )


class Enseignant(SyncTrackedModel):
    """Modèle représentant un enseignant"""

    # Informations personnelles
    nom = models.CharField(max_length=100, verbose_name="Nom")
    prenoms = models.CharField(max_length=150, verbose_name="Prénoms")
    telephone = models.CharField(max_length=20, blank=True, verbose_name="Téléphone")
    email = models.EmailField(blank=True, verbose_name="Email")
    adresse = models.TextField(blank=True, verbose_name="Adresse")

    photo = models.ImageField(upload_to="enseignants/photos/%Y/%m/", blank=True, verbose_name="Photo")

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
    classe_principale = models.ForeignKey(
        Classe,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='enseignants_principaux',
        verbose_name="Classe principale",
        help_text=(
            "Classe tenue par l'enseignant en garderie, maternelle ou primaire."
        ),
    )
    fonction = models.CharField(
        max_length=150,
        blank=True,
        verbose_name="Fonction administrative",
        help_text="Ex. Directeur, comptable, secrétaire ou surveillant général.",
    )

    # Rémunération
    taux_horaire = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name="Taux horaire (GNF)",
        help_text="Pour les enseignants du secondaire uniquement",
        validators=[MinValueValidator(Decimal('0'))],
    )
    mode_calcul_horaire = models.CharField(
        max_length=10,
        choices=ModeCalculHoraire.choices,
        default=ModeCalculHoraire.POINTAGE,
        verbose_name="Mode de calcul des heures",
        help_text=(
            "Pour le secondaire : utiliser les pointages quotidiens ou un total "
            "mensuel saisi globalement."
        ),
    )
    salaire_fixe = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name="Salaire fixe (GNF)",
        help_text="Pour garderie, maternelle, primaire et administrateurs",
        validators=[MinValueValidator(Decimal('0'))],
    )
    heures_mensuelles = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name="Heures mensuelles",
        help_text="Total mensuel global utilisé pour calculer le salaire horaire",
        validators=[
            MinValueValidator(Decimal('0')),
            MaxValueValidator(Decimal('200')),
        ],
    )

    # Identification et primes récurrentes (état de salaire / bulletin de paie)
    matricule = models.CharField(
        max_length=30,
        blank=True,
        verbose_name="Matricule",
    )
    prime_fonction = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0'),
        verbose_name="Prime de fonction (GNF)",
        help_text="Montant mensuel fixe reporté sur chaque état de salaire.",
        validators=[MinValueValidator(Decimal('0'))],
    )
    prime_performance = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0'),
        verbose_name="Prime de performance (GNF)",
        validators=[MinValueValidator(Decimal('0'))],
    )
    prime_exceptionnelle = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0'),
        verbose_name="Prime exceptionnelle (GNF)",
        validators=[MinValueValidator(Decimal('0'))],
    )
    distance_km = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        default=Decimal('0'),
        verbose_name="Distance domicile-école (km)",
        help_text="Sert au calcul de la prime d'éloignement.",
        validators=[MinValueValidator(Decimal('0'))],
    )
    professeur_principal = models.BooleanField(
        default=False,
        verbose_name="Professeur principal",
        help_text="Secondaire : ouvre droit à la prime de professeur principal.",
    )
    # Emploi du temps hebdomadaire (feuille « Etat Prof final », colonnes L à S)
    heures_lundi = _heures_jour('Lundi')
    heures_mardi = _heures_jour('Mardi')
    heures_mercredi = _heures_jour('Mercredi')
    heures_jeudi = _heures_jour('Jeudi')
    heures_vendredi = _heures_jour('Vendredi')
    heures_samedi = _heures_jour('Samedi')

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

    @property
    def utilise_classe_principale(self):
        return self.type_enseignant in {
            TypeEnseignant.GARDERIE,
            TypeEnseignant.MATERNELLE,
            TypeEnseignant.PRIMAIRE,
        }

    @property
    def classe_ou_fonction(self):
        """Libellé professionnel affiché dans les listes et les exports."""
        if self.utilise_classe_principale:
            return self.classe_principale.nom if self.classe_principale else ''
        if self.type_enseignant == TypeEnseignant.ADMINISTRATEUR:
            return self.fonction
        return ', '.join(
            affectation.classe.nom
            for affectation in self.affectations.all()
            if affectation.actif
        )

    def clean(self):
        super().clean()

        if self.classe_principale_id:
            if not self.utilise_classe_principale:
                raise ValidationError({
                    'classe_principale': (
                        "La classe principale est réservée à la garderie, "
                        "la maternelle et au primaire."
                    )
                })
            if self.ecole_id != self.classe_principale.ecole_id:
                raise ValidationError({
                    'classe_principale': (
                        "La classe principale doit appartenir à la même école "
                        "que l'enseignant."
                    )
                })
            niveaux_autorises = NIVEAUX_PAR_TYPE_ENSEIGNANT.get(
                self.type_enseignant, set()
            )
            if self.classe_principale.niveau not in niveaux_autorises:
                raise ValidationError({
                    'classe_principale': (
                        "Le niveau de cette classe ne correspond pas au type "
                        "d'enseignant sélectionné."
                    )
                })

        if self.est_taux_horaire and not self.taux_horaire:
            raise ValidationError({
                'taux_horaire': 'Le taux horaire est obligatoire pour les enseignants du secondaire.'
            })

        if (
            self.est_taux_horaire
            and self.mode_calcul_horaire == ModeCalculHoraire.MENSUEL
            and not self.heures_mensuelles
        ):
            raise ValidationError({
                'heures_mensuelles': (
                    "Le total d'heures mensuelles est obligatoire pour le mode mensuel global."
                )
            })

        if (
            self.est_taux_horaire
            and self.mode_calcul_horaire == ModeCalculHoraire.HEBDOMADAIRE
            and self.heures_hebdomadaires <= 0
        ):
            raise ValidationError({
                'heures_lundi': (
                    "Renseignez les heures d'au moins un jour de la semaine "
                    "pour le mode emploi du temps."
                )
            })

        if self.est_salaire_fixe and not self.salaire_fixe:
            raise ValidationError({
                'salaire_fixe': f'Le salaire fixe est obligatoire pour les {self.get_type_enseignant_display().lower()}.'
            })

    def save(self, *args, **kwargs):
        # Les validateurs doivent aussi protéger les imports, scripts et API,
        # pas uniquement les ModelForm de l'interface.
        self.full_clean()
        super().save(*args, **kwargs)

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

            # Un pointage absent ne doit jamais être remplacé silencieusement
            # par un forfait. Le total mensuel n'est utilisé que si ce mode a
            # été explicitement sélectionné sur le dossier de l'enseignant.
            if heures_realisees is not None:
                heures = heures_realisees
            elif self.mode_calcul_horaire == ModeCalculHoraire.MENSUEL:
                heures = self.heures_mensuelles or Decimal('0')
            else:
                heures = Decimal('0')
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

    @property
    def heures_par_jour_semaine(self):
        """Heures de cours du lundi au samedi, dans cet ordre."""
        return [
            getattr(self, f'heures_{jour}') or Decimal('0')
            for jour, _, _ in JOURS_SEMAINE_PAIE
        ]

    @property
    def heures_hebdomadaires(self):
        return sum(self.heures_par_jour_semaine, Decimal('0'))

    @property
    def categorie_paie(self):
        """Regroupement utilisé par la masse salariale : Direction, Primaire ou Secondaire."""
        return categorie_paie(self.type_enseignant)

    def anciennete_annees(self, annee_reference):
        """Ancienneté en années pleines de calendrier (année de paie - année d'embauche)."""
        if not self.date_embauche:
            return 0
        return max(int(annee_reference) - self.date_embauche.year, 0)


class CategoriePaie(models.TextChoices):
    """Sections de la masse salariale (feuilles Direction / Primaire / Secondaire)."""

    DIRECTION = 'DIRECTION', 'Direction'
    PRIMAIRE = 'PRIMAIRE', 'Primaire'
    SECONDAIRE = 'SECONDAIRE', 'Secondaire'


def categorie_paie(type_enseignant):
    if type_enseignant == TypeEnseignant.ADMINISTRATEUR:
        return CategoriePaie.DIRECTION
    if type_enseignant == TypeEnseignant.SECONDAIRE:
        return CategoriePaie.SECONDAIRE
    return CategoriePaie.PRIMAIRE


def _montant(max_digits=12, **kwargs):
    return models.DecimalField(
        max_digits=max_digits,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0'))],
        **kwargs,
    )


class ParametrePaie(SyncTrackedModel):
    """Barèmes des primes et signataires des documents de paie d'une école."""

    ecole = models.OneToOneField(
        Ecole,
        on_delete=models.CASCADE,
        related_name='parametre_paie',
        verbose_name="École",
    )
    jours_ouvrables = models.PositiveIntegerField(
        default=20,
        verbose_name="Jours ouvrables par mois",
        validators=[MinValueValidator(1), MaxValueValidator(31)],
    )
    taux_anciennete_par_an = _montant(
        default=Decimal('0'),
        verbose_name="Prime d'ancienneté par année (GNF)",
        help_text="Ex. 10 000 GNF par année d'ancienneté.",
    )
    taux_eloignement_par_km = _montant(
        default=Decimal('0'),
        verbose_name="Prime d'éloignement par km (GNF)",
        help_text="Ex. 2 000 GNF par km.",
    )
    prime_craie_par_eleve = _montant(
        default=Decimal('0'),
        verbose_name="Prime de craie par élève de la classe (GNF)",
        help_text="Garderie, maternelle et primaire : effectif de la classe principale × ce montant (ex. 500 GNF).",
    )
    prime_par_heure_revision = _montant(
        default=Decimal('0'),
        verbose_name="Prime par heure de révision (GNF)",
        help_text="Ex. 10 000 GNF par heure.",
    )
    prime_professeur_principal = _montant(
        default=Decimal('0'),
        verbose_name="Prime de professeur principal (GNF)",
        help_text="Ex. 50 000 GNF par mois.",
    )
    retenue_par_jour_chome = _montant(
        default=Decimal('0'),
        verbose_name="Imputation par jour chômé (GNF)",
        help_text=(
            "Sanction retenue pour chaque jour chômé (absence non justifiée), "
            "ex. 30 000 GNF."
        ),
    )

    signataire_1_titre = models.CharField(max_length=80, default="La Fondation", blank=True, verbose_name="Signataire 1 - titre")
    signataire_1_nom = models.CharField(max_length=120, blank=True, verbose_name="Signataire 1 - nom")
    signataire_2_titre = models.CharField(max_length=80, default="Le Directeur Général", blank=True, verbose_name="Signataire 2 - titre")
    signataire_2_nom = models.CharField(max_length=120, blank=True, verbose_name="Signataire 2 - nom")
    signataire_3_titre = models.CharField(max_length=80, default="La Gestionnaire", blank=True, verbose_name="Signataire 3 - titre")
    signataire_3_nom = models.CharField(max_length=120, blank=True, verbose_name="Signataire 3 - nom")
    lieu_signature = models.CharField(max_length=80, blank=True, verbose_name="Lieu de signature")

    date_modification = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Paramètres de paie"
        verbose_name_plural = "Paramètres de paie"

    def __str__(self):
        return f"Paramètres de paie - {self.ecole.nom}"

    @classmethod
    def pour_ecole(cls, ecole):
        parametre, _ = cls.objects.get_or_create(ecole=ecole)
        return parametre

    @property
    def signataires(self):
        return [
            (titre, nom)
            for titre, nom in (
                (self.signataire_1_titre, self.signataire_1_nom),
                (self.signataire_2_titre, self.signataire_2_nom),
                (self.signataire_3_titre, self.signataire_3_nom),
            )
            if titre or nom
        ]


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
        help_text="Nombre d'heures d'enseignement par semaine dans cette classe",
        validators=[
            MinValueValidator(Decimal('0')),
            MaxValueValidator(Decimal('168')),
        ],
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
        super().clean()

        if self.enseignant.est_taux_horaire and not self.heures_par_semaine:
            raise ValidationError({
                'heures_par_semaine': 'Le nombre d\'heures par semaine est obligatoire pour les enseignants du secondaire.'
            })

        if (
            self.enseignant_id
            and self.classe_id
            and self.enseignant.type_enseignant == TypeEnseignant.SECONDAIRE
            and self.classe.niveau not in NIVEAUX_SECONDAIRE
        ):
            raise ValidationError({
                'classe': (
                    "Une affectation secondaire doit utiliser une classe du "
                    "collège ou du lycée."
                )
            })

        if self.date_fin and self.date_fin < self.date_debut:
            raise ValidationError({
                'date_fin': 'La date de fin ne peut pas être antérieure à la date de début.'
            })
        if (
            self.enseignant_id
            and self.classe_id
            and self.enseignant.ecole_id != self.classe.ecole_id
        ):
            raise ValidationError({
                'classe': "La classe et l'enseignant doivent appartenir à la même école."
            })

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)


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
        help_text="Nombre moyen de semaines dans le mois (défaut: 4.33)",
        validators=[
            MinValueValidator(Decimal('0.01')),
            MaxValueValidator(Decimal('6')),
        ],
    )

    # Nombre de lundis, mardis... réellement travaillés dans le mois
    # (vide = calendrier du mois). Sert au mode emploi du temps hebdomadaire.
    nb_lundis = _occurrences_jour('Lundi')
    nb_mardis = _occurrences_jour('Mardi')
    nb_mercredis = _occurrences_jour('Mercredi')
    nb_jeudis = _occurrences_jour('Jeudi')
    nb_vendredis = _occurrences_jour('Vendredi')
    nb_samedis = _occurrences_jour('Samedi')

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

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    @property
    def nom_periode(self):
        mois_noms = [
            '', 'Janvier', 'Février', 'Mars', 'Avril', 'Mai', 'Juin',
            'Juillet', 'Août', 'Septembre', 'Octobre', 'Novembre', 'Décembre'
        ]
        return f"{mois_noms[self.mois]} {self.annee}"

    def occurrences_calendrier(self):
        """Nombre de lundis ... samedis du mois civil."""
        from calendar import monthrange

        premier_jour_semaine, nb_jours = monthrange(self.annee, self.mois)
        compteurs = [0] * 7
        for jour in range(nb_jours):
            compteurs[(premier_jour_semaine + jour) % 7] += 1
        return compteurs[:6]

    def occurrences_jours_semaine(self):
        """Nombre de lundis ... samedis travaillés (saisie ou calendrier)."""
        calendrier = self.occurrences_calendrier()
        return [
            valeur if valeur is not None else calendrier[index]
            for index, valeur in enumerate(
                getattr(self, f'nb_{jour}s') for jour, _, _ in JOURS_SEMAINE_PAIE
            )
        ]


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
    mode_calcul_heures = models.CharField(
        max_length=10,
        choices=ModeCalculHoraire.choices,
        blank=True,
        default='',
        verbose_name="Source des heures",
        help_text="Mode conservé au moment du calcul pour l'historique",
    )
    taux_horaire_applique = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name="Taux horaire appliqué",
        help_text="Taux conservé au moment du calcul pour l'historique",
        validators=[MinValueValidator(Decimal('0'))],
    )
    jours_presence = models.PositiveIntegerField(
        default=0,
        verbose_name="Jours de présence",
        help_text=(
            "Nombre de jours présents ou en retard conservé au moment du calcul."
        ),
    )

    # Montants
    salaire_base = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        verbose_name="Salaire de base",
        validators=[MinValueValidator(Decimal('0'))],
    )
    primes = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0'),
        verbose_name="Primes",
        help_text="Total des rubriques de primes, recalculé à chaque enregistrement.",
        validators=[MinValueValidator(Decimal('0'))],
    )
    # Rubriques du bulletin de paie (colonnes PRIMES de l'état Excel)
    prime_fonction = _montant(default=Decimal('0'), verbose_name="Prime de fonction")
    prime_craie = _montant(default=Decimal('0'), verbose_name="Prime de craie / révision")
    prime_anciennete = _montant(default=Decimal('0'), verbose_name="Prime d'ancienneté")
    prime_eloignement = _montant(default=Decimal('0'), verbose_name="Prime d'éloignement")
    prime_performance = _montant(default=Decimal('0'), verbose_name="Prime de performance")
    prime_exceptionnelle = _montant(default=Decimal('0'), verbose_name="Prime exceptionnelle")
    heures_revision = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        default=Decimal('0'),
        verbose_name="Heures de révision",
        validators=[MinValueValidator(Decimal('0'))],
    )
    effectif_classe = models.PositiveIntegerField(
        default=0,
        verbose_name="Effectif de la classe",
        help_text="Effectif retenu pour la prime de craie au moment du calcul.",
    )
    jours_chomes = models.PositiveIntegerField(
        default=0,
        verbose_name="Jours chômés",
        help_text="Absences non justifiées du mois (jours travaillés = jours ouvrables - jours chômés).",
    )
    imputation_sanctions = _montant(
        default=Decimal('0'),
        verbose_name="Imputation liée aux sanctions",
        help_text="Jours chômés × imputation par jour chômé des paramètres de paie.",
    )
    heures_a_prester = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name="Heures à prester",
        help_text="Emploi du temps hebdomadaire × nombre de jours travaillés du mois.",
    )
    heures_absence = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        default=Decimal('0'),
        verbose_name="Heures d'absence",
        help_text="Heures non prestées retirées des heures à prester.",
        validators=[MinValueValidator(Decimal('0'))],
    )
    primes_ajustees = models.BooleanField(
        default=False,
        verbose_name="Primes saisies manuellement",
        help_text="Si coché, un recalcul conserve les primes saisies sur cet état.",
    )
    deductions = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0'),
        verbose_name="Déductions",
        validators=[MinValueValidator(Decimal('0'))],
    )
    avances_deduites = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0'),
        verbose_name="Avances déduites",
        help_text="Montant des avances récupéré sur ce salaire",
        validators=[MinValueValidator(Decimal('0'))],
    )
    salaire_net = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        verbose_name="Salaire net",
        validators=[MinValueValidator(Decimal('0'))],
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
        super().clean()
        salaire_base = self.salaire_base or Decimal('0')
        primes = self.primes or Decimal('0')
        deductions = self.deductions or Decimal('0')
        avances_deduites = self.avances_deduites or Decimal('0')
        sanctions = self.imputation_sanctions or Decimal('0')
        errors = {}

        if sanctions > salaire_base + primes:
            errors['imputation_sanctions'] = (
                "L'imputation liée aux sanctions ne peut pas dépasser le salaire brut."
            )
        elif deductions + avances_deduites + sanctions > salaire_base + primes:
            errors['deductions'] = (
                "Les retenues et avances ne peuvent pas dépasser le salaire de base et les primes."
            )

        if (
            self.enseignant_id
            and self.periode_id
            and self.enseignant.ecole_id != self.periode.ecole_id
        ):
            errors['enseignant'] = (
                "L'enseignant et la période doivent appartenir à la même école."
            )

        if errors:
            raise ValidationError(errors)

    RUBRIQUES_PRIMES = (
        ('prime_fonction', 'Prime de fonction'),
        ('prime_craie', 'Prime de craie/Révision'),
        ('prime_anciennete', "Prime d'ancienneté"),
        ('prime_eloignement', "Prime d'éloignement"),
        ('prime_performance', 'Prime de performance'),
        ('prime_exceptionnelle', 'Prime exceptionnelle'),
    )

    @property
    def rubriques_primes(self):
        return [
            (libelle, getattr(self, champ) or Decimal('0'))
            for champ, libelle in self.RUBRIQUES_PRIMES
        ]

    @property
    def salaire_brut(self):
        return (self.salaire_base or Decimal('0')) + (self.primes or Decimal('0'))

    @property
    def retenues_totales(self):
        return (
            (self.deductions or Decimal('0'))
            + (self.avances_deduites or Decimal('0'))
            + (self.imputation_sanctions or Decimal('0'))
        )

    @property
    def retenues_hors_avances(self):
        """Retenues diverses + imputation liée aux sanctions."""
        return (self.deductions or Decimal('0')) + (self.imputation_sanctions or Decimal('0'))

    def jours_travailles(self, jours_ouvrables):
        """Jours travaillés de l'état Excel : jours ouvrables - jours chômés.

        Au secondaire en emploi du temps, la base est le nombre de jours de
        cours du mois (somme des lundis ... samedis travaillés).
        """
        if self.mode_calcul_heures == ModeCalculHoraire.HEBDOMADAIRE:
            jours_ouvrables = sum(self.periode.occurrences_jours_semaine())
        return max(int(jours_ouvrables) - (self.jours_chomes or 0), 0)

    def _synchroniser_total_primes(self):
        total = sum(
            (getattr(self, champ) or Decimal('0') for champ, _ in self.RUBRIQUES_PRIMES),
            Decimal('0'),
        )
        if total == 0 and (self.primes or Decimal('0')) > 0:
            # Compatibilité : un ancien total global sans détail devient une
            # prime exceptionnelle afin de ne rien perdre.
            self.prime_exceptionnelle = self.primes
            total = self.primes
        self.primes = Decimal(total).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

    def save(self, *args, **kwargs):
        self._synchroniser_total_primes()
        # Calcul automatique du salaire net
        salaire_base = self.salaire_base or Decimal('0')
        primes = self.primes or Decimal('0')
        deductions = self.deductions or Decimal('0')
        avances_deduites = self.avances_deduites or Decimal('0')
        sanctions = self.imputation_sanctions or Decimal('0')
        self.salaire_net = (
            salaire_base + primes - deductions - avances_deduites - sanctions
        ).quantize(
            Decimal('0.01'), rounding=ROUND_HALF_UP
        )
        self.full_clean()
        if kwargs.get('update_fields') is not None:
            kwargs['update_fields'] = set(kwargs['update_fields']) | {
                'salaire_net', 'primes', 'prime_exceptionnelle',
            }
        super().save(*args, **kwargs)

    @property
    def peut_etre_valide(self):
        """Vérifie si l'état de salaire peut être validé"""
        from calendar import monthrange
        from datetime import date

        dernier_jour = date(
            self.periode.annee,
            self.periode.mois,
            monthrange(self.periode.annee, self.periode.mois)[1],
        )
        return (
            not self.valide
            and not self.periode.cloturee
            and self.enseignant.statut == 'ACTIF'
            and self.enseignant.date_embauche <= dernier_jour
        )

    @property
    def peut_etre_paye(self):
        """Vérifie si l'état de salaire peut être marqué comme payé"""
        return self.valide and not self.paye


class AvanceSalaire(SyncTrackedModel):
    """Somme versée à un enseignant avant son règlement mensuel."""

    enseignant = models.ForeignKey(
        Enseignant,
        on_delete=models.PROTECT,
        related_name='avances_salaire',
        verbose_name="Enseignant",
    )
    periode_prevue = models.ForeignKey(
        PeriodeSalaire,
        on_delete=models.PROTECT,
        related_name='avances_salaire',
        verbose_name="Première période de retenue",
    )
    date_avance = models.DateField(default=datetime.now, verbose_name="Date de l'avance")
    montant = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))],
        verbose_name="Montant de l'avance (GNF)",
    )
    motif = models.TextField(verbose_name="Motif")
    reference_externe = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="Référence externe / numéro de reçu",
    )
    cree_par = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='avances_salaire_creees',
    )
    date_creation = models.DateTimeField(auto_now_add=True)
    date_modification = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Avance sur salaire"
        verbose_name_plural = "Avances sur salaire"
        ordering = ['-date_avance', '-id']

    def __str__(self):
        return f"{self.enseignant.nom_complet} - {self.montant} GNF"

    def clean(self):
        super().clean()
        if (
            self.enseignant_id
            and self.periode_prevue_id
            and self.enseignant.ecole_id != self.periode_prevue.ecole_id
        ):
            raise ValidationError({
                'periode_prevue': (
                    "La période de retenue doit appartenir à l'école de l'enseignant."
                )
            })

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    @property
    def montant_rembourse(self):
        total = self.remboursements.aggregate(total=models.Sum('montant'))['total']
        return (total or Decimal('0')).quantize(Decimal('0.01'))

    @property
    def solde_restant(self):
        return max(self.montant - self.montant_rembourse, Decimal('0'))

    @property
    def est_soldee(self):
        return self.solde_restant <= 0

    @property
    def est_modifiable(self):
        return not self.remboursements.filter(
            models.Q(etat_salaire__valide=True)
            | models.Q(etat_salaire__paye=True)
            | models.Q(etat_salaire__periode__cloturee=True)
        ).exists()


class RemboursementAvance(SyncTrackedModel):
    """Imputation d'une avance sur un état de salaire précis."""

    avance = models.ForeignKey(
        AvanceSalaire,
        on_delete=models.CASCADE,
        related_name='remboursements',
        verbose_name="Avance",
    )
    etat_salaire = models.ForeignKey(
        EtatSalaire,
        on_delete=models.CASCADE,
        related_name='remboursements_avances',
        verbose_name="État de salaire",
    )
    montant = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))],
        verbose_name="Montant remboursé",
    )
    date_creation = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Remboursement d'avance"
        verbose_name_plural = "Remboursements d'avances"
        ordering = ['etat_salaire__periode__annee', 'etat_salaire__periode__mois', 'id']
        constraints = [
            models.UniqueConstraint(
                fields=['avance', 'etat_salaire'],
                name='unique_avance_par_etat_salaire',
            )
        ]

    def __str__(self):
        return f"{self.avance} - {self.etat_salaire.periode.nom_periode}"

    def clean(self):
        super().clean()
        if (
            self.avance_id
            and self.etat_salaire_id
            and self.avance.enseignant_id != self.etat_salaire.enseignant_id
        ):
            raise ValidationError(
                "L'avance et l'état de salaire doivent concerner le même enseignant."
            )

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)


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
        help_text="Calculé automatiquement ou saisi manuellement",
        validators=[
            MinValueValidator(Decimal('0')),
            MaxValueValidator(Decimal('24')),
        ],
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

    def clean(self):
        super().clean()
        errors = {}
        heures = self.heures_travaillees

        if bool(self.heure_arrivee) != bool(self.heure_depart):
            errors['heure_depart'] = (
                "L'heure d'arrivée et l'heure de départ doivent être renseignées ensemble."
            )

        if self.statut in {'ABSENT', 'CONGE', 'MALADIE'}:
            if self.heure_arrivee or self.heure_depart or (heures is not None and heures > 0):
                errors['heures_travaillees'] = (
                    'Aucune heure travaillée ne peut être enregistrée pour ce statut.'
                )
        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
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
            self.heures_travaillees = (
                Decimal(str(delta.total_seconds())) / Decimal('3600')
            ).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        elif not self.heure_arrivee or not self.heure_depart:
            # Si pas d'heures d'arrivée/départ, mettre à 0 si non défini
            if self.heures_travaillees is None:
                self.heures_travaillees = Decimal('0')

        self.full_clean()
        if kwargs.get('update_fields') is not None:
            kwargs['update_fields'] = set(kwargs['update_fields']) | {
                'heures_travaillees'
            }
        super().save(*args, **kwargs)

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
        help_text="Heures prévues selon l'affectation",
        validators=[MinValueValidator(Decimal('0'))],
    )
    heures_realisees = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        verbose_name="Heures réalisées",
        help_text="Heures effectivement enseignées",
        validators=[MinValueValidator(Decimal('0'))],
    )

    taux_horaire_applique = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name="Taux horaire appliqué",
        validators=[MinValueValidator(Decimal('0'))],
    )

    montant = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name="Montant",
        validators=[MinValueValidator(Decimal('0'))],
    )

    class Meta:
        verbose_name = "Détail heures par classe"
        verbose_name_plural = "Détails heures par classe"
        unique_together = ['etat_salaire', 'affectation_classe']

    def __str__(self):
        return f"{self.etat_salaire.enseignant.nom_complet} - {self.affectation_classe.classe.nom}"

    def save(self, *args, **kwargs):
        # Calcul automatique du montant
        self.montant = (self.heures_realisees * self.taux_horaire_applique).quantize(
            Decimal('0.01'), rounding=ROUND_HALF_UP
        )
        self.full_clean()
        if kwargs.get('update_fields') is not None:
            kwargs['update_fields'] = set(kwargs['update_fields']) | {'montant'}
        super().save(*args, **kwargs)
