"""
Module d'importation d'élèves depuis Excel/CSV
Permet l'importation massive d'élèves avec génération automatique de matricules
"""
import pandas as pd
from datetime import datetime
from django.db import transaction
from django.core.exceptions import ValidationError
from eleves.models import Eleve, Classe, Responsable


class ImportElevesError(Exception):
    """Exception personnalisée pour l'importation d'élèves"""
    pass


# Colonnes du modèle d'importation (ordre exact du template téléchargeable)
COLONNES_TEMPLATE = [
    'Matricule',  # Optionnel - sera généré si vide
    'Prénom',  # Obligatoire
    'Nom',  # Obligatoire
    'Sexe',  # M ou F - Obligatoire
    'Date de Naissance',  # Optionnel - Format: JJ/MM/AAAA
    'Lieu de Naissance',  # Optionnel
    'Nom du Père/Tuteur',  # Optionnel
    'Prénom du Père/Tuteur',  # Optionnel
    'Téléphone Principal',  # Optionnel
    'Adresse',  # Optionnel
    'Nom de la Mère',  # Optionnel
    'Prénom de la Mère',  # Optionnel
    'Téléphone Secondaire',  # Optionnel
    'Email',  # Optionnel
]

# Format exact de transfert vers un autre poste. L'ordre est volontairement
# figé : le fichier produit peut être envoyé directement au module d'importation.
COLONNES_TRANSFERT = [
    'École',
    'Classe',
    'Année scolaire',
    *COLONNES_TEMPLATE,
]


def normaliser_nom_classe(valeur):
    """Cle de rapprochement d'un nom de classe entre deux postes."""
    if valeur is None or (isinstance(valeur, float) and pd.isna(valeur)):
        return ''
    return ' '.join(str(valeur).strip().upper().split())


def nettoyer_telephone(valeur):
    """Numero tel qu'il sera enregistre : sans espaces ni tirets, le '+' conserve."""
    if valeur is None or (isinstance(valeur, float) and pd.isna(valeur)):
        return ''
    texte = str(valeur).strip()
    # Excel renvoie parfois un nombre : 224622613559.0
    if texte.endswith('.0'):
        texte = texte[:-2]
    return texte.replace(' ', '').replace('-', '')


def cle_telephone(valeur):
    """Cle de rapprochement d'un numero : '+224...' et '224...' designent le meme parent."""
    texte = nettoyer_telephone(valeur)
    return texte[1:] if texte.startswith('+') else texte


def cle_matricule(valeur):
    """Cle d'unicite d'un matricule, insensible a la casse et aux espaces."""
    if valeur is None or (not isinstance(valeur, str) and pd.isna(valeur)):
        return ''
    return ' '.join(str(valeur).strip().upper().split())


def _texte(valeur, defaut=''):
    """Valeur de cellule convertie en texte propre ('' si vide/NaN)."""
    if valeur is None or (not isinstance(valeur, str) and pd.isna(valeur)):
        return defaut
    texte = str(valeur).strip()
    return texte if texte else defaut


def generer_matricule(classe, numero_ordre, annee_scolaire=None, matricules_existants=None):
    """
    Génère un matricule unique pour un élève - VERSION OPTIMISÉE
    Format: [CODE_CLASSE][ANNEE][NUMERO]
    Exemple: 6A-2024-001
    
    Args:
        matricules_existants: Set des matricules déjà utilisés (pour éviter requêtes SQL)
    """
    if not annee_scolaire:
        annee_scolaire = datetime.now().year
    
    # Extraire l'année du format "2024-2025"
    if isinstance(annee_scolaire, str) and '-' in annee_scolaire:
        annee_scolaire = annee_scolaire.split('-')[0]
    
    # Obtenir le code de la classe ou utiliser le nom simplifié
    code_classe = getattr(classe, 'code_matricule', None) or classe.nom.replace(' ', '').upper()[:3]
    
    # Format du matricule
    matricule = f"{code_classe}-{annee_scolaire}-{numero_ordre:03d}"
    
    # ⚡ OPTIMISATION: Vérifier l'unicité en mémoire (pas de requête SQL)
    if matricules_existants is None:
        # Fallback si pas de set fourni (pas optimal)
        while Eleve.objects.filter(matricule__iexact=matricule).exists():
            numero_ordre += 1
            matricule = f"{code_classe}-{annee_scolaire}-{numero_ordre:03d}"
    else:
        # Utiliser le set en mémoire (RAPIDE!)
        while cle_matricule(matricule) in matricules_existants:
            numero_ordre += 1
            matricule = f"{code_classe}-{annee_scolaire}-{numero_ordre:03d}"
        # Ajouter au set pour éviter réutilisation
        matricules_existants.add(cle_matricule(matricule))
    
    return matricule


