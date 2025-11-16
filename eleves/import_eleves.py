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


def generer_matricule(classe, numero_ordre, annee_scolaire=None):
    """
    Génère un matricule unique pour un élève
    Format: [CODE_CLASSE][ANNEE][NUMERO]
    Exemple: 6A-2024-001
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
    
    # Vérifier l'unicité
    while Eleve.objects.filter(matricule=matricule).exists():
        numero_ordre += 1
        matricule = f"{code_classe}-{annee_scolaire}-{numero_ordre:03d}"
    
    return matricule


def lire_fichier_eleves(file_path_or_obj):
    """
    Lit un fichier Excel ou CSV contenant la liste des élèves
    """
    try:
        # Déterminer le type de fichier
        if hasattr(file_path_or_obj, 'name'):
            if file_path_or_obj.name.endswith('.csv'):
                df = pd.read_csv(file_path_or_obj)
            else:
                df = pd.read_excel(file_path_or_obj)
        else:
            # Si c'est un chemin
            if str(file_path_or_obj).endswith('.csv'):
                df = pd.read_csv(file_path_or_obj)
            else:
                df = pd.read_excel(file_path_or_obj)
        
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
            'Sexe',  # M ou F
            'Date de Naissance',  # Format: JJ/MM/AAAA
            'Lieu de Naissance',  # Obligatoire
            'Nom du Père/Tuteur',  # Obligatoire
            'Prénom du Père/Tuteur',  # Obligatoire
            'Téléphone Principal',  # Obligatoire
            'Adresse',  # Obligatoire
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
        
    def valider(self):
        """
        Valide le fichier importé
        """
        # Vérifier les colonnes requises
        colonnes_requises = ['Prénom', 'Nom', 'Sexe', 'Date de Naissance', 
                           'Lieu de Naissance', 'Nom du Père/Tuteur', 
                           'Prénom du Père/Tuteur', 'Téléphone Principal', 'Adresse']
        
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
        # Vérifier les champs obligatoires
        champs_obligatoires = ['Prénom', 'Nom', 'Sexe', 'Date de Naissance', 
                              'Lieu de Naissance', 'Nom du Père/Tuteur', 
                              'Prénom du Père/Tuteur', 'Téléphone Principal', 'Adresse']
        
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
        
        # Valider la date de naissance
        if row.get('Date de Naissance'):
            try:
                # Essayer différents formats
                date_str = str(row['Date de Naissance'])
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
        
        # Valider le téléphone
        if row.get('Téléphone Principal'):
            tel = str(row['Téléphone Principal']).replace(' ', '').replace('-', '')
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
            'matricules_generes': 0
        }
        self.eleves_importes = []
        
    def importer(self):
        """
        Importe les élèves depuis le DataFrame
        """
        try:
            # Récupérer la classe
            classe = Classe.objects.get(id=self.classe_id)
        except Classe.DoesNotExist:
            raise ImportElevesError("Classe introuvable")
        
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
        
        with transaction.atomic():
            for index, row in self.df.iterrows():
                try:
                    self.stats['total'] += 1
                    self._importer_eleve(row, classe, numero_ordre)
                    numero_ordre += 1
                except Exception as e:
                    self.stats['erreurs'] += 1
                    print(f"Erreur ligne {index + 2}: {e}")
        
        return self.stats
    
    def _importer_eleve(self, row, classe, numero_ordre):
        """
        Importe un élève individuel
        """
        # Préparer les données de l'élève
        matricule = row.get('Matricule')
        
        # Générer le matricule si nécessaire
        if not matricule or pd.isna(matricule) or str(matricule).strip() == '':
            if self.generer_matricules:
                matricule = generer_matricule(classe, numero_ordre, classe.annee_scolaire)
                self.stats['matricules_generes'] += 1
            else:
                raise ImportElevesError("Matricule manquant et génération désactivée")
        else:
            matricule = str(matricule).strip()
        
        # Gérer le responsable principal
        responsable = self._obtenir_ou_creer_responsable(row)
        
        # Gérer le responsable secondaire (mère)
        responsable_secondaire = None
        if row.get('Nom de la Mère') and not pd.isna(row.get('Nom de la Mère')):
            responsable_secondaire = self._obtenir_ou_creer_responsable_secondaire(row)
        
        # Formater la date de naissance
        date_naissance = self._formater_date(row.get('Date de Naissance'))
        
        # Données de l'élève
        donnees_eleve = {
            'prenom': str(row['Prénom']).strip(),
            'nom': str(row['Nom']).strip().upper(),
            'sexe': str(row['Sexe']).upper(),
            'date_naissance': date_naissance,
            'lieu_naissance': str(row['Lieu de Naissance']).strip(),
            'classe': classe,
            'date_inscription': datetime.now().date(),
            'responsable_principal': responsable,
            'responsable_secondaire': responsable_secondaire,
            'statut': 'ACTIF'
        }
        
        # Créer ou mettre à jour l'élève
        eleve, created = Eleve.objects.update_or_create(
            matricule=matricule,
            defaults=donnees_eleve
        )
        
        if created:
            self.stats['crees'] += 1
        else:
            self.stats['modifies'] += 1
        
        self.eleves_importes.append(eleve)
        
        return eleve
    
    def _obtenir_ou_creer_responsable(self, row):
        """
        Obtient ou crée un responsable principal (père/tuteur)
        """
        telephone = str(row['Téléphone Principal']).replace(' ', '').replace('-', '')
        
        responsable, created = Responsable.objects.get_or_create(
            telephone=telephone,
            defaults={
                'nom': str(row['Nom du Père/Tuteur']).strip().upper(),
                'prenom': str(row['Prénom du Père/Tuteur']).strip(),
                'adresse': str(row['Adresse']).strip(),
                'email': row.get('Email') if not pd.isna(row.get('Email')) else None
            }
        )
        
        return responsable
    
    def _obtenir_ou_creer_responsable_secondaire(self, row):
        """
        Obtient ou crée un responsable secondaire (mère)
        """
        telephone = row.get('Téléphone Secondaire')
        
        if pd.isna(telephone) or str(telephone).strip() == '':
            telephone = str(row['Téléphone Principal']).replace(' ', '').replace('-', '') + '_2'
        else:
            telephone = str(telephone).replace(' ', '').replace('-', '')
        
        responsable, created = Responsable.objects.get_or_create(
            telephone=telephone,
            defaults={
                'nom': str(row['Nom de la Mère']).strip().upper(),
                'prenom': str(row['Prénom de la Mère']).strip(),
                'adresse': str(row['Adresse']).strip()
            }
        )
        
        return responsable
    
    def _formater_date(self, date_str):
        """
        Formate une date depuis différents formats possibles
        """
        if pd.isna(date_str):
            return None
        
        date_str = str(date_str)
        
        # Essayer différents formats
        for fmt in ['%d/%m/%Y', '%Y-%m-%d', '%d-%m-%Y', '%d.%m.%Y']:
            try:
                return datetime.strptime(date_str, fmt).date()
            except:
                continue
        
        # Si aucun format ne marche, lever une exception
        raise ImportElevesError(f"Format de date invalide: {date_str}")


def exporter_liste_eleves(classe_id):
    """
    Exporte la liste des élèves d'une classe au format Excel
    """
    try:
        classe = Classe.objects.get(id=classe_id)
        eleves = Eleve.objects.filter(classe=classe, statut='ACTIF').order_by('nom', 'prenom')
        
        data = []
        for eleve in eleves:
            responsable = eleve.responsable_principal
            responsable_2 = eleve.responsable_secondaire
            
            data.append({
                'Matricule': eleve.matricule,
                'Prénom': eleve.prenom,
                'Nom': eleve.nom,
                'Sexe': eleve.sexe,
                'Date de Naissance': eleve.date_naissance.strftime('%d/%m/%Y') if eleve.date_naissance else '',
                'Lieu de Naissance': eleve.lieu_naissance,
                'Nom du Père/Tuteur': responsable.nom if responsable else '',
                'Prénom du Père/Tuteur': responsable.prenom if responsable else '',
                'Téléphone Principal': responsable.telephone if responsable else '',
                'Adresse': responsable.adresse if responsable else '',
                'Nom de la Mère': responsable_2.nom if responsable_2 else '',
                'Prénom de la Mère': responsable_2.prenom if responsable_2 else '',
                'Téléphone Secondaire': responsable_2.telephone if responsable_2 else '',
                'Email': responsable.email if responsable else ''
            })
        
        df = pd.DataFrame(data)
        
        return df
    
    except Exception as e:
        raise ImportElevesError(f"Erreur lors de l'export: {e}")
