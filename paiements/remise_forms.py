from django import forms
from decimal import Decimal
from .models import RemiseReduction, PaiementRemise
from .remise_utils import (
    BASE_CALCUL_CHOICES,
    BASE_TRANCHE,
    TRANCHE_CHOICES,
    calculer_base_remise,
    normaliser_tranches,
)


class PaiementRemiseForm(forms.Form):
    """Formulaire pour appliquer des remises à un paiement"""

    # Motifs qui déterminent eux-mêmes le pourcentage accordé
    POURCENTAGE_PAR_MOTIF = {
        'NE_PAIE_RIEN': 100,
        'LA_MOITIE': 50,
    }

    remises = forms.ModelMultipleChoiceField(
        queryset=RemiseReduction.objects.filter(actif=True),
        widget=forms.CheckboxSelectMultiple(attrs={
            'class': 'form-check-input'
        }),
        required=False,
        label="Remises disponibles"
    )

    montant_original = forms.DecimalField(
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'readonly': True
        }),
        label="Montant original"
    )

    # Nouveau: pourcentage scolarité sélectionnable par l'utilisateur (1 à 10%)
    POURCENT_CHOICES = [("", "— Choisir —")] + [(str(i), f"{i}%") for i in range(1, 101)]
    pourcentage_scolarite = forms.ChoiceField(
        choices=POURCENT_CHOICES,
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'}),
        label="Remise scolarité (%)"
    )

    # Portée de la remise: une ou plusieurs tranches, jamais l'inscription
    tranches = forms.MultipleChoiceField(
        choices=TRANCHE_CHOICES,
        widget=forms.CheckboxSelectMultiple(attrs={'class': 'form-check-input'}),
        required=False,
        label="Tranches concernées",
    )

    base_calcul = forms.ChoiceField(
        choices=BASE_CALCUL_CHOICES,
        initial=BASE_TRANCHE,
        widget=forms.RadioSelect(attrs={'class': 'form-check-input'}),
        required=False,
        label="Base de calcul",
    )

    # Motif obligatoire: toute remise doit être justifiée
    motif = forms.ChoiceField(
        choices=[("", "— Choisir un motif —")] + PaiementRemise.MOTIF_CHOICES,
        required=True,
        widget=forms.Select(attrs={'class': 'form-select'}),
        label="Motif de la remise",
        error_messages={'required': "Le motif de la remise est obligatoire."},
    )

    def __init__(self, *args, **kwargs):
        paiement = kwargs.pop('paiement', None)
        super().__init__(*args, **kwargs)
        self.paiement = paiement

        if paiement:
            self.fields['montant_original'].initial = paiement.montant
            # Filtrer les remises valides à la date du paiement
            today = paiement.date_paiement
            self.fields['remises'].queryset = RemiseReduction.objects.filter(
                actif=True,
                date_debut__lte=today,
                date_fin__gte=today
            )
            self._appliquer_valeurs_existantes(paiement)

    def _appliquer_valeurs_existantes(self, paiement):
        """Pré-coche la portée déjà enregistrée sur ce paiement."""
        if self.is_bound:
            return
        try:
            existantes = list(paiement.remises.all())
        except Exception:
            existantes = []
        if not existantes:
            return
        tranches = set()
        for lien in existantes:
            tranches.update(str(numero) for numero in lien.tranches_appliquees)
        if tranches:
            self.fields['tranches'].initial = sorted(tranches)
        self.fields['base_calcul'].initial = existantes[0].base_calcul or BASE_TRANCHE
        self.fields['motif'].initial = existantes[0].motif or ''

    def clean_base_calcul(self):
        return self.cleaned_data.get('base_calcul') or BASE_TRANCHE

    def clean_tranches(self):
        return [str(numero) for numero in normaliser_tranches(self.cleaned_data.get('tranches'))]

    def clean(self):
        cleaned = super().clean()
        remises = cleaned.get('remises') or []
        pct = cleaned.get('pourcentage_scolarite') or ''
        pct_value = int(pct) if str(pct).isdigit() else 0
        tranches = cleaned.get('tranches') or []
        motif = cleaned.get('motif') or ''

        # « Ne paie rien » et « La moitié » portent leur propre pourcentage:
        # on l'applique quand l'utilisateur n'a rien choisi d'autre.
        if not remises and pct_value <= 0 and motif in self.POURCENTAGE_PAR_MOTIF:
            pct_value = self.POURCENTAGE_PAR_MOTIF[motif]
            cleaned['pourcentage_scolarite'] = str(pct_value)

        if (remises or pct_value > 0) and not tranches:
            self.add_error(
                'tranches',
                "Sélectionnez au moins une tranche (1, 2 ou 3). "
                "Une remise ne peut pas porter sur l'inscription ou la réinscription.",
            )
        return cleaned

    def tranches_selectionnees(self):
        """Tranches cochées (str), que le formulaire soit lié ou non."""
        if self.is_bound:
            valeurs = self.data.getlist('tranches') if hasattr(self.data, 'getlist') else self.data.get('tranches') or []
        else:
            valeurs = self.fields['tranches'].initial or []
        return [str(numero) for numero in normaliser_tranches(valeurs)]

    def base_calcul_selectionne(self):
        """Base de calcul retenue pour l'affichage."""
        if self.is_bound:
            valeur = self.data.get('base_calcul')
        else:
            valeur = self.fields['base_calcul'].initial
        return valeur if valeur in dict(BASE_CALCUL_CHOICES) else BASE_TRANCHE

    def get_base_remise(self):
        """Base de calcul retenue selon les tranches et le mode sélectionnés."""
        if not self.paiement:
            return Decimal('0')
        return calculer_base_remise(
            self.paiement,
            self.cleaned_data.get('tranches') or [],
            self.cleaned_data.get('base_calcul') or BASE_TRANCHE,
        )

    def calculate_total_remise(self, montant_base):
        """Calcule le montant total des remises sélectionnées"""
        remises = self.cleaned_data.get('remises', [])
        total_remise = Decimal('0')
        
        for remise in remises:
            montant_remise = remise.calculer_remise(montant_base)
            total_remise += montant_remise
        
        return min(total_remise, montant_base)  # La remise ne peut pas dépasser le montant
    
    def get_remises_details(self, montant_base):
        """Retourne les détails de chaque remise appliquée"""
        remises = self.cleaned_data.get('remises', [])
        details = []
        
        for remise in remises:
            montant_remise = remise.calculer_remise(montant_base)
            details.append({
                'remise': remise,
                'montant': montant_remise,
                'description': f"{remise.nom} - {montant_remise:,.0f} GNF".replace(',', ' ')
            })
        
        return details


class CalculateurRemiseForm(forms.Form):
    """Formulaire pour calculer les remises en temps réel"""
    
    montant = forms.DecimalField(
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': 'Montant en GNF',
            'min': '0',
            'step': '1000'
        }),
        label="Montant du paiement"
    )
    
    remise_id = forms.ModelChoiceField(
        queryset=RemiseReduction.objects.filter(actif=True),
        widget=forms.Select(attrs={
            'class': 'form-select'
        }),
        required=False,
        empty_label="Sélectionner une remise",
        label="Remise à appliquer"
    )
    
    def calculate_remise_preview(self):
        """Calcule un aperçu de la remise"""
        if not self.is_valid():
            return None
            
        montant = self.cleaned_data.get('montant')
        remise = self.cleaned_data.get('remise_id')
        
        if not montant or not remise:
            return None
            
        montant_remise = remise.calculer_remise(montant)
        montant_final = montant - montant_remise
        
        return {
            'montant_original': montant,
            'montant_remise': montant_remise,
            'montant_final': montant_final,
            'pourcentage_remise': (montant_remise / montant * 100) if montant > 0 else 0,
            'remise_nom': remise.nom,
            'remise_type': remise.get_type_remise_display()
        }
