from django import forms
from django.core.exceptions import ValidationError
from decimal import Decimal
from .models import (
    AffectationClasse,
    AvanceSalaire,
    Enseignant,
    EtatSalaire,
    JOURS_SEMAINE_PAIE,
    ModeCalculHoraire,
    NIVEAUX_GARDERIE,
    ParametrePaie,
    NIVEAUX_MATERNELLE,
    NIVEAUX_PAR_TYPE_ENSEIGNANT,
    NIVEAUX_PRIMAIRE,
    NIVEAUX_SECONDAIRE,
    PeriodeSalaire,
    PresenceEnseignant,
    StatutEnseignant,
    TypeEnseignant,
)
from eleves.models import Ecole, Classe


class MontantGNFField(forms.DecimalField):
    """Champ acceptant aussi « 250 000 GNF » et les espaces insécables."""

    def to_python(self, value):
        if isinstance(value, str):
            value = value.strip()
            for espace in ('\u00a0', '\u202f', '\u2009', ' '):
                value = value.replace(espace, '')
            for sigle in ('GNF', 'gnf', 'Gnf', 'FG', 'fg'):
                value = value.replace(sigle, '')
            value = value.strip()
        return super().to_python(value)


CHAMPS_HEURES_JOURS = [f'heures_{jour}' for jour, _, _ in JOURS_SEMAINE_PAIE]
CHAMPS_OCCURRENCES_JOURS = [f'nb_{jour}s' for jour, _, _ in JOURS_SEMAINE_PAIE]


