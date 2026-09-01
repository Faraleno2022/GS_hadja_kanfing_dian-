"""Palettes de couleurs personnalisables pour les cartes imprimées."""

import re


COULEURS_CARTES_PAR_DEFAUT = {
    "scolaire": "#1746A2",
    "retrait": "#0F766E",
    "bus": "#2563EB",
    "cantine": "#B45309",
}

_COULEUR_HEX = re.compile(r"^#[0-9A-Fa-f]{6}$")


def normaliser_couleur(couleur, defaut):
    """Retourne une couleur #RRGGBB sûre, sinon la valeur par défaut."""
    valeur = str(couleur or "").strip()
    if not _COULEUR_HEX.fullmatch(valeur):
        valeur = defaut
    return valeur.upper()


def _melanger(couleur, cible, proportion):
    """Mélange une couleur avec une couleur cible."""
    couleur = normaliser_couleur(couleur, "#1746A2")
    cible = normaliser_couleur(cible, "#FFFFFF")
    proportion = max(0.0, min(1.0, float(proportion)))
    rgb = []
    for index in (1, 3, 5):
        source = int(couleur[index:index + 2], 16)
        destination = int(cible[index:index + 2], 16)
        rgb.append(round(source + (destination - source) * proportion))
    return "#" + "".join(f"{composante:02X}" for composante in rgb)


def _texte_contraste(couleur):
    """Choisit un texte clair ou foncé lisible sur la couleur donnée."""
    couleur = normaliser_couleur(couleur, "#1746A2")
    rouge, vert, bleu = (
        int(couleur[index:index + 2], 16) / 255
        for index in (1, 3, 5)
    )
    luminance = 0.2126 * rouge + 0.7152 * vert + 0.0722 * bleu
    return "#111827" if luminance > 0.62 else "#FFFFFF"


def palette_carte(ecole, type_carte):
    """Construit toutes les nuances d'une carte à partir du réglage de l'école."""
    if type_carte not in COULEURS_CARTES_PAR_DEFAUT:
        raise ValueError(f"Type de carte inconnu : {type_carte}")

    defaut = COULEURS_CARTES_PAR_DEFAUT[type_carte]
    primaire = normaliser_couleur(
        getattr(ecole, f"couleur_carte_{type_carte}", None),
        defaut,
    )
    texte_entete = _texte_contraste(primaire)
    sous_titre = (
        "#334155"
        if texte_entete == "#111827"
        else _melanger(primaire, "#FFFFFF", 0.78)
    )
    return {
        "primary": primaire,
        "accent": _melanger(primaire, "#000000", 0.18),
        "line": _melanger(primaire, "#FFFFFF", 0.78),
        "soft": _melanger(primaire, "#FFFFFF", 0.94),
        "footer": _melanger(primaire, "#FFFFFF", 0.90),
        "placeholder": _melanger(primaire, "#FFFFFF", 0.86),
        "header_text": texte_entete,
        "subtitle": sous_titre,
    }
