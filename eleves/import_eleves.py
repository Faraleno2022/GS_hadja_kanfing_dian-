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
        while Eleve.objects.filter(matricule=matricule).exists():
            numero_ordre += 1
            matricule = f"{code_classe}-{annee_scolaire}-{numero_ordre:03d}"
    else:
        # Utiliser le set en mémoire (RAPIDE!)
        while matricule in matricules_existants:
            numero_ordre += 1
            matricule = f"{code_classe}-{annee_scolaire}-{numero_ordre:03d}"
        # Ajouter au set pour éviter réutilisation
        matricules_existants.add(matricule)
    
    return matricule


def lire_fichier_eleves(file_path_or_obj):
    """
    Lit un fichier Excel ou CSV contenant la liste des élèves
    """
    try:
        # Tout lire en texte : Excel convertirait sinon les numéros de
        # téléphone et les matricules en flottants (622613559 -> 6.22e+08).
        if hasattr(file_path_or_obj, 'name'):
            nom = file_path_or_obj.name
        else:
            nom = str(file_path_or_obj)

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
        # Colonnes du template
        colonnes = [
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
            'Email'  # Optionnel
        ]
        
        # Créer un DataFrame avec des exemples
        data = {col: [] for col in colonnes}
        
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
        # Index (au sens du DataFrame) des lignes en erreur, pour pouvoir
        # importer les lignes valides et ne signaler que les autres.
        self.lignes_invalides = set()

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
            avant = len(self.erreurs)
            self._valider_ligne(index + 2, row)  # +2 car Excel commence à 1 + en-tête
            if len(self.erreurs) > avant:
                self.lignes_invalides.add(index)

        return len(self.erreurs) == 0

    def lignes_valides(self):
        """Retourne le sous-ensemble du fichier exempt d'erreurs."""
        if not self.lignes_invalides:
            return self.df
        return self.df.drop(index=list(self.lignes_invalides), errors='ignore')

    def _valider_ligne(self, ligne_num, row):
        """
        Valide une ligne du fichier
        """
        # Seuls le prénom et le nom sont indispensables pour créer un élève
        for champ in ['Prénom', 'Nom']:
            if not _valeur_texte(row.get(champ)):
                self.erreurs.append(
                    f"Ligne {ligne_num}: Le champ '{champ}' est obligatoire"
                )

        # Le sexe est signalé mais ne bloque pas : un transfert entre postes
        # doit reproduire la base d'origine, y compris ses champs incomplets.
        sexe = _valeur_texte(row.get('Sexe')).upper()
        if not sexe:
            self.avertissements.append(
                f"Ligne {ligne_num}: Sexe non renseigné"
            )
        elif sexe not in ['M', 'F']:
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
        tel = normaliser_telephone(row.get('Téléphone Principal'))
        if tel:
            chiffres = ''.join(c for c in tel if c.isdigit())
            if len(chiffres) < 8:
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
            'matricules_generes': 0
        }
        self.eleves_importes = []
        
    def importer(self):
        """
        Importe les élèves depuis le DataFrame - VERSION OPTIMISÉE
        """
        try:
            # Récupérer la classe
            classe = Classe.objects.get(id=self.classe_id)
        except Classe.DoesNotExist:
            raise ImportElevesError("Classe introuvable")
        
        # ⚡ OPTIMISATION: Charger tous les matricules existants (1 seule requête)
        matricules_existants = set(Eleve.objects.values_list('matricule', flat=True))
        
        # ⚡ OPTIMISATION: Charger tous les responsables existants (1 seule requête)
        responsables_dict = {r.telephone: r for r in Responsable.objects.all()}
        
        # ⚡ OPTIMISATION: Charger les élèves de la classe (détection doublons)
        eleves_existants = {}
        for eleve in Eleve.objects.filter(classe=classe).select_related('responsable_principal', 'responsable_secondaire'):
            key = f"{eleve.prenom}_{eleve.nom}".lower()
            eleves_existants[key] = eleve
        
        # Obtenir le prochain numéro d'ordre pour les matricules
        derniere_matricule = Eleve.objects.filter(
            classe=classe
        ).order_by('-matricule').first()
        
        if derniere_matricule and '-' in derniere_matricule.matricule:
            try:
                numero_ordre = int(derniere_matricule.matricule.split('-')[-1]) + 1
            except:
                numero_ordre = 1
        else:
            numero_ordre = 1
        
        # Listes pour bulk operations
        eleves_a_creer = []
        eleves_a_modifier = []
        responsables_a_creer = []
        
        with transaction.atomic():
            for index, row in self.df.iterrows():
                try:
                    self.stats['total'] += 1
                    resultat = self._preparer_eleve(
                        row, classe, numero_ordre, 
                        matricules_existants, responsables_dict, eleves_existants
                    )
                    
                    if resultat:
                        if resultat['type'] == 'creer':
                            eleves_a_creer.append(resultat['eleve'])
                            if resultat.get('responsables'):
                                responsables_a_creer.extend(resultat['responsables'])
                        elif resultat['type'] == 'modifier':
                            eleves_a_modifier.append(resultat['eleve'])
                    
                    numero_ordre += 1
                    
                except Exception as e:
                    self.stats['erreurs'] += 1
                    print(f"Erreur ligne {index + 2}: {e}")
            
            # ⚡ BULK CREATE responsables d'abord
            if responsables_a_creer:
                Responsable.objects.bulk_create(responsables_a_creer, ignore_conflicts=True)
                # Recharger pour avoir les IDs
                responsables_dict = {r.telephone: r for r in Responsable.objects.all()}
            
            # Assigner les responsables aux élèves
            for eleve_data in eleves_a_creer:
                if hasattr(eleve_data, '_responsable_tel'):
                    eleve_data.responsable_principal = responsables_dict.get(eleve_data._responsable_tel)
                if hasattr(eleve_data, '_responsable2_tel'):
                    eleve_data.responsable_secondaire = responsables_dict.get(eleve_data._responsable2_tel)
            
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
        
        return self.stats
    
    def _preparer_eleve(self, row, classe, numero_ordre, matricules_existants, responsables_dict, eleves_existants):
        """
        Prépare un élève pour bulk creation/update - VERSION OPTIMISÉE
        """
        # Préparer les données de l'élève
        matricule = _valeur_texte(row.get('Matricule'))

        # Générer le matricule si nécessaire
        if not matricule:
            if self.generer_matricules:
                matricule = generer_matricule(classe, numero_ordre, classe.annee_scolaire, matricules_existants)
                self.stats['matricules_generes'] += 1
            else:
                raise ImportElevesError("Matricule manquant et génération désactivée")
        elif matricule in matricules_existants:
            # Matricule déjà pris par un autre élève : en générer un nouveau
            if self.generer_matricules:
                matricule = generer_matricule(classe, numero_ordre, classe.annee_scolaire, matricules_existants)
                self.stats['matricules_generes'] += 1
            else:
                raise ImportElevesError(f"Matricule déjà utilisé: {matricule}")
        else:
            matricules_existants.add(matricule)

        # Gérer le responsable principal (optionnel)
        responsable = None
        nouveau_resp = None
        if normaliser_telephone(row.get('Téléphone Principal')):
            responsable, nouveau_resp = self._preparer_responsable(row, responsables_dict)

        # Gérer le responsable secondaire (mère) - optionnel
        responsable_secondaire = None
        nouveau_resp2 = None
        if _valeur_texte(row.get('Nom de la Mère')):
            responsable_secondaire, nouveau_resp2 = self._preparer_responsable_secondaire(row, responsables_dict)

        # Formater la date de naissance (optionnel)
        date_naissance = self._formater_date(row.get('Date de Naissance'))

        # Vérifier si l'élève existe déjà
        key = f"{_valeur_texte(row.get('Prénom'))}_{_valeur_texte(row.get('Nom'))}".lower()
        eleve_existant = eleves_existants.get(key)

        # Gérer lieu de naissance (optionnel)
        lieu_naissance = _valeur_texte(row.get('Lieu de Naissance')) or None

        if eleve_existant:
            # Modifier
            eleve_existant.prenom = _valeur_texte(row.get('Prénom'))
            eleve_existant.nom = _valeur_texte(row.get('Nom')).upper()
            eleve_existant.sexe = _valeur_texte(row.get('Sexe')).upper()
            eleve_existant.date_naissance = date_naissance
            eleve_existant.lieu_naissance = lieu_naissance
            eleve_existant.responsable_principal = responsable
            eleve_existant.responsable_secondaire = responsable_secondaire
            eleve_existant.statut = 'ACTIF'
            
            return {'type': 'modifier', 'eleve': eleve_existant}
        else:
            # Créer
            eleve = Eleve(
                matricule=matricule,
                prenom=_valeur_texte(row.get('Prénom')),
                nom=_valeur_texte(row.get('Nom')).upper(),
                sexe=_valeur_texte(row.get('Sexe')).upper(),
                date_naissance=date_naissance,
                lieu_naissance=lieu_naissance,
                classe=classe,
                date_inscription=datetime.now().date(),
                statut='ACTIF'
            )
            
            # Stocker les téléphones pour lier après bulk_create des responsables
            if responsable:
                eleve.responsable_principal = responsable
            elif nouveau_resp:
                eleve._responsable_tel = nouveau_resp.telephone
            
            if responsable_secondaire:
                eleve.responsable_secondaire = responsable_secondaire
            elif nouveau_resp2:
                eleve._responsable2_tel = nouveau_resp2.telephone
            
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
    
    def _preparer_responsable(self, row, responsables_dict):
        """
        Prépare un responsable principal (père/tuteur) - VERSION OPTIMISÉE
        Retourne (responsable_existant, nouveau_responsable)
        """
        telephone = normaliser_telephone(row.get('Téléphone Principal'))

        # Vérifier en mémoire
        if telephone in responsables_dict:
            return (responsables_dict[telephone], None)

        # Créer un nouveau responsable (sera bulk_create plus tard)
        nouveau_resp = Responsable(
            telephone=telephone,
            nom=_valeur_texte(row.get('Nom du Père/Tuteur')).upper(),
            prenom=_valeur_texte(row.get('Prénom du Père/Tuteur')),
            adresse=_valeur_texte(row.get('Adresse')),
            email=_valeur_texte(row.get('Email')) or None,
        )

        # Ajouter au dict pour éviter duplicatas dans le même batch
        responsables_dict[telephone] = nouveau_resp

        return (None, nouveau_resp)

    def _preparer_responsable_secondaire(self, row, responsables_dict):
        """
        Prépare un responsable secondaire (mère) - VERSION OPTIMISÉE
        Retourne (responsable_existant, nouveau_responsable)
        """
        telephone = normaliser_telephone(row.get('Téléphone Secondaire'))

        if not telephone:
            principal = normaliser_telephone(row.get('Téléphone Principal'))
            telephone = f"{principal}_2" if principal else ''

        if not telephone:
            return (None, None)

        # Vérifier en mémoire
        if telephone in responsables_dict:
            return (responsables_dict[telephone], None)

        # Créer un nouveau responsable (sera bulk_create plus tard)
        nouveau_resp = Responsable(
            telephone=telephone,
            nom=_valeur_texte(row.get('Nom de la Mère')).upper(),
            prenom=_valeur_texte(row.get('Prénom de la Mère')),
            adresse=_valeur_texte(row.get('Adresse')),
        )

        # Ajouter au dict pour éviter duplicatas dans le même batch
        responsables_dict[telephone] = nouveau_resp

        return (None, nouveau_resp)

    def _formater_date(self, date_str):
        """
        Formate une date depuis différents formats possibles
        """
        if hasattr(date_str, 'date') and not isinstance(date_str, str):
            try:
                return date_str.date()
            except Exception:
                pass

        texte = _valeur_texte(date_str)
        if not texte:
            return None

        # Excel peut renvoyer "2010-01-01 00:00:00"
        texte = texte.split(' ')[0]

        for fmt in ['%d/%m/%Y', '%Y-%m-%d', '%d-%m-%Y', '%d.%m.%Y']:
            try:
                return datetime.strptime(texte, fmt).date()
            except ValueError:
                continue

        # Si aucun format ne marche, lever une exception
        raise ImportElevesError(f"Format de date invalide: {texte}")


