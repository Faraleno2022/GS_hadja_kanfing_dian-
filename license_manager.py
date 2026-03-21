"""
MySchoolGN - Système de Gestion des Licences
=============================================
Auteur  : GS Hadja Kanfing Dian
Version : 1.0.0

Ce module gère la validation des licences d'utilisation de MySchoolGN.
Chaque licence est liée à l'identifiant unique de la machine.
"""

import os
import sys
import uuid
import hmac
import hashlib
import json
import base64
import socket
import platform
from datetime import datetime, timedelta, timezone
from pathlib import Path

# Compatibilité Python 3.11+
def _now_utc() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)

# ─── Clé secrète (obfusquée — ne pas modifier) ───────────────────────────────
def _gk():
    _d = [29,9,119,18,27,30,16,27,119,17,27,20,28,19,20,29,119,30,19,27,20,119,23,3,9,25,18,21,21,22,119,29,20,119,104,106,104,110,119,9,31,25,8,31,14,119,17,31,3,119,44,107]
    return bytes(x ^ 0x5A for x in _d)
_DEV_SECRET = _gk()
del _gk

# ─── Chemin de stockage de la licence ─────────────────────────────────────────
def _get_license_path() -> Path:
    if getattr(sys, 'frozen', False):
        base = Path(sys.executable).parent
    else:
        base = Path(__file__).parent
    return base / 'license.dat'

def _get_appdata_license_path() -> Path:
    appdata = os.environ.get('APPDATA', os.path.expanduser('~'))
    folder = Path(appdata) / 'MySchoolGN'
    folder.mkdir(parents=True, exist_ok=True)
    return folder / 'license.dat'

# ─── Identifiant machine ───────────────────────────────────────────────────────
def get_machine_id() -> str:
    """Génère un identifiant unique et stable pour cette machine."""
    parts = []

    # UUID Windows (registre)
    try:
        import winreg
        key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE,
                             r'SOFTWARE\Microsoft\Cryptography')
        machine_guid, _ = winreg.QueryValueEx(key, 'MachineGuid')
        parts.append(machine_guid)
    except Exception:
        pass

    # Hostname
    try:
        parts.append(socket.gethostname())
    except Exception:
        pass

    # UUID du système
    try:
        parts.append(str(uuid.getnode()))
    except Exception:
        pass

    # Plateforme
    parts.append(platform.system() + platform.machine())

    combined = '|'.join(parts).encode('utf-8')
    return hashlib.sha256(combined).hexdigest()[:32].upper()


def get_machine_id_short() -> str:
    """Version courte de 8 caractères pour affichage."""
    return get_machine_id()[:8]


# ─── Empreinte machine autorisée pour la génération ───────────────────────────
def _ak():
    _d = [0xD4,0xD1,0xA5,0xD4,0xA3,0xA0,0xA0,0xA3]
    return bytes(x ^ 0x95 for x in _d).decode()
_AUTHORIZED_PREFIX = _ak()
del _ak


def _is_authorized_machine() -> bool:
    """Vérifie que la machine courante est autorisée à générer des licences."""
    try:
        mid = get_machine_id()[:8]
        return hmac.compare_digest(mid, _AUTHORIZED_PREFIX)
    except Exception:
        return False


