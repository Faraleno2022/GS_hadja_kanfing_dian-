from django import forms

from eleves.models import Classe, Eleve
from paiements.models import ModePaiement

from .models import AbonnementBus, AbonnementCantine, GrilleTarifaireBus


class EleveAbonnementChoiceField(forms.ModelChoiceField):
    """Affiche le matricule avant le prénom et le nom dans les listes."""

    def label_from_instance(self, eleve):
        matricule = eleve.matricule or "Sans matricule"
        return f"{matricule} — {eleve.prenom} {eleve.nom}"


class ClasseAbonnementChoiceField(forms.ModelChoiceField):
    def label_from_instance(self, classe):
        ecole = getattr(classe, 'ecole', None)
        return f"{classe.nom} — {ecole.nom}" if ecole else classe.nom


def _configurer_selection_eleve(form, ecole=None):
    classes = Classe.objects.select_related('ecole')
    eleves = Eleve.objects.select_related('classe', 'classe__ecole')
    if ecole:
        classes = classes.filter(ecole=ecole)
        eleves = eleves.filter(classe__ecole=ecole)
    form.fields['classe'].queryset = classes.order_by(
        'ecole__nom', 'nom', '-annee_scolaire'
    )
    form.fields['eleve'].queryset = eleves.order_by(
        'classe__nom', 'nom', 'prenom', 'matricule'
    )
    form.fields['classe'].empty_label = "Toutes les classes"
    form.fields['eleve'].empty_label = "Sélectionner un élève"

    eleve_initial = form.initial.get('eleve')
    if getattr(form.instance, 'pk', None) and getattr(form.instance, 'eleve_id', None):
        eleve_initial = form.instance.eleve
    if eleve_initial:
        if not isinstance(eleve_initial, Eleve):
            try:
                eleve_initial = eleves.get(pk=eleve_initial)
            except (Eleve.DoesNotExist, TypeError, ValueError):
                eleve_initial = None
        if eleve_initial and eleve_initial.classe_id:
            form.fields['classe'].initial = eleve_initial.classe_id
            form.initial.setdefault('classe', eleve_initial.classe_id)


class GrilleTarifaireBusForm(forms.ModelForm):
    class Meta:
        model = GrilleTarifaireBus
        fields = [
            'ecole', 'zone', 'annee_scolaire',
            'tranche_1', 'date_echeance_tranche_1',
            'tranche_2', 'date_echeance_tranche_2',
            'tranche_3', 'date_echeance_tranche_3', 'actif',
        ]
        widgets = {
            'ecole': forms.Select(attrs={'class': 'form-select'}),
            'zone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex. Ratoma'}),
            'annee_scolaire': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '2026-2027'}),
            'tranche_1': forms.NumberInput(attrs={'class': 'form-control', 'min': 0}),
            'tranche_2': forms.NumberInput(attrs={'class': 'form-control', 'min': 0}),
            'tranche_3': forms.NumberInput(attrs={'class': 'form-control', 'min': 0}),
            'date_echeance_tranche_1': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'date_echeance_tranche_2': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'date_echeance_tranche_3': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'actif': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def __init__(self, *args, ecole=None, allow_school_choice=False, **kwargs):
        super().__init__(*args, **kwargs)
        self.ecole_autorisee = ecole
        if ecole and not allow_school_choice:
            self.fields['ecole'].queryset = self.fields['ecole'].queryset.filter(pk=ecole.pk)
            self.fields['ecole'].initial = ecole
            self.fields['ecole'].widget = forms.HiddenInput()

    def clean_ecole(self):
        ecole = self.cleaned_data['ecole']
        if self.ecole_autorisee and ecole.pk != self.ecole_autorisee.pk:
            raise forms.ValidationError("Vous ne pouvez créer une grille que pour votre école.")
        return ecole

    def clean(self):
        cleaned = super().clean()
        montants = [cleaned.get(f'tranche_{numero}') or 0 for numero in (1, 2, 3)]
        if not any(montant > 0 for montant in montants):
            raise forms.ValidationError("Au moins une tranche doit avoir un montant supérieur à zéro.")
        echeances = [
            cleaned.get(f'date_echeance_tranche_{numero}') for numero in (1, 2, 3)
        ]
        dates_definies = [date_value for date_value in echeances if date_value]
        if dates_definies != sorted(dates_definies):
            raise forms.ValidationError("Les dates d'échéance doivent être dans l'ordre des tranches.")
        return cleaned


