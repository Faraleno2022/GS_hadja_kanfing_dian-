"""Conversion d'un montant en toutes lettres (français, francs guinéens)."""

from decimal import Decimal, ROUND_HALF_UP

_UNITES = [
    'zéro', 'un', 'deux', 'trois', 'quatre', 'cinq', 'six', 'sept', 'huit',
    'neuf', 'dix', 'onze', 'douze', 'treize', 'quatorze', 'quinze', 'seize',
    'dix-sept', 'dix-huit', 'dix-neuf',
]
_DIZAINES = {
    2: 'vingt', 3: 'trente', 4: 'quarante', 5: 'cinquante', 6: 'soixante',
}


def _moins_de_cent(n):
    if n < 20:
        return _UNITES[n]
    dizaine, unite = divmod(n, 10)
    if dizaine in (7, 9):
        base = 'soixante' if dizaine == 7 else 'quatre-vingt'
        reste = 10 + unite
        liaison = ' et ' if dizaine == 7 and unite == 1 else '-'
        return f"{base}{liaison}{_UNITES[reste]}"
    if dizaine == 8:
        return 'quatre-vingts' if unite == 0 else f"quatre-vingt-{_UNITES[unite]}"
    mot = _DIZAINES[dizaine]
    if unite == 0:
        return mot
    if unite == 1:
        return f"{mot} et un"
    return f"{mot}-{_UNITES[unite]}"


def _moins_de_mille(n, final=True):
    centaine, reste = divmod(n, 100)
    morceaux = []
    if centaine:
        if centaine == 1:
            morceaux.append('cent')
        else:
            pluriel = 's' if reste == 0 and final else ''
            morceaux.append(f"{_UNITES[centaine]} cent{pluriel}")
    if reste:
        texte = _moins_de_cent(reste)
        if not final and texte == 'quatre-vingts':
            texte = 'quatre-vingt'
        morceaux.append(texte)
    return ' '.join(morceaux)


def nombre_en_lettres(nombre):
    nombre = int(nombre)
    if nombre == 0:
        return 'zéro'
    if nombre < 0:
        return 'moins ' + nombre_en_lettres(-nombre)

    echelles = [
        (10 ** 9, 'milliard', 'milliards'),
        (10 ** 6, 'million', 'millions'),
    ]
    morceaux = []
    for valeur, singulier, pluriel in echelles:
        quantite, nombre = divmod(nombre, valeur)
        if quantite:
            mot = singulier if quantite == 1 else pluriel
            morceaux.append(f"{nombre_en_lettres(quantite)} {mot}")
    milliers, reste = divmod(nombre, 1000)
    if milliers:
        morceaux.append('mille' if milliers == 1 else f"{_moins_de_mille(milliers, final=False)} mille")
    if reste:
        morceaux.append(_moins_de_mille(reste))
    return ' '.join(morceaux)


def montant_en_lettres(montant, devise='francs guinéens'):
    """Ex. 1 600 000 -> « Un million six cent mille francs guinéens »."""
    entier = int(Decimal(montant or 0).quantize(Decimal('1'), rounding=ROUND_HALF_UP))
    texte = nombre_en_lettres(entier)
    return f"{texte[0].upper()}{texte[1:]} {devise}"
