"""Mise à jour sécurisée de l'application Desktop depuis GitHub Releases.

Le module utilise uniquement la bibliothèque standard afin de rester disponible
dans l'exécutable PyInstaller. Une mise à jour n'est installable que si son
empreinte SHA-256 est publiée avec l'installateur.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Any, Callable
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from app_version import APP_VERSION


GITHUB_REPOSITORY = "Faraleno2022/GS_hadja_kanfing_dian-"
LATEST_RELEASE_URL = (
    f"https://api.github.com/repos/{GITHUB_REPOSITORY}/releases/latest"
)
USER_AGENT = f"MySchoolGN-Desktop/{APP_VERSION}"
CHECK_INTERVAL_SECONDS = 6 * 60 * 60
NETWORK_TIMEOUT_SECONDS = 12
DOWNLOAD_CHUNK_SIZE = 1024 * 1024

_ALLOWED_DOWNLOAD_HOSTS = {
    "github.com",
    "objects.githubusercontent.com",
    "release-assets.githubusercontent.com",
    "github-releases.githubusercontent.com",
}
_INSTALLER_NAME_RE = re.compile(
    r"^MySchoolGN_Setup_v?[0-9][0-9A-Za-z._-]*\.exe$",
    re.IGNORECASE,
)
_SHA256_RE = re.compile(r"\b([0-9a-fA-F]{64})\b")


class UpdateError(RuntimeError):
    """Erreur de mise à jour affichable sans bloquer l'application."""


def version_tuple(value: str) -> tuple[int, ...]:
    """Convertit ``desktop-v1.2.3`` ou ``1.2.3`` en tuple comparable."""
    match = re.search(r"(?<!\d)(\d+(?:\.\d+){1,3})(?!\d)", value or "")
    if not match:
        raise UpdateError(f"Version invalide : {value!r}")
    parts = tuple(int(part) for part in match.group(1).split("."))
    return parts + (0,) * (4 - len(parts))


def is_newer_version(candidate: str, current: str = APP_VERSION) -> bool:
    return version_tuple(candidate) > version_tuple(current)


def _request(url: str) -> Request:
    return Request(
        url,
        headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": USER_AGENT,
            "X-GitHub-Api-Version": "2022-11-28",
        },
    )