class EnseignantForm(forms.ModelForm):
    """Formulaire pour créer/modifier un enseignant"""

    class Meta:
        model = Enseignant
        fields = [
            'nom', 'prenoms', 'telephone', 'email', 'adresse', 'photo',
            'ecole', 'type_enseignant', 'statut',
            'classe_principale', 'fonction',
            'taux_horaire', 'mode_calcul_horaire', 'salaire_fixe',
            'heures_mensuelles', 'date_embauche',
            'matricule', 'prime_fonction', 'prime_performance',
            'prime_exceptionnelle', 'distance_km', 'professeur_principal',
            *CHAMPS_HEURES_JOURS,
        ]
        widgets = {
            **{
                champ: forms.NumberInput(attrs={
                    'class': 'form-control', 'min': '0', 'max': '24', 'step': '0.5',
                })
                for champ in CHAMPS_HEURES_JOURS
            },
            'photo': forms.ClearableFileInput(attrs={'class': 'form-control', 'accept': 'image/jpeg,image/png,image/webp'}),
            'nom': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Nom de famille'
            }),
            'prenoms': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Prénoms'
            }),
            'telephone': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '+224 XXX XX XX XX'
            }),
            'email': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'adresse@exemple.com'
            }),
            'adresse': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Adresse complète'
            }),
            'ecole': forms.Select(attrs={
                'class': 'form-select'
            }),
            'type_enseignant': forms.Select(attrs={
                'class': 'form-select'
            }),
            'statut': forms.Select(attrs={
                'class': 'form-select'
            }),
            'classe_principale': forms.Select(attrs={
                'class': 'form-select'
            }),
            'fonction': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ex. Directeur, secrétaire, comptable'
            }),
            'taux_horaire': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Taux horaire en GNF',
                'step': '0.01'
            }),
            'mode_calcul_horaire': forms.Select(attrs={
                'class': 'form-select'
            }),
            'salaire_fixe': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Salaire fixe en GNF',
                'step': '0.01'
            }),
            'heures_mensuelles': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Nombre d\'heures par mois',
                'step': '0.25',
                'min': '0'
            }),
            'date_embauche': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'matricule': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ex. 0499120'
            }),
            'prime_fonction': forms.NumberInput(attrs={
                'class': 'form-control', 'min': '0', 'step': '1'
            }),
            'prime_performance': forms.NumberInput(attrs={
                'class': 'form-control', 'min': '0', 'step': '1'
            }),
            'prime_exceptionnelle': forms.NumberInput(attrs={
                'class': 'form-control', 'min': '0', 'step': '1'
            }),
            'distance_km': forms.NumberInput(attrs={
                'class': 'form-control', 'min': '0', 'step': '0.5'
            }),
            'professeur_principal': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
        }
        labels = {
            'nom': 'Nom de famille *',
            'prenoms': 'Prénoms *',
            'telephone': 'Téléphone',
            'email': 'Email',
            'adresse': 'Adresse',
            'ecole': 'École *',
            'type_enseignant': 'Type d\'enseignant *',
            'statut': 'Statut',
            'classe_principale': 'Classe principale *',
            'fonction': 'Fonction administrative *',
            'taux_horaire': 'Taux horaire (GNF)',
            'mode_calcul_horaire': 'Calcul des heures',
            'salaire_fixe': 'Salaire fixe (GNF)',
            'heures_mensuelles': 'Heures mensuelles',
            'date_embauche': 'Date d\'embauche *',
            'matricule': 'Matricule',
            'prime_fonction': 'Prime de fonction (GNF / mois)',
            'prime_performance': 'Prime de performance (GNF / mois)',
            'prime_exceptionnelle': 'Prime exceptionnelle (GNF / mois)',
            'distance_km': 'Distance domicile-école (km)',
            'professeur_principal': 'Professeur principal (secondaire)',
            **{
                f'heures_{jour}': libelle
                for jour, _, libelle in JOURS_SEMAINE_PAIE
            },
        }
        help_texts = {
            'taux_horaire': 'Pour les enseignants du secondaire uniquement',
            'mode_calcul_horaire': (
                "Pointage arrivée/départ, total mensuel global ou emploi du temps hebdomadaire (heures du lundi au samedi)."
            ),
            'salaire_fixe': 'Pour garderie, maternelle, primaire et administrateurs',
            'heures_mensuelles': (
                "Total global du mois multiplié par le taux horaire."
            ),
            'date_embauche': 'Date d\'entrée en fonction',
            'classe_principale': (
                "Pour la garderie, la maternelle et le primaire uniquement."
            ),
            'fonction': (
                "Fonction occupée par le membre du personnel administratif."
            ),
        }

    def clean_photo(self):
        photo = self.cleaned_data.get('photo')
        if photo and photo.size > 5 * 1024 * 1024:
            raise ValidationError('La photo ne doit pas dépasser 5 Mo.')
        image = getattr(photo, 'image', None)
        if image and image.width * image.height > 25_000_000:
            raise ValidationError('La photo est trop grande. Choisissez une image de moins de 25 mégapixels.')
        return photo

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

        # Rendre certains champs obligatoires
        self.fields['nom'].required = True
        self.fields['prenoms'].required = True
        self.fields['ecole'].required = True
        self.fields['type_enseignant'].required = True
        self.fields['date_embauche'].required = True

        # Restreindre les écoles visibles selon l'utilisateur
        from utilisateurs.utils import user_is_superadmin, user_school
        ecole_user = user_school(self.user) if self.user else None
        if self.user and not user_is_superadmin(self.user):
            if ecole_user:
                self.fields['ecole'].queryset = Ecole.objects.filter(id=ecole_user.id)
                self.fields['ecole'].initial = ecole_user
            else:
                self.fields['ecole'].queryset = Ecole.objects.none()

        type_selectionne = (
            self.data.get(self.add_prefix('type_enseignant'))
            if self.is_bound else self.instance.type_enseignant
        )
        ecole_id = None
        if self.is_bound:
            valeur_ecole = self.data.get(self.add_prefix('ecole'))
            if str(valeur_ecole or '').isdigit():
                ecole_id = int(valeur_ecole)
        if not ecole_id and getattr(self.instance, 'ecole_id', None):
            ecole_id = self.instance.ecole_id
        if not ecole_id and ecole_user:
            ecole_id = ecole_user.id

        niveaux_classe_principale = (
            NIVEAUX_GARDERIE | NIVEAUX_MATERNELLE | NIVEAUX_PRIMAIRE
        )
        if type_selectionne in NIVEAUX_PAR_TYPE_ENSEIGNANT:
            niveaux_classe_principale = NIVEAUX_PAR_TYPE_ENSEIGNANT[
                type_selectionne
            ]
        classes = Classe.objects.filter(
            niveau__in=niveaux_classe_principale
        ).select_related('ecole').order_by(
            '-annee_scolaire', 'niveau', 'nom'
        )
        if ecole_id:
            classes = classes.filter(ecole_id=ecole_id)
        self.fields['classe_principale'].queryset = classes
        self.fields['classe_principale'].required = False
        self.fields['fonction'].required = False
        for champ in (
            'prime_fonction', 'prime_performance', 'prime_exceptionnelle',
            'distance_km',
        ):
            self.fields[champ].required = False

        # Définir le statut par défaut
        if not self.instance.pk:
            self.fields['statut'].initial = StatutEnseignant.ACTIF

        # La saisie manuelle est réservée à un état de salaire mensuel. Elle
        # ne doit pas devenir le mode permanent du dossier enseignant.
        self.fields['mode_calcul_horaire'].choices = [
            (ModeCalculHoraire.POINTAGE, ModeCalculHoraire.POINTAGE.label),
            (ModeCalculHoraire.MENSUEL, ModeCalculHoraire.MENSUEL.label),
            (ModeCalculHoraire.HEBDOMADAIRE, ModeCalculHoraire.HEBDOMADAIRE.label),
        ]
        for champ in CHAMPS_HEURES_JOURS:
            self.fields[champ].required = False

    def clean(self):
        cleaned_data = super().clean()
        type_enseignant = cleaned_data.get('type_enseignant')
        taux_horaire = cleaned_data.get('taux_horaire')
        salaire_fixe = cleaned_data.get('salaire_fixe')
        heures_mensuelles = cleaned_data.get('heures_mensuelles')
        mode_calcul = cleaned_data.get(
            'mode_calcul_horaire', ModeCalculHoraire.POINTAGE
        )
        classe_principale = cleaned_data.get('classe_principale')
        fonction = (cleaned_data.get('fonction') or '').strip()
        for champ in (
            'prime_fonction', 'prime_performance', 'prime_exceptionnelle',
            'distance_km', *CHAMPS_HEURES_JOURS,
        ):
            if cleaned_data.get(champ) is None:
                cleaned_data[champ] = Decimal('0')
        if type_enseignant != TypeEnseignant.SECONDAIRE:
            cleaned_data['professeur_principal'] = False
        ecole = cleaned_data.get('ecole')

        types_avec_classe = {
            TypeEnseignant.GARDERIE,
            TypeEnseignant.MATERNELLE,
            TypeEnseignant.PRIMAIRE,
        }
        if type_enseignant in types_avec_classe:
            if not classe_principale:
                self.add_error(
                    'classe_principale',
                    "Sélectionnez la classe principale de l'enseignant."
                )
            elif ecole and classe_principale.ecole_id != ecole.id:
                self.add_error(
                    'classe_principale',
                    "La classe doit appartenir à l'école sélectionnée."
                )
            elif classe_principale.niveau not in NIVEAUX_PAR_TYPE_ENSEIGNANT.get(
                type_enseignant, set()
            ):
                self.add_error(
                    'classe_principale',
                    "Cette classe ne correspond pas au type d'enseignant."
                )
            cleaned_data['fonction'] = ''
        elif type_enseignant == TypeEnseignant.ADMINISTRATEUR:
            cleaned_data['classe_principale'] = None
            if not fonction:
                self.add_error(
                    'fonction',
                    "Renseignez la fonction du membre du personnel administratif."
                )
            else:
                cleaned_data['fonction'] = fonction
        else:
            cleaned_data['classe_principale'] = None
            cleaned_data['fonction'] = ''

        # Validation selon le type d'enseignant
        if type_enseignant == TypeEnseignant.SECONDAIRE:
            if not taux_horaire:
                raise ValidationError({
                    'taux_horaire': 'Le taux horaire est obligatoire pour les enseignants du secondaire.'
                })
            if (
                mode_calcul == ModeCalculHoraire.MENSUEL
                and not heures_mensuelles
            ):
                raise ValidationError({
                    'heures_mensuelles': (
                        "Le total d'heures mensuelles est obligatoire pour le mode mensuel global."
                    )
                })
            if (
                mode_calcul == ModeCalculHoraire.HEBDOMADAIRE
                and sum(cleaned_data[c] for c in CHAMPS_HEURES_JOURS) <= 0
            ):
                raise ValidationError({
                    'heures_lundi': (
                        "Renseignez les heures d'au moins un jour de la semaine "
                        "pour le mode emploi du temps."
                    )
                })
            if salaire_fixe:
                cleaned_data['salaire_fixe'] = None  # Effacer le salaire fixe
            if mode_calcul != ModeCalculHoraire.MENSUEL:
                cleaned_data['heures_mensuelles'] = None
        elif type_enseignant:
            if not salaire_fixe:
                raise ValidationError({
                    'salaire_fixe': f'Le salaire fixe est obligatoire pour les enseignants de type {type_enseignant}.'
                })
            if taux_horaire:
                cleaned_data['taux_horaire'] = None  # Effacer le taux horaire
            cleaned_data['mode_calcul_horaire'] = ModeCalculHoraire.POINTAGE
            cleaned_data['heures_mensuelles'] = None
            for champ in CHAMPS_HEURES_JOURS:
                cleaned_data[champ] = Decimal('0')

        # Validation des heures mensuelles
        if heures_mensuelles is not None and heures_mensuelles <= 0:
            raise ValidationError({
                'heures_mensuelles': 'Le nombre d\'heures mensuelles doit être supérieur à 0.'
            })

        if heures_mensuelles is not None and heures_mensuelles > 200:
            raise ValidationError({
                'heures_mensuelles': 'Le nombre d\'heures mensuelles ne peut pas dépasser 200 heures par mois.'
            })

        return cleaned_data

    def clean_telephone(self):
        telephone = self.cleaned_data.get('telephone')
        if telephone:
            # Validation basique du format téléphone guinéen
            telephone = telephone.replace(' ', '').replace('-', '')
            if not telephone.startswith('+224') and not telephone.startswith('224'):
                if len(telephone) == 9 and telephone.startswith(('6', '7')):
                    telephone = '+224' + telephone
                else:
                    raise ValidationError('Format de téléphone invalide. Utilisez le format guinéen.')
        return telephone


