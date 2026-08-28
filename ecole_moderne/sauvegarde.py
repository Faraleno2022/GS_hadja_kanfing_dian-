"""
Sauvegarde automatique des donnees (regle 3-2-1) — application Desktop.

Objectif : qu'une panne de machine, un vol, un formatage ou une reinstallation
ne fasse JAMAIS perdre les donnees de l'ecole.

Regle 3-2-1 appliquee ici :
  * 3 copies   : l'installation elle-meme + le dossier local `backups/` +
                 chaque destination externe configuree ;
  * 2 supports : un dossier synchronise dans le cloud (OneDrive / Google Drive /
                 Dropbox, deja installe sur la plupart des postes) et une cle USB
                 ou un disque externe laisse sur place ;
  * 1 hors-site : le dossier cloud part automatiquement chez le fournisseur des
                 que la connexion revient.

Ce que contient une sauvegarde, sur chaque destination :

    <destination>/MySchoolGN_Sauvegardes/<ecole>/
        archives/    MySchoolGN_<ecole>_20260812_1430.zip   (base + manifeste)
        medias/      miroir des photos/logos (copie incrementale)
        DERNIERE_SAUVEGARDE.txt
        COMMENT_RESTAURER.txt

La base de donnees est petite : elle est archivee entierement a chaque passage.
Les medias (photos d'eleves, logos) sont volumineux : ils sont copies en miroir,
donc seuls les fichiers nouveaux ou modifies transitent — indispensable pour une
cle USB ou un dossier cloud.

Aucune dependance externe : uniquement la bibliotheque standard. Django n'est
importe QUE dans les fonctions qui en ont besoin, afin que la restauration au
demarrage fonctionne avant meme `django.setup()`.

Configuration par machine (jamais embarquee dans le build) :
`backup_config.json`, a la racine du dossier d'installation.
"""
import hashlib
import json
import os
import shutil
import sqlite3
import threading
import time
import unicodedata
import zipfile
from datetime import datetime, timedelta

# ─── Emplacements ─────────────────────────────────────────────────────────────
NOM_CONFIG = 'backup_config.json'
NOM_MARQUEUR_RESTAURATION = '.restauration_en_attente.json'
DOSSIER_RACINE_DESTINATION = 'MySchoolGN_Sauvegardes'
FORMAT_ARCHIVE = 1

CONFIG_DEFAUT = {
    'actif': True,
    'intervalle_heures': 6,
    'sauvegarde_au_demarrage': True,
    'destinations': [],           # [{'chemin', 'libelle', 'type'}]
    'conserver_recentes': 8,      # les N dernieres, quelle que soit leur date
    'conserver_quotidiennes': 7,
    'conserver_hebdomadaires': 4,
    'conserver_mensuelles': 12,
    'derniere_sauvegarde': None,  # ISO
}

_lock_sauvegarde = threading.Lock()
_worker_demarre = False
_lock_worker = threading.Lock()


def base_dir():
    """Dossier d'installation (contient db.sqlite3, media/, backups/)."""
    depuis_env = os.environ.get('MYSCHOOL_BASE_DIR')
    if depuis_env:
        return depuis_env
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def chemin_config():
    return os.path.join(base_dir(), NOM_CONFIG)


def chemin_db():
    """Chemin reel de la base SQLite (Django si dispo, sinon convention)."""
    try:
        from django.db import connection
        nom = connection.settings_dict.get('NAME')
        if nom and str(nom).endswith('.sqlite3'):
            return str(nom)
    except Exception:
        pass
    return os.path.join(base_dir(), 'db.sqlite3')


def chemin_media():
    try:
        from django.conf import settings
        racine = getattr(settings, 'MEDIA_ROOT', None)
        if racine:
            return str(racine)
    except Exception:
        pass
    return os.path.join(base_dir(), 'media')


def dossier_local_sauvegardes():
    chemin = os.path.join(base_dir(), 'backups', 'archives')
    os.makedirs(chemin, exist_ok=True)
    return chemin


def chemin_journal():
    return os.path.join(base_dir(), 'backups', 'journal_sauvegarde.json')


# ─── Configuration ────────────────────────────────────────────────────────────
def charger_config():
    """Configuration de la machine, completee par les valeurs par defaut."""
    config = dict(CONFIG_DEFAUT)
    try:
        with open(chemin_config(), 'r', encoding='utf-8') as fichier:
            enregistree = json.load(fichier)
        if isinstance(enregistree, dict):
            config.update({k: v for k, v in enregistree.items() if k in CONFIG_DEFAUT})
    except Exception:
        pass
    destinations = []
    for item in config.get('destinations') or []:
        if isinstance(item, str):
            destinations.append({'chemin': item, 'libelle': item, 'type': 'dossier', 'volume': ''})
        elif isinstance(item, dict) and item.get('chemin'):
            destinations.append({
                'chemin': item['chemin'],
                'libelle': item.get('libelle') or item['chemin'],
                'type': item.get('type') or 'dossier',
                'volume': item.get('volume') or '',
            })
    config['destinations'] = destinations
    return config


def enregistrer_config(config):
    a_ecrire = {cle: config.get(cle, valeur) for cle, valeur in CONFIG_DEFAUT.items()}
    temporaire = chemin_config() + '.tmp'
    with open(temporaire, 'w', encoding='utf-8') as fichier:
        json.dump(a_ecrire, fichier, indent=2, ensure_ascii=False)
    os.replace(temporaire, chemin_config())
    return a_ecrire


