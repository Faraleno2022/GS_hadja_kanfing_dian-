"""
Interface de sauvegarde/restauration des donnees (regle 3-2-1).

Reservee aux administrateurs de l'application desktop hors-ligne : c'est la que
se joue la survie des donnees en cas de panne, de vol ou de reinstallation de
l'ordinateur. Sur le serveur en ligne, ces vues sont inactives (les sauvegardes
y sont gerees par l'hebergeur).
"""
import os
from datetime import datetime

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import FileResponse, Http404, HttpResponseForbidden
from django.shortcuts import redirect, render
from django.views.decorators.http import require_POST

from . import sauvegarde as moteur


def _est_desktop():
    """Vrai en application desktop (ou en developpement local hors serveur)."""
    if os.environ.get('OFFLINE_MODE', '0') == '1':
        return True
    if os.environ.get('RENDER_EXTERNAL_HOSTNAME'):
        return False
    from django.conf import settings
    return bool(getattr(settings, 'DEBUG', False))


def _refus(request):
    """Garde commune : desktop + administrateur."""
    if not _est_desktop():
        return HttpResponseForbidden(
            "La sauvegarde locale n'est disponible que dans l'application installee."
        )
    if not (request.user.is_superuser or request.user.is_staff):
        return HttpResponseForbidden(
            "Seul un administrateur peut gerer les sauvegardes."
        )
    return None


def _date_fr(valeur):
    """ISO -> '12/08/2026 a 14:30' (chaine inchangee si illisible)."""
    if not valeur:
        return ''
    try:
        return datetime.fromisoformat(valeur).strftime('%d/%m/%Y a %H:%M')
    except (TypeError, ValueError):
        return str(valeur)


@login_required
def tableau_sauvegarde(request):
    """Etat des sauvegardes, destinations detectees et restauration possible."""
    refus = _refus(request)
    if refus:
        return refus

    config = moteur.charger_config()
    echeance = moteur.prochaine_echeance(config)

    destinations = moteur.etat_destinations()
    for destination in destinations:
        destination['derniere_affichee'] = _date_fr(destination.get('derniere_reussite'))

    journal = moteur.lire_journal(limite=15)
    for entree in journal:
        entree['date_affichee'] = _date_fr(entree.get('date'))
        entree['taille_affichee'] = moteur.taille_lisible(entree.get('octets'))

    archives = moteur.lister_archives_disponibles()
    for archive in archives:
        archive['date_affichee'] = _date_fr(archive.get('date'))
        archive['taille_affichee'] = moteur.taille_lisible(archive.get('octets'))

    contexte = {
        'config': config,
        'destinations': destinations,
        'suggestions': moteur.destinations_suggerees(),
        'cloud_non_montes': moteur.clients_cloud_non_montes(),
        'journal': journal,
        'archives': archives,
        'derniere_affichee': _date_fr(config.get('derniere_sauvegarde')),
        'prochaine_affichee': echeance.strftime('%d/%m/%Y a %H:%M') if echeance else '',
        'a_cloud': any(d.get('type') == 'cloud' for d in destinations),
        'a_amovible': any(d.get('type') in ('amovible', 'disque') for d in destinations),
        'prochaine': echeance,
        'restauration_attente': moteur.restauration_en_attente(),
        'dossier_local': moteur.dossier_local_sauvegardes(),
        'nom_ecole': moteur.infos_ecole()[0],
        'titre_page': 'Sauvegarde des donnees',
    }
    return render(request, 'desktop/sauvegarde.html', contexte)


@login_required
@require_POST
def enregistrer_reglages(request):
    """Active/desactive la sauvegarde automatique et regle sa frequence."""
    refus = _refus(request)
    if refus:
        return refus

    config = moteur.charger_config()
    config['actif'] = request.POST.get('actif') == 'on'
    try:
        heures = int(request.POST.get('intervalle_heures') or 6)
        config['intervalle_heures'] = min(168, max(1, heures))
    except (TypeError, ValueError):
        pass
    for cle, maximum in (
        ('conserver_recentes', 50),
        ('conserver_quotidiennes', 60),
        ('conserver_hebdomadaires', 52),
        ('conserver_mensuelles', 60),
    ):
        try:
            valeur = int(request.POST.get(cle) or moteur.CONFIG_DEFAUT[cle])
            config[cle] = min(maximum, max(1, valeur))
        except (TypeError, ValueError):
            pass

    moteur.enregistrer_config(config)
    messages.success(request, "Reglages de sauvegarde enregistres.")
    return redirect('sauvegarde_tableau')