class AffectationClasseForm(forms.ModelForm):
    """Formulaire pour affecter un enseignant à une classe"""

    class Meta:
        model = AffectationClasse
        fields = [
            'classe', 'heures_par_semaine', 'matiere',
            'date_debut', 'date_fin', 'actif'
        ]
        widgets = {
            'classe': forms.Select(attrs={'class': 'form-select'}),
            'heures_par_semaine': forms.NumberInput(attrs={
                'class': 'form-control', 'step': '0.25', 'min': '0'
            }),
            'matiere': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex: Mathématiques'}),
            'date_debut': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'date_fin': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'actif': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
        labels = {
            'classe': 'Classe *',
            'heures_par_semaine': 'Heures par semaine',
            'matiere': 'Matière',
            'date_debut': 'Date de début *',
            'date_fin': 'Date de fin',
            'actif': 'Active',
        }

    def __init__(self, *args, **kwargs):
        # Attendre un paramètre optionnel enseignant pour filtrer les classes
        self.enseignant = kwargs.pop('enseignant', None)
        super().__init__(*args, **kwargs)

        # IMPORTANT: fournir l'enseignant à l'instance dès l'init pour que
        # la validation du modèle (AffectationClasse.clean) puisse y accéder
        # pendant form.is_valid() sans déclencher RelatedObjectDoesNotExist.
        if self.enseignant is not None:
            try:
                self.instance.enseignant = self.enseignant
            except Exception:
                pass

        # Champs requis
        self.fields['classe'].required = True
        self.fields['date_debut'].required = True

        # Restreindre les classes à l'école de l'enseignant (année la plus récente)
        if self.enseignant and getattr(self.enseignant, 'ecole_id', None):
            qs = Classe.objects.filter(
                ecole_id=self.enseignant.ecole_id,
                niveau__in=NIVEAUX_SECONDAIRE,
            )
            annee_recente = (
                Classe.objects.filter(ecole_id=self.enseignant.ecole_id)
                .values_list('annee_scolaire', flat=True)
                .distinct().order_by('-annee_scolaire').first()
            )
            if annee_recente:
                qs = qs.filter(annee_scolaire=annee_recente)
            self.fields['classe'].queryset = qs
        else:
            self.fields['classe'].queryset = Classe.objects.none()

        self.fields['classe'].label = 'Classe du secondaire *'
        if not self.is_bound and not self.instance.pk and self.enseignant:
            self.fields['date_debut'].initial = self.enseignant.date_embauche

    def clean(self):
        cleaned_data = super().clean()
        if not self.enseignant:
            raise ValidationError('Enseignant requis pour créer une affectation.')

        if self.enseignant.type_enseignant != TypeEnseignant.SECONDAIRE:
            raise ValidationError(
                "Les affectations multiples sont réservées aux enseignants "
                "du secondaire. Utilisez la classe principale pour la "
                "garderie, la maternelle et le primaire."
            )

        # Validation spécifique aux enseignants du secondaire
        if self.enseignant.type_enseignant == TypeEnseignant.SECONDAIRE:
            if not cleaned_data.get('heures_par_semaine'):
                raise ValidationError({'heures_par_semaine': "Obligatoire pour les enseignants du secondaire."})

        # Vérifier cohérence des dates
        d_debut = cleaned_data.get('date_debut')
        d_fin = cleaned_data.get('date_fin')
        if d_debut and d_fin and d_fin < d_debut:
            raise ValidationError({'date_fin': 'La date de fin ne peut pas être antérieure à la date de début.'})

        classe = cleaned_data.get('classe')
        actif = cleaned_data.get('actif')
        if classe and actif:
            doublons = AffectationClasse.objects.filter(
                enseignant=self.enseignant,
                classe=classe,
                actif=True,
            )
            if self.instance.pk:
                doublons = doublons.exclude(pk=self.instance.pk)
            if doublons.exists():
                self.add_error(
                    'classe',
                    "Cet enseignant possède déjà une affectation active dans cette classe."
                )

        return cleaned_data

    def save(self, commit=True):
        obj = super().save(commit=False)
        if self.enseignant:
            obj.enseignant = self.enseignant
        if commit:
            obj.save()
        return obj


class PresenceForm(forms.ModelForm):
    """Formulaire pour pointer/modifier une présence"""

    class Meta:
        model = PresenceEnseignant
        fields = [
            'enseignant', 'date', 'statut',
            'heure_arrivee', 'heure_depart', 'heures_travaillees',
            'observations', 'justifie'
        ]
        widgets = {
            'enseignant': forms.Select(attrs={'class': 'form-select'}),
            'date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'statut': forms.Select(attrs={'class': 'form-select'}),
            'heure_arrivee': forms.TimeInput(attrs={'class': 'form-control', 'type': 'time'}),
            'heure_depart': forms.TimeInput(attrs={'class': 'form-control', 'type': 'time'}),
            'heures_travaillees': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.25',
                'min': '0',
                'placeholder': 'Calculé automatiquement si vide'
            }),
            'observations': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Motif d\'absence, retard, etc.'
            }),
            'justifie': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
        labels = {
            'enseignant': 'Enseignant *',
            'date': 'Date *',
            'statut': 'Statut *',
            'heure_arrivee': 'Heure d\'arrivée',
            'heure_depart': 'Heure de départ',
            'heures_travaillees': 'Heures travaillées',
            'observations': 'Observations',
            'justifie': 'Absence/Retard justifié',
        }

    def __init__(self, *args, **kwargs):
        ecole = kwargs.pop('ecole', None)
        super().__init__(*args, **kwargs)

        # Filtrer les enseignants par école
        if ecole:
            self.fields['enseignant'].queryset = Enseignant.objects.filter(
                ecole=ecole,
                statut='ACTIF'
            ).order_by('nom', 'prenoms')

    def clean(self):
        cleaned_data = super().clean()
        heure_arrivee = cleaned_data.get('heure_arrivee')
        heure_depart = cleaned_data.get('heure_depart')
        heures_travaillees = cleaned_data.get('heures_travaillees')
        statut = cleaned_data.get('statut')

        if bool(heure_arrivee) != bool(heure_depart):
            raise ValidationError(
                "L'heure d'arrivée et l'heure de départ doivent être renseignées ensemble."
            )

        if statut in {'ABSENT', 'CONGE', 'MALADIE'}:
            if heure_arrivee or heure_depart or (
                heures_travaillees is not None and heures_travaillees > 0
            ):
                raise ValidationError(
                    'Aucune heure travaillée ne peut être enregistrée pour ce statut.'
                )

        return cleaned_data


