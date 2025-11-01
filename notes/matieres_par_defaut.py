"""
Matières par défaut pour chaque niveau scolaire
Basé sur les images fournies par l'utilisateur
"""

MATIERES_PAR_NIVEAU = {
    # Collège 7ème (Image 1)
    'COLLEGE_7': [
        {'nom': 'MATHEMATIQUE', 'code': 'MATH', 'coefficient': 2.0},
        {'nom': 'DICTEE ET OUEST', 'code': 'DICT', 'coefficient': 2.0},
        {'nom': 'REDACTION', 'code': 'REDA', 'coefficient': 1.0},
        {'nom': 'PHYSIQUE', 'code': 'PHY', 'coefficient': 1.0},
        {'nom': 'CHIMIE', 'code': 'CHIM', 'coefficient': 1.0},
        {'nom': 'HISTOIRE', 'code': 'HIST', 'coefficient': 1.0},
        {'nom': 'GEOGRAPHIE', 'code': 'GEO', 'coefficient': 1.0},
        {'nom': 'E.C.M', 'code': 'ECM', 'coefficient': 1.0},
        {'nom': 'BIOLOGIE', 'code': 'BIO', 'coefficient': 1.0},
        {'nom': 'ANGLAIS', 'code': 'ANG', 'coefficient': 1.0},
        {'nom': 'E.P.S', 'code': 'EPS', 'coefficient': 1.0},
    ],
    
    # Collège 8ème (Image 1 - même structure que 7ème)
    'COLLEGE_8': [
        {'nom': 'MATHEMATIQUE', 'code': 'MATH', 'coefficient': 2.0},
        {'nom': 'DICTEE ET OUEST', 'code': 'DICT', 'coefficient': 2.0},
        {'nom': 'REDACTION', 'code': 'REDA', 'coefficient': 1.0},
        {'nom': 'PHYSIQUE', 'code': 'PHY', 'coefficient': 1.0},
        {'nom': 'CHIMIE', 'code': 'CHIM', 'coefficient': 1.0},
        {'nom': 'HISTOIRE', 'code': 'HIST', 'coefficient': 1.0},
        {'nom': 'GEOGRAPHIE', 'code': 'GEO', 'coefficient': 1.0},
        {'nom': 'E.C.M', 'code': 'ECM', 'coefficient': 1.0},
        {'nom': 'BIOLOGIE', 'code': 'BIO', 'coefficient': 1.0},
        {'nom': 'ANGLAIS', 'code': 'ANG', 'coefficient': 1.0},
        {'nom': 'E.P.S', 'code': 'EPS', 'coefficient': 1.0},
    ],
    
    # Collège 9ème (Image 2)
    'COLLEGE_9': [
        {'nom': 'MATHEMATIQUE', 'code': 'MATH', 'coefficient': 4.0},
        {'nom': 'PHYSIQUE', 'code': 'PHY', 'coefficient': 3.0},
        {'nom': 'CHIMIE', 'code': 'CHIM', 'coefficient': 3.0},
        {'nom': 'ANGLAIS', 'code': 'ANG', 'coefficient': 2.0},
        {'nom': 'ECONOMIE', 'code': 'ECO', 'coefficient': 2.0},
        {'nom': 'PHYLOSOPHIE', 'code': 'PHILO', 'coefficient': 2.0},
        {'nom': 'BIOLOGIE', 'code': 'BIO', 'coefficient': 1.0},
        {'nom': 'FRANCAIS', 'code': 'FR', 'coefficient': 2.0},
        {'nom': 'GEOLOGIE', 'code': 'GEOL', 'coefficient': 1.0},
    ],
    
    # Collège 10ème (Image 3)
    'COLLEGE_10': [
        {'nom': 'BIOLOGIE', 'code': 'BIO', 'coefficient': 3.0},
        {'nom': 'PHYSIQUE', 'code': 'PHY', 'coefficient': 3.0},
        {'nom': 'CHIMIE', 'code': 'CHIM', 'coefficient': 3.0},
        {'nom': 'ANGLAIS', 'code': 'ANG', 'coefficient': 2.0},
        {'nom': 'ECONOMIE', 'code': 'ECO', 'coefficient': 2.0},
        {'nom': 'PHYLOSOPHIE', 'code': 'PHILO', 'coefficient': 2.0},
        {'nom': 'MATHEMATIQUE', 'code': 'MATH', 'coefficient': 2.0},
        {'nom': 'FRANCAIS', 'code': 'FR', 'coefficient': 2.0},
        {'nom': 'GEOLOGIE', 'code': 'GEOL', 'coefficient': 1.0},
    ],
    
    # Lycée 11ème (Image 4)
    'LYCEE_11': [
        {'nom': 'MATHEMATIQUE', 'code': 'MATH', 'coefficient': 2.0},
        {'nom': 'Francais', 'code': 'FR', 'coefficient': 4.0},
        {'nom': 'PHYLOSOPHIE', 'code': 'PHILO', 'coefficient': 3.0},
        {'nom': 'ANGLAIS', 'code': 'ANG', 'coefficient': 3.0},
        {'nom': 'GEOGRAPHIE', 'code': 'GEO', 'coefficient': 2.0},
        {'nom': 'HISTOIRE', 'code': 'HIST', 'coefficient': 2.0},
        {'nom': 'ECONOMIE', 'code': 'ECO', 'coefficient': 2.0},
    ],
    
    # Lycée 12ème (similaire à 11ème)
    'LYCEE_12': [
        {'nom': 'MATHEMATIQUE', 'code': 'MATH', 'coefficient': 2.0},
        {'nom': 'Francais', 'code': 'FR', 'coefficient': 4.0},
        {'nom': 'PHYLOSOPHIE', 'code': 'PHILO', 'coefficient': 3.0},
        {'nom': 'ANGLAIS', 'code': 'ANG', 'coefficient': 3.0},
        {'nom': 'GEOGRAPHIE', 'code': 'GEO', 'coefficient': 2.0},
        {'nom': 'HISTOIRE', 'code': 'HIST', 'coefficient': 2.0},
        {'nom': 'ECONOMIE', 'code': 'ECO', 'coefficient': 2.0},
    ],
    
    # Terminale (similaire à 11ème et 12ème)
    'TERMINALE': [
        {'nom': 'MATHEMATIQUE', 'code': 'MATH', 'coefficient': 2.0},
        {'nom': 'Francais', 'code': 'FR', 'coefficient': 4.0},
        {'nom': 'PHYLOSOPHIE', 'code': 'PHILO', 'coefficient': 3.0},
        {'nom': 'ANGLAIS', 'code': 'ANG', 'coefficient': 3.0},
        {'nom': 'GEOGRAPHIE', 'code': 'GEO', 'coefficient': 2.0},
        {'nom': 'HISTOIRE', 'code': 'HIST', 'coefficient': 2.0},
        {'nom': 'ECONOMIE', 'code': 'ECO', 'coefficient': 2.0},
    ],
}