# ─── Detection des supports (Windows) ─────────────────────────────────────────
def _lettres_lecteurs():
    """Lettres de lecteurs presents, avec leur type Windows."""
    if os.name != 'nt':
        return []
    import ctypes
    import string
    kernel32 = ctypes.windll.kernel32
    masque = kernel32.GetLogicalDrives()
    resultats = []
    for index, lettre in enumerate(string.ascii_uppercase):
        if not (masque >> index) & 1:
            continue
        racine = f'{lettre}:\\'
        try:
            type_lecteur = kernel32.GetDriveTypeW(ctypes.c_wchar_p(racine))
        except Exception:
            type_lecteur = 0
        resultats.append((racine, type_lecteur))
    return resultats


def _nom_volume(racine):
    if os.name != 'nt':
        return ''
    import ctypes
    tampon = ctypes.create_unicode_buffer(261)
    try:
        ctypes.windll.kernel32.GetVolumeInformationW(
            ctypes.c_wchar_p(racine), tampon, 260,
            None, None, None, None, 0,
        )
    except Exception:
        return ''
    return tampon.value or ''


def espace_libre_go(chemin):
    """Espace libre en Go sur le volume du chemin (0 si indisponible)."""
    try:
        usage = shutil.disk_usage(chemin)
        return round(usage.free / (1024 ** 3), 1)
    except Exception:
        return 0.0


def detecter_disques_amovibles():
    """Cles USB et disques externes actuellement branches."""
    lecteur_systeme = (os.environ.get('SystemDrive') or 'C:').upper() + '\\'
    supports = []
    for racine, type_lecteur in _lettres_lecteurs():
        # 2 = amovible (USB), 3 = disque fixe (peut etre un disque externe)
        if type_lecteur not in (2, 3):
            continue
        if racine.upper() == lecteur_systeme:
            continue
        if not os.path.isdir(racine):
            continue  # lecteur declare mais sans support insere
        nom = _nom_volume(racine)
        supports.append({
            'chemin': os.path.join(racine, DOSSIER_RACINE_DESTINATION),
            'libelle': f"{nom or 'Disque'} ({racine[:2]})",
            'type': 'amovible' if type_lecteur == 2 else 'disque',
            'volume': nom,  # permet de retrouver le support si la lettre change
            'espace_libre_go': espace_libre_go(racine),
        })
    return supports


def detecter_dossiers_cloud():
    """Dossiers synchronises cloud presents sur la machine."""
    trouves = []
    vus = set()

    def ajouter(chemin, libelle):
        if not chemin:
            return
        chemin = os.path.normpath(chemin)
        if not os.path.isdir(chemin) or chemin.lower() in vus:
            return
        vus.add(chemin.lower())
        trouves.append({
            'chemin': os.path.join(chemin, DOSSIER_RACINE_DESTINATION),
            'libelle': libelle,
            'type': 'cloud',
            'espace_libre_go': espace_libre_go(chemin),
        })

    profil = os.environ.get('USERPROFILE') or os.path.expanduser('~')

    # ── OneDrive (variables posees par le client OneDrive) ──
    for variable, libelle in (
        ('OneDriveCommercial', 'OneDrive Entreprise'),
        ('OneDriveConsumer', 'OneDrive personnel'),
        ('OneDrive', 'OneDrive'),
    ):
        ajouter(os.environ.get(variable), libelle)
    try:
        for nom in os.listdir(profil):
            if nom.lower().startswith('onedrive'):
                ajouter(os.path.join(profil, nom), nom)
    except Exception:
        pass

    # ── Google Drive : dossier classique, montage dans un dossier, ou lecteur
    #    virtuel de « Drive pour ordinateur » (souvent G:, lettre variable) ──
    for nom in ('Google Drive', 'My Drive', 'Mon Drive'):
        ajouter(os.path.join(profil, nom), f'Google Drive ({nom})')
    for racine, type_lecteur in _lettres_lecteurs():
        if type_lecteur == 5:  # lecteur CD/DVD
            continue
        for nom in ('My Drive', 'Mon Drive'):
            chemin = os.path.join(racine, nom)
            if os.path.isdir(chemin):
                ajouter(chemin, f'Google Drive ({racine[:2]}\\{nom})')

    # ── Dropbox (info.json donne le chemin exact) ──
    for variable in ('LOCALAPPDATA', 'APPDATA'):
        info = os.path.join(os.environ.get(variable, ''), 'Dropbox', 'info.json')
        try:
            if os.path.isfile(info):
                with open(info, 'r', encoding='utf-8') as fichier:
                    donnees = json.load(fichier)
                for cle in ('business', 'personal'):
                    chemin = (donnees.get(cle) or {}).get('path')
                    ajouter(chemin, f'Dropbox ({cle})')
        except Exception:
            pass
    ajouter(os.path.join(profil, 'Dropbox'), 'Dropbox')

    return trouves


