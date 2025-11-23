"""
Module d'importation de notes depuis fichiers Excel/CSV
Supporte: Notes mensuelles, Compositions, Évaluations
"""
import pandas as pd
from decimal import Decimal, InvalidOperation
from django.db import transaction
from django.contrib import messages
from .models import NoteEleve, NoteMensuelle, CompositionNote, MatiereNote, Evaluation, ClasseNote
from eleves.models import Eleve


class ImportNotesError(Exception):
    """Erreur lors de l'importation"""
    pass


class ImportNotesValidator:
    """Validateur pour l'importation de notes"""
    
    def __init__(self, df, classe_id=None, matiere_id=None, evaluation_id=None, type_import='MENSUELLE'):
        self.df = df
        self.classe_id = classe_id
        self.matiere_id = matiere_id
        self.evaluation_id = evaluation_id
        self.type_import = type_import
        self.erreurs = []
        self.avertissements = []
    
    def valider(self):
        """Valide le fichier importé"""
        # Vérifier les colonnes requises
        colonnes_requises = self._get_colonnes_requises()
        colonnes_manquantes = set(colonnes_requises) - set(self.df.columns)
        
        if colonnes_manquantes:
            raise ImportNotesError(
                f"Colonnes manquantes: {', '.join(colonnes_manquantes)}"
            )
        
        # Valider chaque ligne
        for index, row in self.df.iterrows():
            self._valider_ligne(index + 2, row)  # +2 car Excel commence à 1 et il y a l'en-tête
        
        return len(self.erreurs) == 0
    
    def _get_colonnes_requises(self):
        """Retourne les colonnes requises selon le type d'import"""
        colonnes_base = ['Matricule', 'Prénom', 'Nom']
        
        if self.type_import == 'MENSUELLE':
            return colonnes_base + ['Note', 'Absent']
        elif self.type_import == 'COMPOSITION':
            return colonnes_base + ['Note', 'Absent']
        elif self.type_import == 'EVALUATION':
            return colonnes_base + ['Note', 'Absent']
        
        return colonnes_base
    
    def _valider_ligne(self, numero_ligne, row):
        """Valide une ligne du fichier"""
        # Vérifier le matricule
        matricule = str(row.get('Matricule', '')).strip()
        if not matricule or pd.isna(row['Matricule']):
            self.erreurs.append(f"Ligne {numero_ligne}: Matricule manquant")
            return
        
        # Vérifier que l'élève existe
        try:
            eleve = Eleve.objects.get(matricule=matricule)
        except Eleve.DoesNotExist:
            self.erreurs.append(f"Ligne {numero_ligne}: Élève avec matricule '{matricule}' introuvable")
            return
        
        # Vérifier la note
        absent = str(row.get('Absent', 'NON')).strip().upper() in ['OUI', 'O', 'YES', 'Y', '1', 'TRUE']
        
        if not absent:
            note = row.get('Note')
            if pd.isna(note) or note == '':
                self.avertissements.append(f"Ligne {numero_ligne}: Note manquante pour {eleve}")
            else:
                try:
                    note_decimal = Decimal(str(note))
                    if note_decimal < 0 or note_decimal > 20:
                        self.erreurs.append(f"Ligne {numero_ligne}: Note invalide ({note}) - doit être entre 0 et 20")
                except (InvalidOperation, ValueError):
                    self.erreurs.append(f"Ligne {numero_ligne}: Format de note invalide ({note})")