def lire_fichier_eleves(file_path_or_obj):
    """
    Lit un fichier Excel ou CSV contenant la liste des élèves
    """
    try:
        nom = getattr(file_path_or_obj, 'name', None) or str(file_path_or_obj)

        # dtype=str : sinon pandas convertit '+224622613559' en 2.246e11 et le
        # matricule '0012' en 12, ce qui casse la validation et les rapprochements.
        if nom.endswith('.csv'):
            df = pd.read_csv(file_path_or_obj, dtype=str)
        else:
            df = pd.read_excel(file_path_or_obj, dtype=str)

        # Nettoyer les noms de colonnes
        df.columns = df.columns.str.strip()

        return df
    except Exception as e:
        raise ImportElevesError(f"Erreur lors de la lecture du fichier: {e}")


def generer_template_eleves(classe_id=None):
    """
    Génère un template Excel pour l'importation d'élèves
    """
    try:
        # Créer un DataFrame avec des exemples
        data = {col: [] for col in COLONNES_TEMPLATE}
        
        # Ajouter quelques lignes d'exemple
        data['Matricule'] = ['', '', '']  # Laisser vide pour génération auto
        data['Prénom'] = ['Mamadou', 'Fatoumata', 'Ibrahim']
        data['Nom'] = ['DIALLO', 'BAH', 'CAMARA']
        data['Sexe'] = ['M', 'F', 'M']
        data['Date de Naissance'] = ['15/01/2010', '23/05/2010', '10/09/2010']
        data['Lieu de Naissance'] = ['Conakry', 'Kindia', 'Labé']
        data['Nom du Père/Tuteur'] = ['DIALLO', 'BAH', 'CAMARA']
        data['Prénom du Père/Tuteur'] = ['Amadou', 'Ousmane', 'Sékou']
        data['Téléphone Principal'] = ['622000001', '622000002', '622000003']
        data['Adresse'] = ['Ratoma', 'Matoto', 'Dixinn']
        data['Nom de la Mère'] = ['BARRY', 'SOW', 'SYLLA']
        data['Prénom de la Mère'] = ['Aissatou', 'Mariama', 'Binta']
        data['Téléphone Secondaire'] = ['', '', '']
        data['Email'] = ['', '', '']
        
        df = pd.DataFrame(data)
        
        return df
    
    except Exception as e:
        raise ImportElevesError(f"Erreur lors de la génération du template: {e}")