def clients_cloud_non_montes():
    """Clients cloud installes sur le poste mais dont aucun dossier n'est visible.

    Cas courant : « Drive pour ordinateur » est installe et tourne, mais la
    synchronisation est en pause -> aucun lecteur monte, donc rien a proposer.
    Sans ce diagnostic, l'utilisateur croit a un defaut de l'application.
    """
    if os.name != 'nt':
        return []
    deja_detectes = {(d.get('libelle') or '').split(' ')[0].lower()
                     for d in detecter_dossiers_cloud()}
    local = os.environ.get('LOCALAPPDATA', '')
    programmes = os.environ.get('PROGRAMFILES', '')
    programmes_x86 = os.environ.get('PROGRAMFILES(X86)', '')
    clients = (
        ('Google Drive', 'google', [
            os.path.join(local, 'Google', 'DriveFS'),
            os.path.join(programmes, 'Google', 'Drive File Stream'),
        ]),
        ('OneDrive', 'onedrive', [
            os.path.join(programmes, 'Microsoft OneDrive'),
            os.path.join(local, 'Microsoft', 'OneDrive'),
        ]),
        ('Dropbox', 'dropbox', [
            os.path.join(programmes, 'Dropbox'),
            os.path.join(programmes_x86, 'Dropbox'),
            os.path.join(local, 'Dropbox'),
        ]),
    )
    absents = []
    for libelle, cle, chemins in clients:
        if cle in deja_detectes:
            continue
        if any(chemin and os.path.isdir(chemin) for chemin in chemins):
            absents.append(libelle)
    return absents


def _dossier_utilisable(chemin):
    """Le dossier existe, ou peut etre cree (son parent existe)."""
    if not chemin:
        return False
    parent = os.path.dirname(os.path.normpath(chemin)) or chemin
    return os.path.isdir(chemin) or os.path.isdir(parent)


def chemin_effectif(destination):
    """Chemin reellement utilisable d'une destination.

    Windows change volontiers la lettre d'une cle USB (E: un jour, F: le
    lendemain) : plutot que d'arreter silencieusement de sauvegarder, on
    retrouve le support par son nom de volume.
    """
    chemin = destination.get('chemin') or ''
    if _dossier_utilisable(chemin):
        return chemin
    volume = (destination.get('volume') or '').strip()
    if not volume or os.name != 'nt' or len(chemin) < 2 or chemin[1] != ':':
        return chemin
    reste = chemin[2:]
    for racine, type_lecteur in _lettres_lecteurs():
        if type_lecteur not in (2, 3):
            continue
        if _nom_volume(racine).strip().lower() != volume.lower():
            continue
        candidat = racine[:2] + reste
        if _dossier_utilisable(candidat):
            return candidat
    return chemin


def destinations_suggerees():
    """Supports detectes, non encore configures : cloud d'abord, puis USB."""
    deja = {
        os.path.normcase(os.path.normpath(dest['chemin']))
        for dest in charger_config()['destinations']
    }
    suggestions = []
    for support in detecter_dossiers_cloud() + detecter_disques_amovibles():
        if os.path.normcase(os.path.normpath(support['chemin'])) not in deja:
            suggestions.append(support)
    return suggestions


# ─── Identite de l'ecole ──────────────────────────────────────────────────────
def _slug(texte, defaut='MySchoolGN'):
    texte = unicodedata.normalize('NFKD', texte or '').encode('ascii', 'ignore').decode()
    propre = ''.join(caractere if caractere.isalnum() else '_' for caractere in texte)
    propre = '_'.join(partie for partie in propre.split('_') if partie)
    return propre[:60] or defaut


def infos_ecole():
    """(nom, slug) de l'ecole ; valeurs neutres si la base n'est pas lisible."""
    try:
        from eleves.models import Ecole
        ecole = Ecole.objects.order_by('id').first()
        if ecole and getattr(ecole, 'nom', ''):
            return ecole.nom, _slug(ecole.nom)
    except Exception:
        pass
    return 'MySchoolGN', 'MySchoolGN'


def _statistiques_base():
    """Quelques compteurs pour rendre le manifeste verifiable a l'oeil nu."""
    stats = {}
    try:
        from eleves.models import Eleve
        stats['eleves'] = Eleve.objects.count()
    except Exception:
        pass
    try:
        from paiements.models import Paiement
        stats['paiements'] = Paiement.objects.count()
    except Exception:
        pass
    return stats


# ─── Outils fichiers ──────────────────────────────────────────────────────────
def _sha256(chemin, blocs=1024 * 1024):
    empreinte = hashlib.sha256()
    with open(chemin, 'rb') as fichier:
        while True:
            bloc = fichier.read(blocs)
            if not bloc:
                break
            empreinte.update(bloc)
    return empreinte.hexdigest()


def _instantane_sqlite(source, destination):
    """Copie SQLite coherente (meme en mode WAL) puis controle d'integrite."""
    temporaire = destination + '.tmp'
    if os.path.exists(temporaire):
        os.remove(temporaire)
    connexion_source = connexion_dest = None
    try:
        connexion_source = sqlite3.connect(source, timeout=30)
        connexion_dest = sqlite3.connect(temporaire, timeout=30)
        connexion_source.backup(connexion_dest)
        connexion_dest.commit()
        controle = connexion_dest.execute('PRAGMA quick_check').fetchone()
        if not controle or str(controle[0]).lower() != 'ok':
            raise RuntimeError(f'controle SQLite invalide : {controle}')
    except Exception:
        if connexion_dest is not None:
            connexion_dest.close()
            connexion_dest = None
        if connexion_source is not None:
            connexion_source.close()
            connexion_source = None
        if os.path.exists(temporaire):
            os.remove(temporaire)
        raise
    finally:
        if connexion_dest is not None:
            connexion_dest.close()
        if connexion_source is not None:
            connexion_source.close()
    if not os.path.exists(temporaire) or os.path.getsize(temporaire) == 0:
        raise RuntimeError('instantane de base vide')
    os.replace(temporaire, destination)
    return destination


