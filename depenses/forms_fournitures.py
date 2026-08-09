from decimal import Decimal

from django import forms
from django.core.exceptions import ValidationError

from utilisateurs.utils import filter_by_user_school

from .models_fournitures import FournitureScolaire, VenteFourniture


class FournitureScolaireForm(forms.ModelForm):
    class Meta:
        model = FournitureScolaire
        fields = [
            'reference', 'nom', 'categorie', 'unite', 'quantite_stock',
            'stock_minimum', 'prix_achat_unitaire', 'prix_vente_unitaire',
            'description', 'actif',
        ]
        widgets = {
            'reference': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Générée automatiquement si vide',
            }),
            'nom': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ex. Cahier 200 pages',
            }),
            'categorie': forms.Select(attrs={'class': 'form-select'}),
            'unite': forms.Select(attrs={'class': 'form-select'}),
            'quantite_stock': forms.NumberInput(attrs={
                'class': 'form-control', 'min': 0, 'step': 1,
            }),
            'stock_minimum': forms.NumberInput(attrs={
                'class': 'form-control', 'min': 0, 'step': 1,
            }),
            'prix_achat_unitaire': forms.NumberInput(attrs={
                'class': 'form-control', 'min': 0, 'step': 1,
            }),
            'prix_vente_unitaire': forms.NumberInput(attrs={
                'class': 'form-control', 'min': 0, 'step': 1,
            }),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'actif': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def __init__(self, *args, ecole=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.ecole = ecole or getattr(self.instance, 'ecole', None)
        self.fields['reference'].required = False

    def clean_reference(self):
        reference = (self.cleaned_data.get('reference') or '').strip().upper()
        if reference and self.ecole:
            qs = FournitureScolaire.objects.filter(
                ecole=self.ecole,
                reference=reference,
            )
            if self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise ValidationError('Cette référence existe déjà dans cet établissement.')
        return reference

    def clean_quantite_stock(self):
        quantite = self.cleaned_data.get('quantite_stock') or 0
        if self.instance.pk:
            vendue = self.instance.quantite_vendue
            if quantite < vendue:
                raise ValidationError(
                    f'La quantité ne peut pas être inférieure aux {vendue} unités déjà vendues.'
                )
        return quantite


class VenteFournitureForm(forms.ModelForm):
    class Meta:
        model = VenteFourniture
        fields = [
            'produit', 'quantite', 'prix_vente_unitaire',
            'client', 'date_vente', 'observations',
        ]
        widgets = {
            'produit': forms.Select(attrs={'class': 'form-select'}),
            'quantite': forms.NumberInput(attrs={
                'class': 'form-control', 'min': 1, 'step': 1,
            }),
            'prix_vente_unitaire': forms.NumberInput(attrs={
                'class': 'form-control', 'min': 1, 'step': 1,
                'placeholder': 'Prix configuré sur le produit',
            }),
            'client': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Nom du client (facultatif)',
            }),
            'date_vente': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'observations': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        produits = FournitureScolaire.objects.select_related('ecole').filter(actif=True)
        if user is not None:
            produits = filter_by_user_school(produits, user, 'ecole')
        else:
            produits = produits.none()
        self.fields['produit'].queryset = produits.order_by('nom')
        self.fields['produit'].label_from_instance = lambda produit: (
            f'{produit.reference} — {produit.nom} '
            f'({produit.quantite_restante} disponible(s))'
        )
        self.fields['prix_vente_unitaire'].required = False

    def clean(self):
        cleaned_data = super().clean()
        produit = cleaned_data.get('produit')
        quantite = cleaned_data.get('quantite')
        prix = cleaned_data.get('prix_vente_unitaire')

        if produit and not prix:
            prix = produit.prix_vente_unitaire
            cleaned_data['prix_vente_unitaire'] = prix
        if prix is not None and Decimal(prix) <= 0:
            self.add_error(
                'prix_vente_unitaire',
                'Le prix de vente doit être supérieur à zéro.',
            )
        if produit and quantite and quantite > produit.quantite_restante:
            self.add_error(
                'quantite',
                f'Stock restant insuffisant : {produit.quantite_restante} disponible(s).',
            )
        return cleaned_data
