"""
Configuration des matières par défaut pour chaque niveau d'enseignement
"""

# Matières par défaut pour le COLLÈGE (7ème, 8ème, 9ème, 10ème)
MATIERES_COLLEGE = [
    {'nom': 'Mathématique', 'code': 'MATHS', 'coefficient': 2.0},
    {'nom': 'Physique', 'code': 'PHYS', 'coefficient': 1.0},
    {'nom': 'Chimie', 'code': 'CHI', 'coefficient': 1.0},
    {'nom': 'Biologie', 'code': 'BIO', 'coefficient': 1.0},
    {'nom': 'Français', 'code': 'FR', 'coefficient': 2.0},
    {'nom': 'Anglais', 'code': 'ANG', 'coefficient': 1.0},
    {'nom': 'Histoire', 'code': 'HIS', 'coefficient': 1.0},
    {'nom': 'Géographie', 'code': 'GEO', 'coefficient': 1.0},
    {'nom': 'Education Civique et Morale', 'code': 'ECM', 'coefficient': 1.0},
    {'nom': 'Education Physique et Sportive', 'code': 'EPS', 'coefficient': 1.0},
    {'nom': 'Dictée et Questions', 'code': 'DICQ', 'coefficient': 2.0},
    {'nom': 'Rédaction', 'code': 'RED', 'coefficient': 1.0},
]

# Matières par défaut pour le PRIMAIRE (CP, CE1, CE2, CM1, CM2)
MATIERES_PRIMAIRE = [
    {'nom': 'Calcul écrit', 'code': 'CALC', 'coefficient': 1.0},
    {'nom': 'Dictée et Questions', 'code': 'DICQ', 'coefficient': 1.0},
    {'nom': 'Géographie', 'code': 'GEO', 'coefficient': 1.0},
    {'nom': 'Histoire', 'code': 'HIS', 'coefficient': 1.0},
    {'nom': 'E.C.M', 'code': 'ECM', 'coefficient': 1.0},
    {'nom': 'Rédaction', 'code': 'RED', 'coefficient': 1.0},
    {'nom': 'Sciences d\'observation', 'code': 'SCI', 'coefficient': 1.0},
    {'nom': 'Lecture', 'code': 'LECT', 'coefficient': 1.0},
    {'nom': 'Langage', 'code': 'LANG', 'coefficient': 1.0},
    {'nom': 'Écriture', 'code': 'ECR', 'coefficient': 1.0},
    {'nom': 'Récitation/Chant', 'code': 'REC', 'coefficient': 1.0},
    {'nom': 'Dessin', 'code': 'DESS', 'coefficient': 1.0},
    {'nom': 'EPS', 'code': 'EPS', 'coefficient': 1.0},
]

# Matières par défaut pour la MATERNELLE
MATIERES_MATERNELLE = [
    {'nom': 'Langage', 'code': 'LANG', 'coefficient': 1.0},
    {'nom': 'Écriture', 'code': 'ECR', 'coefficient': 1.0},
    {'nom': 'Calcul', 'code': 'CALC', 'coefficient': 1.0},
    {'nom': 'Dessin', 'code': 'DESS', 'coefficient': 1.0},
    {'nom': 'Récitation/Chant', 'code': 'REC', 'coefficient': 1.0},
    {'nom': 'Jeux éducatifs', 'code': 'JEUX', 'coefficient': 1.0},
    {'nom': 'Psychomotricité', 'code': 'PSYCH', 'coefficient': 1.0},
]

# Matières par défaut pour le LYCÉE - Série Sciences Mathématiques (11ème SM, 12ème SM)
MATIERES_LYCEE_SM = [
    {'nom': 'Mathématique', 'code': 'MATHS', 'coefficient': 4.0},
    {'nom': 'Physique', 'code': 'PHYS', 'coefficient': 3.0},
    {'nom': 'Chimie', 'code': 'CHI', 'coefficient': 3.0},
    {'nom': 'Anglais', 'code': 'ANG', 'coefficient': 2.0},
    {'nom': 'Économie', 'code': 'ECO', 'coefficient': 2.0},
    {'nom': 'Philosophie', 'code': 'PHILO', 'coefficient': 2.0},
    {'nom': 'Biologie', 'code': 'BIO', 'coefficient': 1.0},
    {'nom': 'Français', 'code': 'FR', 'coefficient': 2.0},
    {'nom': 'Géologie', 'code': 'GEOL', 'coefficient': 1.0},
]

# Matières par défaut pour le LYCÉE - Série Sciences Expérimentales (11ème SE, 12ème SE)
MATIERES_LYCEE_SE = [
    {'nom': 'Biologie', 'code': 'BIO', 'coefficient': 3.0},
    {'nom': 'Physique', 'code': 'PHYS', 'coefficient': 3.0},
    {'nom': 'Chimie', 'code': 'CHI', 'coefficient': 3.0},
    {'nom': 'Anglais', 'code': 'ANG', 'coefficient': 2.0},
    {'nom': 'Économie', 'code': 'ECO', 'coefficient': 2.0},
    {'nom': 'Philosophie', 'code': 'PHILO', 'coefficient': 2.0},
    {'nom': 'Mathématique', 'code': 'MATHS', 'coefficient': 2.0},
    {'nom': 'Français', 'code': 'FR', 'coefficient': 2.0},
    {'nom': 'Géologie', 'code': 'GEOL', 'coefficient': 1.0},
]