def taille_lisible(octets):
    valeur = float(octets or 0)
    for unite in ('o', 'Ko', 'Mo', 'Go', 'To'):
        if valeur < 1024 or unite == 'To':
            return f'{valeur:.0f} {unite}' if unite == 'o' else f'{valeur:.1f} {unite}'
        valeur /= 1024
    return f'{valeur:.1f} To'


# ─── Creation de l'archive ────────────────────────────────────────────────────
TEXTE_RESTAURATION = """MySchoolGN — comment recuperer ces donnees
==========================================

Cette archive contient la base de donnees complete de l'ecole
(eleves, paiements, notes, depenses, salaires...).

En cas de panne, de vol ou de reinstallation de l'ordinateur :

  1. Installez MySchoolGN sur la nouvelle machine (installateur habituel).
  2. Lancez l'application et connectez-vous (admin / admin1234 par defaut).
  3. Menu utilisateur (en haut a droite) > Sauvegarde des donnees.
  4. Section "Restaurer" : branchez la cle USB ou ouvrez le dossier cloud,
     choisissez la sauvegarde la plus recente, puis confirmez.
  5. MySchoolGN se ferme ; relancez-le : les donnees sont revenues.

Les photos d'eleves et logos se trouvent dans le dossier "medias" situe a cote
du dossier "archives" : ils sont restaures automatiquement avec la base.

IMPORTANT : ne modifiez jamais le contenu de ces fichiers a la main.
La licence est liee a la machine : apres un changement d'ordinateur, demandez
une nouvelle licence a GS Hadja Kanfing Dian (les donnees, elles, sont intactes).
"""


