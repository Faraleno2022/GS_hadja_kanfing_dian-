"""Formulaires des modules de recouvrement."""

from django import forms
from django.core.exceptions import ValidationError
from django.utils import timezone

from .models_recouvrement import (
    AbonnementInformatique, DepenseCuisine, DepenseDocument, Versement,
)


class _LigneRecouvrementForm(forms.ModelForm):
    """Base commune: la date est proposée automatiquement mais reste corrigeable."""

    class Meta:
        fields = ['date', 'montant', 'observation']
        widgets = {
            'date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'montant': forms.NumberInput(attrs={
                'class': 'form-control', 'min': 0, 'step': 1, 'placeholder': '0',
            }),
            'observation': forms.Textarea(attrs={
                'class': 'form-control', 'rows': 3,
                'placeholder': 'Précisions éventuelles (facultatif)',
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not self.instance.pk and not self.initial.get('date'):
            self.initial['date'] = timezone.localdate()

    def clean_montant(self):
        montant = self.cleaned_data.get('montant')
        if montant is None or montant <= 0:
            raise ValidationError('Le montant doit être supérieur à zéro.')
        return montant

    def clean_date(self):
        date = self.cleaned_data.get('date') or timezone.localdate()
        if date > timezone.localdate():
            raise ValidationError("La date ne peut pas être dans le futur.")
        return date


class DepenseCuisineForm(_LigneRecouvrementForm):
    class Meta(_LigneRecouvrementForm.Meta):
        model = DepenseCuisine
        fields = ['date', 'designation', 'montant', 'observation']
        widgets = dict(_LigneRecouvrementForm.Meta.widgets, designation=forms.TextInput(attrs={
            'class': 'form-control', 'placeholder': 'Ex. Achat de riz, gaz, condiments',
        }))


class DepenseDocumentForm(_LigneRecouvrementForm):
    class Meta(_LigneRecouvrementForm.Meta):
        model = DepenseDocument
        fields = ['date', 'designation', 'montant', 'observation']
        widgets = dict(_LigneRecouvrementForm.Meta.widgets, designation=forms.TextInput(attrs={
            'class': 'form-control', 'placeholder': 'Ex. Impression bulletins, certificats',
        }))


class VersementForm(_LigneRecouvrementForm):
    class Meta(_LigneRecouvrementForm.Meta):
        model = Versement
        fields = ['date', 'montant', 'lieu_versement', 'observation']
        widgets = dict(_LigneRecouvrementForm.Meta.widgets, lieu_versement=forms.TextInput(attrs={
            'class': 'form-control', 'placeholder': 'Ex. Ecobank agence Matam, Direction',
        }))


class AbonnementInformatiqueForm(forms.ModelForm):
    """Abonnement à la salle informatique, rattaché à un élève."""

    class Meta:
        model = AbonnementInformatique
        fields = [
            'eleve', 'date', 'montant', 'date_debut', 'date_fin',
            'alerte_avant_jours', 'statut', 'observation',
        ]
        widgets = {
            'eleve': forms.Select(attrs={'class': 'form-select', 'id': 'id_eleve'}),
            'date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'montant': forms.NumberInput(attrs={
                'class': 'form-control', 'min': 0, 'step': 1, 'placeholder': '0',
            }),
            'date_debut': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'date_fin': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'alerte_avant_jours': forms.NumberInput(attrs={
                'class': 'form-control', 'min': 0, 'step': 1,
            }),
            'statut': forms.Select(attrs={'class': 'form-select'}),
            'observation': forms.Textarea(attrs={
                'class': 'form-control', 'rows': 3,
                'placeholder': 'Précisions éventuelles (facultatif)',
            }),
        }

    def __init__(self, *args, eleves=None, **kwargs):
        super().__init__(*args, **kwargs)
        if eleves is not None:
            self.fields['eleve'].queryset = eleves
        self.fields['eleve'].label_from_instance = (
            lambda eleve: f"{eleve.matricule} — {eleve.prenom} {eleve.nom}"
            + (f" ({eleve.classe.nom})" if eleve.classe_id else '')
        )
        if not self.instance.pk:
            aujourdhui = timezone.localdate()
            self.initial.setdefault('date', aujourdhui)
            self.initial.setdefault('date_debut', aujourdhui)

    def clean_montant(self):
        montant = self.cleaned_data.get('montant')
        if montant is None or montant <= 0:
            raise ValidationError('Le montant doit être supérieur à zéro.')
        return montant

    def clean(self):
        cleaned = super().clean()
        debut = cleaned.get('date_debut')
        fin = cleaned.get('date_fin')
        if debut and fin and fin < debut:
            self.add_error('date_fin', "La fin doit être postérieure au début de l'abonnement.")
        return cleaned
