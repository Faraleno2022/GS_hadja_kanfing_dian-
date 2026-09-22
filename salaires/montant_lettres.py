"""Conversion des montants en toutes lettres (français, orthographe usuelle).

Utilisé par les états de salaire : « Arrêté le présent état … à la somme
de : Sept millions neuf cent quatre-vingt-deux mille cinq cents francs
guinéens (7 982 500 GNF) ».
"""

from decimal import Decimal, ROUND_HALF_UP

UNITES = [
    'zéro', 'un', 'deux', 'trois', 'quatre', 'cinq', 'six', 'sept', 'huit',
    'neuf', 'dix', 'onze', 'douze', 'treize', 'quatorze', 'quinze', 'seize',
    'dix-sept', 'dix-huit', 'dix-neuf',
]
DIZAINES = {
    2: 'vingt', 3: 'trente', 4: 'quarante', 5: 'cinquante', 6: 'soixante',
}


def _moins_de_cent(n):
    if n < 20:
        return UNITES[n]
    dizaine, unite = divmod(n, 10)
    if dizaine in (7, 9):
        # 70-79 et 90-99 se construisent sur soixante / quatre-vingt + 10..19.
        base = 'soixante' if dizaine == 7 else 'quatre-vingt'
        reste = 10 + unite
        if dizaine == 7 and unite == 1:
            return 'soixante et onze'
        return f"{base}-{UNITES[reste]}"
    if dizaine == 8:
        return 'quatre-vingts' if unite == 0 else f"quatre-vingt-{UNITES[unite]}"
    mot = DIZAINES[dizaine]
    if unite == 0:
        return mot
    if unite == 1:
        return f"{mot} et un"
    return f"{mot}-{UNITES[unite]}"


def _moins_de_mille(n, final=True):
    """``final`` : le nombre termine l'expression (accord de « cents »)."""
    centaine, reste = divmod(n, 100)
    morceaux = []
    if centaine:
        if centaine == 1:
            morceaux.append('cent')
        else:
            pluriel = 's' if reste == 0 and final else ''
            morceaux.append(f"{UNITES[centaine]} cent{pluriel}")
    if reste:
        texte = _moins_de_cent(reste)
        if not final and texte.endswith('quatre-vingts'):
            texte = texte[:-1]
        morceaux.append(texte)
    return ' '.join(morceaux)


def nombre_en_lettres(nombre):
    """Entier positif en toutes lettres : 1 250 000 -> « un million deux cent cinquante mille »."""
    n = int(nombre)
    if n < 0:
        return 'moins ' + nombre_en_lettres(-n)
    if n == 0:
        return UNITES[0]

    morceaux = []
    for valeur, singulier, pluriel in (
        (10 ** 9, 'milliard', 'milliards'),
        (10 ** 6, 'million', 'millions'),
    ):
        bloc, n = divmod(n, valeur)
        if bloc:
            # « millions » est un nom : le nombre qui précède reste invariable.
            texte = nombre_en_lettres(bloc) if bloc >= 1000 else _moins_de_mille(bloc)
            morceaux.append(f"{texte} {singulier if bloc == 1 else pluriel}")

    milliers, n = divmod(n, 1000)
    if milliers:
        # « mille » est invariable et « deux cent mille » ne prend pas de s.
        morceaux.append('mille' if milliers == 1 else f"{_moins_de_mille(milliers, final=False)} mille")
    if n:
        morceaux.append(_moins_de_mille(n))
    return ' '.join(morceaux)


def montant_en_lettres(montant, devise='francs guinéens'):
    """« Sept millions … francs guinéens » (arrondi au franc, majuscule initiale)."""
    entier = int(Decimal(montant or 0).quantize(Decimal('1'), rounding=ROUND_HALF_UP))
    texte = nombre_en_lettres(entier)
    if devise:
        texte = f"{texte} {'franc guinéen' if abs(entier) <= 1 else devise}"
    return texte[:1].upper() + texte[1:]


def formater_gnf(montant):
    """7982500 -> « 7 982 500 »."""
    entier = int(Decimal(montant or 0).quantize(Decimal('1'), rounding=ROUND_HALF_UP))
    return f"{entier:,}".replace(',', ' ')
