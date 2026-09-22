"""Validation explicite et transactionnelle des élèves proposés."""
import unicodedata

from django.core.exceptions import PermissionDenied, ValidationError
from django.db import IntegrityError, transaction
from django.utils import timezone

from .collecte_permissions import peut_gerer_collecte
from .models import Classe, Eleve, HistoriqueEleve, Responsable
from .models_collecte import PropositionEleve


def cle_nom(value):
    value = unicodedata.normalize('NFKD', value or '')
    return ' '.join(''.join(c for c in value if not unicodedata.combining(c)).casefold().split())


def homonymes(proposition, eleves=None):
    if eleves is None:
        eleves = Eleve.objects.filter(
            classe_id=proposition.envoi.lien.classe_id,
            classe__ecole_id=proposition.envoi.lien.ecole_id,
        )
    return [
        eleve for eleve in eleves
        if cle_nom(eleve.nom) == cle_nom(proposition.nom)
        and cle_nom(eleve.prenom) == cle_nom(proposition.prenom)
    ]


@transaction.atomic
def decider_proposition(pk, user, action, verrouiller=True, confirmer_homonymes=False):
    if not peut_gerer_collecte(user):
        raise PermissionDenied
    if action not in ('accepter', 'refuser'):
        raise ValidationError("Décision invalide.")
    base = PropositionEleve.objects.select_related('envoi__lien').get(pk=pk)
    lien = base.envoi.lien
    if not user.is_superuser and lien.ecole_id != user.profil.ecole_id:
        raise PermissionDenied
    # Une classe à la fois : deux validations concurrentes ne créent pas
    # deux élèves pour une même proposition ou pour le même homonyme.
    classe = Classe.objects.select_for_update().get(pk=lien.classe_id)
    proposition = PropositionEleve.objects.select_for_update().get(pk=pk)
    if proposition.statut != PropositionEleve.Statut.EN_ATTENTE:
        return None
    if classe.ecole_id != lien.ecole_id or classe.annee_scolaire != lien.annee_scolaire:
        raise ValidationError("La classe de ce lien a changé. Cette proposition ne peut pas être validée ici.")
    if action == 'accepter':
        if not confirmer_homonymes and homonymes(proposition):
            raise ValidationError(
                f"{proposition.nom_complet} : un élève de mêmes prénom et nom existe déjà. "
                "Vérifiez la proposition avant de confirmer la création d'un homonyme."
            )
        responsable = None
        if proposition.prenom_responsable and proposition.nom_responsable:
            # Ne jamais rattacher un parent d'une autre école à partir de son téléphone.
            responsable = Responsable.objects.create(
                prenom=proposition.prenom_responsable, nom=proposition.nom_responsable,
                telephone=proposition.telephone_responsable, adresse=proposition.adresse,
                relation='AUTRE',
            )
        for tentative in range(3):
            try:
                with transaction.atomic():
                    eleve = Eleve.objects.create(
                        prenom=proposition.prenom, nom=proposition.nom, sexe=proposition.sexe,
                        date_naissance=proposition.date_naissance,
                        lieu_naissance=proposition.lieu_naissance,
                        classe=classe, date_inscription=timezone.localdate(),
                        import_verrouille=verrouiller, responsable_principal=responsable,
                        cree_par=user,
                    )
                break
            except IntegrityError:
                if tentative == 2:
                    raise ValidationError("Une création simultanée empêche l'attribution du matricule. Réessayez.")
        HistoriqueEleve.objects.create(
            eleve=eleve, action='CREATION', utilisateur=user,
            description=f"Proposition de {base.envoi.auteur} validée depuis la collecte #{lien.pk}.",
        )
        proposition.eleve = eleve
        proposition.statut = PropositionEleve.Statut.ACCEPTEE
    else:
        proposition.statut = PropositionEleve.Statut.REFUSEE
    proposition.traite_par = user
    proposition.traite_le = timezone.now()
    proposition.save(update_fields=['eleve', 'statut', 'traite_par', 'traite_le'])
    return proposition
