from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone

try:
    from django.db.models import JSONField
except ImportError:
    from django.contrib.postgres.fields import JSONField

User = get_user_model()


class SystemLog(models.Model):
    """Journal des actions administratives importantes"""
    
    ACTION_CHOICES = [
        ('DELETE', 'Suppression'),
        ('SUPPRESSION_DEFINITIVE', 'Suppression définitive'),
        ('RESET', 'Réinitialisation'),
        ('BACKUP', 'Sauvegarde'),
        ('RESTORE', 'Restauration'),
        ('LOGIN', 'Connexion admin'),
        ('ERROR', 'Erreur système'),
    ]
    
    action = models.CharField(max_length=30, choices=ACTION_CHOICES, db_index=True)
    description = models.TextField()
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    timestamp = models.DateTimeField(default=timezone.now, db_index=True)
    details = JSONField(default=dict, blank=True)
    
    class Meta:
        ordering = ['-timestamp']
        verbose_name = 'Log système'
        verbose_name_plural = 'Logs système'
    
    def __str__(self):
        return f"{self.action} - {self.timestamp.strftime('%d/%m/%Y %H:%M')} - {self.user or 'Système'}"


class CorbeilleEleve(models.Model):
    """Corbeille des élèves supprimés.

    Conserve un instantané complet (élève + responsables + paiements +
    abonnements + échéancier) permettant une restauration ultérieure.
    """

    eleve_id_origine = models.PositiveIntegerField(db_index=True, verbose_name="ID d'origine")
    matricule = models.CharField(max_length=50, db_index=True)
    nom = models.CharField(max_length=100)
    prenom = models.CharField(max_length=100)
    classe_nom = models.CharField(max_length=150, blank=True)
    ecole_nom = models.CharField(max_length=200, blank=True)
    annee_scolaire = models.CharField(max_length=9, blank=True)

    donnees = JSONField(default=dict, blank=True, verbose_name="Instantané des données")
    motif = models.TextField(blank=True, verbose_name="Motif de la suppression")

    supprime_par = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='eleves_mis_corbeille'
    )
    date_suppression = models.DateTimeField(default=timezone.now, db_index=True)

    restaure = models.BooleanField(default=False, db_index=True)
    date_restauration = models.DateTimeField(null=True, blank=True)
    restaure_par = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='eleves_restaures'
    )

    class Meta:
        ordering = ['-date_suppression']
        verbose_name = 'Élève en corbeille'
        verbose_name_plural = 'Corbeille des élèves'

    def __str__(self):
        return f"{self.prenom} {self.nom} ({self.matricule})"

    @property
    def nom_complet(self):
        return f"{self.prenom} {self.nom}".strip()

    @property
    def nb_paiements(self):
        return len((self.donnees or {}).get('paiements', []))

    @property
    def nb_abonnements(self):
        donnees = self.donnees or {}
        return len(donnees.get('abonnements_bus', [])) + len(donnees.get('abonnements_cantine', []))


class CorbeilleElement(models.Model):
    """Corbeille générique : paiements, échéanciers, abonnements, remises...

    Chaque entrée conserve un instantané de l'objet supprimé et de ses lignes
    liées, ce qui permet de le recréer à l'identique.
    """

    app_label = models.CharField(max_length=100, db_index=True)
    model_name = models.CharField(max_length=100, db_index=True)
    modele_libelle = models.CharField(max_length=150, blank=True, verbose_name="Type d'objet")

    objet_id_origine = models.PositiveIntegerField(db_index=True, verbose_name="ID d'origine")
    objet_repr = models.CharField(max_length=255, blank=True)
    contexte = models.CharField(max_length=255, blank=True, verbose_name="Élève / rattachement")
    ecole_nom = models.CharField(max_length=200, blank=True)

    donnees = JSONField(default=dict, blank=True, verbose_name="Instantané des données")
    motif = models.TextField(blank=True)

    supprime_par = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='elements_mis_corbeille'
    )
    date_suppression = models.DateTimeField(default=timezone.now, db_index=True)

    restaure = models.BooleanField(default=False, db_index=True)
    date_restauration = models.DateTimeField(null=True, blank=True)
    restaure_par = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='elements_restaures'
    )

    class Meta:
        ordering = ['-date_suppression']
        verbose_name = 'Élément en corbeille'
        verbose_name_plural = 'Corbeille des éléments supprimés'
        indexes = [
            models.Index(fields=['app_label', 'model_name']),
        ]

    def __str__(self):
        return f"{self.modele_libelle or self.model_name} — {self.objet_repr}"

    @property
    def nb_lignes_liees(self):
        donnees = self.donnees or {}
        total = sum(len(v) for v in donnees.get('relations', {}).values())
        if donnees.get('recu'):
            total += 1
        if donnees.get('echeancier'):
            total += 1
        return total