class ImportElevesValidator:
    """
    Validateur pour l'importation d'élèves
    """
    
    def __init__(self, df, classe_id):
        self.df = df
        self.classe_id = classe_id
        self.erreurs = []
        self.avertissements = []
        
    def valider(self):
        """
        Valide le fichier importé
        """
        # Vérifier les colonnes requises (seuls Prénom, Nom et Sexe sont obligatoires)
        colonnes_requises = ['Prénom', 'Nom', 'Sexe']
        
        colonnes_manquantes = []
        for col in colonnes_requises:
            if col not in self.df.columns:
                colonnes_manquantes.append(col)
        
        if colonnes_manquantes:
            raise ImportElevesError(
                f"Colonnes manquantes: {', '.join(colonnes_manquantes)}"
            )
        
        # Valider chaque ligne
        for index, row in self.df.iterrows():
            self._valider_ligne(index + 2, row)  # +2 car Excel commence à 1 + en-tête
        
        return len(self.erreurs) == 0
    
    def _valider_ligne(self, ligne_num, row):
        """
        Valide une ligne du fichier
        """
        # Vérifier les champs obligatoires (seuls Prénom, Nom et Sexe sont obligatoires)
        champs_obligatoires = ['Prénom', 'Nom', 'Sexe']
        
        for champ in champs_obligatoires:
            if pd.isna(row.get(champ)) or str(row.get(champ)).strip() == '':
                self.erreurs.append(
                    f"Ligne {ligne_num}: Le champ '{champ}' est obligatoire"
                )
        
        # Valider le sexe
        if row.get('Sexe') and str(row['Sexe']).upper() not in ['M', 'F']:
            self.erreurs.append(
                f"Ligne {ligne_num}: Le sexe doit être 'M' ou 'F' (trouvé: {row['Sexe']})"
            )
        
        # Valider la date de naissance (optionnel - valider uniquement si présent)
        date_val = row.get('Date de Naissance')
        if date_val and not pd.isna(date_val) and str(date_val).strip() != '':
            try:
                # Essayer différents formats
                date_str = str(date_val).strip()
                for fmt in ['%d/%m/%Y', '%Y-%m-%d', '%d-%m-%Y']:
                    try:
                        date_naissance = datetime.strptime(date_str, fmt)
                        break
                    except:
                        continue
                else:
                    raise ValueError("Format de date invalide")
                    
                # Vérifier que la date est raisonnable
                age = (datetime.now() - date_naissance).days // 365
                if age < 3 or age > 25:
                    self.avertissements.append(
                        f"Ligne {ligne_num}: Âge inhabituel ({age} ans)"
                    )
            except Exception as e:
                self.erreurs.append(
                    f"Ligne {ligne_num}: Date de naissance invalide (format attendu: JJ/MM/AAAA)"
                )
        
        # Valider le téléphone (optionnel - valider uniquement si présent)
        tel_val = row.get('Téléphone Principal')
        if tel_val is not None and not pd.isna(tel_val) and str(tel_val).strip() != '':
            tel = cle_telephone(tel_val)
            if not tel.isdigit() or len(tel) < 8:
                self.erreurs.append(
                    f"Ligne {ligne_num}: Téléphone invalide (doit contenir au moins 8 chiffres)"
                )
        
        # Vérifier les doublons potentiels
        if row.get('Prénom') and row.get('Nom'):
            prenom = str(row['Prénom']).strip()
            nom = str(row['Nom']).strip()
            
            # Vérifier dans la base de données
            if Eleve.objects.filter(
                prenom__iexact=prenom,
                nom__iexact=nom,
                classe_id=self.classe_id
            ).exists():
                self.avertissements.append(
                    f"Ligne {ligne_num}: Un élève '{prenom} {nom}' existe déjà dans cette classe"
                )


