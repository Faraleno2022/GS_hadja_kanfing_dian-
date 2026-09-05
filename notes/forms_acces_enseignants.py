from datetime import timedelta

from django import forms
from django.utils import timezone

from salaires.models import Enseignant
from utilisateurs.utils import filter_by_user_school
from .acces_enseignants import classes_affectees
from .models import ClasseNote, MatiereNote


class ExpirationForm(forms.Form):
    expire_le = forms.DateTimeField(
        label='Accès valable jusqu’au',
        widget=forms.DateTimeInput(attrs={'type': 'datetime-local'}, format='%Y-%m-%dT%H:%M'),
    )

    def clean_expire_le(self):
        value = self.cleaned_data['expire_le']
        if not timezone.now() < value <= timezone.now() + timedelta(days=90):
            raise forms.ValidationError('Choisissez une date future, dans les 90 prochains jours.')
        return value


class CreerAccesEnseignantForm(ExpirationForm):
    enseignant = forms.ModelChoiceField(queryset=Enseignant.objects.none(), widget=forms.HiddenInput)
    classes = forms.ModelMultipleChoiceField(
        label='Classes autorisées', queryset=ClasseNote.objects.none(), widget=forms.CheckboxSelectMultiple,
    )
    matieres = forms.ModelMultipleChoiceField(
        label='Matières autorisées (secondaire)', queryset=MatiereNote.objects.none(),
        widget=forms.CheckboxSelectMultiple, required=False,
    )

    def __init__(self, *args, user, enseignant, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['enseignant'].queryset = filter_by_user_school(Enseignant.objects.all(), user).filter(
            statut='ACTIF', sync_deleted_at__isnull=True,
            type_enseignant__in=['MATERNELLE', 'PRIMAIRE', 'SECONDAIRE'],
        )
        self.enseignant = enseignant
        classes = classes_affectees(enseignant)
        self.fields['classes'].queryset = classes
        self.fields['matieres'].queryset = MatiereNote.objects.filter(
            classe__in=classes, actif=True, sync_deleted_at__isnull=True,
        ).select_related('classe').order_by('classe__nom', 'nom')
        self.fields['matieres'].label_from_instance = lambda matiere: f'{matiere.classe.nom} ({matiere.classe.annee_scolaire}) — {matiere.nom}'
        if enseignant.type_enseignant != 'SECONDAIRE':
            self.fields['matieres'].widget = forms.HiddenInput()
        self.initial.update(enseignant=enseignant.pk, classes=list(classes), expire_le=timezone.now() + timedelta(days=7))

    def clean(self):
        data = super().clean()
        classes, matieres = data.get('classes'), data.get('matieres')
        if data.get('enseignant') != self.enseignant:
            raise forms.ValidationError('Enseignant invalide.')
        if classes is None:
            return data
        if self.enseignant.type_enseignant == 'SECONDAIRE':
            if not matieres:
                self.add_error('matieres', 'Sélectionnez les matières enseignées.')
            elif any(m.classe_id not in {c.pk for c in classes} for m in matieres):
                self.add_error('matieres', 'Une matière sélectionnée appartient à une classe non autorisée.')
            elif any(not any(m.classe_id == c.pk for m in matieres) for c in classes):
                self.add_error('matieres', 'Choisissez au moins une matière par classe autorisée.')
        else:
            data['matieres'] = MatiereNote.objects.filter(classe__in=classes, actif=True, sync_deleted_at__isnull=True)
            if not data['matieres'].exists():
                self.add_error('classes', 'Ajoutez d’abord les matières de cette classe dans Notes.')
        return data
