"""
Module d'intégration du calculateur de notes avec Django
Permet d'utiliser le calculateur avec les modèles Django existants
"""

from .calculateur_notes_guineen import (
    CalculateurNotes, NiveauScolaire, SystemeEvaluation,
    EleveSecondaire, ElevePrimaire
)
from .models import ClasseNote, MatiereNote, Evaluation, NoteEleve
from eleves.models import Eleve
from typing import Dict, List
from decimal import Decimal


class CalculateurDjango:
    """Intégration du calculateur avec les modèles Django"""
    
    @staticmethod
    def detecter_niveau(classe: ClasseNote) -> NiveauScolaire:
        """Détecte le niveau scolaire à partir d'une classe"""
        niveau_mapping = {
            'MATERNELLE': NiveauScolaire.MATERNELLE,
            'PRIMAIRE': NiveauScolaire.PRIMAIRE,
            'COLLEGE': NiveauScolaire.COLLEGE,
            'LYCEE': NiveauScolaire.LYCEE,
        }
        return niveau_mapping.get(classe.niveau_enseignement, NiveauScolaire.PRIMAIRE)
    
    @staticmethod
    def detecter_systeme(periode: str) -> SystemeEvaluation:
        """Détecte le système d'évaluation à partir de la période"""
        if 'SEMESTRE' in periode:
            return SystemeEvaluation.SEMESTRE
        return SystemeEvaluation.TRIMESTRE
    
    @staticmethod
    def calculer_moyenne_periode_secondaire(eleve: Eleve, matiere: MatiereNote, 
                                            periode: str) -> Decimal:
        """
        Calcule la moyenne d'une période pour le secondaire
        Formule: 40% cours + 60% composition
        """
        # Récupérer les notes mensuelles
        notes_mensuelles = {}
        
        # Mapper les périodes aux mois correspondants
        mois_par_periode = {
            'TRIMESTRE_1': ['OCTOBRE', 'NOVEMBRE', 'DECEMBRE'],
            'TRIMESTRE_2': ['JANVIER', 'FEVRIER', 'MARS'],
            'TRIMESTRE_3': ['AVRIL', 'MAI', 'JUIN'],
            'SEMESTRE_1': ['OCTOBRE', 'NOVEMBRE', 'DECEMBRE', 'JANVIER'],
            'SEMESTRE_2': ['MARS', 'AVRIL', 'MAI', 'JUIN'],
        }
        
        mois_periode = mois_par_periode.get(periode, [])
        
        for mois in mois_periode:
            notes_mois = NoteEleve.objects.filter(
                eleve=eleve,
                evaluation__matiere=matiere,
                evaluation__periode=mois,
                evaluation__type_eval='DEVOIR'
            ).values_list('note', flat=True)
            
            if notes_mois:
                notes_mensuelles[mois.lower()] = [float(n) for n in notes_mois if n is not None]
        
        # Récupérer la composition
        composition = NoteEleve.objects.filter(
            eleve=eleve,
            evaluation__matiere=matiere,
            evaluation__periode=periode,
            evaluation__type_eval='COMPOSITION'
        ).first()
        
        composition_note = float(composition.note) if composition and composition.note else 0.0
        
        # Calculer avec le calculateur
        niveau = CalculateurDjango.detecter_niveau(matiere.classe)
        systeme = CalculateurDjango.detecter_systeme(periode)
        calculateur = CalculateurNotes(niveau, systeme)
        
        moyenne = calculateur.calculer_note_periode_secondaire(notes_mensuelles, composition_note)
        return Decimal(str(moyenne))
    
    @staticmethod
    def calculer_moyenne_annuelle_matiere(eleve: Eleve, matiere: MatiereNote) -> Dict:
        """
        Calcule la moyenne annuelle d'une matière
        Retourne: {'moyenne': Decimal, 'details_periodes': List}
        """
        niveau = CalculateurDjango.detecter_niveau(matiere.classe)
        
        if niveau == NiveauScolaire.PRIMAIRE:
            # Pour le primaire: moyenne des 3 compositions
            compositions = NoteEleve.objects.filter(
                eleve=eleve,
                evaluation__matiere=matiere,
                evaluation__type_eval='COMPOSITION'
            ).order_by('evaluation__periode').values_list('note', flat=True)
            
            if len(compositions) == 3:
                calculateur = CalculateurNotes(niveau, SystemeEvaluation.TRIMESTRE)
                compositions_float = [float(c) for c in compositions if c is not None]
                moyenne = calculateur.calculer_moyenne_annuelle_matiere_primaire(compositions_float)
                
                return {
                    'moyenne': Decimal(str(moyenne)),
                    'details_periodes': compositions_float
                }
        else:
            # Pour le secondaire: calculer chaque période puis moyenne annuelle
            periodes = ['TRIMESTRE_1', 'TRIMESTRE_2', 'TRIMESTRE_3']
            notes_periodes = []
            
            for periode in periodes:
                moyenne_periode = CalculateurDjango.calculer_moyenne_periode_secondaire(
                    eleve, matiere, periode
                )
                notes_periodes.append(float(moyenne_periode))
            
            if len(notes_periodes) == 3:
                calculateur = CalculateurNotes(niveau, SystemeEvaluation.TRIMESTRE)
                moyenne_annuelle = calculateur.calculer_moyenne_annuelle_matiere_secondaire(notes_periodes)
                
                return {
                    'moyenne': Decimal(str(moyenne_annuelle)),
                    'details_periodes': notes_periodes
                }
        
        return {'moyenne': Decimal('0'), 'details_periodes': []}
    
    @staticmethod
    def calculer_moyenne_generale_annuelle(eleve: Eleve, classe: ClasseNote) -> Dict:
        """
        Calcule la moyenne générale annuelle d'un élève
        Retourne le bulletin complet
        """
        matieres = MatiereNote.objects.filter(classe=classe)
        resultats_matieres = []
        
        for matiere in matieres:
            resultat = CalculateurDjango.calculer_moyenne_annuelle_matiere(eleve, matiere)
            
            if resultat['moyenne'] > 0:
                resultats_matieres.append({
                    'matiere': matiere.nom,
                    'moyenne': float(resultat['moyenne']),
                    'coefficient': float(matiere.coefficient),
                    'details_periodes': resultat['details_periodes']
                })
        
        # Calculer la moyenne générale
        niveau = CalculateurDjango.detecter_niveau(classe)
        calculateur = CalculateurNotes(niveau, SystemeEvaluation.TRIMESTRE)
        
        moyenne_generale = calculateur.calculer_moyenne_generale_annuelle(resultats_matieres)
        
        return {
            'eleve': f"{eleve.prenom} {eleve.nom}",
            'matricule': eleve.matricule,
            'classe': classe.nom,
            'annee_scolaire': classe.annee_scolaire,
            'matieres': resultats_matieres,
            'moyenne_generale': moyenne_generale,
            'total_coefficients': sum(r['coefficient'] for r in resultats_matieres)
        }
    
    @staticmethod
    def generer_bulletin_annuel_eleve(eleve_id: int, classe_id: int) -> Dict:
        """
        Génère un bulletin annuel complet pour un élève
        À utiliser dans les vues Django
        """
        try:
            eleve = Eleve.objects.get(id=eleve_id)
            classe = ClasseNote.objects.get(id=classe_id)
            
            bulletin = CalculateurDjango.calculer_moyenne_generale_annuelle(eleve, classe)
            
            # Ajouter le rang si possible
            # TODO: Implémenter le calcul du rang
            bulletin['rang'] = None
            bulletin['total_eleves'] = Eleve.objects.filter(classe=classe).count()
            
            return {
                'success': True,
                'bulletin': bulletin
            }
        
        except (Eleve.DoesNotExist, ClasseNote.DoesNotExist) as e:
            return {
                'success': False,
                'error': str(e)
            }