# Colonnes du modèle d'importation, dans l'ordre attendu par l'importateur
COLONNES_TEMPLATE = [
    'Matricule',
    'Prénom',
    'Nom',
    'Sexe',
    'Date de Naissance',
    'Lieu de Naissance',
    'Nom du Père/Tuteur',
    'Prénom du Père/Tuteur',
    'Téléphone Principal',
    'Adresse',
    'Nom de la Mère',
    'Prénom de la Mère',
    'Téléphone Secondaire',
    'Email',
]


def ligne_template_eleve(eleve):
    """Transforme un élève en une ligne au format du template d'importation."""
    responsable = eleve.responsable_principal
    responsable_2 = eleve.responsable_secondaire

    return {
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


def exporter_liste_eleves(classe_id):
    """
    Exporte la liste des élèves d'une classe au format Excel
    """
    try:
        classe = Classe.objects.get(id=classe_id)
        eleves = Eleve.objects.filter(classe=classe, statut='ACTIF').select_related(
            'responsable_principal', 'responsable_secondaire'
        ).order_by('nom', 'prenom')

        data = [ligne_template_eleve(eleve) for eleve in eleves]

        return pd.DataFrame(data, columns=COLONNES_TEMPLATE)

    except Exception as e:
        raise ImportElevesError(f"Erreur lors de l'export: {e}")


# Colonnes de localisation ajoutées en tête de l'export complet : elles
# permettent de réimporter un fichier sur un autre poste sans avoir à choisir
# la classe de destination pour chaque feuille.
COLONNES_LOCALISATION = ['École', 'Classe', 'Année scolaire']

COLONNES_EXPORT_COMPLET = COLONNES_LOCALISATION + COLONNES_TEMPLATE

# Variantes tolérées à la lecture (accents, casse, abréviations)
ALIAS_COLONNES_LOCALISATION = {
    'école': 'École',
    'ecole': 'École',
    'etablissement': 'École',
    'établissement': 'École',
    'classe': 'Classe',
    'année scolaire': 'Année scolaire',
    'annee scolaire': 'Année scolaire',
    'annee_scolaire': 'Année scolaire',
    'année': 'Année scolaire',
    'annee': 'Année scolaire',
}


def normaliser_colonnes_localisation(df):
    """Renomme les variantes des colonnes École / Classe / Année scolaire."""
    renommage = {}
    for colonne in df.columns:
        cle = str(colonne).strip().lower()
        cible = ALIAS_COLONNES_LOCALISATION.get(cle)
        if cible and cible not in df.columns:
            renommage[colonne] = cible
    if renommage:
        df = df.rename(columns=renommage)
    return df


def ligne_export_complet(eleve):
    """Ligne d'export incluant l'école, la classe et l'année scolaire."""
    classe = eleve.classe
    ligne = {
        'École': getattr(getattr(classe, 'ecole', None), 'nom', '') or '',
        'Classe': getattr(classe, 'nom', '') or '',
        'Année scolaire': getattr(classe, 'annee_scolaire', '') or '',
    }
    ligne.update(ligne_template_eleve(eleve))
    return ligne


def _valeur_texte(valeur):
    """Convertit une cellule pandas en texte propre ('' si vide)."""
    if valeur is None or (isinstance(valeur, float) and pd.isna(valeur)):
        return ''
    try:
        if pd.isna(valeur):
            return ''
    except (TypeError, ValueError):
        pass
    texte = str(valeur).strip()
    # Excel transforme volontiers un identifiant numérique en flottant
    if texte.endswith('.0') and texte[:-2].replace('-', '').isdigit():
        texte = texte[:-2]
    return texte


def normaliser_telephone(valeur):
    """Nettoie un numéro lu depuis Excel et restaure le préfixe guinéen.

    Excel convertit « 224622613559 » en flottant : on reconstruit une chaîne,
    on retire séparateurs et espaces, puis on remet le ``+224`` attendu par le
    validateur du modèle.
    """
    texte = _valeur_texte(valeur).replace(' ', '').replace('-', '').replace('.', '')
    if not texte:
        return ''
    if texte.startswith('+'):
        return texte
    if texte.startswith('224') and len(texte) >= 11:
        return '+' + texte
    if texte.isdigit() and len(texte) in (8, 9):
        return '+224' + texte
    return texte


def resoudre_classe(nom_classe, annee_scolaire, ecole, creer=True, niveau_defaut='PRIMAIRE_1'):
    """Retrouve — ou crée — la classe correspondant à une ligne du fichier.

    La recherche se fait sur (école, nom, année scolaire), puis sur
    (école, nom) si l'année n'a pas donné de résultat. Retourne
    ``(classe, cree)``.
    """
    nom_classe = _valeur_texte(nom_classe)
    annee_scolaire = _valeur_texte(annee_scolaire)

    if not nom_classe:
        raise ImportElevesError("Nom de classe manquant dans le fichier.")
    if ecole is None:
        raise ImportElevesError(
            f"Aucune école ne correspond pour la classe « {nom_classe} »."
        )

    classes = Classe.objects.filter(ecole=ecole, nom__iexact=nom_classe)
    if annee_scolaire:
        classe = classes.filter(annee_scolaire=annee_scolaire).first()
        if classe:
            return classe, False
    classe = classes.first()
    if classe:
        return classe, False

    if not creer:
        raise ImportElevesError(
            f"La classe « {nom_classe} » n'existe pas dans l'école {ecole.nom}."
        )

    # Deviner le niveau à partir du nom, sinon retomber sur le niveau par défaut
    niveau = _deviner_niveau(nom_classe) or niveau_defaut
    classe = Classe.objects.create(
        ecole=ecole,
        nom=nom_classe,
        niveau=niveau,
        annee_scolaire=annee_scolaire or _annee_scolaire_courante(),
    )
    return classe, True


def _annee_scolaire_courante():
    aujourdhui = datetime.now()
    if aujourdhui.month >= 9:
        return f"{aujourdhui.year}-{aujourdhui.year + 1}"
    return f"{aujourdhui.year - 1}-{aujourdhui.year}"


_MOTS_NIVEAUX = [
    ('GARDERIE', ['GARDERIE', 'CRECHE', 'CRÈCHE']),
    ('MATERNELLE', ['MATERNELLE', 'PETITE SECTION', 'MOYENNE SECTION', 'GRANDE SECTION']),
    ('PRIMAIRE_1', ['1ERE ANNEE', '1ÈRE ANNÉE', '1RE ANNEE', 'CP1']),
    ('PRIMAIRE_2', ['2EME ANNEE', '2ÈME ANNÉE', 'CP2']),
    ('PRIMAIRE_3', ['3EME ANNEE', '3ÈME ANNÉE', 'CE1']),
    ('PRIMAIRE_4', ['4EME ANNEE', '4ÈME ANNÉE', 'CE2']),
    ('PRIMAIRE_5', ['5EME ANNEE', '5ÈME ANNÉE', 'CM1']),
    ('PRIMAIRE_6', ['6EME ANNEE', '6ÈME ANNÉE', 'CM2']),
    ('COLLEGE_7', ['7EME ANNEE', '7ÈME ANNÉE']),
    ('COLLEGE_8', ['8EME ANNEE', '8ÈME ANNÉE']),
    ('COLLEGE_9', ['9EME ANNEE', '9ÈME ANNÉE']),
    ('COLLEGE_10', ['10EME ANNEE', '10ÈME ANNÉE']),
    ('LYCEE_11', ['11EME', '11ÈME', '11 ']),
    ('LYCEE_12', ['12EME', '12ÈME', '12 ']),
    ('TERMINALE', ['TERMINALE', 'TSS', 'TSE', 'TSM']),
]


def _deviner_niveau(nom_classe):
    """Déduit le niveau d'une classe depuis son nom (retourne None si inconnu)."""
    nom = (nom_classe or '').upper()
    for niveau, motifs in _MOTS_NIVEAUX:
        if any(motif in nom for motif in motifs):
            return niveau
    return None


def exporter_tous_les_eleves(ecole=None, inclure_inactifs=False):
    """Exporte tous les élèves dans un tableau unique prêt à être réimporté.

    Le fichier produit contient l'école, la classe et l'année scolaire de
    chaque élève : il peut donc être importé tel quel sur un autre poste, la
    répartition dans les classes étant déduite du fichier lui-même.
    """
    try:
        eleves = Eleve.objects.select_related(
            'classe', 'classe__ecole', 'responsable_principal', 'responsable_secondaire'
        ).order_by('classe__ecole__nom', 'classe__annee_scolaire', 'classe__nom', 'nom', 'prenom')

        if ecole is not None:
            eleves = eleves.filter(classe__ecole=ecole)
        if not inclure_inactifs:
            eleves = eleves.filter(statut='ACTIF')

        lignes = [ligne_export_complet(eleve) for eleve in eleves]

        return pd.DataFrame(lignes, columns=COLONNES_EXPORT_COMPLET)

    except Exception as e:
        raise ImportElevesError(f"Erreur lors de l'export global: {e}")