# Matières de base pour le primaire (à adapter selon vos besoins)
MATIERES_PRIMAIRE = [
    {'nom': 'MATHEMATIQUE', 'code': 'MATH', 'coefficient': 2.0},
    {'nom': 'FRANCAIS', 'code': 'FR', 'coefficient': 2.0},
    {'nom': 'LECTURE', 'code': 'LECT', 'coefficient': 1.0},
    {'nom': 'DICTEE', 'code': 'DICT', 'coefficient': 1.0},
    {'nom': 'SCIENCES', 'code': 'SCI', 'coefficient': 1.0},
    {'nom': 'HISTOIRE-GEOGRAPHIE', 'code': 'HG', 'coefficient': 1.0},
    {'nom': 'E.C.M', 'code': 'ECM', 'coefficient': 1.0},
    {'nom': 'ANGLAIS', 'code': 'ANG', 'coefficient': 1.0},
    {'nom': 'E.P.S', 'code': 'EPS', 'coefficient': 1.0},
]

# Appliquer les matières primaires à tous les niveaux primaires
for niveau in ['PRIMAIRE_1', 'PRIMAIRE_2', 'PRIMAIRE_3', 'PRIMAIRE_4', 'PRIMAIRE_5', 'PRIMAIRE_6']:
    MATIERES_PAR_NIVEAU[niveau] = MATIERES_PRIMAIRE

# Matières de base pour maternelle et garderie
MATIERES_MATERNELLE = [
    {'nom': 'LECTURE', 'code': 'LECT', 'coefficient': 1.0},
    {'nom': 'ECRITURE', 'code': 'ECR', 'coefficient': 1.0},
    {'nom': 'CALCUL', 'code': 'CALC', 'coefficient': 1.0},
    {'nom': 'DESSIN', 'code': 'DESS', 'coefficient': 1.0},
    {'nom': 'CHANT', 'code': 'CHANT', 'coefficient': 1.0},
]

MATIERES_PAR_NIVEAU['MATERNELLE'] = MATIERES_MATERNELLE
MATIERES_PAR_NIVEAU['GARDERIE'] = MATIERES_MATERNELLE


def obtenir_matieres_par_niveau(niveau):
    """
    Retourne la liste des matières par défaut pour un niveau donné
    
    Args:
        niveau: Code du niveau (ex: 'COLLEGE_7', 'LYCEE_11')
    
    Returns:
        Liste de dictionnaires avec nom, code et coefficient
    """
    return MATIERES_PAR_NIVEAU.get(niveau, [])
