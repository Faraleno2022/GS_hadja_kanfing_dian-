"""Modification de la structure d'une école avec permissions distinctes."""
from django import forms
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404, redirect, render
from django.http import HttpResponseForbidden

from utilisateurs.utils import user_school, user_is_superadmin, user_can_manage_school_structure
from .models import Classe, GrilleTarifaire


def _autorise(user, ecole, permission):
    if user_is_superadmin(user):
        return True
    if ecole.created_by_id == user.pk and ecole.etat in ('BROUILLON', 'EN_ATTENTE'):
        return True
    return getattr(user_school(user), 'pk', None) == ecole.pk and user_can_manage_school_structure(user, permission)


class ClasseConfigurationForm(forms.ModelForm):
    class Meta:
        model = Classe
        fields = ['nom', 'niveau', 'annee_scolaire', 'capacite_max', 'code_matricule']

    def clean(self):
        data = super().clean()
        if self.instance.pk and self.instance.eleves.exists():
            ancienne = Classe.objects.get(pk=self.instance.pk)
            for champ in ('niveau', 'annee_scolaire'):
                if data.get(champ) and data[champ] != getattr(ancienne, champ):
                    self.add_error(champ, "Cette classe contient des élèves : utilisez le transfert ou le passage à la nouvelle année.")
        return data


class GrilleConfigurationForm(forms.ModelForm):
    class Meta:
        model = GrilleTarifaire
        fields = ['niveau', 'annee_scolaire', 'frais_inscription', 'frais_reinscription',
                  'tranche_1', 'tranche_2', 'tranche_3', 'periode_1', 'periode_2', 'periode_3',
                  'date_echeance_inscription_defaut', 'date_echeance_tranche_1_defaut',
                  'date_echeance_tranche_2_defaut', 'date_echeance_tranche_3_defaut']

    def clean(self):
        data = super().clean()
        dates = [data.get(champ) for champ in self.Meta.fields if champ.startswith('date_echeance_')]
        dates = [d for d in dates if d is not None]
        if dates != sorted(dates):
            raise ValidationError("Les échéances doivent respecter l'ordre Inscription, T1, T2, T3.")
        return data


def _modifier(request, objet, formulaire, permission, titre):
    if not _autorise(request.user, objet.ecole, permission):
        return HttpResponseForbidden('Vous ne pouvez pas modifier cet élément.')
    form = formulaire(request.POST if request.method == 'POST' else None, instance=objet)
    for field in form.fields.values():
        field.widget.attrs['class'] = 'form-control'
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Modifications enregistrées.')
        return redirect('eleves:configurer_ecole', ecole_id=objet.ecole_id)
    return render(request, 'eleves/configuration_form.html', {
        'form': form, 'ecole': objet.ecole, 'titre_page': titre,
    })


@login_required
def modifier_classe_configuration(request, classe_id):
    return _modifier(request, get_object_or_404(Classe.objects.select_related('ecole'), pk=classe_id),
                     ClasseConfigurationForm, 'peut_gerer_classes', 'Modifier la classe')


@login_required
def modifier_grille_tarifaire(request, grille_id):
    return _modifier(request, get_object_or_404(GrilleTarifaire.objects.select_related('ecole'), pk=grille_id),
                     GrilleConfigurationForm, 'peut_gerer_grilles_tarifaires', 'Modifier la grille tarifaire')
