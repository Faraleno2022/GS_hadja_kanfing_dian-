from datetime import timedelta
import re
import uuid

from django import forms
from django.forms import formset_factory
from django.utils import timezone

from .models_collecte import LienCollecteEleves, PropositionEleve

CHAMPS_ELEVE = (
    'prenom', 'nom', 'sexe', 'date_naissance', 'lieu_naissance',
    'prenom_responsable', 'nom_responsable', 'telephone_responsable', 'adresse',
)


def styliser(form):
    for field in form.fields.values():
        if not isinstance(field.widget, forms.HiddenInput):
            field.widget.attrs['class'] = (
                'form-check-input' if isinstance(field.widget, forms.CheckboxInput)
                else 'form-select' if isinstance(field.widget, forms.Select) else 'form-control'
            )


class ExpirationCollecteForm(forms.ModelForm):
    class Meta:
        model = LienCollecteEleves
        fields = ('expire_le',)
        widgets = {'expire_le': forms.DateTimeInput(
            format='%Y-%m-%dT%H:%M', attrs={'type': 'datetime-local'},
        )}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['expire_le'].input_formats = ['%Y-%m-%dT%H:%M', '%Y-%m-%dT%H:%M:%S']
        styliser(self)

    def clean_expire_le(self):
        date = self.cleaned_data['expire_le']
        if date <= timezone.now():
            raise forms.ValidationError("Choisissez une date et une heure dans le futur.")
        if date > timezone.now() + timedelta(days=366):
            raise forms.ValidationError("La durée maximale d'un lien est d'un an.")
        return date


class CreerLienCollecteForm(ExpirationCollecteForm):
    class Meta(ExpirationCollecteForm.Meta):
        fields = ('classe', 'destinataire', 'expire_le')

    def __init__(self, *args, classes, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['classe'].queryset = classes
        if not self.is_bound:
            self.initial.setdefault('expire_le', timezone.localtime(timezone.now() + timedelta(days=7)))
        self.fields['expire_le'].help_text = "Le lien se désactive automatiquement à cette échéance."


class EnvoiCollecteForm(forms.Form):
    auteur = forms.CharField(max_length=150, label="Votre nom")
    identifiant = forms.UUIDField(initial=uuid.uuid4, widget=forms.HiddenInput)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        styliser(self)


class PropositionEleveForm(forms.ModelForm):
    class Meta:
        model = PropositionEleve
        fields = CHAMPS_ELEVE
        widgets = {'date_naissance': forms.DateInput(
            format='%Y-%m-%d', attrs={'type': 'date'},
        )}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        styliser(self)
        self.fields['telephone_responsable'].help_text = "Facultatif. Exemple : 622123456 ou +224622123456."

    def clean_date_naissance(self):
        value = self.cleaned_data.get('date_naissance')
        if value and value > timezone.localdate():
            raise forms.ValidationError("La date de naissance ne peut pas être dans le futur.")
        return value

    def clean_telephone_responsable(self):
        value = re.sub(r'[\s().-]', '', self.cleaned_data.get('telephone_responsable', ''))
        if not value:
            return ''
        if re.fullmatch(r'\d{8,9}', value):
            value = '+224' + value
        if not re.fullmatch(r'\+224\d{8,9}', value):
            raise forms.ValidationError("Saisissez un numéro guinéen valide ou laissez ce champ vide.")
        return value

    def clean(self):
        data = super().clean()
        if any(data.get(key) for key in ('prenom_responsable', 'nom_responsable', 'telephone_responsable', 'adresse')):
            for key in ('prenom_responsable', 'nom_responsable'):
                if not data.get(key):
                    self.add_error(key, "Renseignez le prénom et le nom du responsable, ou laissez ses coordonnées vides.")
        return data


PropositionsFormSet = formset_factory(
    PropositionEleveForm, extra=0, min_num=1, validate_min=True,
    max_num=50, validate_max=True, absolute_max=50,
)


class DecisionCollecteForm(forms.Form):
    action = forms.ChoiceField(choices=[('accepter', 'Accepter'), ('refuser', 'Refuser')])
    propositions = forms.ModelMultipleChoiceField(queryset=PropositionEleve.objects.none())
    verrouiller = forms.BooleanField(required=False, initial=True,
        label="Verrouiller les élèves jusqu'au premier paiement validé")
    confirmer_homonymes = forms.BooleanField(required=False,
        label="Créer même si un élève porte déjà les mêmes prénom et nom dans cette classe")

    def __init__(self, *args, propositions, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['propositions'].queryset = propositions
        styliser(self)

    def clean_propositions(self):
        values = self.cleaned_data['propositions']
        if len(values) > 50:
            raise forms.ValidationError("Sélectionnez au maximum 50 propositions à la fois.")
        return values