# ─── Génération de clé de licence ─────────────────────────────────────────────
def generate_license_key(machine_id: str, expiry_days: int = 365,
                          school_name: str = '', edition: str = 'Standard') -> str:
    """
    Génère une clé de licence pour une machine donnée.
    Réservé au développeur / outil d'activation.
    BLOQUÉ si la machine n'est pas autorisée.

    Format retourné : XXXX-XXXX-XXXX-XXXX-XXXX
    """
    if not _is_authorized_machine():
        raise PermissionError(
            "Génération de licence non autorisée sur cette machine.\n"
            "Seule la machine du développeur GS Hadja Kanfing Dian peut générer des licences."
        )
    payload = {
        'mid': machine_id,
        'exp': (_now_utc() + timedelta(days=expiry_days)).strftime('%Y%m%d'),
        'school': school_name[:40],
        'edition': edition,
    }
    payload_str = json.dumps(payload, separators=(',', ':'))
    payload_b64 = base64.b64encode(payload_str.encode()).decode()

    # Signature HMAC-SHA256
    sig = hmac.new(_DEV_SECRET, payload_b64.encode(), hashlib.sha256).hexdigest()[:16].upper()

    # Encoder le payload en blocs de 4 chars
    payload_hex = hashlib.md5(payload_b64.encode()).hexdigest().upper()
    blocks = [payload_hex[i:i+4] for i in range(0, 16, 4)]
    sig_blocks = [sig[i:i+4] for i in range(0, 16, 4)]

    # Stocker le payload complet encodé séparément
    full_key_data = base64.b64encode(
        json.dumps({'payload': payload_b64, 'sig': sig}).encode()
    ).decode()

    # Clé affichable = 5 groupes de 4 chars
    display_key = '-'.join(blocks + [sig_blocks[0]])
    return display_key, full_key_data


def generate_activation_file(machine_id: str, expiry_days: int = 365,
                               school_name: str = '', edition: str = 'Standard') -> dict:
    """
    Génère un fichier d'activation complet (à envoyer au client).
    BLOQUÉ si la machine n'est pas autorisée.
    """
    if not _is_authorized_machine():
        raise PermissionError(
            "Génération de licence non autorisée sur cette machine.\n"
            "Seule la machine du développeur GS Hadja Kanfing Dian peut générer des licences."
        )
    payload = {
        'mid': machine_id,
        'exp': (_now_utc() + timedelta(days=expiry_days)).strftime('%Y%m%d'),
        'school': school_name[:60],
        'edition': edition,
        'issued': _now_utc().strftime('%Y-%m-%d'),
        'issuer': 'GS Hadja Kanfing Dian',
    }
    payload_str = json.dumps(payload, separators=(',', ':'))
    payload_b64 = base64.b64encode(payload_str.encode()).decode()
    sig = hmac.new(_DEV_SECRET, payload_b64.encode(), hashlib.sha256).hexdigest().upper()

    return {
        'license_data': payload_b64,
        'signature': sig,
        'version': '1.0',
    }


# ─── Validation de licence ─────────────────────────────────────────────────────
def _validate_license_data(license_dict: dict) -> dict:
    """
    Valide un dictionnaire de licence.
    Retourne un dict avec 'valid', 'reason', 'payload'.
    """
    try:
        payload_b64 = license_dict.get('license_data', '')
        sig = license_dict.get('signature', '')
        version = license_dict.get('version', '1.0')

        if not payload_b64 or not sig:
            return {'valid': False, 'reason': 'Fichier de licence incomplet.'}

        # Vérifier la signature
        expected_sig = hmac.new(
            _DEV_SECRET, payload_b64.encode(), hashlib.sha256
        ).hexdigest().upper()

        if not hmac.compare_digest(sig.upper(), expected_sig):
            return {'valid': False, 'reason': 'Signature de licence invalide.'}

        # Décoder le payload
        payload = json.loads(base64.b64decode(payload_b64).decode())
        machine_id = get_machine_id()

        # Vérifier la machine (tolérance : vérifier les 16 premiers chars)
        if payload.get('mid', '')[:16] != machine_id[:16]:
            return {'valid': False, 'reason': 'Cette licence appartient à une autre machine.'}

        # Vérifier l'expiration
        exp_str = payload.get('exp', '20000101')
        exp_date = datetime.strptime(exp_str, '%Y%m%d')
        now = _now_utc()
        days_left = (exp_date - now).days

        if days_left < 0:
            return {
                'valid': False,
                'reason': f"Licence expirée depuis {abs(days_left)} jour(s).",
                'payload': payload,
            }

        return {
            'valid': True,
            'reason': 'Licence valide.',
            'payload': payload,
            'days_left': days_left,
            'school': payload.get('school', ''),
            'edition': payload.get('edition', 'Standard'),
        }

    except Exception as e:
        return {'valid': False, 'reason': f'Erreur lors de la validation : {e}'}