class JournalModification(models.Model):
    """Corbeille de mémoire : trace de toutes les modifications de données.

    Conserve, pour chaque objet modifié, la valeur avant et après de chaque
    champ afin de pouvoir consulter (et au besoin annuler) un changement.
    """

    ACTION_CREATION = 'CREATION'
    ACTION_MODIFICATION = 'MODIFICATION'
    ACTION_SUPPRESSION = 'SUPPRESSION'
    ACTION_RESTAURATION = 'RESTAURATION'
    ACTION_CHOICES = [
        (ACTION_CREATION, 'Création'),
        (ACTION_MODIFICATION, 'Modification'),
        (ACTION_SUPPRESSION, 'Suppression'),
        (ACTION_RESTAURATION, 'Restauration'),
    ]

    app_label = models.CharField(max_length=100, db_index=True)
    model_name = models.CharField(max_length=100, db_index=True)
    objet_id = models.PositiveIntegerField(null=True, blank=True, db_index=True)
    objet_repr = models.CharField(max_length=255, blank=True)

    action = models.CharField(max_length=20, choices=ACTION_CHOICES, default=ACTION_MODIFICATION, db_index=True)
    # {'champ': {'avant': ..., 'apres': ...}, ...}
    changements = JSONField(default=dict, blank=True)
    commentaire = models.TextField(blank=True)

    utilisateur = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='modifications_journal'
    )
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    date_modification = models.DateTimeField(default=timezone.now, db_index=True)

    annule = models.BooleanField(default=False, db_index=True)
    date_annulation = models.DateTimeField(null=True, blank=True)
    annule_par = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='modifications_annulees'
    )

    class Meta:
        ordering = ['-date_modification']
        verbose_name = 'Modification (corbeille mémoire)'
        verbose_name_plural = 'Corbeille mémoire des modifications'
        indexes = [
            models.Index(fields=['app_label', 'model_name', 'objet_id']),
        ]

    def __str__(self):
        return f"{self.get_action_display()} {self.model_name} #{self.objet_id} - {self.date_modification:%d/%m/%Y %H:%M}"

    @property
    def libelle_modele(self):
        return f"{self.app_label}.{self.model_name}"

    @property
    def liste_changements(self):
        """Retourne les changements sous forme de liste triée pour l'affichage."""
        resultat = []
        for champ, valeurs in sorted((self.changements or {}).items()):
            if isinstance(valeurs, dict):
                resultat.append({
                    'champ': champ,
                    'avant': valeurs.get('avant'),
                    'apres': valeurs.get('apres'),
                })
            else:
                resultat.append({'champ': champ, 'avant': None, 'apres': valeurs})
        return resultat


class MaintenanceMode(models.Model):
    """Mode maintenance du système"""
    
    is_active = models.BooleanField(default=False)
    message = models.TextField(
        default="Le système est en maintenance. Veuillez réessayer plus tard.",
        help_text="Message affiché aux utilisateurs"
    )
    allowed_users = models.ManyToManyField(
        User, 
        blank=True,
        help_text="Utilisateurs autorisés pendant la maintenance"
    )
    activated_by = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        related_name='maintenance_activated'
    )
    activated_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        verbose_name = 'Mode maintenance'
        verbose_name_plural = 'Mode maintenance'
    
    def __str__(self):
        status = "Actif" if self.is_active else "Inactif"
        return f"Mode maintenance - {status}"
    
    def save(self, *args, **kwargs):
        if self.is_active and not self.activated_at:
            self.activated_at = timezone.now()
        super().save(*args, **kwargs)