class ImportNotesProcessor:
    """Processeur pour importer les notes"""
    
    def __init__(self, df, classe_id, matiere_id, periode, annee_scolaire, type_import='MENSUELLE', 
                 evaluation_id=None, user=None):
        self.df = df
        self.classe_id = classe_id
        self.matiere_id = matiere_id
        self.periode = periode
        self.annee_scolaire = annee_scolaire
        self.type_import = type_import
        self.evaluation_id = evaluation_id
        self.user = user
        self.stats = {
            'total': 0,
            'importees': 0,
            'modifiees': 0,
            'erreurs': 0,
            'absents': 0
        }
    
    def importer(self):
        """Importe les notes depuis le DataFrame"""
        try:
            matiere = MatiereNote.objects.get(id=self.matiere_id)
        except MatiereNote.DoesNotExist:
            raise ImportNotesError("Matière introuvable")
        
        if self.type_import == 'MENSUELLE':
            return self._importer_notes_mensuelles(matiere)
        elif self.type_import == 'COMPOSITION':
            return self._importer_notes_composition(matiere)
        elif self.type_import == 'EVALUATION':
            return self._importer_notes_evaluation(matiere)
        
        raise ImportNotesError(f"Type d'import non supporté: {self.type_import}")
    
    def _importer_notes_mensuelles(self, matiere):
        """Importe des notes mensuelles - VERSION OPTIMISÉE"""
        # ⚡ OPTIMISATION: Charger tous les élèves en mémoire (1 seule requête)
        eleves_dict = {e.matricule: e for e in Eleve.objects.all()}
        
        # ⚡ OPTIMISATION: Charger les notes existantes (1 seule requête)
        notes_existantes = {}
        for note in NoteMensuelle.objects.filter(
            matiere=matiere,
            mois=self.periode,
            annee_scolaire=self.annee_scolaire
        ).select_related('eleve'):
            notes_existantes[note.eleve.matricule] = note
        
        notes_a_creer = []
        notes_a_modifier = []
        
        with transaction.atomic():
            for index, row in self.df.iterrows():
                self.stats['total'] += 1
                
                try:
                    matricule = str(row['Matricule']).strip()
                    eleve = eleves_dict.get(matricule)
                    
                    if not eleve:
                        self.stats['erreurs'] += 1
                        print(f"Erreur ligne {index + 2}: Élève {matricule} introuvable")
                        continue
                    
                    absent = str(row.get('Absent', 'NON')).strip().upper() in ['OUI', 'O', 'YES', 'Y', '1', 'TRUE']
                    note_value = None if absent else row.get('Note')
                    
                    note_decimal = Decimal(str(note_value)) if note_value is not None and not pd.isna(note_value) else Decimal('0')
                    
                    # Vérifier si la note existe déjà
                    if matricule in notes_existantes:
                        # Modifier
                        note = notes_existantes[matricule]
                        note.note = note_decimal
                        note.absent = absent
                        note.cree_par = self.user
                        notes_a_modifier.append(note)
                        self.stats['modifiees'] += 1
                    else:
                        # Créer
                        notes_a_creer.append(NoteMensuelle(
                            eleve=eleve,
                            matiere=matiere,
                            mois=self.periode,
                            annee_scolaire=self.annee_scolaire,
                            note=note_decimal,
                            absent=absent,
                            cree_par=self.user
                        ))
                        self.stats['importees'] += 1
                    
                    if absent:
                        self.stats['absents'] += 1
                
                except Exception as e:
                    self.stats['erreurs'] += 1
                    print(f"Erreur ligne {index + 2}: {e}")
            
            # ⚡ BULK OPERATIONS (1 seule requête pour toutes les créations)
            if notes_a_creer:
                NoteMensuelle.objects.bulk_create(notes_a_creer, batch_size=500)
            
            # ⚡ BULK UPDATE (1 seule requête pour toutes les modifications)
            if notes_a_modifier:
                NoteMensuelle.objects.bulk_update(
                    notes_a_modifier, 
                    ['note', 'absent', 'cree_par'],
                    batch_size=500
                )
        
        return self.stats
    
    def _importer_notes_composition(self, matiere):
        """Importe des notes de composition - VERSION OPTIMISÉE"""
        # ⚡ OPTIMISATION: Charger tous les élèves en mémoire (1 seule requête)
        eleves_dict = {e.matricule: e for e in Eleve.objects.all()}
        
        # ⚡ OPTIMISATION: Charger les notes existantes (1 seule requête)
        notes_existantes = {}
        for note in CompositionNote.objects.filter(
            matiere=matiere,
            periode=self.periode,
            annee_scolaire=self.annee_scolaire
        ).select_related('eleve'):
            notes_existantes[note.eleve.matricule] = note
        
        notes_a_creer = []
        notes_a_modifier = []
        
        with transaction.atomic():
            for index, row in self.df.iterrows():
                self.stats['total'] += 1
                
                try:
                    matricule = str(row['Matricule']).strip()
                    eleve = eleves_dict.get(matricule)
                    
                    if not eleve:
                        self.stats['erreurs'] += 1
                        print(f"Erreur ligne {index + 2}: Élève {matricule} introuvable")
                        continue
                    
                    absent = str(row.get('Absent', 'NON')).strip().upper() in ['OUI', 'O', 'YES', 'Y', '1', 'TRUE']
                    note_value = None if absent else row.get('Note')
                    
                    note_decimal = Decimal(str(note_value)) if note_value is not None and not pd.isna(note_value) else Decimal('0')
                    
                    # Vérifier si la note existe déjà
                    if matricule in notes_existantes:
                        # Modifier
                        note = notes_existantes[matricule]
                        note.note = note_decimal
                        note.absent = absent
                        note.cree_par = self.user
                        notes_a_modifier.append(note)
                        self.stats['modifiees'] += 1
                    else:
                        # Créer
                        notes_a_creer.append(CompositionNote(
                            eleve=eleve,
                            matiere=matiere,
                            periode=self.periode,
                            annee_scolaire=self.annee_scolaire,
                            note=note_decimal,
                            absent=absent,
                            cree_par=self.user
                        ))
                        self.stats['importees'] += 1
                    
                    if absent:
                        self.stats['absents'] += 1
                
                except Exception as e:
                    self.stats['erreurs'] += 1
                    print(f"Erreur ligne {index + 2}: {e}")
            
            # ⚡ BULK OPERATIONS (1 seule requête pour toutes les créations)
            if notes_a_creer:
                CompositionNote.objects.bulk_create(notes_a_creer, batch_size=500)
            
            # ⚡ BULK UPDATE (1 seule requête pour toutes les modifications)
            if notes_a_modifier:
                CompositionNote.objects.bulk_update(
                    notes_a_modifier, 
                    ['note', 'absent', 'cree_par'],
                    batch_size=500
                )
        
        return self.stats
    
    def _importer_notes_evaluation(self, matiere):
        """Importe des notes d'évaluation - VERSION OPTIMISÉE"""
        try:
            evaluation = Evaluation.objects.get(id=self.evaluation_id)
        except Evaluation.DoesNotExist:
            raise ImportNotesError("Évaluation introuvable")
        
        # ⚡ OPTIMISATION: Charger tous les élèves en mémoire (1 seule requête)
        eleves_dict = {e.matricule: e for e in Eleve.objects.all()}
        
        # ⚡ OPTIMISATION: Charger les notes existantes (1 seule requête)
        notes_existantes = {}
        for note in NoteEleve.objects.filter(
            evaluation=evaluation
        ).select_related('eleve'):
            notes_existantes[note.eleve.matricule] = note
        
        notes_a_creer = []
        notes_a_modifier = []
        
        with transaction.atomic():
            for index, row in self.df.iterrows():
                self.stats['total'] += 1
                
                try:
                    matricule = str(row['Matricule']).strip()
                    eleve = eleves_dict.get(matricule)
                    
                    if not eleve:
                        self.stats['erreurs'] += 1
                        print(f"Erreur ligne {index + 2}: Élève {matricule} introuvable")
                        continue
                    
                    absent = str(row.get('Absent', 'NON')).strip().upper() in ['OUI', 'O', 'YES', 'Y', '1', 'TRUE']
                    note_value = None if absent else row.get('Note')
                    
                    note_decimal = Decimal(str(note_value)) if note_value is not None and not pd.isna(note_value) else None
                    
                    # Vérifier si la note existe déjà
                    if matricule in notes_existantes:
                        # Modifier
                        note = notes_existantes[matricule]
                        note.note = note_decimal
                        note.absent = absent
                        note.cree_par = self.user
                        notes_a_modifier.append(note)
                        self.stats['modifiees'] += 1
                    else:
                        # Créer
                        notes_a_creer.append(NoteEleve(
                            evaluation=evaluation,
                            eleve=eleve,
                            note=note_decimal,
                            absent=absent,
                            cree_par=self.user
                        ))
                        self.stats['importees'] += 1
                    
                    if absent:
                        self.stats['absents'] += 1
                
                except Exception as e:
                    self.stats['erreurs'] += 1
                    print(f"Erreur ligne {index + 2}: {e}")
            
            # ⚡ BULK OPERATIONS (1 seule requête pour toutes les créations)
            if notes_a_creer:
                NoteEleve.objects.bulk_create(notes_a_creer, batch_size=500)
            
            # ⚡ BULK UPDATE (1 seule requête pour toutes les modifications)
            if notes_a_modifier:
                NoteEleve.objects.bulk_update(
                    notes_a_modifier, 
                    ['note', 'absent', 'cree_par'],
                    batch_size=500
                )
        
        return self.stats