# Fonctions utilitaires pour les vues

def obtenir_moyenne_periode(eleve_id: int, matiere_id: int, periode: str) -> Decimal:
    """Obtient la moyenne d'une période pour un élève dans une matière"""
    try:
        eleve = Eleve.objects.get(id=eleve_id)
        matiere = MatiereNote.objects.get(id=matiere_id)
        
        return CalculateurDjango.calculer_moyenne_periode_secondaire(eleve, matiere, periode)
    except (Eleve.DoesNotExist, MatiereNote.DoesNotExist):
        return Decimal('0')


def obtenir_moyenne_annuelle(eleve_id: int, matiere_id: int) -> Decimal:
    """Obtient la moyenne annuelle d'un élève dans une matière"""
    try:
        eleve = Eleve.objects.get(id=eleve_id)
        matiere = MatiereNote.objects.get(id=matiere_id)
        
        resultat = CalculateurDjango.calculer_moyenne_annuelle_matiere(eleve, matiere)
        return resultat['moyenne']
    except (Eleve.DoesNotExist, MatiereNote.DoesNotExist):
        return Decimal('0')


def obtenir_bulletin_complet(eleve_id: int, classe_id: int) -> Dict:
    """Obtient le bulletin annuel complet d'un élève"""
    return CalculateurDjango.generer_bulletin_annuel_eleve(eleve_id, classe_id)


# Exemple d'utilisation dans une vue Django
"""
from notes.integration_calculateur import obtenir_bulletin_complet

def vue_bulletin_annuel(request, eleve_id):
    classe_id = request.GET.get('classe_id')
    
    resultat = obtenir_bulletin_complet(eleve_id, classe_id)
    
    if resultat['success']:
        return render(request, 'notes/bulletin_annuel.html', {
            'bulletin': resultat['bulletin']
        })
    else:
        messages.error(request, resultat['error'])
        return redirect('notes:liste_eleves')
"""
