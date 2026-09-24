"""Validation complète d'une saisie avant son enregistrement atomique."""
import json
from decimal import Decimal, InvalidOperation

from django.db import transaction
from django.http import JsonResponse

from eleves.models import Eleve
from utilisateurs.permissions import has_permission
from utilisateurs.utils import filter_by_user_school
from .classes_utils import normaliser_nom_classe, trouver_classe_eleve
from .models import CompositionNote, MatiereNote, NoteMensuelle


def _note_validee(value, maximum):
    if value is None:
        return None
    absent = False
    if isinstance(value, dict):
        absent = value.get('absent', False)
        value = value.get('note')
    if not isinstance(absent, bool):
        raise ValueError("L'indicateur d'absence doit être vrai ou faux.")
    if absent:
        return {'note': Decimal('0'), 'absent': True}
    if value is None or value == '':
        return None
    if isinstance(value, bool):
        raise ValueError('La note doit être un nombre.')
    try:
        note = Decimal(str(value).replace(',', '.'))
    except InvalidOperation:
        raise ValueError('La note doit être un nombre.') from None
    if not note.is_finite() or note < 0 or note > maximum:
        raise ValueError(f'Note invalide : elle doit être entre 0 et {maximum}.')
    if note != note.quantize(Decimal('0.01')):
        raise ValueError('La note ne peut avoir plus de deux décimales.')
    return {'note': note, 'absent': False}


def classe_de_saisie(classe_note):
    """Ne pas assimiler deux sections A/B au seul motif du même niveau."""
    from eleves.models import Classe
    nom = normaliser_nom_classe(classe_note.nom)
    candidats = [
        classe for classe in Classe.objects.filter(
            ecole_id=classe_note.ecole_id, annee_scolaire=classe_note.annee_scolaire,
        ) if normaliser_nom_classe(classe.nom) == nom
    ]
    return candidats[0] if len(candidats) == 1 else None


def enregistrer_notes_guineennes(request):
    def refus(message, status=400):
        return JsonResponse({'success': False, 'error': message}, status=status)

    if request.method != 'POST':
        response = refus('Méthode non autorisée', 405)
        response['Allow'] = 'POST'
        return response
    if not has_permission(request.user, 'peut_gerer_notes'):
        return refus("Vous n'êtes pas autorisé à gérer les notes.", 403)
    try:
        data = json.loads(request.body)
    except (ValueError, UnicodeDecodeError):
        return refus('Données JSON invalides')
    if not isinstance(data, dict):
        return refus('Un objet JSON est attendu.')
    try:
        eleve_id = int(str(data.get('eleve_id')))
        matiere_id = int(str(data.get('matiere_id')))
    except (ValueError, TypeError):
        return refus('Identifiants élève et matière invalides.')
    matiere = filter_by_user_school(
        MatiereNote.objects.select_related('classe').filter(actif=True, classe__actif=True),
        request.user, 'classe__ecole',
    ).filter(pk=matiere_id).first()
    eleve = filter_by_user_school(
        Eleve.pedagogiques.select_related('classe').filter(statut='ACTIF'),
        request.user, 'classe__ecole',
    ).filter(pk=eleve_id).first()
    if matiere is None or eleve is None:
        return refus('Élève ou matière non trouvé.', 404)
    classe_note = matiere.classe
    classe_eleve = classe_de_saisie(classe_note)
    if classe_eleve is None or eleve.classe_id != classe_eleve.pk:
        return refus("L'élève n'appartient pas à la classe de cette matière.")
    annee = classe_note.annee_scolaire
    if data.get('annee_scolaire') not in (None, '', annee):
        return refus("L'année scolaire ne correspond pas à la classe.")
    secondaire = classe_note.niveau_enseignement == 'SECONDAIRE'
    maximum = Decimal('10') if classe_note.niveau_enseignement == 'PRIMAIRE' else Decimal('20')
    periodes = {
        f'composition{i}': f"{'SEMESTRE' if secondaire else 'TRIMESTRE'}_{i}"
        for i in range(1, 3 if secondaire else 4)
    }
    lignes = []
    try:
        for champ, model, field, mapping in (
            ('notes_mois', NoteMensuelle, 'mois', {code: code for code, _ in NoteMensuelle.MOIS_CHOICES}),
            ('compositions', CompositionNote, 'periode', periodes),
        ):
            values = data.get(champ, {})
            if not isinstance(values, dict):
                raise ValueError(f'Le champ {champ} doit être un objet.')
            seen = set()
            for key, value in values.items():
                key = key.upper() if champ == 'notes_mois' else key
                if key not in mapping or key in seen:
                    raise ValueError('Période inconnue ou répétée.')
                seen.add(key)
                defaults = _note_validee(value, maximum)
                if defaults is not None:
                    lignes.append((model, field, mapping[key], defaults))
    except ValueError as exc:
        return refus(str(exc))

    saved = updated = 0
    with transaction.atomic():
        # Sérialiser les soumissions concernant un même élève.
        eleve_verrouille = Eleve.pedagogiques.select_for_update().filter(pk=eleve.pk, statut='ACTIF').first()
        if eleve_verrouille is None or eleve_verrouille.classe_id != classe_eleve.pk:
            return refus("L'affectation de l'élève a changé. Rechargez la page.")
        for model, field, periode, defaults in lignes:
            _, created = model.objects.update_or_create(
                eleve=eleve, matiere=matiere, annee_scolaire=annee,
                **{field: periode}, defaults=defaults,
            )
            saved += int(created)
            updated += int(not created)
        if lignes:
            from .utils_rangs import invalider_cache_rangs
            transaction.on_commit(lambda: invalider_cache_rangs(classe_note))
    return JsonResponse({
        'success': True,
        'message': f'{saved} note(s) créée(s), {updated} mise(s) à jour',
        'saved': saved, 'updated': updated,
    })
