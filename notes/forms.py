from django import forms
from .models import ClasseNote, MatiereNote, Evaluation, NoteEleve, ThemeBulletin

class ClasseNoteForm(forms.ModelForm):
    """Formulaire pour créer/modifier une classe"""
    
    class Meta:
        model = ClasseNote
        fields = ['nom', 'niveau', 'annee_scolaire', 'effectif', 'description', 'actif']
        widgets = {
            'nom': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ex: 7ème A, CM2 B, etc.'
            }),
            'niveau': forms.Select(attrs={
                'class': 'form-select'
            }),
            'annee_scolaire': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '2024-2025'
            }),
            'effectif': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '0',
                'placeholder': 'Nombre d\'élèves'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Description optionnelle de la classe...'
            }),
            'actif': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
        }

class MatiereNoteForm(forms.ModelForm):
    """Formulaire pour créer/modifier une matière"""
    
    # Rendre le coefficient optionnel
    coefficient = forms.DecimalField(
        required=False,
        max_digits=4,
        decimal_places=2,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': '1.0 (optionnel pour Maternelle/Primaire)',
            'min': '0.5',
            'step': '0.5'
        })
    )
    
    class Meta:
        model = MatiereNote
        fields = ['nom', 'code', 'coefficient', 'description', 'actif']
        widgets = {
            'nom': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ex: Mathématiques, Français, etc.'
            }),
            'code': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ex: MATH, FR, ANG'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 2,
                'placeholder': 'Description optionnelle...'
            }),
            'actif': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
        }

class EvaluationForm(forms.ModelForm):
    """Formulaire pour créer/modifier une évaluation"""
    
    class Meta:
        model = Evaluation
        fields = ['titre', 'type_evaluation', 'periode', 'date_evaluation', 'note_sur', 'coefficient', 'description']
        widgets = {
            'titre': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ex: Devoir 1, Composition Trimestre 1'
            }),
            'type_evaluation': forms.Select(attrs={
                'class': 'form-select'
            }),
            'periode': forms.Select(attrs={
                'class': 'form-select'
            }),
            'date_evaluation': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'note_sur': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '1',
                'step': '0.5',
                'placeholder': '20'
            }),
            'coefficient': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '0.5',
                'step': '0.5',
                'placeholder': '1.0'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 2,
                'placeholder': 'Description optionnelle...'
            }),
        }

class NoteEleveForm(forms.ModelForm):
    """Formulaire pour saisir une note"""
    
    class Meta:
        model = NoteEleve
        fields = ['note', 'absent', 'commentaire']
        widgets = {
            'note': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '0',
                'step': '0.25'
            }),
            'absent': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'commentaire': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 2,
                'placeholder': 'Commentaire optionnel...'
            }),
        }


class ThemeBulletinForm(forms.ModelForm):
    """Formulaire pour personnaliser les couleurs du bulletin"""
    
    class Meta:
        model = ThemeBulletin
        fields = [
            'nom', 'couleur_primaire', 'couleur_secondaire', 'couleur_accent',
            'couleur_texte_principal', 'couleur_texte_secondaire',
            'couleur_fond_header', 'couleur_fond_tableau', 'couleur_fond_carte',
            'couleur_bordure', 'couleur_mention_tb', 'couleur_mention_bien',
            'couleur_mention_ab', 'couleur_mention_passable', 'couleur_mention_insuffisant',
            'actif', 'par_defaut'
        ]
        widgets = {
            'nom': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ex: Thème Bleu, Thème Vert, etc.'
            }),
            'couleur_primaire': forms.TextInput(attrs={
                'class': 'form-control',
                'type': 'color'
            }),
            'couleur_secondaire': forms.TextInput(attrs={
                'class': 'form-control',
                'type': 'color'
            }),
            'couleur_accent': forms.TextInput(attrs={
                'class': 'form-control',
                'type': 'color'
            }),
            'couleur_texte_principal': forms.TextInput(attrs={
                'class': 'form-control',
                'type': 'color'
            }),
            'couleur_texte_secondaire': forms.TextInput(attrs={
                'class': 'form-control',
                'type': 'color'
            }),
            'couleur_fond_header': forms.TextInput(attrs={
                'class': 'form-control',
                'type': 'color'
            }),
            'couleur_fond_tableau': forms.TextInput(attrs={
                'class': 'form-control',
                'type': 'color'
            }),
            'couleur_fond_carte': forms.TextInput(attrs={
                'class': 'form-control',
                'type': 'color'
            }),
            'couleur_bordure': forms.TextInput(attrs={
                'class': 'form-control',
                'type': 'color'
            }),
            'couleur_mention_tb': forms.TextInput(attrs={
                'class': 'form-control',
                'type': 'color'
            }),
            'couleur_mention_bien': forms.TextInput(attrs={
                'class': 'form-control',
                'type': 'color'
            }),
            'couleur_mention_ab': forms.TextInput(attrs={
                'class': 'form-control',
                'type': 'color'
            }),
            'couleur_mention_passable': forms.TextInput(attrs={
                'class': 'form-control',
                'type': 'color'
            }),
            'couleur_mention_insuffisant': forms.TextInput(attrs={
                'class': 'form-control',
                'type': 'color'
            }),
            'actif': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'par_defaut': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
        }