def _read_json_url(
    url: str,
    *,
    opener: Callable[..., Any] = urlopen,
    timeout: int = NETWORK_TIMEOUT_SECONDS,
) -> dict[str, Any]:
    with opener(_request(url), timeout=timeout) as response:
        payload = response.read()
    try:
        value = json.loads(payload.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise UpdateError("Réponse GitHub illisible.") from exc
    if not isinstance(value, dict):
        raise UpdateError("Réponse GitHub inattendue.")
    return value


def fetch_latest_release(
    *, opener: Callable[..., Any] = urlopen
) -> dict[str, Any]:
    release = _read_json_url(LATEST_RELEASE_URL, opener=opener)
    if release.get("draft") or release.get("prerelease"):
        raise UpdateError("La dernière version publiée n'est pas stable.")
    if not release.get("tag_name"):
        raise UpdateError("La version publiée ne contient pas de tag.")
    return release


def find_installer_asset(release: dict[str, Any]) -> dict[str, Any]:
    assets = release.get("assets") or []
    if not isinstance(assets, list):
        raise UpdateError("Liste des fichiers de mise à jour invalide.")

    candidates = []
    for asset in assets:
        if not isinstance(asset, dict):
            continue
        name = str(asset.get("name") or "")
        if _INSTALLER_NAME_RE.fullmatch(name):
            candidates.append(asset)

    if not candidates:
        raise UpdateError("Installateur Windows absent de la Release GitHub.")

    release_version = version_tuple(str(release.get("tag_name")))
    for asset in candidates:
        try:
            if version_tuple(str(asset.get("name"))) == release_version:
                return asset
        except UpdateError:
            continue
    raise UpdateError(
        "L'installateur ne correspond pas à la version de la Release GitHub."
    )


def _validate_download_url(url: str) -> None:
    parsed = urlparse(url)
    if parsed.scheme != "https" or parsed.hostname not in _ALLOWED_DOWNLOAD_HOSTS:
        raise UpdateError("Adresse de téléchargement non autorisée.")


def _asset_digest(asset: dict[str, Any]) -> str | None:
    digest = str(asset.get("digest") or "")
    if digest.lower().startswith("sha256:"):
        digest = digest.split(":", 1)[1]
    return digest.lower() if re.fullmatch(r"[0-9a-fA-F]{64}", digest) else None


def expected_installer_digest(
    release: dict[str, Any],
    installer_asset: dict[str, Any],
    *,
    opener: Callable[..., Any] = urlopen,
) -> str:
    """Obtient l'empreinte GitHub ou le fichier compagnon ``.sha256``."""
    digest = _asset_digest(installer_asset)
    if digest:
        return digest

    expected_name = f"{installer_asset.get('name', '')}.sha256".lower()
    checksum_asset = next(
        (
            asset
            for asset in (release.get("assets") or [])
            if isinstance(asset, dict)
            and str(asset.get("name") or "").lower() == expected_name
        ),
        None,
    )
    if not checksum_asset:
        raise UpdateError(
            "Empreinte SHA-256 absente : installation annulée par sécurité."
        )

    url = str(checksum_asset.get("browser_download_url") or "")
    _validate_download_url(url)
    with opener(_request(url), timeout=NETWORK_TIMEOUT_SECONDS) as response:
        final_url = getattr(response, "geturl", lambda: url)()
        _validate_download_url(final_url)
        content = response.read(4096).decode("ascii", errors="ignore")
    match = _SHA256_RE.search(content)
    if not match:
        raise UpdateError("Fichier SHA-256 invalide.")
    return match.group(1).lower()


def _update_directory() -> Path:
    local_app_data = os.environ.get("LOCALAPPDATA")
    root = Path(local_app_data) if local_app_data else Path(tempfile.gettempdir())
    return root / "MySchoolGN" / "updates"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(DOWNLOAD_CHUNK_SIZE), b""):
            digest.update(block)
    return digest.hexdigest()


def download_installer(
    asset: dict[str, Any],
    expected_digest: str,
    *,
    opener: Callable[..., Any] = urlopen,
    progress: Callable[[int, int | None], None] | None = None,
) -> Path:
    name = str(asset.get("name") or "")
    if not _INSTALLER_NAME_RE.fullmatch(name):
        raise UpdateError("Nom d'installateur invalide.")
    url = str(asset.get("browser_download_url") or "")
    _validate_download_url(url)

    update_dir = _update_directory()
    update_dir.mkdir(parents=True, exist_ok=True)
    destination = update_dir / name
    partial = update_dir / f"{name}.part"

    if destination.is_file() and sha256_file(destination) == expected_digest:
        return destination

    try:
        with opener(_request(url), timeout=NETWORK_TIMEOUT_SECONDS) as response:
            final_url = getattr(response, "geturl", lambda: url)()
            _validate_download_url(final_url)
            header_value = response.headers.get("Content-Length")
            total = int(header_value) if header_value and header_value.isdigit() else None
            received = 0
            digest = hashlib.sha256()
            with partial.open("wb") as stream:
                while True:
                    block = response.read(DOWNLOAD_CHUNK_SIZE)
                    if not block:
                        break
                    stream.write(block)
                    digest.update(block)
                    received += len(block)
                    if progress:
                        progress(received, total)
        if digest.hexdigest().lower() != expected_digest.lower():
            raise UpdateError(
                "L'empreinte de l'installateur ne correspond pas à la Release."
            )
        os.replace(partial, destination)
        return destination
    except Exception:
        try:
            partial.unlink(missing_ok=True)
        except OSError:
            pass
        raise


def launch_installer(path: Path) -> None:
    if os.name != "nt":
        raise UpdateError("L'installateur Desktop ne peut être lancé que sous Windows.")
    subprocess.Popen([str(path)], cwd=str(path.parent), close_fds=True)


def _state_path() -> Path:
    return _update_directory().parent / "update_state.json"


