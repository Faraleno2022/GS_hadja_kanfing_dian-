"""
Signals Django pour convertir automatiquement les champs texte en majuscules
avant l'enregistrement en base de données.
"""
from django.db.models.signals import pre_save, post_save
from django.dispatch import receiver
from decimal import Decimal
from .models import Eleve, Responsable, Classe, Ecole


def convertir_majuscules_model(instance, champs):
    """Convertit les champs spécifiés en majuscules"""
    for champ in champs:
        if hasattr(instance, champ):
            valeur = getattr(instance, champ)
            if valeur and isinstance(valeur, str):
                setattr(instance, champ, valeur.upper())


@receiver(pre_save, sender=Eleve)
def convertir_eleve_majuscules(sender, instance, **kwargs):
    """Convertit les champs texte de l'élève en majuscules avant sauvegarde"""
    convertir_majuscules_model(instance, ['prenom', 'nom', 'lieu_naissance'])


@receiver(pre_save, sender=Responsable)
def convertir_responsable_majuscules(sender, instance, **kwargs):
    """Convertit les champs texte du responsable en majuscules avant sauvegarde"""
    convertir_majuscules_model(instance, ['prenom', 'nom', 'adresse', 'profession'])


@receiver(pre_save, sender=Classe)
def convertir_classe_majuscules(sender, instance, **kwargs):
    """Convertit le nom de la classe en majuscules avant sauvegarde"""
    convertir_majuscules_model(instance, ['nom'])


@receiver(pre_save, sender=Ecole)
def convertir_ecole_majuscules(sender, instance, **kwargs):
    """Convertit les champs texte de l'école en majuscules avant sauvegarde"""
    convertir_majuscules_model(instance, ['nom', 'adresse', 'directeur', 'ire', 'dpe', 'desee'])


@receiver(post_save, sender='paiements.Paiement')
def deverrouiller_apres_premier_paiement(sender, instance, raw=False, **kwargs):
    if raw or instance.statut != 'VALIDE' or Decimal(str(instance.montant or 0)) <= 0:
        return
    from django.db import transaction
    with transaction.atomic():
        eleve = Eleve.objects.select_for_update().filter(
            pk=instance.eleve_id, import_verrouille=True,
            classe__annee_scolaire=instance.annee_scolaire,
        ).first()
        if eleve:
            eleve.import_verrouille = False
            eleve.statut = 'ACTIF'
            eleve.save(update_fields=['import_verrouille', 'statut'])