def load_and_validate_license() -> dict:
    """
    Charge et valide la licence depuis les emplacements connus.
    Retourne un dict avec 'valid', 'reason', etc.
    """
    license_paths = [
        _get_license_path(),
        _get_appdata_license_path(),
    ]

    for path in license_paths:
        if path.exists():
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    license_dict = json.load(f)
                result = _validate_license_data(license_dict)
                result['license_path'] = str(path)
                return result
            except Exception:
                continue

    return {
        'valid': False,
        'reason': 'Aucune licence trouvée. Veuillez activer votre copie.',
    }


def save_license(license_dict: dict) -> bool:
    """Sauvegarde la licence dans tous les emplacements standards (redondance)."""
    saved = False
    for path in [_get_license_path(), _get_appdata_license_path()]:
        try:
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(license_dict, f, indent=2)
            saved = True
        except Exception:
            continue
    return saved


def activate_from_file(activation_file_path: str) -> dict:
    """
    Active la licence depuis un fichier .lic fourni par le développeur.
    """
    try:
        with open(activation_file_path, 'r', encoding='utf-8') as f:
            license_dict = json.load(f)
        result = _validate_license_data(license_dict)
        if result['valid']:
            if save_license(license_dict):
                return {**result, 'message': 'Licence activée avec succès !'}
            else:
                return {'valid': False, 'reason': 'Impossible de sauvegarder la licence.'}
        return result
    except Exception as e:
        return {'valid': False, 'reason': f'Erreur lecture du fichier : {e}'}


# ─── Mode démo (30 jours sans licence) ────────────────────────────────────────
_TRIAL_FILE_NAME = '.trial_start'

def get_or_create_trial() -> dict:
    """
    Gère une période d'essai de 30 jours sans licence.
    L'essai est lié à la machine : si l'application est copiée sur une
    autre machine, un nouvel essai de 30 jours démarre automatiquement.
    Format du fichier : machine_id_16|YYYY-MM-DD
    """
    trial_paths = [
        _get_license_path().parent / _TRIAL_FILE_NAME,
        _get_appdata_license_path().parent / _TRIAL_FILE_NAME,
    ]

    current_mid = get_machine_id()[:16]
    trial_start = None
    trial_path_used = None

    for tp in trial_paths:
        if tp.exists():
            try:
                with open(tp, 'r') as f:
                    content = f.read().strip()
                # Nouveau format : machine_id|date
                if '|' in content:
                    stored_mid, date_str = content.split('|', 1)
                    if stored_mid == current_mid:
                        trial_start = datetime.strptime(date_str, '%Y-%m-%d')
                        trial_path_used = tp
                        break
                    # Machine différente → ignorer ce fichier (copie USB)
                else:
                    # Ancien format (date seule) → migrer pour cette machine
                    trial_start = datetime.strptime(content, '%Y-%m-%d')
                    trial_path_used = tp
                    try:
                        with open(tp, 'w') as f:
                            f.write(f"{current_mid}|{content}")
                    except Exception:
                        pass
                    break
            except Exception:
                continue

    if trial_start is None:
        # Nouvelle machine ou première installation → nouvel essai de 30 jours
        trial_start = _now_utc()
        for tp in trial_paths:
            try:
                with open(tp, 'w') as f:
                    f.write(f"{current_mid}|{trial_start.strftime('%Y-%m-%d')}")
                trial_path_used = tp
                break
            except Exception:
                continue

    days_elapsed = (_now_utc() - trial_start).days
    days_left = max(0, 30 - days_elapsed)

    return {
        'trial': True,
        'valid': days_left > 0,
        'days_left': days_left,
        'days_elapsed': days_elapsed,
        'reason': (
            f"Mode essai : {days_left} jour(s) restant(s)."
            if days_left > 0
            else "Période d'essai expirée. Veuillez acheter une licence."
        ),
    }


