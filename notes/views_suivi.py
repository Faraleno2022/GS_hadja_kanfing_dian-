"""
Saisie des notes de suivi continu (cours/interrogations, orales, écrites,
devoirs, participation) qui produisent un bonus plafonné sur la note mensuelle.
"""
from decimal import Decimal, InvalidOperation

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.db import transaction
from django.http import HttpResponseBadRequest
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme

from eleves.models import Classe as ClasseEleve, Eleve
from .models import ClasseNote, MatiereNote, NoteSuivi, NoteMensuelle
from .calculs_moyennes import (
    BONUS_SUIVI_MAX, details_bonus_suivi_batch, _appliquer_bonus,
)
from .utils_rangs import invalider_cache_rangs


def _eleves_de_classe_note(classe_note):
    """Élèves actifs correspondant à une ClasseNote (mapping par nom+année+école)."""
    classe_eleve = ClasseEleve.objects.filter(
        nom=classe_note.nom,
        annee_scolaire=classe_note.annee_scolaire,
        ecole=classe_note.ecole,
    ).first()
    if not classe_eleve:
        return []
    return list(Eleve.pedagogiques.filter(classe=classe_eleve, statut='ACTIF')
                .order_by('prenom', 'nom'))


@login_required
def toggle_bonus_suivi(request):
    """Active/désactive le bonus de suivi pour l'école de l'utilisateur."""
    profil = getattr(request.user, 'profil', None)
    ecole = profil.ecole if profil else None
    retour = request.POST.get('next') or request.GET.get('next')
    if not retour or not url_has_allowed_host_and_scheme(
        retour, allowed_hosts={request.get_host()}, require_https=request.is_secure(),
    ):
        retour = reverse('notes:saisie_suivi')
    if not ecole:
        messages.error(request, "Aucune école associée à votre compte.")
        return redirect('notes:saisie_suivi')
    if request.method == 'POST':
        ecole.bonus_suivi_actif = not ecole.bonus_suivi_actif
        ecole.save(update_fields=['bonus_suivi_actif'])
        # Recalcul nécessaire: vider le cache des moyennes/rangs
        from .utils_rangs import invalider_cache_rangs
        for cn in ClasseNote.objects.filter(ecole=ecole, actif=True):
            invalider_cache_rangs(cn)
        if ecole.bonus_suivi_actif:
            messages.success(request, "✅ Bonus de suivi ACTIVÉ pour votre école.")
        else:
            messages.info(request, "⛔ Bonus de suivi DÉSACTIVÉ pour votre école.")
    try:
        return redirect(retour)
    except Exception:
        return redirect('notes:saisie_suivi')