RUBRIQUES_PRIMES_FORM = [champ for champ, _ in EtatSalaire.RUBRIQUES_PRIMES]


class EtatSalaireAjustementForm(forms.ModelForm):
    """Modification contrôlée d'un brouillon de salaire avant validation."""

    class Meta:
        model = EtatSalaire
        fields = [
            'salaire_base', 'taux_horaire_applique', 'total_heures',
            'heures_absence', 'heures_revision',
            *RUBRIQUES_PRIMES_FORM,
            'jours_chomes', 'deductions', 'observations',
        ]
        widgets = {
            'salaire_base': forms.NumberInput(attrs={
                'class': 'form-control', 'min': '0', 'step': '0.01'
            }),
            'taux_horaire_applique': forms.NumberInput(attrs={
                'class': 'form-control', 'min': '0', 'step': '0.01'
            }),
            'total_heures': forms.NumberInput(attrs={
                'class': 'form-control', 'min': '0', 'max': '744',
                'step': '0.25'
            }),
            'heures_revision': forms.NumberInput(attrs={
                'class': 'form-control', 'min': '0', 'step': '0.25'
            }),
            'heures_absence': forms.NumberInput(attrs={
                'class': 'form-control', 'min': '0', 'step': '0.25'
            }),
            'jours_chomes': forms.NumberInput(attrs={
                'class': 'form-control', 'min': '0', 'max': '31', 'step': '1'
            }),
            **{
                champ: forms.NumberInput(attrs={
                    'class': 'form-control prime-input', 'min': '0', 'step': '0.01'
                })
                for champ in RUBRIQUES_PRIMES_FORM
            },
            'deductions': forms.NumberInput(attrs={
                'class': 'form-control', 'min': '0', 'step': '0.01'
            }),
            'observations': forms.Textarea(attrs={
                'class': 'form-control', 'rows': 4,
                'placeholder': 'Motif des primes ou retenues',
            }),
        }
        labels = {
            'deductions': 'Autres retenues (GNF)',
            'heures_revision': 'Heures de révision',
            'heures_absence': "Heures d'absence",
            'jours_chomes': 'Jours chômés',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.est_horaire = bool(
            self.instance
            and self.instance.enseignant_id
            and self.instance.enseignant.est_taux_horaire
        )

        # Garder la compatibilité avec les anciens formulaires et permettre
        # une valeur nulle (0 heure / 0 GNF) tant que le brouillon n'est pas
        # validé.
        self.fields['salaire_base'].required = False
        self.fields['taux_horaire_applique'].required = False
        self.fields['total_heures'].required = False
        self.fields['heures_revision'].required = False
        self.fields['heures_absence'].required = False
        self.fields['jours_chomes'].required = False
        for champ in RUBRIQUES_PRIMES_FORM:
            self.fields[champ].required = False

        if self.est_horaire:
            self.fields['salaire_base'].disabled = True
            self.fields['salaire_base'].help_text = (
                "Calculé automatiquement : heures travaillées × taux horaire."
            )
            self.fields['total_heures'].label = 'Nombre d’heures travaillées'
            self.fields['total_heures'].help_text = (
                "Le pointage est proposé automatiquement. Modifiez ce total "
                "uniquement si le pointage du mois est absent ou incomplet."
            )
        else:
            self.fields['salaire_base'].label = 'Salaire de base (GNF)'

    def clean(self):
        cleaned_data = super().clean()
        for champ in RUBRIQUES_PRIMES_FORM + ['heures_revision', 'heures_absence']:
            if cleaned_data.get(champ) is None and champ not in self.errors:
                cleaned_data[champ] = Decimal('0')
        if cleaned_data.get('jours_chomes') is None and 'jours_chomes' not in self.errors:
            cleaned_data['jours_chomes'] = 0
        primes = sum(
            (cleaned_data.get(champ) or Decimal('0') for champ in RUBRIQUES_PRIMES_FORM),
            Decimal('0'),
        )
        cleaned_data['primes'] = primes
        deductions = cleaned_data.get('deductions') or Decimal('0')

        if self.est_horaire:
            total_heures = cleaned_data.get('total_heures')
            taux_horaire = cleaned_data.get('taux_horaire_applique')
            if total_heures is None:
                total_heures = self.instance.total_heures or Decimal('0')
            if taux_horaire is None:
                taux_horaire = (
                    self.instance.taux_horaire_applique or Decimal('0')
                )

            if total_heures < 0 or total_heures > Decimal('744'):
                self.add_error(
                    'total_heures',
                    "Le total d'heures doit être compris entre 0 et 744.",
                )
            if taux_horaire <= 0:
                self.add_error(
                    'taux_horaire_applique',
                    "Le taux horaire doit être supérieur à zéro.",
                )

            cleaned_data['total_heures'] = total_heures
            cleaned_data['taux_horaire_applique'] = taux_horaire
            salaire_base = (total_heures * taux_horaire).quantize(
                Decimal('0.01')
            )
            cleaned_data['salaire_base'] = salaire_base
        else:
            salaire_base = cleaned_data.get('salaire_base')
            if salaire_base is None:
                salaire_base = self.instance.salaire_base or Decimal('0')
                cleaned_data['salaire_base'] = salaire_base

        sanctions = Decimal('0')
        if self.instance.periode_id:
            sanctions = Decimal(cleaned_data.get('jours_chomes') or 0) * (
                ParametrePaie.pour_ecole(self.instance.periode.ecole).retenue_par_jour_chome
            )
        cleaned_data['imputation_sanctions'] = sanctions
        if sanctions > salaire_base + primes:
            self.add_error(
                'jours_chomes',
                "L'imputation des jours chômés dépasse le salaire de base et les primes.",
            )
        elif deductions + sanctions > salaire_base + primes:
            self.add_error(
                'deductions',
                'Les retenues ne peuvent pas dépasser le salaire de base et les primes.',
            )

        return cleaned_data

    def _post_clean(self):
        # Une avance portée sur un brouillon sera entièrement rejouée par la
        # vue après l'ajustement. L'ancienne imputation ne doit donc pas faire
        # échouer la validation d'une baisse du salaire de base.
        avances_courantes = self.instance.avances_deduites
        sanctions_courantes = self.instance.imputation_sanctions
        self.instance.avances_deduites = Decimal('0')
        self.instance.primes = self.cleaned_data.get('primes', self.instance.primes)
        if 'jours_chomes' not in self.errors:
            self.instance.imputation_sanctions = self.cleaned_data.get(
                'imputation_sanctions', sanctions_courantes
            )
        else:
            self.instance.imputation_sanctions = Decimal('0')
        try:
            super()._post_clean()
        finally:
            self.instance.avances_deduites = avances_courantes
            self.instance.imputation_sanctions = sanctions_courantes


class ParametrePaieForm(forms.ModelForm):
    """Barèmes des primes et signataires des documents de paie."""

    class Meta:
        model = ParametrePaie
        fields = [
            'jours_ouvrables',
            'taux_anciennete_par_an', 'taux_eloignement_par_km',
            'prime_craie_par_eleve', 'prime_par_heure_revision',
            'prime_professeur_principal', 'retenue_par_jour_chome',
            'signataire_1_titre', 'signataire_1_nom',
            'signataire_2_titre', 'signataire_2_nom',
            'signataire_3_titre', 'signataire_3_nom',
            'lieu_signature',
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.setdefault('class', 'form-control')


class AvanceSalaireForm(forms.ModelForm):
    montant = MontantGNFField(
        min_value=1,
        max_digits=12,
        decimal_places=2,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'inputmode': 'decimal',
            'placeholder': 'Ex. 500 000',
        }),
        label="Montant de l'avance (GNF)",
    )

    class Meta:
        model = AvanceSalaire
        fields = [
            'enseignant',
            'periode_prevue',
            'date_avance',
            'montant',
            'reference_externe',
            'motif',
        ]
        widgets = {
            'enseignant': forms.Select(attrs={'class': 'form-select'}),
            'periode_prevue': forms.Select(attrs={'class': 'form-select'}),
            'date_avance': forms.DateInput(attrs={
                'class': 'form-control', 'type': 'date'
            }, format='%Y-%m-%d'),
            'reference_externe': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Numéro de reçu ou référence (facultatif)',
            }),
            'motif': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': "Motif obligatoire de l'avance",
            }),
        }

    def __init__(self, *args, ecole=None, enseignant=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['date_avance'].input_formats = ['%Y-%m-%d', '%d/%m/%Y']

        enseignant_cible = enseignant
        if enseignant_cible is None and self.instance and self.instance.pk:
            enseignant_cible = self.instance.enseignant

        enseignants = Enseignant.objects.filter(statut='ACTIF').select_related('ecole')
        periodes = PeriodeSalaire.objects.filter(cloturee=False).select_related('ecole')
        if enseignant_cible is not None:
            enseignants = Enseignant.objects.filter(pk=enseignant_cible.pk)
            periodes = periodes.filter(ecole=enseignant_cible.ecole)
            self.fields['enseignant'].initial = enseignant_cible
        elif ecole is not None:
            enseignants = enseignants.filter(ecole=ecole)
            periodes = periodes.filter(ecole=ecole)

        self.fields['enseignant'].queryset = enseignants.order_by('nom', 'prenoms')
        self.fields['periode_prevue'].queryset = periodes.order_by('-annee', '-mois')

    def clean_motif(self):
        motif = (self.cleaned_data.get('motif') or '').strip()
        if len(motif) < 3:
            raise ValidationError("Précisez le motif de l'avance.")
        return motif


class CalendrierPeriodeForm(forms.ModelForm):
    """Nombre de lundis ... samedis réellement travaillés dans le mois."""

    class Meta:
        model = PeriodeSalaire
        fields = CHAMPS_OCCURRENCES_JOURS
        labels = {
            f'nb_{jour}s': libelle for jour, _, libelle in JOURS_SEMAINE_PAIE
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        calendrier = self.instance.occurrences_calendrier()
        for index, champ in enumerate(CHAMPS_OCCURRENCES_JOURS):
            self.fields[champ].required = False
            self.fields[champ].widget.attrs.update({
                'class': 'form-control', 'min': '0', 'max': '6',
                'placeholder': str(calendrier[index]),
            })
            self.fields[champ].help_text = f"Calendrier : {calendrier[index]}"