class AbonnementBusForm(forms.ModelForm):
    classe = ClasseAbonnementChoiceField(
        queryset=Classe.objects.none(),
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'}),
        label="Filtrer par classe",
    )
    eleve = EleveAbonnementChoiceField(
        queryset=Eleve.objects.none(),
        widget=forms.Select(attrs={'class': 'form-select'}),
        label="Élève",
    )

    class Meta:
        model = AbonnementBus
        fields = [
            'classe', 'eleve', 'grille', 'periodicite', 'montant', 'date_debut',
            'mode_paiement', 'reference_externe', 'observations',
        ]
        widgets = {
            'grille': forms.Select(attrs={'class': 'form-select'}),
            'periodicite': forms.Select(attrs={'class': 'form-select'}),
            'montant': forms.NumberInput(attrs={'class': 'form-control', 'min': 1}),
            'date_debut': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'mode_paiement': forms.Select(attrs={'class': 'form-select'}),
            'reference_externe': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'N° reçu externe, transaction Mobile Money, chèque…',
            }),
            'observations': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }

    def __init__(self, *args, ecole=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.ecole_autorisee = ecole
        _configurer_selection_eleve(self, ecole)
        grilles = GrilleTarifaireBus.objects.filter(actif=True).select_related('ecole')
        if ecole:
            grilles = grilles.filter(ecole=ecole)
        if self.instance and self.instance.pk and self.instance.grille_id:
            grilles = GrilleTarifaireBus.objects.filter(
                pk__in=list(grilles.values_list('pk', flat=True)) + [self.instance.grille_id]
            ).select_related('ecole')
        self.fields['grille'].queryset = grilles.order_by('-annee_scolaire', 'zone')
        self.fields['grille'].empty_label = "Sélectionner la zone et l'année"
        self.fields['mode_paiement'].queryset = ModePaiement.objects.filter(actif=True).order_by('nom')
        self.fields['date_debut'].label = "Date du paiement"
        self.fields['periodicite'].label = "Type de paiement / tranche"
        self.fields['periodicite'].choices = [
            (AbonnementBus.Periodicite.ANNUEL, "Annuel — totalité des 3 tranches"),
            (AbonnementBus.Periodicite.TRANCHE_1, "1ère tranche"),
            (AbonnementBus.Periodicite.TRANCHE_2, "2ème tranche"),
            (AbonnementBus.Periodicite.TRANCHE_3, "3ème tranche"),
        ]
        if self.instance and self.instance.pk and self.instance.periodicite not in {'ANNUEL', 'T1', 'T2', 'T3'}:
            self.fields['periodicite'].choices = [
                (self.instance.periodicite, self.instance.get_periodicite_display()),
                *self.fields['periodicite'].choices,
            ]
        if self.instance and self.instance.pk and not self.instance.grille_id:
            self.fields['grille'].required = False
        if self.instance and self.instance.pk and not self.instance.mode_paiement_id:
            self.fields['mode_paiement'].required = False

    def clean(self):
        cleaned = super().clean()
        eleve = cleaned.get('eleve')
        classe = cleaned.get('classe')
        grille = cleaned.get('grille')
        periodicite = cleaned.get('periodicite')
        montant = cleaned.get('montant')

        if montant is not None and montant <= 0:
            self.add_error('montant', "Le montant du paiement doit être supérieur à zéro.")

        if classe and eleve and eleve.classe_id != classe.pk:
            self.add_error('eleve', "L'élève sélectionné n'appartient pas à cette classe.")

        if not grille and not (self.instance and self.instance.pk):
            self.add_error('grille', "Sélectionnez une grille tarifaire bus.")
            return cleaned

        if grille and eleve:
            ecole_eleve_id = getattr(getattr(eleve, 'classe', None), 'ecole_id', None)
            if ecole_eleve_id != grille.ecole_id:
                self.add_error('eleve', "L'élève et la grille doivent appartenir à la même école.")
            if self.ecole_autorisee and grille.ecole_id != self.ecole_autorisee.pk:
                self.add_error('grille', "Cette grille n'appartient pas à votre école.")

        if grille and eleve and periodicite in {'ANNUEL', 'T1', 'T2', 'T3'} and montant is not None:
            situation = grille.situation_paiements(
                eleve,
                exclude_pk=self.instance.pk if self.instance and self.instance.pk else None,
            )
            reste = situation[periodicite]['reste']
            if montant > reste:
                self.add_error(
                    'montant',
                    f"Le montant dépasse le reste à payer ({reste:,.0f} GNF).".replace(',', ' '),
                )
        return cleaned


class AbonnementCantineForm(forms.ModelForm):
    classe = ClasseAbonnementChoiceField(
        queryset=Classe.objects.none(),
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'}),
        label="Filtrer par classe",
    )
    eleve = EleveAbonnementChoiceField(
        queryset=Eleve.objects.none(),
        widget=forms.Select(attrs={'class': 'form-select'}),
        label="Élève",
    )

    class Meta:
        model = AbonnementCantine
        fields = [
            'classe', 'eleve', 'montant', 'periodicite', 'type_repas', 'date_debut', 'date_expiration',
            'statut', 'alerte_avant_jours', 'regime_alimentaire', 'allergies', 
            'contact_parent', 'reference_externe', 'observations'
        ]
        widgets = {
            'date_debut': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'date_expiration': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'montant': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Montant en GNF'}),
            'periodicite': forms.Select(attrs={'class': 'form-control'}),
            'type_repas': forms.Select(attrs={'class': 'form-control'}),
            'statut': forms.Select(attrs={'class': 'form-control'}),
            'alerte_avant_jours': forms.NumberInput(attrs={'class': 'form-control', 'value': 7}),
            'regime_alimentaire': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex: Végétarien, Halal, etc.'}),
            'allergies': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Indiquez les allergies alimentaires'}),
            'contact_parent': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '+224XXXXXXXXX'}),
            'reference_externe': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'N° reçu externe, transaction Mobile Money, chèque…',
            }),
            'observations': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

    def __init__(self, *args, ecole=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.ecole_autorisee = ecole
        _configurer_selection_eleve(self, ecole)

    def clean(self):
        cleaned = super().clean()
        classe = cleaned.get('classe')
        eleve = cleaned.get('eleve')
        if classe and eleve and eleve.classe_id != classe.pk:
            self.add_error('eleve', "L'élève sélectionné n'appartient pas à cette classe.")
        if self.ecole_autorisee and eleve:
            ecole_eleve_id = getattr(getattr(eleve, 'classe', None), 'ecole_id', None)
            if ecole_eleve_id != self.ecole_autorisee.pk:
                self.add_error('eleve', "Cet élève n'appartient pas à votre école.")
        return cleaned
