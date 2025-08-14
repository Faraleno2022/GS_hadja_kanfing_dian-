from django.db import models
from django.contrib.auth.models import User
from django.core.validators import RegexValidator
from eleves.models import Ecole

class Profil(models.Model):
    """Modèle pour étendre le profil utilisateur"""
    ROLE_CHOICES = [
        ('ADMIN', 'Administrateur'),
        ('DIRECTEUR', 'Directeur'),
        ('COMPTABLE', 'Comptable'),
        ('SECRETAIRE', 'Secrétaire'),
        ('ENSEIGNANT', 'Enseignant'),
        ('SURVEILLANT', 'Surveillant'),
    ]
    
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profil')
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, verbose_name="Rôle")
    telephone = models.CharField(
        max_length=20, 
        validators=[RegexValidator(r'^\+224\d{8,9}$', 'Format: +224XXXXXXXXX')],
        verbose_name="Téléphone"
    )
    adresse = models.TextField(blank=True, null=True, verbose_name="Adresse")
    photo = models.ImageField(upload_to='utilisateurs/photos/', blank=True, null=True, verbose_name="Photo")
    ecole = models.ForeignKey(Ecole, on_delete=models.PROTECT, related_name='profils', verbose_name="École", null=True, blank=True)
    
    # Permissions spécifiques
    peut_valider_paiements = models.BooleanField(default=False, verbose_name="Peut valider les paiements")
    peut_valider_depenses = models.BooleanField(default=False, verbose_name="Peut valider les dépenses")
    peut_generer_rapports = models.BooleanField(default=False, verbose_name="Peut générer des rapports")
    peut_gerer_utilisateurs = models.BooleanField(default=False, verbose_name="Peut gérer les utilisateurs")
    
    # Permissions granulaires pour les comptables
    peut_ajouter_paiements = models.BooleanField(default=True, verbose_name="Peut ajouter des paiements")
    peut_ajouter_depenses = models.BooleanField(default=True, verbose_name="Peut ajouter des dépenses")
    peut_ajouter_enseignants = models.BooleanField(default=True, verbose_name="Peut ajouter des enseignants")
    peut_modifier_paiements = models.BooleanField(default=True, verbose_name="Peut modifier les paiements")
    peut_modifier_depenses = models.BooleanField(default=True, verbose_name="Peut modifier les dépenses")
    peut_supprimer_paiements = models.BooleanField(default=False, verbose_name="Peut supprimer les paiements")
    peut_supprimer_depenses = models.BooleanField(default=False, verbose_name="Peut supprimer les dépenses")
    peut_consulter_rapports = models.BooleanField(default=True, verbose_name="Peut consulter les rapports")
    
    # Informations de connexion
    derniere_connexion = models.DateTimeField(null=True, blank=True, verbose_name="Dernière connexion")
    actif = models.BooleanField(default=True, verbose_name="Actif")
    
    # Métadonnées
    date_creation = models.DateTimeField(auto_now_add=True)
    date_modification = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Profil utilisateur"
        verbose_name_plural = "Profils utilisateurs"
    
    def __str__(self):
        return f"{self.user.get_full_name()} ({self.get_role_display()})"
    
    @property
    def nom_complet(self):
        return self.user.get_full_name() or self.user.username

