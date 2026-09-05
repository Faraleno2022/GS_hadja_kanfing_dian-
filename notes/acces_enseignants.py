"""Périmètre commun à toutes les entrées de l'espace enseignant."""
import hashlib
import secrets
from decimal import Decimal, InvalidOperation

from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from django.utils.crypto import constant_time_compare

from eleves.models import Classe, Eleve
from salaires.models import niveaux_classes_pour_type_enseignant
from .models import (AccesEnseignantTemporaire, ClasseNote, MatiereNote,
                     NoteMensuelle, CompositionNote, AppreciationMaternelle)

SESSION_KEY = 'acces_notes_empreinte'


def nouveau_lien():
    token = secrets.token_hex(32)
    return token, empreinte(token)


def empreinte(token):
    return hashlib.sha256(token.encode('utf-8')).hexdigest()


def classes_affectees(enseignant):
    """Rapprochement exact école + nom + année, sans repli inter-écoles."""
    today = timezone.localdate()
    affectations = enseignant.affectations.filter(
        actif=True, sync_deleted_at__isnull=True, date_debut__lte=today,
        classe__ecole_id=enseignant.ecole_id, classe__sync_deleted_at__isnull=True,
        classe__niveau__in=niveaux_classes_pour_type_enseignant(enseignant.type_enseignant),
    ).filter(Q(date_fin__isnull=True) | Q(date_fin__gte=today)).select_related('classe')
    pairs = Q(pk__in=[])
    for affectation in affectations:
        pairs |= Q(nom=affectation.classe.nom, annee_scolaire=affectation.classe.annee_scolaire)
    return ClasseNote.objects.filter(
        pairs, ecole_id=enseignant.ecole_id, actif=True,
        sync_deleted_at__isnull=True, niveau_enseignement=enseignant.type_enseignant,
    ).order_by('annee_scolaire', 'nom')


def classes_autorisees(acces):
    return classes_affectees(acces.enseignant).filter(acces_enseignants=acces)


def matieres_autorisees(acces, classe):
    return MatiereNote.objects.filter(
        classe=classe, actif=True, sync_deleted_at__isnull=True, acces_enseignants=acces,
    ).order_by('nom')


def eleves_autorises(classe):
    classe_eleve = Classe.objects.filter(
        ecole_id=classe.ecole_id, nom=classe.nom, annee_scolaire=classe.annee_scolaire,
        sync_deleted_at__isnull=True,
    ).first()
    return Eleve.objects.filter(
        classe=classe_eleve, statut='ACTIF', sync_deleted_at__isnull=True,
    ).order_by('nom', 'prenom', 'matricule') if classe_eleve else Eleve.objects.none()


def verifier_session(request, verrouiller=False):
    if not request.user.is_authenticated:
        raise PermissionDenied('Votre session enseignant est absente ou a expiré. Rouvrez le lien personnel transmis par votre école, puis cliquez sur « Ouvrir mon espace enseignant ». Une adresse de saisie seule ne permet pas de vous connecter.')
    qs = AccesEnseignantTemporaire.objects
    if verrouiller:
        qs = qs.select_for_update()
    else:
        qs = qs.select_related('utilisateur__profil', 'enseignant', 'ecole')
    acces = qs.filter(
        utilisateur=request.user,
    ).first()
    if not acces:
        raise PermissionDenied('Le compte actuellement connecté ne dispose pas d’un accès temporaire enseignant. Ouvrez le lien personnel de l’enseignant dans une fenêtre privée pour conserver votre session actuelle.')
    if not acces.est_valide or not constant_time_compare(
        acces.empreinte_lien, request.session.get(SESSION_KEY, ''),
    ):
        raise PermissionDenied('Accès expiré ou révoqué. Demandez un nouveau lien à votre école.')
    return acces


def configuration(classe, genre, periode):
    if classe.niveau_enseignement == 'MATERNELLE':
        model, field, choices, expected = AppreciationMaternelle, 'trimestre', AppreciationMaternelle.TRIMESTRE_CHOICES, 'maternelle'
    elif genre == 'mensuelle':
        model, field, choices, expected = NoteMensuelle, 'mois', NoteMensuelle.MOIS_CHOICES, 'mensuelle'
    else:
        model, field, choices, expected = CompositionNote, 'periode', CompositionNote.PERIODE_CHOICES, 'composition'
    if genre != expected or periode not in dict(choices):
        raise ValidationError('Type de notes ou période invalide.')
    return model, field


def valeur_note(raw, classe):
    value = str(raw).strip().upper().replace(',', '.')
    if not value:
        return None  # Une cellule vide ne supprime jamais une note existante.
    if value == 'ABS':
        return {'absent': True, 'appreciation': ''} if classe.niveau_enseignement == 'MATERNELLE' else {'absent': True, 'note': None}
    if classe.niveau_enseignement == 'MATERNELLE':
        if value not in dict(AppreciationMaternelle.APPRECIATION_CHOICES):
            raise ValidationError('Appréciation invalide : utilisez A+, A, B+, B, B-, C, D ou ABS.')
        return {'absent': False, 'appreciation': value}
    maximum = 10 if classe.niveau_enseignement == 'PRIMAIRE' else 20
    try:
        number = Decimal(value)
        if not number.is_finite() or not 0 <= number <= maximum or number != number.quantize(Decimal('0.01')):
            raise InvalidOperation
    except (InvalidOperation, ValueError):
        raise ValidationError(f'Note invalide : nombre entre 0 et {maximum}, avec deux décimales maximum, ou ABS.')
    return {'absent': False, 'note': number}


def valider_cellules(acces, classe, cellules):
    eleves = set(eleves_autorises(classe).values_list('pk', flat=True))
    matieres = set(matieres_autorisees(acces, classe).values_list('pk', flat=True))
    seen, result = set(), []
    if not isinstance(cellules, list) or len(cellules) > 10000:
        raise ValidationError('Le lot ne peut pas dépasser 10 000 cellules.')
    for cell in cellules:
        try:
            eid, mid = int(cell['eleve']), int(cell['matiere'])
            raw = cell['valeur']
        except (KeyError, TypeError, ValueError):
            raise ValidationError('Cellule mal formée.')
        if eid not in eleves or mid not in matieres:
            raise PermissionDenied('Élève ou matière hors de votre affectation.')
        if (eid, mid) in seen:
            raise ValidationError('Un élève apparaît plusieurs fois pour la même matière.')
        seen.add((eid, mid))
        try:
            value = valeur_note(raw, classe)
        except ValidationError as exc:
            raise ValidationError(f'Élève #{eid}, matière #{mid} : {exc.messages[0]}')
        if value is not None:
            result.append((eid, mid, value))
    return result


@transaction.atomic
def enregistrer_cellules(request, classe_id, genre, periode, cellules):
    # La révocation et l'expiration sont revérifiées au moment de l'écriture.
    acces = verifier_session(request, verrouiller=True)
    classe = classes_autorisees(acces).filter(pk=classe_id).first()
    if not classe:
        raise PermissionDenied('Classe non autorisée.')
    model, field = configuration(classe, genre, periode)
    values = valider_cellules(acces, classe, cellules)
    for eid, mid, value in values:
        model.objects.update_or_create(
            eleve_id=eid, matiere_id=mid, annee_scolaire=classe.annee_scolaire,
            **{field: periode}, defaults={**value, 'cree_par': request.user},
        )
    return len(values)