def creer_archive(dossier_sortie=None):
    """Cree une archive .zip (base + manifeste) et renvoie ses informations."""
    dossier_sortie = dossier_sortie or dossier_local_sauvegardes()
    os.makedirs(dossier_sortie, exist_ok=True)

    nom_ecole, slug = infos_ecole()
    horodatage = datetime.now().strftime('%Y%m%d_%H%M%S')
    nom_archive = f'MySchoolGN_{slug}_{horodatage}.zip'
    chemin_archive = os.path.join(dossier_sortie, nom_archive)
    temporaire = chemin_archive + '.part'

    dossier_travail = os.path.join(base_dir(), 'backups', '.travail')
    os.makedirs(dossier_travail, exist_ok=True)
    instantane = os.path.join(dossier_travail, 'db.sqlite3')

    try:
        _instantane_sqlite(chemin_db(), instantane)
        manifeste = {
            'application': 'MySchoolGN',
            'format': FORMAT_ARCHIVE,
            'date': datetime.now().isoformat(timespec='seconds'),
            'machine': os.environ.get('COMPUTERNAME') or '',
            'ecole': nom_ecole,
            'db_sha256': _sha256(instantane),
            'db_octets': os.path.getsize(instantane),
            'statistiques': _statistiques_base(),
        }
        with zipfile.ZipFile(temporaire, 'w', zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
            archive.write(instantane, 'db.sqlite3')
            archive.writestr('manifest.json', json.dumps(manifeste, indent=2, ensure_ascii=False))
            archive.writestr('COMMENT_RESTAURER.txt', TEXTE_RESTAURATION)
            reference = os.path.join(base_dir(), 'sync_config.json')
            if os.path.isfile(reference):
                # Copie de reference uniquement : jamais reappliquee telle quelle
                # (l'identifiant d'appareil doit rester unique par poste).
                archive.write(reference, 'reference/sync_config.json')
        os.replace(temporaire, chemin_archive)
    finally:
        for reste in (temporaire, instantane):
            try:
                if os.path.exists(reste):
                    os.remove(reste)
            except Exception:
                pass

    return {
        'chemin': chemin_archive,
        'nom': nom_archive,
        'octets': os.path.getsize(chemin_archive),
        'sha256': _sha256(chemin_archive),
        'manifeste': manifeste,
        'slug': slug,
    }


# ─── Copie vers une destination ───────────────────────────────────────────────
def dossier_ecole_destination(racine_destination, slug):
    return os.path.join(racine_destination, slug)


def _copier_verifie(source, destination):
    """Copie atomique + verification d'empreinte cote destination."""
    os.makedirs(os.path.dirname(destination), exist_ok=True)
    temporaire = destination + '.part'
    shutil.copy2(source, temporaire)
    if _sha256(temporaire) != _sha256(source):
        os.remove(temporaire)
        raise RuntimeError('copie corrompue (empreinte differente)')
    os.replace(temporaire, destination)
    return destination


def _miroir_medias(destination_medias):
    """Copie incrementale des medias : seuls les fichiers nouveaux/modifies."""
    source = chemin_media()
    copies = 0
    octets = 0
    if not os.path.isdir(source):
        return copies, octets
    for racine, _dossiers, fichiers in os.walk(source):
        relatif = os.path.relpath(racine, source)
        cible_dossier = destination_medias if relatif == '.' else os.path.join(destination_medias, relatif)
        os.makedirs(cible_dossier, exist_ok=True)
        for nom in fichiers:
            origine = os.path.join(racine, nom)
            cible = os.path.join(cible_dossier, nom)
            try:
                stat_origine = os.stat(origine)
                if os.path.exists(cible):
                    stat_cible = os.stat(cible)
                    identique = (
                        stat_cible.st_size == stat_origine.st_size
                        and int(stat_cible.st_mtime) >= int(stat_origine.st_mtime)
                    )
                    if identique:
                        continue
                shutil.copy2(origine, cible)
                copies += 1
                octets += stat_origine.st_size
            except Exception:
                # Un media illisible ne doit jamais faire echouer la sauvegarde.
                continue
    return copies, octets


def _ecrire_etat_destination(dossier, archive_info, medias):
    contenu = (
        "MySchoolGN — sauvegarde automatique des donnees\n"
        "===============================================\n\n"
        f"Ecole            : {archive_info['manifeste'].get('ecole', '')}\n"
        f"Derniere reussie : {datetime.now().strftime('%d/%m/%Y a %H:%M')}\n"
        f"Archive          : archives/{archive_info['nom']}\n"
        f"Taille archive   : {taille_lisible(archive_info['octets'])}\n"
        f"Eleves           : {archive_info['manifeste'].get('statistiques', {}).get('eleves', '-')}\n"
        f"Paiements        : {archive_info['manifeste'].get('statistiques', {}).get('paiements', '-')}\n"
        f"Medias copies    : {medias[0]} fichier(s) ce passage\n\n"
        "Pour restaurer : voir COMMENT_RESTAURER.txt dans ce dossier.\n"
    )
    try:
        with open(os.path.join(dossier, 'DERNIERE_SAUVEGARDE.txt'), 'w', encoding='utf-8') as fichier:
            fichier.write(contenu)
        with open(os.path.join(dossier, 'COMMENT_RESTAURER.txt'), 'w', encoding='utf-8') as fichier:
            fichier.write(TEXTE_RESTAURATION)
    except Exception:
        pass


def _deposer_sur_destination(destination, archive_info, config):
    """Depose l'archive + le miroir des medias sur une destination."""
    configure = destination['chemin']
    racine = chemin_effectif(destination)
    debut = time.time()
    resultat = {
        'chemin': configure,
        'libelle': destination.get('libelle') or configure,
        'type': destination.get('type') or 'dossier',
        'ok': False,
        'message': '',
        'medias_copies': 0,
    }
    if racine != configure:
        resultat['chemin_utilise'] = racine

    # Un support absent (USB debranche, cloud pas encore monte) n'est pas une
    # erreur : on reessaiera au prochain passage.
    if not _dossier_utilisable(racine):
        resultat['message'] = 'support absent (cle USB debranchee ou dossier introuvable)'
        resultat['absent'] = True
        return resultat

    try:
        dossier_ecole = dossier_ecole_destination(racine, archive_info['slug'])
        dossier_archives = os.path.join(dossier_ecole, 'archives')
        dossier_medias = os.path.join(dossier_ecole, 'medias')
        os.makedirs(dossier_archives, exist_ok=True)
        os.makedirs(dossier_medias, exist_ok=True)

        _copier_verifie(archive_info['chemin'], os.path.join(dossier_archives, archive_info['nom']))
        medias = _miroir_medias(dossier_medias)
        appliquer_rotation(dossier_archives, config)
        _ecrire_etat_destination(dossier_ecole, archive_info, medias)

        resultat['ok'] = True
        resultat['medias_copies'] = medias[0]
        resultat['message'] = (
            f"archive + {medias[0]} media(s) ({taille_lisible(medias[1])}) en "
            f"{time.time() - debut:.0f}s"
        )
    except Exception as erreur:
        resultat['message'] = str(erreur)
    return resultat


# ─── Rotation (grand-pere / pere / fils) ──────────────────────────────────────
def _date_archive(nom, chemin):
    """Date d'une archive, lue dans son nom (repli : date du fichier)."""
    base = os.path.splitext(nom)[0]
    morceaux = base.split('_')
    if len(morceaux) >= 2:
        try:
            return datetime.strptime('_'.join(morceaux[-2:]), '%Y%m%d_%H%M%S')
        except ValueError:
            pass
    try:
        return datetime.fromtimestamp(os.path.getmtime(chemin))
    except Exception:
        return datetime.now()


def appliquer_rotation(dossier_archives, config=None):
    """Conserve les N dernieres archives, puis une par jour / semaine / mois.

    Les N dernieres sont gardees quoi qu'il arrive : si une donnee est abimee a
    10 h et sauvegardee a 12 h, la version de 6 h du meme jour existe encore.
    """
    config = config or charger_config()
    try:
        entrees = []
        for nom in os.listdir(dossier_archives):
            if nom.startswith('MySchoolGN_') and nom.endswith('.zip'):
                chemin = os.path.join(dossier_archives, nom)
                entrees.append((_date_archive(nom, chemin), chemin))
    except Exception:
        return 0
    if not entrees:
        return 0

    entrees.sort(key=lambda item: item[0], reverse=True)
    recentes = max(1, int(config.get('conserver_recentes', 8) or 8))
    a_garder = {chemin for _date, chemin in entrees[:recentes]}

    def retenir(cle_periode, limite):
        vues = []
        for date, chemin in entrees:
            cle = cle_periode(date)
            if cle in vues:
                continue
            vues.append(cle)
            if len(vues) > limite:
                break
            a_garder.add(chemin)

    retenir(lambda d: d.strftime('%Y%m%d'), int(config.get('conserver_quotidiennes', 7)))
    retenir(lambda d: '%s-%s' % d.isocalendar()[:2], int(config.get('conserver_hebdomadaires', 4)))
    retenir(lambda d: d.strftime('%Y%m'), int(config.get('conserver_mensuelles', 12)))

    supprimees = 0
    for _date, chemin in entrees:
        if chemin in a_garder:
            continue
        try:
            os.remove(chemin)
            supprimees += 1
        except Exception:
            pass
    return supprimees


# ─── Journal ──────────────────────────────────────────────────────────────────
def lire_journal(limite=30):
    try:
        with open(chemin_journal(), 'r', encoding='utf-8') as fichier:
            entrees = json.load(fichier)
        if isinstance(entrees, list):
            return entrees[:limite]
    except Exception:
        pass
    return []


def _ajouter_journal(entree, maximum=100):
    entrees = lire_journal(limite=maximum)
    entrees.insert(0, entree)
    try:
        os.makedirs(os.path.dirname(chemin_journal()), exist_ok=True)
        temporaire = chemin_journal() + '.tmp'
        with open(temporaire, 'w', encoding='utf-8') as fichier:
            json.dump(entrees[:maximum], fichier, indent=2, ensure_ascii=False)
        os.replace(temporaire, chemin_journal())
    except Exception:
        pass


# ─── Sauvegarde complete ──────────────────────────────────────────────────────
def executer_sauvegarde(declencheur='manuel', destinations=None):
    """Cree une archive et la depose sur toutes les destinations configurees.

    Renvoie un rapport : {'ok', 'archive', 'destinations': [...], 'message'}.
    Une seule sauvegarde a la fois (le worker et un clic manuel ne se marchent
    jamais dessus).
    """
    if not _lock_sauvegarde.acquire(blocking=False):
        return {'ok': False, 'message': 'Une sauvegarde est deja en cours.', 'destinations': []}

    debut = time.time()
    config = charger_config()
    cibles = destinations if destinations is not None else config['destinations']
    rapport = {'ok': False, 'declencheur': declencheur, 'destinations': [], 'message': ''}

    try:
        archive_info = creer_archive()
        rapport['archive'] = archive_info['nom']
        rapport['octets'] = archive_info['octets']
        appliquer_rotation(dossier_local_sauvegardes(), config)

        for destination in cibles:
            rapport['destinations'].append(
                _deposer_sur_destination(destination, archive_info, config)
            )

        reussies = [d for d in rapport['destinations'] if d['ok']]
        absentes = [d for d in rapport['destinations'] if d.get('absent')]
        rapport['ok'] = bool(reussies) or not cibles
        if not cibles:
            rapport['message'] = (
                'Sauvegarde locale creee. Aucune destination externe configuree : '
                'ajoutez un dossier cloud et une cle USB pour etre protege en cas '
                'de panne de la machine.'
            )
        else:
            details = f'{len(reussies)}/{len(cibles)} destination(s) a jour'
            if absentes:
                details += f", {len(absentes)} support(s) absent(s)"
            rapport['message'] = details
    except Exception as erreur:
        rapport['message'] = f'Echec de la sauvegarde : {erreur}'
    finally:
        rapport['duree_s'] = round(time.time() - debut, 1)
        rapport['date'] = datetime.now().isoformat(timespec='seconds')
        _lock_sauvegarde.release()

    if rapport['ok']:
        config['derniere_sauvegarde'] = rapport['date']
        try:
            enregistrer_config(config)
        except Exception:
            pass
    _ajouter_journal(rapport)
    return rapport


def prochaine_echeance(config=None):
    """Date de la prochaine sauvegarde automatique (None si desactivee)."""
    config = config or charger_config()
    if not config.get('actif', True):
        return None
    derniere = config.get('derniere_sauvegarde')
    heures = max(1, int(config.get('intervalle_heures', 6) or 6))
    if not derniere:
        return datetime.now()
    try:
        return datetime.fromisoformat(derniere) + timedelta(hours=heures)
    except Exception:
        return datetime.now()


def etat_destinations():
    """Etat de chaque destination : derniere reussite, anciennete, disponibilite."""
    config = charger_config()
    journal = lire_journal(limite=100)
    etats = []
    for destination in config['destinations']:
        chemin = destination['chemin']
        derniere = None
        for entree in journal:
            for detail in entree.get('destinations') or []:
                if detail.get('chemin') == chemin and detail.get('ok'):
                    derniere = entree.get('date')
                    break
            if derniere:
                break
        jours = None
        if derniere:
            try:
                jours = (datetime.now() - datetime.fromisoformat(derniere)).days
            except Exception:
                jours = None
        effectif = chemin_effectif(destination)
        parent = os.path.dirname(os.path.normpath(effectif)) or effectif
        etats.append({
            **destination,
            'chemin_utilise': effectif if effectif != chemin else '',
            'disponible': _dossier_utilisable(effectif),
            'derniere_reussite': derniere,
            'jours_depuis': jours,
            'alerte': jours is None or jours >= 7,
            'espace_libre_go': espace_libre_go(parent if os.path.isdir(parent) else effectif),
        })
    return etats


# ─── Inventaire des sauvegardes disponibles (pour la restauration) ────────────
def _lire_manifeste(chemin_archive):
    try:
        with zipfile.ZipFile(chemin_archive) as archive:
            return json.loads(archive.read('manifest.json').decode('utf-8'))
    except Exception:
        return {}


def lister_archives_disponibles(limite_par_source=15):
    """Archives trouvees en local et sur chaque destination/support detecte."""
    sources = [{'libelle': 'Cet ordinateur (dossier backups)',
                'chemin': os.path.dirname(dossier_local_sauvegardes()),
                'type': 'local'}]
    sources += charger_config()['destinations']
    sources += destinations_suggerees()

    resultats = []
    vus = set()
    for source in sources:
        racine = chemin_effectif(source)
        dossiers_archives = []
        if source.get('type') == 'local':
            dossiers_archives.append(dossier_local_sauvegardes())
        else:
            try:
                for nom_ecole in os.listdir(racine):
                    candidat = os.path.join(racine, nom_ecole, 'archives')
                    if os.path.isdir(candidat):
                        dossiers_archives.append(candidat)
            except Exception:
                continue

        for dossier in dossiers_archives:
            try:
                noms = [n for n in os.listdir(dossier)
                        if n.startswith('MySchoolGN_') and n.endswith('.zip')]
            except Exception:
                continue
            noms.sort(reverse=True)
            for nom in noms[:limite_par_source]:
                chemin = os.path.join(dossier, nom)
                cle = os.path.normcase(chemin)
                if cle in vus:
                    continue
                vus.add(cle)
                manifeste = _lire_manifeste(chemin)
                resultats.append({
                    'chemin': chemin,
                    'nom': nom,
                    'source': source.get('libelle') or racine,
                    'type': source.get('type') or 'dossier',
                    'date': manifeste.get('date') or '',
                    'ecole': manifeste.get('ecole') or '',
                    'eleves': (manifeste.get('statistiques') or {}).get('eleves'),
                    'paiements': (manifeste.get('statistiques') or {}).get('paiements'),
                    'octets': os.path.getsize(chemin),
                    'valide': bool(manifeste.get('db_sha256')),
                    'medias': os.path.isdir(os.path.join(os.path.dirname(dossier), 'medias')),
                })
    resultats.sort(key=lambda item: item['date'] or item['nom'], reverse=True)
    return resultats


# ─── Restauration ─────────────────────────────────────────────────────────────
def chemin_marqueur_restauration(racine=None):
    return os.path.join(racine or base_dir(), NOM_MARQUEUR_RESTAURATION)


def verifier_archive(chemin_archive):
    """Controle qu'une archive est exploitable. Renvoie (ok, message, manifeste)."""
    if not os.path.isfile(chemin_archive):
        return False, "Fichier de sauvegarde introuvable (support debranche ?).", {}
    try:
        with zipfile.ZipFile(chemin_archive) as archive:
            noms = archive.namelist()
            if 'db.sqlite3' not in noms:
                return False, "Cette archive ne contient pas de base de donnees.", {}
            manifeste = {}
            if 'manifest.json' in noms:
                manifeste = json.loads(archive.read('manifest.json').decode('utf-8'))
    except zipfile.BadZipFile:
        return False, "Archive illisible ou incomplete.", {}
    except Exception as erreur:
        return False, f"Archive inexploitable : {erreur}", {}
    return True, 'ok', manifeste


def demander_restauration(chemin_archive, demandee_par=''):
    """Programme une restauration : elle sera appliquee au prochain demarrage.

    On n'ecrase jamais la base pendant que l'application tourne : le marqueur
    est lu par run_server.py avant que Django n'ouvre la base.
    """
    ok, message, manifeste = verifier_archive(chemin_archive)
    if not ok:
        raise RuntimeError(message)
    dossier_medias = os.path.join(os.path.dirname(os.path.dirname(chemin_archive)), 'medias')
    marqueur = {
        'archive': os.path.abspath(chemin_archive),
        'medias': dossier_medias if os.path.isdir(dossier_medias) else None,
        'demande_le': datetime.now().isoformat(timespec='seconds'),
        'demandee_par': demandee_par,
        'manifeste': manifeste,
    }
    temporaire = chemin_marqueur_restauration() + '.tmp'
    with open(temporaire, 'w', encoding='utf-8') as fichier:
        json.dump(marqueur, fichier, indent=2, ensure_ascii=False)
    os.replace(temporaire, chemin_marqueur_restauration())
    return marqueur


def restauration_en_attente():
    try:
        with open(chemin_marqueur_restauration(), 'r', encoding='utf-8') as fichier:
            return json.load(fichier)
    except Exception:
        return None


def annuler_restauration():
    try:
        os.remove(chemin_marqueur_restauration())
        return True
    except Exception:
        return False


def _restaurer_medias(source, destination):
    copies = 0
    if not os.path.isdir(source):
        return copies
    for racine, _dossiers, fichiers in os.walk(source):
        relatif = os.path.relpath(racine, source)
        cible_dossier = destination if relatif == '.' else os.path.join(destination, relatif)
        os.makedirs(cible_dossier, exist_ok=True)
        for nom in fichiers:
            origine = os.path.join(racine, nom)
            cible = os.path.join(cible_dossier, nom)
            try:
                if os.path.exists(cible) and os.path.getsize(cible) == os.path.getsize(origine):
                    continue
                shutil.copy2(origine, cible)
                copies += 1
            except Exception:
                continue
    return copies


def appliquer_restauration_si_demandee(racine=None):
    """A appeler au demarrage, AVANT que Django n'ouvre la base.

    Remplace la base et les medias par ceux de l'archive choisie, apres avoir
    mis l'ancienne base de cote. Renvoie un rapport ou None si rien a faire.
    Ne leve jamais : en cas de probleme, l'installation reste telle quelle.
    """
    racine = racine or base_dir()
    marqueur_chemin = chemin_marqueur_restauration(racine)
    if not os.path.isfile(marqueur_chemin):
        return None

    rapport = {'ok': False, 'message': '', 'date': datetime.now().isoformat(timespec='seconds')}
    try:
        with open(marqueur_chemin, 'r', encoding='utf-8') as fichier:
            marqueur = json.load(fichier)
        chemin_archive = marqueur.get('archive') or ''
        ok, message, _manifeste = verifier_archive(chemin_archive)
        if not ok:
            raise RuntimeError(message)

        db_cible = os.path.join(racine, 'db.sqlite3')
        dossier_travail = os.path.join(racine, 'backups', '.restauration')
        shutil.rmtree(dossier_travail, ignore_errors=True)
        os.makedirs(dossier_travail, exist_ok=True)

        with zipfile.ZipFile(chemin_archive) as archive:
            archive.extract('db.sqlite3', dossier_travail)
        db_extraite = os.path.join(dossier_travail, 'db.sqlite3')

        # La base restauree doit etre saine AVANT de toucher a l'existante.
        connexion = sqlite3.connect(db_extraite, timeout=30)
        try:
            controle = connexion.execute('PRAGMA quick_check').fetchone()
        finally:
            connexion.close()
        if not controle or str(controle[0]).lower() != 'ok':
            raise RuntimeError(f'base restauree invalide : {controle}')

        # Mettre l'ancienne base de cote (jamais de suppression seche).
        if os.path.exists(db_cible):
            dossier_avant = os.path.join(racine, 'backups')
            os.makedirs(dossier_avant, exist_ok=True)
            horodatage = datetime.now().strftime('%Y%m%d_%H%M%S')
            shutil.move(db_cible, os.path.join(dossier_avant, f'db_avant_restauration_{horodatage}.sqlite3'))
        for suffixe in ('-wal', '-shm', '-journal'):
            reste = db_cible + suffixe
            if os.path.exists(reste):
                try:
                    os.remove(reste)
                except Exception:
                    pass

        shutil.move(db_extraite, db_cible)

        medias_restaures = 0
        if marqueur.get('medias'):
            medias_restaures = _restaurer_medias(marqueur['medias'], os.path.join(racine, 'media'))

        shutil.rmtree(dossier_travail, ignore_errors=True)
        rapport['ok'] = True
        rapport['archive'] = os.path.basename(chemin_archive)
        rapport['medias_restaures'] = medias_restaures
        rapport['message'] = (
            f"Donnees restaurees depuis {os.path.basename(chemin_archive)} "
            f"({medias_restaures} media(s))."
        )
    except Exception as erreur:
        rapport['message'] = f'Restauration impossible : {erreur}'
    finally:
        # Le marqueur est toujours retire : pas de boucle de restauration au
        # demarrage si l'archive est illisible.
        try:
            os.remove(marqueur_chemin)
        except Exception:
            pass
        try:
            dossier_logs = os.path.join(racine, 'logs')
            os.makedirs(dossier_logs, exist_ok=True)
            with open(os.path.join(dossier_logs, 'restauration.log'), 'a', encoding='utf-8') as fichier:
                fichier.write(f"[{rapport['date']}] {rapport['message']}\n")
        except Exception:
            pass
    return rapport


# ─── Worker automatique ───────────────────────────────────────────────────────
def _boucle(delai_demarrage):
    time.sleep(max(0, delai_demarrage))
    while True:
        attente = 900  # 15 min : on reverifie souvent (USB rebranchee, etc.)
        try:
            config = charger_config()
            if not config.get('actif', True):
                attente = 3600
            else:
                echeance = prochaine_echeance(config)
                if echeance and datetime.now() >= echeance:
                    executer_sauvegarde(declencheur='automatique')
        except Exception:
            pass
        time.sleep(attente)


def demarrer_worker(delai_demarrage=90):
    """Demarre la sauvegarde automatique en tache de fond (idempotent)."""
    global _worker_demarre
    with _lock_worker:
        if _worker_demarre:
            return False
        _worker_demarre = True
    threading.Thread(
        target=_boucle, args=(delai_demarrage,),
        name='sauvegarde-auto', daemon=True,
    ).start()
    return True