class ImportElevesProcessor:
    """
    Processeur pour importer les élèves
    """
    
    def __init__(self, df, classe_id, user=None, generer_matricules=True):
        self.df = df
        self.classe_id = classe_id
        self.user = user
        self.generer_matricules = generer_matricules
        self.stats = {
            'total': 0,
            'crees': 0,
            'modifies': 0,
            'erreurs': 0,
            'matricules_generes': 0,
            'doublons_ignores': 0,
            'doublons_details': [],
            'classes_ciblees': 0,
            'classes_introuvables': [],
            'lignes_classes_rejetees': 0,
        }
        self.eleves_importes = []

    def _prochain_numero_ordre(self, classe):
        """Prochain numero de matricule disponible pour une classe."""
        derniere_matricule = Eleve.objects.filter(classe=classe).order_by('-matricule').first()
        if derniere_matricule and derniere_matricule.matricule and '-' in derniere_matricule.matricule:
            try:
                return int(derniere_matricule.matricule.split('-')[-1]) + 1
            except (TypeError, ValueError):
                return 1
        return 1

    def _resoudre_classe(self, row, classe_defaut, classes_exactes, classes_par_nom):
        """Resout une classe d'un export multi-classes sans melanger les classes.

        Un fichier classique sans colonne ``Classe`` utilise la classe choisie
        dans le formulaire. Dans un export global, l'ecole, la classe et l'annee
        sont rapprochees. Une correspondance sans annee n'est acceptee que si
        le nom de classe est unique dans l'ecole cible.
        """
        if 'Classe' not in self.df.columns:
            return classe_defaut

        nom = normaliser_nom_classe(row.get('Classe'))
        if not nom:
            return classe_defaut

        ecole_defaut = normaliser_nom_classe(classe_defaut.ecole.nom)
        ecole_fichier = (
            normaliser_nom_classe(row.get('École'))
            if 'École' in self.df.columns else ''
        )
        ecole = ecole_fichier or ecole_defaut
        annee = _texte(row.get('Année scolaire'))

        classe = classes_exactes.get((ecole, nom, annee)) if annee else None
        if classe is None:
            candidates = classes_par_nom.get((ecole, nom), [])
            if len(candidates) == 1:
                classe = candidates[0]
        if classe:
            return classe

        libelle = f"{ecole_fichier + ' / ' if ecole_fichier else ''}{nom}"
        if annee:
            libelle += f" ({annee})"
        if libelle not in self.stats['classes_introuvables']:
            self.stats['classes_introuvables'].append(libelle)
        return None

    def importer(self):
        """
        Importe les élèves depuis le DataFrame - VERSION OPTIMISÉE
        """
        try:
            # Récupérer la classe
            classe = Classe.objects.get(id=self.classe_id)
        except Classe.DoesNotExist:
            raise ImportElevesError("Classe introuvable")

        # Charger les matricules une seule fois. La normalisation évite qu'une
        # variation de casse ou d'espaces contourne le contrôle d'unicité.
        matricules_existants = {
            cle_matricule(matricule)
            for matricule in Eleve.objects.values_list('matricule', flat=True)
            if matricule
        }

        # ⚡ OPTIMISATION: Charger tous les responsables existants (1 seule requête)
        responsables_dict = {cle_telephone(r.telephone): r for r in Responsable.objects.all()}

        # Seul le compte administrateur peut traiter un export couvrant
        # plusieurs écoles. Pour tout autre compte, les classes d'une autre
        # école sont hors de portée : les lignes concernées seront rejetées.
        from utilisateurs.utils import user_is_superadmin

        classes_qs = Classe.objects.select_related('ecole')
        if not (self.user and user_is_superadmin(self.user)):
            classes_qs = classes_qs.filter(ecole=classe.ecole)
        classes_autorisees = list(classes_qs)

        classes_exactes = {}
        classes_par_nom = {}
        for classe_disponible in classes_autorisees:
            cle_ecole = normaliser_nom_classe(classe_disponible.ecole.nom)
            cle_classe = normaliser_nom_classe(classe_disponible.nom)
            classes_exactes[
                (cle_ecole, cle_classe, classe_disponible.annee_scolaire or '')
            ] = classe_disponible
            classes_par_nom.setdefault((cle_ecole, cle_classe), []).append(
                classe_disponible
            )

        # ⚡ OPTIMISATION: Charger les élèves déjà présents (détection doublons)
        eleves_existants = {}
        ids_classes_autorisees = [c.id for c in classes_autorisees]
        for eleve in Eleve.objects.filter(classe_id__in=ids_classes_autorisees).select_related('responsable_principal', 'responsable_secondaire'):
            key = (eleve.classe_id, f"{eleve.prenom}_{eleve.nom}".lower())
            eleves_existants[key] = eleve

        # Prochain numéro d'ordre des matricules, par classe
        numeros_ordre = {classe.id: self._prochain_numero_ordre(classe)}
        classes_utilisees = set()

        # Listes pour bulk operations
        eleves_a_creer = []
        eleves_a_modifier = []
        # Indexer les responsables en attente évite d'envoyer plusieurs fois
        # le même objet non enregistré à bulk_create().
        responsables_a_creer = {}

        with transaction.atomic():
            for index, row in self.df.iterrows():
                try:
                    self.stats['total'] += 1
                    classe_cible = self._resoudre_classe(
                        row, classe, classes_exactes, classes_par_nom
                    )
                    if classe_cible is None:
                        self.stats['erreurs'] += 1
                        self.stats['lignes_classes_rejetees'] += 1
                        continue
                    classes_utilisees.add(classe_cible.id)
                    if classe_cible.id not in numeros_ordre:
                        numeros_ordre[classe_cible.id] = self._prochain_numero_ordre(classe_cible)

                    resultat = self._preparer_eleve(
                        row, classe_cible, numeros_ordre[classe_cible.id],
                        matricules_existants, responsables_dict, eleves_existants
                    )

                    if resultat:
                        if resultat['type'] == 'creer':
                            eleves_a_creer.append(resultat['eleve'])
                        elif resultat['type'] == 'modifier':
                            eleves_a_modifier.append(resultat['eleve'])
                        elif resultat['type'] == 'doublon':
                            self._enregistrer_doublon(
                                index + 2, row, resultat['matricule']
                            )
                            continue

                        for responsable in resultat.get('responsables') or []:
                            responsables_a_creer[
                                cle_telephone(responsable.telephone)
                            ] = responsable

                    numeros_ordre[classe_cible.id] += 1

                except Exception as e:
                    self.stats['erreurs'] += 1
                    print(f"Erreur ligne {index + 2}: {e}")
            
            # ⚡ BULK CREATE responsables d'abord
            if responsables_a_creer:
                Responsable.objects.bulk_create(
                    list(responsables_a_creer.values()), ignore_conflicts=True
                )
                # Recharger pour avoir les IDs
                responsables_dict = {cle_telephone(r.telephone): r for r in Responsable.objects.all()}

            # Assigner uniquement des responsables réellement enregistrés.
            # Avec ignore_conflicts=True, Django ne renseigne pas forcément les
            # PK des objets passés à bulk_create(), d'où le rechargement.
            for eleve_data in eleves_a_creer + eleves_a_modifier:
                if hasattr(eleve_data, '_responsable_tel'):
                    telephone = eleve_data._responsable_tel
                    responsable = responsables_dict.get(telephone)
                    if responsable is None or responsable.pk is None:
                        raise ImportElevesError(
                            "Impossible d'enregistrer le responsable principal "
                            f"({telephone})"
                        )
                    eleve_data.responsable_principal = responsable
                    delattr(eleve_data, '_responsable_tel')
                if hasattr(eleve_data, '_responsable2_tel'):
                    telephone = eleve_data._responsable2_tel
                    responsable = responsables_dict.get(telephone)
                    if responsable is None or responsable.pk is None:
                        raise ImportElevesError(
                            "Impossible d'enregistrer le responsable secondaire "
                            f"({telephone})"
                        )
                    eleve_data.responsable_secondaire = responsable
                    delattr(eleve_data, '_responsable2_tel')

            # ⚡ BULK CREATE élèves
            if eleves_a_creer:
                Eleve.objects.bulk_create(eleves_a_creer, batch_size=500)
                self.stats['crees'] += len(eleves_a_creer)
            
            # ⚡ BULK UPDATE élèves
            if eleves_a_modifier:
                Eleve.objects.bulk_update(
                    eleves_a_modifier,
                    ['prenom', 'nom', 'sexe', 'date_naissance', 'lieu_naissance', 
                     'responsable_principal', 'responsable_secondaire', 'statut'],
                    batch_size=500
                )
                self.stats['modifies'] += len(eleves_a_modifier)

        self.stats['classes_ciblees'] = len(classes_utilisees)

        return self.stats

    def _enregistrer_doublon(self, ligne_num, row, matricule):
        """Conserve un résumé des lignes rejetées pour le retour utilisateur."""
        self.stats['doublons_ignores'] += 1
        if len(self.stats['doublons_details']) < 20:
            identite = f"{_texte(row.get('Prénom'))} {_texte(row.get('Nom'))}".strip()
            self.stats['doublons_details'].append(
                f"ligne {ligne_num} : {matricule}"
                + (f" ({identite})" if identite else "")
            )
    
    def _preparer_eleve(self, row, classe, numero_ordre, matricules_existants, responsables_dict, eleves_existants):
        """
        Prépare un élève pour bulk creation/update - VERSION OPTIMISÉE
        """
        # Le matricule est le seul identifiant de doublon fiable. Le contrôle
        # couvre la base et les lignes déjà acceptées dans le même fichier.
        matricule_fichier = _texte(row.get('Matricule'))
        cle = cle_matricule(matricule_fichier)
        if cle and cle in matricules_existants:
            return {'type': 'doublon', 'matricule': matricule_fichier}

        # Gérer le responsable principal (optionnel)
        cle_resp = None
        responsable = None
        nouveau_resp = None
        if _texte(row.get('Téléphone Principal')):
            cle_resp, responsable, nouveau_resp = self._preparer_responsable(row, responsables_dict)

        # Gérer le responsable secondaire (mère) - optionnel
        cle_resp2 = None
        responsable_secondaire = None
        nouveau_resp2 = None
        if _texte(row.get('Nom de la Mère')):
            cle_resp2, responsable_secondaire, nouveau_resp2 = self._preparer_responsable_secondaire(row, responsables_dict)

        # Formater la date de naissance (optionnel)
        date_naissance = self._formater_date(row.get('Date de Naissance'))

        # Vérifier si l'élève existe déjà dans la classe cible. Un matricule
        # neuf ne suffit pas à en faire un nouvel élève : sans ce rapprochement,
        # le même enfant réimporté sous un autre matricule serait dupliqué.
        key = (classe.id, f"{_texte(row.get('Prénom'))}_{_texte(row.get('Nom'))}".lower())
        eleve_existant = eleves_existants.get(key)

        # Gérer lieu de naissance (optionnel)
        lieu_naissance = _texte(row.get('Lieu de Naissance')) or None

        if eleve_existant:
            # Modifier
            # Le matricule historique est conservé, mais celui du fichier est
            # marqué comme vu afin de rejeter sa répétition dans le même lot.
            if cle:
                matricules_existants.add(cle)
            eleve_existant.prenom = _texte(row.get('Prénom'))
            eleve_existant.nom = _texte(row.get('Nom')).upper()
            eleve_existant.sexe = _texte(row.get('Sexe')).upper()
            eleve_existant.date_naissance = date_naissance
            eleve_existant.lieu_naissance = lieu_naissance
            eleve_existant.statut = 'ACTIF'
            self._lier_responsables(
                eleve_existant, cle_resp, responsable, cle_resp2, responsable_secondaire
            )

            nouveaux_resp = [
                resp for resp in (nouveau_resp, nouveau_resp2) if resp is not None
            ]
            return {
                'type': 'modifier',
                'eleve': eleve_existant,
                'responsables': nouveaux_resp or None,
            }
        else:
            # Créer : un matricule fourni est libre, sinon il est généré.
            matricule = matricule_fichier
            if not matricule:
                if not self.generer_matricules:
                    raise ImportElevesError("Matricule manquant et génération désactivée")
                matricule = generer_matricule(classe, numero_ordre, classe.annee_scolaire, matricules_existants)
                self.stats['matricules_generes'] += 1
            else:
                matricules_existants.add(cle)

            eleve = Eleve(
                matricule=matricule,
                prenom=_texte(row.get('Prénom')),
                nom=_texte(row.get('Nom')).upper(),
                sexe=_texte(row.get('Sexe')).upper(),
                date_naissance=date_naissance,
                lieu_naissance=lieu_naissance,
                classe=classe,
                date_inscription=datetime.now().date(),
                statut='ACTIF'
            )

            self._lier_responsables(eleve, cle_resp, responsable, cle_resp2, responsable_secondaire)

            nouveaux_resp = []
            if nouveau_resp:
                nouveaux_resp.append(nouveau_resp)
            if nouveau_resp2:
                nouveaux_resp.append(nouveau_resp2)
            
            return {
                'type': 'creer', 
                'eleve': eleve,
                'responsables': nouveaux_resp if nouveaux_resp else None
            }
    
    @staticmethod
    def _lier_responsables(eleve, cle_resp, responsable, cle_resp2, responsable_secondaire):
        """Relie les responsables. Ceux pas encore enregistres sont relies par cle,
        apres le bulk_create des responsables (voir importer())."""
        if responsable is not None:
            eleve.responsable_principal = responsable
        elif cle_resp:
            eleve._responsable_tel = cle_resp

        if responsable_secondaire is not None:
            eleve.responsable_secondaire = responsable_secondaire
        elif cle_resp2:
            eleve._responsable2_tel = cle_resp2

    def _preparer_responsable(self, row, responsables_dict):
        """
        Prépare un responsable principal (père/tuteur) - VERSION OPTIMISÉE
        Retourne (cle, responsable_deja_enregistre, nouveau_responsable_a_creer)
        """
        telephone = nettoyer_telephone(row.get('Téléphone Principal'))
        cle = cle_telephone(telephone)

        # Vérifier en mémoire
        existant = responsables_dict.get(cle)
        if existant is not None:
            # Un responsable du même lot n'a pas encore d'ID : le lien sera fait
            # après le bulk_create, via la clé.
            return (cle, existant if existant.pk else None, None)

        # Créer un nouveau responsable (sera bulk_create plus tard)
        nouveau_resp = Responsable(
            telephone=telephone,
            nom=_texte(row.get('Nom du Père/Tuteur')).upper(),
            prenom=_texte(row.get('Prénom du Père/Tuteur')),
            adresse=_texte(row.get('Adresse')),
            email=_texte(row.get('Email')) or None,
        )

        # Ajouter au dict pour éviter duplicatas dans le même batch
        responsables_dict[cle] = nouveau_resp

        return (cle, None, nouveau_resp)

    def _preparer_responsable_secondaire(self, row, responsables_dict):
        """
        Prépare un responsable secondaire (mère) - VERSION OPTIMISÉE
        Retourne (cle, responsable_deja_enregistre, nouveau_responsable_a_creer)
        """
        telephone = nettoyer_telephone(row.get('Téléphone Secondaire'))
        if not telephone:
            telephone = nettoyer_telephone(row.get('Téléphone Principal')) + '_2'

        cle = cle_telephone(telephone)

        # Vérifier en mémoire
        existant = responsables_dict.get(cle)
        if existant is not None:
            return (cle, existant if existant.pk else None, None)

        # Créer un nouveau responsable (sera bulk_create plus tard)
        nouveau_resp = Responsable(
            telephone=telephone,
            nom=_texte(row.get('Nom de la Mère')).upper(),
            prenom=_texte(row.get('Prénom de la Mère')),
            adresse=_texte(row.get('Adresse')),
        )

        # Ajouter au dict pour éviter duplicatas dans le même batch
        responsables_dict[cle] = nouveau_resp

        return (cle, None, nouveau_resp)
    
    def _formater_date(self, date_str):
        """
        Formate une date depuis différents formats possibles
        """
        if date_str is None or pd.isna(date_str):
            return None

        # Cellule Excel de type date
        if hasattr(date_str, 'date') and not isinstance(date_str, str):
            return date_str.date()

        date_str = str(date_str).strip()
        if not date_str:
            return None

        # Essayer différents formats
        for fmt in ['%d/%m/%Y', '%Y-%m-%d', '%d-%m-%Y', '%d.%m.%Y',
                    '%Y-%m-%d %H:%M:%S', '%d/%m/%Y %H:%M:%S']:
            try:
                return datetime.strptime(date_str, fmt).date()
            except ValueError:
                continue

        # Si aucun format ne marche, lever une exception
        raise ImportElevesError(f"Format de date invalide: {date_str}")