def lire_fichier_import(file_path_or_obj):
    """Lit un fichier Excel ou CSV et retourne un DataFrame"""
    try:
        # Essayer Excel
        if hasattr(file_path_or_obj, 'name') and file_path_or_obj.name.endswith('.csv'):
            df = pd.read_csv(file_path_or_obj)
        else:
            df = pd.read_excel(file_path_or_obj)
        
        # Nettoyer les noms de colonnes
        df.columns = df.columns.str.strip()
        
        return df
    except Exception as e:
        raise ImportNotesError(f"Erreur lors de la lecture du fichier: {e}")


def generer_template_excel(classe_id, matiere_id, type_import='MENSUELLE'):
    """Génère un fichier template Excel pour l'importation"""
    try:
        classe = ClasseNote.objects.get(id=classe_id)
        matiere = MatiereNote.objects.get(id=matiere_id)
        
        # Récupérer les élèves de la classe
        from eleves.models import Classe as ClasseEleve
        
        # Trouver la classe d'élèves correspondante
        # Essayer plusieurs méthodes de correspondance
        classe_eleve = None
        
        # Méthode 1: Correspondance exacte avec année scolaire
        classe_eleve = ClasseEleve.objects.filter(
            nom__iexact=classe.nom,
            annee_scolaire=classe.annee_scolaire
        ).first()
        
        # Méthode 2: Correspondance exacte sans année scolaire
        if not classe_eleve:
            classe_eleve = ClasseEleve.objects.filter(
                nom__iexact=classe.nom
            ).first()
        
        # Méthode 3: Correspondance avec normalisation (ignorer casse et accents)
        if not classe_eleve:
            # Normaliser le nom: enlever accents, mettre en minuscules
            nom_normalise = classe.nom.lower().replace('è', 'e').replace('é', 'e').replace('ê', 'e')
            toutes_classes = ClasseEleve.objects.all()
            for c in toutes_classes:
                nom_c_normalise = c.nom.lower().replace('è', 'e').replace('é', 'e').replace('ê', 'e')
                if nom_normalise == nom_c_normalise:
                    classe_eleve = c
                    break
        
        # Méthode 3b: Correspondance partielle (contient premier mot)
        if not classe_eleve:
            premier_mot = classe.nom.split()[0] if classe.nom.split() else classe.nom
            classe_eleve = ClasseEleve.objects.filter(
                nom__icontains=premier_mot
            ).first()
        
        # Méthode 4: Chercher par nom simplifié (sans ÈME/ème/ANNÉE)
        if not classe_eleve:
            nom_simple = classe.nom.replace('ÈME', '').replace('ème', '').replace('ANNÉE', '').replace('Année', '').strip()
            if nom_simple:
                classe_eleve = ClasseEleve.objects.filter(
                    nom__icontains=nom_simple
                ).first()
        
        # Méthode 5: Chercher dans toutes les classes (dernière chance)
        if not classe_eleve:
            # Récupérer toutes les classes et chercher la meilleure correspondance
            toutes_classes = ClasseEleve.objects.all()
            for c in toutes_classes:
                if classe.nom.lower() in c.nom.lower() or c.nom.lower() in classe.nom.lower():
                    classe_eleve = c
                    break
        
        if not classe_eleve:
            # Si pas de correspondance, créer un template avec message d'erreur
            data = {
                'Matricule': [f'ERREUR: Aucun élève trouvé pour la classe "{classe.nom}"'],
                'Prénom': ['Vérifiez que les élèves sont bien affectés à cette classe'],
                'Nom': ['Ou contactez l\'administrateur'],
                'Note': [''],
                'Absent': ['NON']
            }
        else:
            # Récupérer les élèves
            eleves = Eleve.objects.filter(classe=classe_eleve, statut='ACTIF').order_by('nom', 'prenom')
            
            data = {
                'Matricule': [e.matricule for e in eleves],
                'Prénom': [e.prenom for e in eleves],
                'Nom': [e.nom for e in eleves],
                'Note': ['' for _ in eleves],
                'Absent': ['NON' for _ in eleves]
            }
        
        df = pd.DataFrame(data)
        
        return df
    
    except Exception as e:
        raise ImportNotesError(f"Erreur lors de la génération du template: {e}")