@login_required
def saisie_suivi(request):
    """Saisie d'une colonne de notes de suivi (classe + matière + mois + type)."""
    user_profil = getattr(request.user, 'profil', None)
    ecole = user_profil.ecole if user_profil else None
    classes = ClasseNote.objects.filter(actif=True).select_related('ecole').order_by('niveau', 'nom')
    if not request.user.is_superuser:
        classes = classes.filter(ecole=ecole) if ecole else classes.none()

    classe_id = (request.GET.get('classe_id') or request.POST.get('classe_id') or '').strip()
    matiere_id = (request.GET.get('matiere_id') or request.POST.get('matiere_id') or '').strip()
    mois = (request.GET.get('mois') or request.POST.get('mois') or '').strip()
    type_note = (request.GET.get('type_note') or request.POST.get('type_note') or 'COURS').strip()
    numero_raw = (request.GET.get('numero') or request.POST.get('numero') or '1').strip()
    try:
        numero = max(1, min(20, int(numero_raw)))
    except (ValueError, TypeError):
        numero = 1

    classe = None
    matiere = None
    matieres = []
    eleves = []
    notes_existantes = {}

    if mois and mois not in dict(NoteSuivi.MOIS_CHOICES):
        return HttpResponseBadRequest("Mois invalide.")
    if type_note not in dict(NoteSuivi.TYPE_CHOICES):
        return HttpResponseBadRequest("Type de note invalide.")

    if classe_id.isdigit():
        classe = get_object_or_404(classes, pk=int(classe_id))
        matieres = list(MatiereNote.objects.filter(classe=classe, actif=True).order_by('nom'))
        eleves = _eleves_de_classe_note(classe)
        if matiere_id.isdigit():
            matiere = get_object_or_404(MatiereNote, classe=classe, actif=True, pk=int(matiere_id))

    if request.method == 'POST':
        if not (classe and matiere and mois):
            return HttpResponseBadRequest("Choisissez une classe, une matière et un mois.")
        # Valider toute la colonne avant de modifier les notes enregistrées.
        valeurs = {}
        for eleve in eleves:
            cle = f'note_{eleve.id}'
            if cle not in request.POST:
                continue
            brut = (request.POST.get(cle) or '').strip().replace(',', '.')
            if not brut:
                valeurs[eleve.id] = None
                continue
            try:
                valeur = Decimal(brut)
                if not valeur.is_finite() or not 0 <= valeur <= 20:
                    raise ValueError
                valeurs[eleve.id] = valeur
            except (InvalidOperation, ValueError):
                return HttpResponseBadRequest("Les notes de suivi doivent être comprises entre 0 et 20.")

        enregistres, supprimes = 0, 0
        annee = classe.annee_scolaire
        with transaction.atomic():
            for eleve in eleves:
                if eleve.id not in valeurs:
                    continue
                valeur = valeurs[eleve.id]
                if valeur is None:
                    supprimes += NoteSuivi.objects.filter(
                        eleve=eleve, matiere=matiere, mois=mois,
                        type_note=type_note, numero=numero, annee_scolaire=annee).delete()[0]
                else:
                    NoteSuivi.objects.update_or_create(
                        eleve=eleve, matiere=matiere, mois=mois,
                        type_note=type_note, numero=numero, annee_scolaire=annee,
                        defaults={'note': valeur, 'cree_par': request.user},
                    )
                    enregistres += 1
        # Invalider les moyennes/rangs (le bonus modifie la note du mois)
        invalider_cache_rangs(classe, mois)
        messages.success(
            request,
            f"Suivi enregistré : {enregistres} note(s), {supprimes} supprimée(s) — "
            f"{matiere.nom} / {mois} / {dict(NoteSuivi.TYPE_CHOICES).get(type_note, type_note)}.")
        return redirect(f"{request.path}?classe_id={classe.id}&matiere_id={matiere.id}"
                        f"&mois={mois}&type_note={type_note}&numero={numero}")

    # Une seule base de calcul pour le détail et la note corrigée du bulletin.
    bonus_actif = bool(getattr(classe.ecole if classe else ecole, 'bonus_suivi_actif', False))
    details, mensuelles = {}, {}
    if classe and matiere and mois:
        eleve_ids = [e.id for e in eleves]
        notes_existantes = dict(NoteSuivi.objects.filter(
            eleve_id__in=eleve_ids, matiere=matiere, mois=mois, type_note=type_note,
            numero=numero, annee_scolaire=classe.annee_scolaire,
        ).values_list('eleve_id', 'note'))
        details = details_bonus_suivi_batch(
            eleve_ids, [matiere.id], [mois], classe.annee_scolaire,
        )
        mensuelles = {n.eleve_id: n for n in NoteMensuelle.objects.filter(
            eleve_id__in=eleve_ids, matiere=matiere, mois=mois,
            annee_scolaire=classe.annee_scolaire,
        )}

    lignes = []
    for eleve in eleves:
        detail = details.get((eleve.id, matiere.id, mois), {}) if matiere else {}
        mensuelle = mensuelles.get(eleve.id)
        absent = bool(mensuelle and mensuelle.absent)
        avant = float(mensuelle.note) if mensuelle and mensuelle.note is not None and not absent else None
        bonus = detail.get('bonus', 0.0)
        apres = _appliquer_bonus(avant, bonus)
        gain = max(0.0, apres - avant) if avant is not None else 0.0
        lignes.append({
            'eleve': eleve,
            'note': notes_existantes.get(eleve.id, ''),
            'detail': detail,
            'nombre_notes': detail.get('nombre_notes', 0),
            'moyenne_suivi': detail.get('moyenne_suivi'),
            'bonus_calcule': detail.get('bonus_calcule', 0),
            'bonus': bonus,
            'note_avant': avant,
            'note_apres': apres,
            'gain_reel': gain,
            'absent': absent,
            'plafonne': avant is not None and avant + bonus > 20,
        })

    context = {
        'titre_page': "Notes de suivi (bonus)",
        'classes': classes,
        'classe': classe,
        'classe_id': classe_id,
        'matieres': matieres,
        'matiere': matiere,
        'matiere_id': matiere_id,
        'mois': mois,
        'mois_choices': NoteSuivi.MOIS_CHOICES,
        'type_note': type_note,
        'type_choices': NoteSuivi.TYPE_CHOICES,
        'numero': numero,
        'numeros': range(1, 21),
        'lignes': lignes,
        'bonus_max': BONUS_SUIVI_MAX,
        'bonus_actif': bonus_actif,
        'peut_basculer_bonus': bool(ecole and (not classe or classe.ecole_id == ecole.id)),
        'beneficiaires': sum(l['gain_reel'] > 0 for l in lignes),
        'sans_note_mensuelle': sum(l['note_avant'] is None for l in lignes),
        'plafonnes': sum(l['plafonne'] for l in lignes),
    }
    return render(request, 'notes/saisie_suivi.html', context)