# ─── Point d'entrée principal ──────────────────────────────────────────────────
def check_license_or_trial() -> dict:
    """
    Vérifie la licence. Si absente, démarre/continue le mode essai.
    Retourne un dict complet avec le statut.
    """
    result = load_and_validate_license()
    if result['valid']:
        return result

    # Pas de licence valide → essai
    trial = get_or_create_trial()
    return trial


def print_license_status():
    """Affiche le statut de la licence dans la console."""
    mid = get_machine_id()
    mid_short = get_machine_id_short()
    status = check_license_or_trial()

    print("")
    print("=" * 60)
    print("   MySchoolGN — Statut de la Licence")
    print("=" * 60)
    print(f"   ID Machine  : {mid_short}...  (complet : {mid})")

    if status.get('trial'):
        print(f"   Mode        : ESSAI GRATUIT")
        print(f"   Jours rest. : {status['days_left']} / 30")
        print(f"   État        : {'Actif' if status['valid'] else 'EXPIRÉ'}")
        print("")
        print("   Pour obtenir une licence complète :")
        print("   → Contactez GS Hadja Kanfing Dian")
        print(f"   → Fournissez cet ID Machine : {mid}")
    else:
        valid = status['valid']
        print(f"   État        : {'VALIDE ✓' if valid else 'INVALIDE ✗'}")
        if valid:
            print(f"   École       : {status.get('school', 'N/A')}")
            print(f"   Édition     : {status.get('edition', 'Standard')}")
            print(f"   Expiration  : dans {status.get('days_left', 0)} jour(s)")
        else:
            print(f"   Raison      : {status.get('reason', 'Inconnue')}")

    print("=" * 60)
    print("")
    return status


# ─── Outil de génération de licence (usage développeur uniquement) ─────────────
if __name__ == '__main__':
    import sys
    # Forcer UTF-8 pour la console Windows
    if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
        import io
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

    print("\nMySchoolGN - Gestionnaire de Licences")
    print("Auteur : GS Hadja Kanfing Dian")
    print("="*50)

    if len(sys.argv) < 2:
        print("\nUsages :")
        print("  python license_manager.py info")
        print("  python license_manager.py generate <machine_id> <jours> <ecole> <edition>")
        print("  python license_manager.py activate <fichier.lic>")
        print("  python license_manager.py check")
        sys.exit(0)

    cmd = sys.argv[1]

    if cmd == 'info':
        mid = get_machine_id()
        print(f"\nID Machine complet : {mid}")
        print(f"ID Machine court   : {get_machine_id_short()}")
        print(f"\nFournissez l'ID complet à GS Hadja Kanfing Dian pour obtenir une licence.")

    elif cmd == 'generate':
        if len(sys.argv) < 4:
            print("Usage: python license_manager.py generate <machine_id> <jours> [ecole] [edition]")
            sys.exit(1)
        machine_id = sys.argv[2]
        days = int(sys.argv[3])
        school = sys.argv[4] if len(sys.argv) > 4 else ''
        edition = sys.argv[5] if len(sys.argv) > 5 else 'Standard'

        lic_data = generate_activation_file(machine_id, days, school, edition)
        output_file = f'license_{machine_id[:8]}.lic'
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(lic_data, f, indent=2)
        print(f"\nLicence générée : {output_file}")
        print(f"  Machine  : {machine_id}")
        print(f"  École    : {school}")
        print(f"  Édition  : {edition}")
        print(f"  Durée    : {days} jours")
        print(f"\nEnvoyez le fichier '{output_file}' au client.")

    elif cmd == 'activate':
        if len(sys.argv) < 3:
            print("Usage: python license_manager.py activate <fichier.lic>")
            sys.exit(1)
        result = activate_from_file(sys.argv[2])
        if result['valid']:
            print(f"\n✓ {result.get('message', 'Activée')}")
            print(f"  École   : {result.get('school', 'N/A')}")
            print(f"  Édition : {result.get('edition', 'Standard')}")
            print(f"  Expire  : dans {result.get('days_left', 0)} jour(s)")
        else:
            print(f"\n✗ Échec : {result['reason']}")
            sys.exit(1)

    elif cmd == 'check':
        print_license_status()