# Matières par défaut pour le LYCÉE - Série Sciences Sociales/Lettres (11ème SL, 12ème SL)
MATIERES_LYCEE_SL = [
    {'nom': 'Français', 'code': 'FR', 'coefficient': 4.0},
    {'nom': 'Philosophie', 'code': 'PHILO', 'coefficient': 3.0},
    {'nom': 'Anglais', 'code': 'ANG', 'coefficient': 3.0},
    {'nom': 'Mathématique', 'code': 'MATHS', 'coefficient': 2.0},
    {'nom': 'Géographie', 'code': 'GEO', 'coefficient': 2.0},
    {'nom': 'Histoire', 'code': 'HIS', 'coefficient': 2.0},
    {'nom': 'Économie', 'code': 'ECO', 'coefficient': 2.0},
]


def get_matieres_par_defaut(niveau, serie=None, nom_classe=None):
    """
    Retourne la liste des matières par défaut selon le niveau et la série
    
    Args:
        niveau (str): Niveau d'enseignement (MATERNELLE, PRIMAIRE, COLLEGE, LYCEE)
        serie (str, optional): Série pour le lycée (SM, SE, SL)
        nom_classe (str, optional): Nom de la classe pour détecter automatiquement la série
    
    Returns:
        list: Liste de dictionnaires contenant les matières par défaut
    """
    
    # Détecter la série depuis le nom de la classe si non fournie
    if not serie and nom_classe:
        nom_classe_upper = nom_classe.upper()
        if 'SM' in nom_classe_upper or 'SCIENCES MATH' in nom_classe_upper:
            serie = 'SM'
        elif 'SE' in nom_classe_upper or 'SCIENCES EXP' in nom_classe_upper:
            serie = 'SE'
        elif 'SL' in nom_classe_upper or 'LETTRES' in nom_classe_upper or 'SCIENCES SOCIALES' in nom_classe_upper:
            serie = 'SL'
    
    # Retourner les matières selon le niveau
    if niveau == 'MATERNELLE':
        return MATIERES_MATERNELLE.copy()
    
    elif niveau == 'PRIMAIRE':
        return MATIERES_PRIMAIRE.copy()
    
    elif niveau == 'COLLEGE':
        return MATIERES_COLLEGE.copy()
    
    elif niveau == 'LYCEE':
        if serie == 'SM':
            return MATIERES_LYCEE_SM.copy()
        elif serie == 'SE':
            return MATIERES_LYCEE_SE.copy()
        elif serie == 'SL':
            return MATIERES_LYCEE_SL.copy()
        else:
            # Par défaut, retourner SM si la série n'est pas spécifiée
            return MATIERES_LYCEE_SM.copy()
    
    # Par défaut, retourner les matières du collège
    return MATIERES_COLLEGE.copy()


def charger_matieres_pour_classe(classe, user=None):
    """
    Charge les matières par défaut pour une classe donnée
    
    Args:
        classe: Instance de ClasseNote
        user: Utilisateur qui crée les matières (optionnel)
    
    Returns:
        tuple: (nombre_creees, nombre_existantes, erreurs)
    """
    from notes.models import MatiereNote
    
    # Récupérer les matières par défaut
    matieres_defaut = get_matieres_par_defaut(
        niveau=classe.niveau,
        nom_classe=classe.nom
    )
    
    nombre_creees = 0
    nombre_existantes = 0
    erreurs = []
    
    for matiere_data in matieres_defaut:
        try:
            # Vérifier si la matière existe déjà
            matiere_existante = MatiereNote.objects.filter(
                classe=classe,
                code=matiere_data['code']
            ).first()
            
            if matiere_existante:
                nombre_existantes += 1
            else:
                # Créer la nouvelle matière
                MatiereNote.objects.create(
                    classe=classe,
                    nom=matiere_data['nom'],
                    code=matiere_data['code'],
                    coefficient=matiere_data['coefficient'],
                    actif=True,
                    cree_par=user
                )
                nombre_creees += 1
        
        except Exception as e:
            erreurs.append(f"Erreur pour {matiere_data['nom']}: {str(e)}")
    
    return nombre_creees, nombre_existantes, erreurs


# Mapping des niveaux pour faciliter la détection
NIVEAU_KEYWORDS = {
    'MATERNELLE': ['maternelle', 'petite', 'moyenne', 'grande', 'ps', 'ms', 'gs'],
    'PRIMAIRE': ['primaire', 'cp', 'ce1', 'ce2', 'cm1', 'cm2', '1ère', '2ème', '3ème', '4ème', '5ème', '6ème'],
    'COLLEGE': ['collège', 'college', '7ème', '7eme', '8ème', '8eme', '9ème', '9eme', '10ème', '10eme'],
    'LYCEE': ['lycée', 'lycee', '11ème', '11eme', '12ème', '12eme', 'terminale', 'première', 'premiere', 'seconde'],
}


def detecter_niveau_depuis_nom(nom_classe):
    """
    Détecte le niveau d'enseignement depuis le nom de la classe
    
    Args:
        nom_classe (str): Nom de la classe
    
    Returns:
        str: Niveau détecté (MATERNELLE, PRIMAIRE, COLLEGE, LYCEE) ou None
    """
    nom_lower = nom_classe.lower()
    
    for niveau, keywords in NIVEAU_KEYWORDS.items():
        if any(keyword in nom_lower for keyword in keywords):
            return niveau
    
    return None