def _ligne_modele_import(eleve, avec_classe=False):
    """Convertit un eleve en ligne au format du template d'importation."""
    responsable = eleve.responsable_principal
    responsable_2 = eleve.responsable_secondaire

    ligne = {
        'Matricule': eleve.matricule or '',
        'Prénom': eleve.prenom or '',
        'Nom': eleve.nom or '',
        'Sexe': eleve.sexe or '',
        'Date de Naissance': eleve.date_naissance.strftime('%d/%m/%Y') if eleve.date_naissance else '',
        'Lieu de Naissance': eleve.lieu_naissance or '',
        'Nom du Père/Tuteur': responsable.nom if responsable else '',
        'Prénom du Père/Tuteur': responsable.prenom if responsable else '',
        'Téléphone Principal': responsable.telephone if responsable else '',
        'Adresse': responsable.adresse if responsable else '',
        'Nom de la Mère': responsable_2.nom if responsable_2 else '',
        'Prénom de la Mère': responsable_2.prenom if responsable_2 else '',
        'Téléphone Secondaire': responsable_2.telephone if responsable_2 else '',
        'Email': (responsable.email if responsable else '') or '',
    }

    if avec_classe:
        classe = eleve.classe
        ligne['École'] = classe.ecole.nom if classe and classe.ecole else ''
        ligne['Classe'] = classe.nom if classe else ''
        ligne['Année scolaire'] = (classe.annee_scolaire if classe else '') or ''

    return ligne