class SessionUtilisateur(models.Model):
    """Modèle pour suivre les sessions utilisateurs"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sessions')
    session_key = models.CharField(max_length=40, verbose_name="Clé de session")
    adresse_ip = models.GenericIPAddressField(verbose_name="Adresse IP")
    user_agent = models.TextField(verbose_name="User Agent")
    
    date_debut = models.DateTimeField(auto_now_add=True, verbose_name="Début de session")
    date_fin = models.DateTimeField(null=True, blank=True, verbose_name="Fin de session")
    active = models.BooleanField(default=True, verbose_name="Session active")
    
    class Meta:
        verbose_name = "Session utilisateur"
        verbose_name_plural = "Sessions utilisateurs"
        ordering = ['-date_debut']
    
    def __str__(self):
        return f"{self.user.username} - {self.date_debut.strftime('%d/%m/%Y %H:%M')}"

class JournalActivite(models.Model):
    """Modèle pour le journal des activités utilisateurs"""
    ACTION_CHOICES = [
        ('CONNEXION', 'Connexion'),
        ('DECONNEXION', 'Déconnexion'),
        ('CREATION', 'Création'),
        ('MODIFICATION', 'Modification'),
        ('SUPPRESSION', 'Suppression'),
        ('VALIDATION', 'Validation'),
        ('CONSULTATION', 'Consultation'),
        ('EXPORT', 'Export'),
        ('IMPRESSION', 'Impression'),
    ]
    
    TYPE_OBJET_CHOICES = [
        ('ELEVE', 'Élève'),
        ('PAIEMENT', 'Paiement'),
        ('DEPENSE', 'Dépense'),
        ('RAPPORT', 'Rapport'),
        ('UTILISATEUR', 'Utilisateur'),
        ('SYSTEME', 'Système'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='activites')
    action = models.CharField(max_length=20, choices=ACTION_CHOICES, verbose_name="Action")
    type_objet = models.CharField(max_length=20, choices=TYPE_OBJET_CHOICES, verbose_name="Type d'objet")
    objet_id = models.PositiveIntegerField(null=True, blank=True, verbose_name="ID de l'objet")
    description = models.TextField(verbose_name="Description")
    
    # Informations techniques
    adresse_ip = models.GenericIPAddressField(verbose_name="Adresse IP")
    user_agent = models.TextField(blank=True, null=True, verbose_name="User Agent")
    
    date_action = models.DateTimeField(auto_now_add=True, verbose_name="Date de l'action")
    
    class Meta:
        verbose_name = "Journal d'activité"
        verbose_name_plural = "Journal des activités"
        ordering = ['-date_action']
    
    def __str__(self):
        return f"{self.user.username} - {self.get_action_display()} {self.get_type_objet_display()} ({self.date_action.strftime('%d/%m/%Y %H:%M')})"

class ParametreSysteme(models.Model):
    """Modèle pour les paramètres du système"""
    TYPE_CHOICES = [
        ('STRING', 'Chaîne de caractères'),
        ('INTEGER', 'Nombre entier'),
        ('DECIMAL', 'Nombre décimal'),
        ('BOOLEAN', 'Booléen'),
        ('DATE', 'Date'),
        ('JSON', 'JSON'),
    ]
    
    cle = models.CharField(max_length=100, unique=True, verbose_name="Clé")
    valeur = models.TextField(verbose_name="Valeur")
    type_valeur = models.CharField(max_length=10, choices=TYPE_CHOICES, verbose_name="Type de valeur")
    description = models.TextField(verbose_name="Description")
    
    # Métadonnées
    date_creation = models.DateTimeField(auto_now_add=True)
    date_modification = models.DateTimeField(auto_now=True)
    modifie_par = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    
    class Meta:
        verbose_name = "Paramètre système"
        verbose_name_plural = "Paramètres système"
        ordering = ['cle']
    
    def __str__(self):
        return f"{self.cle} = {self.valeur}"
    
    def get_valeur_typee(self):
        """Retourne la valeur avec le bon type"""
        if self.type_valeur == 'INTEGER':
            return int(self.valeur)
        elif self.type_valeur == 'DECIMAL':
            from decimal import Decimal
            return Decimal(self.valeur)
        elif self.type_valeur == 'BOOLEAN':
            return self.valeur.lower() in ['true', '1', 'oui', 'yes']
        elif self.type_valeur == 'DATE':
            from datetime import datetime
            return datetime.fromisoformat(self.valeur).date()
        elif self.type_valeur == 'JSON':
            import json
            return json.loads(self.valeur)
        else:
            return self.valeur

