"""Synchronisation automatique en tache de fond (poste offline <-> serveur).

Meme principe que le worker de sauvegarde (ecole_moderne/sauvegarde.py) :
une seule tache demon, demarree une fois au lancement de l'application.

Vitesse :
- Push declenche immediatement des qu'un changement local est enregistre
  (evenement, pas d'attente de l'intervalle) grace a `notifier_changement()`,
  appele par les signaux post_save/pre_delete de `synchronisation.signals`.
- Pull effectue a intervalle court (configurable, quelques secondes) car le
  serveur ne peut pas pousser vers le poste (pas de canal push serveur->client).
- Transport mutualise (connexions persistantes + gzip) via `synchronisation.client`.
"""
import json
import os
import threading
import time

from django.conf import settings


INTERVALLE_DEFAUT = 10  # secondes : verification rapide des changements distants
INTERVALLE_MINIMUM = 3
DELAI_DEMARRAGE_DEFAUT = 15

_verrou = threading.Lock()
_worker_demarre = False
_reveil = threading.Event()


def notifier_changement():
    """Reveille immediatement le worker (appele par les signaux de sync)."""
    _reveil.set()


def _chemin_config(base_dir):
    return os.path.join(base_dir, 'sync_config.json')


def charger_config(base_dir):
    """Configuration effective : variables d'environnement (.env) completees
    par sync_config.json a cote de l'executable, si present."""
    config = {
        'server_url': (getattr(settings, 'MYSCHOOL_SYNC_SERVER_URL', '') or '').rstrip('/'),
        'device_id': getattr(settings, 'MYSCHOOL_SYNC_DEVICE_ID', '') or '',
        'token': getattr(settings, 'MYSCHOOL_SYNC_TOKEN', '') or '',
        'ecole_id': getattr(settings, 'MYSCHOOL_SYNC_ECOLE_ID', '') or '',
        'interval': INTERVALLE_DEFAUT,
    }

    chemin = _chemin_config(base_dir)
    if os.path.exists(chemin):
        try:
            with open(chemin, 'r', encoding='utf-8') as fichier:
                donnees = json.load(fichier)
        except Exception:
            donnees = {}
        if isinstance(donnees, dict):
            config['server_url'] = (donnees.get('MYSCHOOL_SYNC_SERVER_URL') or config['server_url']).rstrip('/')
            config['device_id'] = donnees.get('MYSCHOOL_SYNC_DEVICE_ID') or config['device_id']
            config['token'] = donnees.get('MYSCHOOL_SYNC_TOKEN') or config['token']
            config['ecole_id'] = donnees.get('MYSCHOOL_SYNC_ECOLE_ID') or config['ecole_id']
            try:
                config['interval'] = max(INTERVALLE_MINIMUM, int(donnees.get('MYSCHOOL_SYNC_INTERVAL') or INTERVALLE_DEFAUT))
            except (TypeError, ValueError):
                pass

    return config


def _pret(config):
    return bool(config['server_url'] and config['device_id'] and config['token'] and config['ecole_id'])


def _cycle(base_dir):
    """Un aller-retour push + pull. Retourne (config, nb_pousses, nb_recus)."""
    from eleves.models import Ecole
    from .client import pull_changes, push_pending

    config = charger_config(base_dir)
    if not _pret(config):
        return config, 0, 0

    # Un poste est toujours dedie a une seule ecole : son id local (attribue
    # a l'amorçage) ne correspond pas forcement a config['ecole_id'] (celui
    # du serveur). On prend l'ecole unique deja presente, quel que soit son id.
    ecole = Ecole.objects.first()
    if not ecole:
        # Poste tout juste installe : rien en local encore, y compris
        # l'ecole elle-meme. pull_changes(ecole=None) l'amorce depuis le
        # premier lot recu du serveur avant de traiter le reste. Sans ce
        # cas particulier, le worker ne ferait jamais rien pour un poste
        # neuf (ecole introuvable en boucle, silencieusement).
        nb_recus = pull_changes(
            config['server_url'], config['device_id'], config['token'],
            ecole=None, initial=True,
        )
        return config, 0, nb_recus

    nb_pousses = push_pending(config['server_url'], config['device_id'], config['token'], ecole)
    nb_recus = pull_changes(config['server_url'], config['device_id'], config['token'], ecole)
    return config, nb_pousses, nb_recus


def _boucle(base_dir, delai_demarrage):
    time.sleep(max(0, delai_demarrage))
    while True:
        intervalle = INTERVALLE_DEFAUT
        try:
            config, nb_pousses, nb_recus = _cycle(base_dir)
            intervalle = config.get('interval', INTERVALLE_DEFAUT)
            if nb_pousses or nb_recus:
                print(f"[Sync] {nb_pousses} envoye(s), {nb_recus} recu(s).")
        except Exception as exc:
            print(f"[Sync] Cycle ignore ({exc})")

        _reveil.wait(timeout=intervalle)
        _reveil.clear()


def demarrer_worker(base_dir, delai_demarrage=DELAI_DEMARRAGE_DEFAUT):
    """Demarre la synchronisation automatique en tache de fond (idempotent).

    Retourne True si le worker a ete demarre, False s'il tournait deja.
    """
    global _worker_demarre
    with _verrou:
        if _worker_demarre:
            return False
        _worker_demarre = True
    threading.Thread(
        target=_boucle, args=(base_dir, delai_demarrage),
        name='sync-auto', daemon=True,
    ).start()
    return True
