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


class ElementCorbeille(models.Model):
    """Corbeille : garde une copie complete de ce qui est supprime ou modifie.

    Une suppression conserve l'instantane de l'objet (`donnees_avant`) pour
    permettre une restauration fidele. Une modification conserve l'avant et
    l'apres, ce qui permet d'annuler la modification.
    """

    SUPPRESSION = 'SUPPRESSION'
    MODIFICATION = 'MODIFICATION'
    TYPE_CHOICES = [
        (SUPPRESSION, 'Suppression'),
        (MODIFICATION, 'Modification'),
    ]

    type_operation = models.CharField(max_length=15, choices=TYPE_CHOICES, db_index=True)
    model_label = models.CharField(max_length=120, db_index=True, help_text="Ex: eleves.Eleve")
    objet_id = models.PositiveIntegerField(null=True, blank=True)
    libelle = models.CharField(max_length=255, verbose_name="Élément")

    donnees_avant = JSONField(default=dict, blank=True)
    donnees_apres = JSONField(default=dict, blank=True)
    champs_modifies = JSONField(default=list, blank=True)
    # Objets rattachés supprimés en cascade (paiements, abonnements...)
    objets_lies = JSONField(default=list, blank=True)
    motif = models.CharField(max_length=255, blank=True, verbose_name="Motif")

    ecole = models.ForeignKey(
        'eleves.Ecole', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='elements_corbeille'
    )
    utilisateur = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    adresse_ip = models.GenericIPAddressField(null=True, blank=True)
    date = models.DateTimeField(default=timezone.now, db_index=True)

    restaure = models.BooleanField(default=False, db_index=True)
    date_restauration = models.DateTimeField(null=True, blank=True)
    restaure_par = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='elements_corbeille_restaures'
    )

    class Meta:
        ordering = ['-date']
        verbose_name = 'Élément de la corbeille'
        verbose_name_plural = 'Corbeille'
        indexes = [
            models.Index(fields=['type_operation', 'restaure', '-date']),
            models.Index(fields=['model_label', 'objet_id']),
        ]

    def __str__(self):
        return f"{self.get_type_operation_display()} - {self.libelle}"

    @property
    def nom_modele(self):
        """Nom lisible du modèle concerné."""
        from django.apps import apps
        try:
            app_label, model_name = self.model_label.split('.', 1)
            return apps.get_model(app_label, model_name)._meta.verbose_name.title()
        except Exception:
            return self.model_label

    @property
    def peut_etre_restaure(self):
        return not self.restaure


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