@login_required
@require_POST
def ajouter_destination(request):
    """Ajoute une destination : support detecte ou dossier saisi a la main."""
    refus = _refus(request)
    if refus:
        return refus

    chemin = (request.POST.get('chemin') or '').strip().strip('"')
    libelle = (request.POST.get('libelle') or '').strip()
    type_support = (request.POST.get('type') or 'dossier').strip()
    if not chemin:
        messages.error(request, "Indiquez le dossier de destination.")
        return redirect('sauvegarde_tableau')

    parent = os.path.dirname(os.path.normpath(chemin)) or chemin
    if not os.path.isdir(chemin) and not os.path.isdir(parent):
        messages.error(
            request,
            f"Dossier introuvable : {chemin}. Branchez la cle USB ou verifiez le chemin.",
        )
        return redirect('sauvegarde_tableau')

    try:
        os.makedirs(chemin, exist_ok=True)
        temoin = os.path.join(chemin, '.myschool_test')
        with open(temoin, 'w', encoding='utf-8') as fichier:
            fichier.write('ok')
        os.remove(temoin)
    except Exception as erreur:
        messages.error(request, f"Ecriture impossible dans ce dossier : {erreur}")
        return redirect('sauvegarde_tableau')

    config = moteur.charger_config()
    normalise = os.path.normcase(os.path.normpath(chemin))
    if any(os.path.normcase(os.path.normpath(d['chemin'])) == normalise
           for d in config['destinations']):
        messages.info(request, "Cette destination est deja configuree.")
        return redirect('sauvegarde_tableau')

    config['destinations'].append({
        'chemin': chemin,
        'libelle': libelle or chemin,
        'type': type_support,
        # Nom du volume : permet de retrouver la cle USB si Windows lui donne
        # une autre lettre au prochain branchement.
        'volume': (request.POST.get('volume') or '').strip(),
    })
    moteur.enregistrer_config(config)
    messages.success(request, f"Destination ajoutee : {libelle or chemin}")
    return redirect('sauvegarde_tableau')


@login_required
@require_POST
def retirer_destination(request):
    refus = _refus(request)
    if refus:
        return refus

    chemin = (request.POST.get('chemin') or '').strip()
    config = moteur.charger_config()
    normalise = os.path.normcase(os.path.normpath(chemin))
    restantes = [
        d for d in config['destinations']
        if os.path.normcase(os.path.normpath(d['chemin'])) != normalise
    ]
    if len(restantes) == len(config['destinations']):
        messages.info(request, "Destination introuvable.")
    else:
        config['destinations'] = restantes
        moteur.enregistrer_config(config)
        messages.success(request, "Destination retiree (les sauvegardes deja copiees restent en place).")
    return redirect('sauvegarde_tableau')


@login_required
@require_POST
def sauvegarder_maintenant(request):
    """Lance immediatement une sauvegarde vers toutes les destinations."""
    refus = _refus(request)
    if refus:
        return refus

    rapport = moteur.executer_sauvegarde(declencheur=f'manuel ({request.user.username})')
    if rapport['ok']:
        messages.success(request, f"Sauvegarde terminee — {rapport['message']}")
    else:
        messages.error(request, rapport['message'])
    for detail in rapport.get('destinations', []):
        if not detail['ok']:
            niveau = messages.warning if detail.get('absent') else messages.error
            niveau(request, f"{detail['libelle']} : {detail['message']}")
    return redirect('sauvegarde_tableau')


@login_required
def telecharger_archive(request):
    """Telecharge une archive (pour la mettre a l'abri ou l'envoyer par mail)."""
    refus = _refus(request)
    if refus:
        return refus

    chemin = (request.GET.get('chemin') or '').strip()
    connues = {a['chemin'] for a in moteur.lister_archives_disponibles()}
    if chemin not in connues or not os.path.isfile(chemin):
        raise Http404("Sauvegarde introuvable.")
    return FileResponse(
        open(chemin, 'rb'), as_attachment=True, filename=os.path.basename(chemin)
    )


@login_required
@require_POST
def restaurer(request):
    """Programme une restauration ; elle s'applique au prochain demarrage."""
    refus = _refus(request)
    if refus:
        return refus

    chemin = (request.POST.get('chemin') or '').strip().strip('"')
    connues = {a['chemin'] for a in moteur.lister_archives_disponibles()}
    if chemin not in connues and not os.path.isfile(chemin):
        messages.error(request, "Sauvegarde introuvable (support debranche ?).")
        return redirect('sauvegarde_tableau')

    try:
        marqueur = moteur.demander_restauration(chemin, demandee_par=request.user.username)
    except Exception as erreur:
        messages.error(request, str(erreur))
        return redirect('sauvegarde_tableau')

    messages.success(
        request,
        "Restauration programmee depuis « %s ». Fermez puis relancez MySchoolGN : "
        "les donnees seront remises en place au demarrage. La base actuelle sera "
        "conservee dans le dossier backups." % os.path.basename(marqueur['archive']),
    )
    return redirect('sauvegarde_tableau')


@login_required
@require_POST
def annuler_restauration(request):
    refus = _refus(request)
    if refus:
        return refus

    if moteur.annuler_restauration():
        messages.success(request, "Restauration annulee.")
    else:
        messages.info(request, "Aucune restauration en attente.")
    return redirect('sauvegarde_tableau')