def exporter_liste_eleves(classe_id):
    """
    Exporte la liste des élèves d'une classe au format Excel
    """
    try:
        classe = Classe.objects.get(id=classe_id)
        eleves = (
            Eleve.objects.filter(classe=classe, statut='ACTIF')
            .select_related('responsable_principal', 'responsable_secondaire')
            .order_by('nom', 'prenom')
        )

        data = [_ligne_modele_import(eleve) for eleve in eleves]

        return pd.DataFrame(data, columns=COLONNES_TEMPLATE)

    except Exception as e:
        raise ImportElevesError(f"Erreur lors de l'export: {e}")


def exporter_eleves_modele_import(eleves_qs):
    """
    Exporte un queryset d'élèves au format de transfert réimportable :
    École / Classe / Année scolaire, puis les champs du template d'importation.
    """
    try:
        eleves = eleves_qs.select_related(
            'classe', 'classe__ecole', 'responsable_principal', 'responsable_secondaire'
        ).order_by('classe__annee_scolaire', 'classe__nom', 'nom', 'prenom')

        data = [_ligne_modele_import(eleve, avec_classe=True) for eleve in eleves]

        return pd.DataFrame(data, columns=COLONNES_TRANSFERT)

    except Exception as e:
        raise ImportElevesError(f"Erreur lors de l'export: {e}")
