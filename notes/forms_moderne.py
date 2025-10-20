"""
Formulaires modernes pour le module de gestion des notes
Interface simplifiée et intuitive
"""

from django import forms
from django.core.exceptions import ValidationError
from .models import MatiereClasse, Evaluation, Note, BaremeAppreciation
from eleves.models import Classe, Eleve


class SaisieNotesForm(forms.Form):
    """
    Formulaire moderne pour la saisie rapide des notes
    """
    donnees = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'form-control textarea-modern',
            'rows': 12,
            'placeholder': 'Saisissez les notes au format:\nMATRICULE;NOTE\n\nExemples:\nPN3-042;14.5\nL11SL-007;16\nCN8-123;12.25\n\nUn élève par ligne...',
            'style': 'font-family: monospace; font-size: 14px;'
        }),
        label='Données des notes',
        help_text='Format: MATRICULE;NOTE (un élève par ligne)',
        required=False
    )
    
    def clean_donnees(self):
        """
        Validation des données saisies
        """
        donnees = self.cleaned_data.get('donnees', '').strip()
        
        if not donnees:
            return donnees
        
        lignes = [ligne.strip() for ligne in donnees.split('\n') if ligne.strip()]
        erreurs = []
        
        for i, ligne in enumerate(lignes, 1):
            if ';' not in ligne:
                erreurs.append(f"Ligne {i}: Format invalide (manque le ';')")
                continue
            
            try:
                matricule, note_str = ligne.split(';', 1)
                matricule = matricule.strip()
                note_str = note_str.strip()
                
                if not matricule:
                    erreurs.append(f"Ligne {i}: Matricule manquant")
                
                if not note_str:
                    erreurs.append(f"Ligne {i}: Note manquante")
                    continue
                
                # Validation de la note
                try:
                    note_value = float(note_str.replace(',', '.'))
                    if not (0 <= note_value <= 20):
                        erreurs.append(f"Ligne {i}: Note hors limites (0-20)")
                except ValueError:
                    erreurs.append(f"Ligne {i}: Note invalide '{note_str}'")
                    
            except Exception:
                erreurs.append(f"Ligne {i}: Erreur de format")
        
        if erreurs:
            raise ValidationError(
                f"Erreurs détectées:\n" + "\n".join(erreurs[:10]) + 
                (f"\n... et {len(erreurs)-10} autres erreurs" if len(erreurs) > 10 else "")
            )
        
        return donnees


class EvaluationModerneForm(forms.ModelForm):
    """
    Formulaire moderne pour créer une évaluation
    """
    class Meta:
        model = Evaluation
        fields = ['titre', 'matiere', 'date', 'categorie', 'coefficient', 'trimestre']
        widgets = {
            'titre': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ex: Devoir de mathématiques n°1'
            }),
            'matiere': forms.Select(attrs={
                'class': 'form-select'
            }),
            'date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'categorie': forms.Select(attrs={
                'class': 'form-select'
            }),
            'coefficient': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 1,
                'max': 20,
                'value': 1
            }),
            'trimestre': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ex: T1, T2, T3'
            })
        }
    
    def __init__(self, *args, **kwargs):
        classe = kwargs.pop('classe', None)
        super().__init__(*args, **kwargs)
        
        if classe:
            self.fields['matiere'].queryset = MatiereClasse.objects.filter(
                classe=classe,
                actif=True
            ).order_by('nom')


class MatiereClasseModerneForm(forms.ModelForm):
    """
    Formulaire moderne pour ajouter une matière à une classe
    """
    class Meta:
        model = MatiereClasse
        fields = ['nom', 'coefficient']
        widgets = {
            'nom': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ex: Mathématiques, Français, Histoire...'
            }),
            'coefficient': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 1,
                'max': 20,
                'value': 1
            })
        }
    
    def clean_nom(self):
        """
        Validation du nom de matière
        """
        nom = self.cleaned_data.get('nom', '').strip()
        
        if not nom:
            raise ValidationError("Le nom de la matière est obligatoire")
        
        if len(nom) < 2:
            raise ValidationError("Le nom doit contenir au moins 2 caractères")
        
        return nom.title()  # Première lettre en majuscule


class FiltreClassementForm(forms.Form):
    """
    Formulaire pour filtrer les classements
    """
    TRIMESTRE_CHOICES = [
        ('T1', '1er Trimestre'),
        ('T2', '2ème Trimestre'), 
        ('T3', '3ème Trimestre'),
        ('ANNUEL', 'Moyenne Annuelle'),
    ]
    
    trimestre = forms.ChoiceField(
        choices=TRIMESTRE_CHOICES,
        initial='T1',
        widget=forms.Select(attrs={
            'class': 'form-select',
            'onchange': 'this.form.submit()'
        })
    )
    
    affichage = forms.ChoiceField(
        choices=[
            ('complet', 'Affichage complet'),
            ('resume', 'Résumé seulement'),
            ('top10', 'Top 10 seulement'),
        ],
        initial='complet',
        widget=forms.Select(attrs={
            'class': 'form-select'
        }),
        required=False
    )


class RechercheEleveForm(forms.Form):
    """
    Formulaire de recherche d'élève pour les notes
    """
    recherche = forms.CharField(
        max_length=100,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Nom, prénom ou matricule...',
            'autocomplete': 'off'
        }),
        required=False
    )
    
    classe = forms.ModelChoiceField(
        queryset=Classe.objects.none(),
        empty_label="Toutes les classes",
        widget=forms.Select(attrs={
            'class': 'form-select'
        }),
        required=False
    )
    
    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        if user:
            from utilisateurs.utils import filter_by_user_school
            self.fields['classe'].queryset = filter_by_user_school(
                Classe.objects.all(), user, 'ecole'
            ).order_by('niveau', 'nom')


class ConfigurationBaremeForm(forms.ModelForm):
    """
    Formulaire pour configurer les barèmes d'appréciation
    """
    class Meta:
        model = BaremeAppreciation
        fields = ['nom', 'description', 'actif']
        widgets = {
            'nom': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ex: Barème standard'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Description du barème...'
            }),
            'actif': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            })
        }
