"""
Commande pour ajouter des données de démonstration au module notes
Matières, évaluations et notes pour tester les nouvelles interfaces
"""

from django.core.management.base import BaseCommand
from django.db import transaction
from decimal import Decimal
import random
from datetime import date, timedelta

from notes.models import MatiereClasse, Evaluation, Note, BaremeAppreciation, SeuilAppreciation
from eleves.models import Classe, Eleve
from utilisateurs.models import Ecole
from django.contrib.auth.models import User


class Command(BaseCommand):
    help = 'Ajoute des données de démonstration pour le module notes'

    def add_arguments(self, parser):
        parser.add_argument(
            '--reset',
            action='store_true',
            help='Supprime les données existantes avant d\'ajouter les nouvelles',
        )

    def handle(self, *args, **options):
        if options['reset']:
            self.stdout.write('🗑️  Suppression des données existantes...')
            Note.objects.all().delete()
            Evaluation.objects.all().delete()
            MatiereClasse.objects.all().delete()

        self.stdout.write('📚 Ajout des données de démonstration...')
        
        with transaction.atomic():
            # 1. Création des barèmes d'appréciation
            self.creer_baremes()
            
            # 2. Ajout des matières par classe
            self.ajouter_matieres()
            
            # 3. Création des évaluations
            self.creer_evaluations()
            
            # 4. Génération des notes
            self.generer_notes()

        self.stdout.write(
            self.style.SUCCESS('✅ Données de démonstration ajoutées avec succès!')
        )
        
        # Statistiques finales
        self.afficher_statistiques()

    def creer_baremes(self):
        """Crée les barèmes d'appréciation s'ils n'existent pas"""
        self.stdout.write('📊 Création des barèmes d\'appréciation...')
        
        # Barème standard
        bareme, created = BaremeAppreciation.objects.get_or_create(
            nom="Barème Standard",
            defaults={
                'description': 'Barème d\'appréciation standard pour toutes les matières',
                'actif': True
            }
        )
        
        if created:
            # Seuils d'appréciation
            seuils = [
                (18, 20, "Excellent", "Travail remarquable"),
                (16, 18, "Très bien", "Très bon travail"),
                (14, 16, "Bien", "Bon travail"),
                (12, 14, "Assez bien", "Travail satisfaisant"),
                (10, 12, "Passable", "Travail acceptable"),
                (8, 10, "Insuffisant", "Travail insuffisant"),
                (0, 8, "Très insuffisant", "Travail très insuffisant")
            ]
            
            for note_min, note_max, appreciation, commentaire in seuils:
                SeuilAppreciation.objects.create(
                    bareme=bareme,
                    note_min=Decimal(str(note_min)),
                    note_max=Decimal(str(note_max)),
                    appreciation=appreciation,
                    commentaire=commentaire
                )

    def ajouter_matieres(self):
        """Ajoute les matières aux classes existantes"""
        self.stdout.write('📖 Ajout des matières aux classes...')
        
        # Matières par niveau
        matieres_primaire = [
            ("Français", 4),
            ("Mathématiques", 4),
            ("Éveil Scientifique", 2),
            ("Histoire-Géographie", 2),
            ("Éducation Civique", 1),
            ("Éducation Physique", 1),
            ("Dessin", 1),
            ("Anglais", 2)
        ]
        
        matieres_college = [
            ("Français", 4),
            ("Mathématiques", 4),
            ("Anglais", 3),
            ("Sciences Physiques", 3),
            ("Sciences Naturelles", 3),
            ("Histoire-Géographie", 3),
            ("Éducation Civique", 2),
            ("Éducation Physique", 2),
            ("Arts Plastiques", 1),
            ("Musique", 1)
        ]
        
        matieres_lycee_litteraire = [
            ("Français", 5),
            ("Philosophie", 4),
            ("Histoire-Géographie", 4),
            ("Anglais", 3),
            ("Mathématiques", 2),
            ("Sciences Physiques", 2),
            ("Sciences Naturelles", 2),
            ("Éducation Physique", 1),
            ("Arts", 1)
        ]
        
        matieres_lycee_scientifique = [
            ("Mathématiques", 5),
            ("Sciences Physiques", 4),
            ("Sciences Naturelles", 4),
            ("Français", 3),
            ("Anglais", 3),
            ("Histoire-Géographie", 2),
            ("Philosophie", 2),
            ("Éducation Physique", 1),
            ("Arts", 1)
        ]
        
        # Application aux classes
        classes = Classe.objects.all()
        
        for classe in classes:
            self.stdout.write(f'   📝 Classe: {classe.nom}')
            
            # Détermination des matières selon le niveau
            if "PRIMAIRE" in classe.niveau:
                matieres = matieres_primaire
            elif "COLLEGE" in classe.niveau:
                matieres = matieres_college
            elif "Littéraire" in classe.nom or "SL" in classe.nom:
                matieres = matieres_lycee_litteraire
            else:  # Lycée scientifique
                matieres = matieres_lycee_scientifique
            
            # Création des matières
            for nom_matiere, coefficient in matieres:
                matiere, created = MatiereClasse.objects.get_or_create(
                    nom=nom_matiere,
                    classe=classe,
                    defaults={
                        'coefficient': coefficient,
                        'ecole': classe.ecole,
                        'actif': True
                    }
                )
                
                if created:
                    self.stdout.write(f'      ✅ {nom_matiere} (coeff. {coefficient})')

    def creer_evaluations(self):
        """Crée des évaluations pour chaque matière"""
        self.stdout.write('📝 Création des évaluations...')
        
        matieres = MatiereClasse.objects.filter(actif=True)
        
        # Types d'évaluations
        evaluations_types = [
            ("Devoir n°1", "COURS", 1),
            ("Devoir n°2", "COURS", 1),
            ("Composition 1er trimestre", "COMPOSITION", 2),
            ("Devoir n°3", "COURS", 1),
            ("Devoir n°4", "COURS", 1),
            ("Composition 2ème trimestre", "COMPOSITION", 2),
        ]
        
        for matiere in matieres:
            self.stdout.write(f'   📋 {matiere.nom} - {matiere.classe.nom}')
            
            for i, (titre, categorie, coeff) in enumerate(evaluations_types):
                # Date d'évaluation (étalée sur l'année)
                date_eval = date.today() - timedelta(days=180) + timedelta(days=i*30)
                
                # Trimestre selon la date
                if i < 2:
                    trimestre = "T1"
                elif i < 4:
                    trimestre = "T2"
                else:
                    trimestre = "T3"
                
                evaluation, created = Evaluation.objects.get_or_create(
                    titre=f"{titre} - {matiere.nom}",
                    classe=matiere.classe,
                    matiere=matiere,
                    defaults={
                        'ecole': matiere.ecole,
                        'date': date_eval,
                        'categorie': categorie,
                        'coefficient': coeff,
                        'trimestre': trimestre,
                        'bareme_sur': Decimal('20')
                    }
                )
                
                if created:
                    self.stdout.write(f'      ✅ {titre}')

    def generer_notes(self):
        """Génère des notes réalistes pour les évaluations"""
        self.stdout.write('🎯 Génération des notes...')
        
        evaluations = Evaluation.objects.all()
        
        for evaluation in evaluations:
            self.stdout.write(f'   📊 {evaluation.titre} - {evaluation.classe.nom}')
            
            # Élèves de la classe
            eleves = Eleve.objects.filter(classe=evaluation.classe, statut='ACTIF')
            
            for eleve in eleves:
                # Génération d'une note réaliste
                note_value = self.generer_note_realiste(evaluation.matiere.nom)
                
                note, created = Note.objects.get_or_create(
                    evaluation=evaluation,
                    eleve=eleve,
                    defaults={
                        'ecole': evaluation.ecole,
                        'classe': evaluation.classe,
                        'matiere': evaluation.matiere,
                        'matricule': eleve.matricule,
                        'note': Decimal(str(note_value)),
                        'saisie_par': User.objects.first()  # Premier utilisateur disponible
                    }
                )
                
                if created:
                    # Calcul automatique de l'appréciation
                    note.save()  # Déclenche le calcul automatique

    def generer_note_realiste(self, matiere):
        """Génère une note réaliste selon la matière"""
        # Moyennes différentes selon les matières
        moyennes_matieres = {
            'Mathématiques': 11.5,
            'Français': 12.0,
            'Anglais': 11.8,
            'Sciences Physiques': 11.2,
            'Sciences Naturelles': 12.5,
            'Histoire-Géographie': 12.8,
            'Philosophie': 11.0,
            'Éducation Physique': 14.0,
            'Arts Plastiques': 13.5,
            'Musique': 13.2,
        }
        
        moyenne = moyennes_matieres.get(matiere, 12.0)
        
        # Distribution normale avec écart-type de 3
        note = random.normalvariate(moyenne, 3.0)
        
        # Contraintes entre 0 et 20
        note = max(0, min(20, note))
        
        # Arrondi à 0.25 près (comme dans la vraie vie)
        note = round(note * 4) / 4
        
        return note

    def afficher_statistiques(self):
        """Affiche les statistiques des données créées"""
        self.stdout.write('\n📈 STATISTIQUES DES DONNÉES CRÉÉES:')
        self.stdout.write('=' * 40)
        
        nb_classes = Classe.objects.count()
        nb_matieres = MatiereClasse.objects.count()
        nb_evaluations = Evaluation.objects.count()
        nb_notes = Note.objects.count()
        
        self.stdout.write(f'📚 Classes: {nb_classes}')
        self.stdout.write(f'📖 Matières: {nb_matieres}')
        self.stdout.write(f'📝 Évaluations: {nb_evaluations}')
        self.stdout.write(f'🎯 Notes: {nb_notes}')
        
        # Moyennes par niveau
        self.stdout.write('\n📊 MOYENNES PAR NIVEAU:')
        
        if nb_notes > 0:
            # Calcul des moyennes
            from django.db.models import Avg
            
            moyenne_generale = Note.objects.aggregate(avg=Avg('note'))['avg']
            self.stdout.write(f'🎯 Moyenne générale: {moyenne_generale:.2f}/20')
            
            # Répartition des notes
            excellents = Note.objects.filter(note__gte=16).count()
            bons = Note.objects.filter(note__gte=14, note__lt=16).count()
            moyens = Note.objects.filter(note__gte=10, note__lt=14).count()
            faibles = Note.objects.filter(note__lt=10).count()
            
            self.stdout.write(f'🌟 Excellents (≥16): {excellents}')
            self.stdout.write(f'👍 Bons (14-16): {bons}')
            self.stdout.write(f'👌 Moyens (10-14): {moyens}')
            self.stdout.write(f'👎 Faibles (<10): {faibles}')
        
        self.stdout.write('\n🎉 DONNÉES PRÊTES POUR LES TESTS!')
        self.stdout.write('Vous pouvez maintenant tester les nouvelles interfaces:')
        self.stdout.write('• Dashboard: /notes/')
        self.stdout.write('• Saisie: /notes/evaluations/{id}/saisie-moderne/')
        self.stdout.write('• Classements: /notes/classes/{id}/classement-moderne/')