def _load_state() -> dict[str, Any]:
    try:
        value = json.loads(_state_path().read_text(encoding="utf-8"))
        return value if isinstance(value, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


def _save_check_time(now: float) -> None:
    path = _state_path()
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps({"last_checked_at": now}, ensure_ascii=False),
            encoding="utf-8",
        )
    except OSError:
        pass


def _check_due(force: bool, now: float) -> bool:
    if force:
        return True
    try:
        last_checked = float(_load_state().get("last_checked_at", 0))
    except (TypeError, ValueError):
        last_checked = 0
    return now - last_checked >= CHECK_INTERVAL_SECONDS


def _message(kind: str, title: str, message: str) -> bool | None:
    import tkinter as tk
    from tkinter import messagebox

    root = tk.Tk()
    root.withdraw()
    root.attributes("-topmost", True)
    try:
        if kind == "ask":
            return messagebox.askyesno(title, message, parent=root)
        getattr(messagebox, kind)(title, message, parent=root)
        return None
    finally:
        root.destroy()


def _download_with_progress(
    asset: dict[str, Any], expected_digest: str
) -> Path:
    import tkinter as tk
    from tkinter import ttk

    root = tk.Tk()
    root.title("MySchoolGN — Mise à jour")
    root.resizable(False, False)
    root.attributes("-topmost", True)
    root.geometry("470x135")
    label = tk.Label(
        root,
        text="Téléchargement sécurisé de la mise à jour…",
        font=("Arial", 10),
        padx=18,
        pady=16,
    )
    label.pack(fill="x")
    bar = ttk.Progressbar(root, length=420, mode="indeterminate")
    bar.pack(padx=20, pady=(0, 8))
    bar.start(12)
    percent = tk.Label(root, text="Connexion à GitHub…", font=("Arial", 9))
    percent.pack()
    root.update()

    def update_progress(received: int, total: int | None) -> None:
        if total:
            bar.stop()
            bar.configure(mode="determinate", maximum=total, value=received)
            percent.configure(text=f"{received * 100 // total} %")
        else:
            percent.configure(text=f"{received // (1024 * 1024)} Mo reçus")
        root.update()

    try:
        return download_installer(
            asset, expected_digest, progress=update_progress
        )
    finally:
        root.destroy()


def check_and_offer_update(*, force: bool = False) -> bool:
    """Vérifie GitHub et retourne ``True`` si l'installateur a été lancé.

    Toute erreur réseau reste non bloquante lors d'une vérification automatique.
    En vérification manuelle, l'utilisateur reçoit toujours un résultat clair.
    """
    now = time.time()
    if not _check_due(force, now):
        return False

    try:
        release = fetch_latest_release()
        _save_check_time(now)
        tag = str(release["tag_name"])
        if not is_newer_version(tag):
            if force:
                _message(
                    "showinfo",
                    "MySchoolGN — Mise à jour",
                    f"Vous utilisez déjà la dernière version ({APP_VERSION}).",
                )
            return False

        asset = find_installer_asset(release)
        accepted = _message(
            "ask",
            "MySchoolGN — Mise à jour disponible",
            "Une nouvelle version de MySchoolGN est disponible.\n\n"
            f"Version installée : {APP_VERSION}\n"
            f"Nouvelle version : {tag}\n\n"
            "Télécharger et installer maintenant ?\n\n"
            "La base de données, les photos, les licences et les réglages "
            "seront conservés.",
        )
        if not accepted:
            return False

        expected_digest = expected_installer_digest(release, asset)
        installer = _download_with_progress(asset, expected_digest)
        _message(
            "showinfo",
            "MySchoolGN — Mise à jour prête",
            "Le téléchargement a été vérifié. L'installateur va s'ouvrir.\n\n"
            "MySchoolGN sera fermé pendant la mise à jour.",
        )
        launch_installer(installer)
        return True
    except Exception as exc:
        print(f"[Mise à jour] Vérification ignorée : {exc}")
        if force:
            try:
                _message(
                    "showerror",
                    "MySchoolGN — Mise à jour",
                    "La vérification n'a pas abouti.\n\n"
                    f"Détail : {exc}\n\n"
                    "Vérifiez la connexion Internet puis réessayez.",
                )
            except Exception:
                pass
        return False
