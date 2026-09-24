from django import forms
from django.core.validators import MinValueValidator
from django.db.models import Q
from decimal import Decimal
from datetime import date, datetime
from django.utils import timezone

from .models import Paiement, EcheancierPaiement, TypePaiement, ModePaiement, RemiseReduction, PaiementRemise
from eleves.models import Eleve, Ecole


class MontantGNFField(forms.DecimalField):
    """Montant GNF tolérant espaces, sigle et séparateurs de milliers."""

    ESPACES = ('\u00a0', '\u202f', '\u2009', ' ')

    def to_python(self, value):
        if isinstance(value, str):
            value = self.nettoyer(value)
        return super().to_python(value)

    @classmethod
    def nettoyer(cls, valeur):
        nettoye = str(valeur or '').strip()
        for espace in cls.ESPACES:
            nettoye = nettoye.replace(espace, '')
        for sigle in ('GNF', 'gnf', 'Gnf', 'FG', 'fg'):
            nettoye = nettoye.replace(sigle, '')
        nettoye = nettoye.strip()
        if not nettoye:
            return nettoye

        signe = ''
        if nettoye[0] in '+-':
            signe, nettoye = nettoye[0], nettoye[1:]
        groupes = nettoye.replace(',', '.').split('.')
        if len(groupes) > 1 and all(groupe.isdigit() for groupe in groupes):
            tete, reste = groupes[0], groupes[1:]
            if all(len(groupe) == 3 for groupe in reste):
                nettoye = tete + ''.join(reste)
            elif len(reste) == 1 and reste[0] and set(reste[0]) == {'0'}:
                nettoye = tete
        return signe + nettoye


class PaiementForm(forms.ModelForm):
    """Formulaire pour créer/modifier un paiement"""

    montant = MontantGNFField(
        max_digits=10,
        decimal_places=0,
        min_value=Decimal('1'),
        localize=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'inputmode': 'numeric',
            'autocomplete': 'off',
            'placeholder': 'Montant en GNF',
        }),
        label="Montant (GNF)",
        help_text="Les espaces et le sigle GNF sont acceptés (1 130 500 GNF).",
    )

    # Pourcentage de remise saisi par le comptable (optionnel)
    remise_pourcentage = forms.DecimalField(
        required=False,
        min_value=0,
        max_value=100,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': '0',
            'step': '0.01',
            'min': '0',
            'max': '100'
        }),
        label="Remise (%)"
    )

    class Meta:
        model = Paiement
        fields = [
            'eleve', 'type_paiement', 'mode_paiement', 'montant',
            'date_paiement', 'observations', 'reference_externe', 'frais_revision_inclus'
        ]
        widgets = {
            'frais_revision_inclus': forms.CheckboxInput(attrs={'class': 'form-check-input', 'role': 'switch'}),
            'eleve': forms.Select(attrs={
                'class': 'form-select',
                'data-live-search': 'true'
            }),
            'type_paiement': forms.Select(attrs={
                'class': 'form-select'
            }),
            'mode_paiement': forms.Select(attrs={
                'class': 'form-select'
            }),
            'date_paiement': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'observations': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Observations sur le paiement (optionnel)'
            }),
            'reference_externe': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Référence externe (optionnel)'
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Ordonner les élèves par nom
        self.fields['eleve'].queryset = Eleve.objects.select_related(
            'classe', 'classe__ecole'
        ).filter(statut__in=['ACTIF', 'ATTENTE_PAIEMENT']).order_by('nom', 'prenom')

        # Filtrer les types et modes actifs
        self.fields['type_paiement'].queryset = TypePaiement.objects.filter(actif=True)
        self.fields['mode_paiement'].queryset = ModePaiement.objects.filter(actif=True)

        # Définir la date du jour par défaut si pas de valeur initiale
        if not self.instance.pk and 'date_paiement' not in self.initial:
            # Utiliser la date locale selon le fuseau horaire Django
            self.fields['date_paiement'].initial = timezone.localdate()

        # Révision déjà prise sur un autre paiement : case grisée, valeur postée ignorée.
        self.revision_existante = None
        eleve = self._eleve_connu()
        if eleve is not None:
            from .revisions import annee_revision_eleve, paiement_revision_existant, message_revision_deja_payee
            self.revision_existante = paiement_revision_existant(eleve, annee_revision_eleve(eleve, timezone.localdate()))
            if self.revision_existante:
                champ = self.fields['frais_revision_inclus']
                champ.disabled = True
                champ.initial = False
                champ.help_text = message_revision_deja_payee(self.revision_existante)

    def _eleve_connu(self):
        valeur = self.data.get(self.add_prefix('eleve')) if self.is_bound else (self.initial.get('eleve') or self.fields['eleve'].initial)
        if isinstance(valeur, Eleve):
            return valeur
        try:
            return Eleve.objects.select_related('classe').get(pk=int(valeur)) if valeur else None
        except (Eleve.DoesNotExist, TypeError, ValueError):
            return None

    def clean_montant(self):
        montant = self.cleaned_data.get('montant')
        if montant and montant <= 0:
            raise forms.ValidationError("Le montant doit être supérieur à zéro.")
        return montant

    def clean(self):
        cleaned = super().clean()
        eleve = cleaned.get('eleve')
        if cleaned.get('frais_revision_inclus') and eleve:
            from .revisions import annee_revision_eleve, paiement_revision_existant, message_revision_deja_payee
            existant = paiement_revision_existant(eleve, annee_revision_eleve(eleve, cleaned.get('date_paiement')))
            if existant:
                self.add_error('frais_revision_inclus', message_revision_deja_payee(existant))
        # Validation supplémentaire de la remise (déjà gérée par min/max, mais on force numérique)
        rp = cleaned.get('remise_pourcentage')
        if rp is not None:
            try:
                # DecimalField assure déjà, mais double sécurité
                Decimal(rp)
            except Exception:
                self.add_error('remise_pourcentage', "Valeur de remise invalide.")
        return cleaned

class EcheancierForm(forms.ModelForm):
    """Formulaire pour créer/modifier un échéancier"""

    class Meta:
        model = EcheancierPaiement
        fields = [
            'annee_scolaire', 'frais_inscription_du', 'tranche_1_due',
            'tranche_2_due', 'tranche_3_due', 'date_echeance_inscription',
            'date_echeance_tranche_1', 'date_echeance_tranche_2',
            'date_echeance_tranche_3'
        ]
        widgets = {
            'annee_scolaire': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '2024-2025'
            }),
            'frais_inscription_du': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Montant en GNF',
                'min': '0',
                'step': '1000'
            }),
            'tranche_1_due': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Montant en GNF',
                'min': '0',
                'step': '1000'
            }),
            'tranche_2_due': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Montant en GNF',
                'min': '0',
                'step': '1000'
            }),
            'tranche_3_due': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Montant en GNF',
                'min': '0',
                'step': '1000'
            }),
            'date_echeance_inscription': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'date_echeance_tranche_1': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'date_echeance_tranche_2': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'date_echeance_tranche_3': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Année scolaire par défaut
        if not self.instance.pk and not self.initial.get('annee_scolaire'):
            # Même règle que le moteur de paiement : une réinscription réglée
            # en juillet ou en août ouvre déjà l'année suivante.
            from .payment_engine import school_year_from_date
            self.fields['annee_scolaire'].initial = school_year_from_date(
                date.today()
            )

        # Attacher data-iso aux champs date pour que le fallback JS du template puisse les remplir
        date_fields = [
            'date_echeance_inscription',
            'date_echeance_tranche_1',
            'date_echeance_tranche_2',
            'date_echeance_tranche_3',
        ]
        for f in date_fields:
            try:
                # Valeur initiale potentielle (passée via initial du formulaire)
                val = self.initial.get(f) or self.fields[f].initial
                if val:
                    # S'assurer que le widget a un attribut data-iso exploitable par le template
                    self.fields[f].widget.attrs['data-iso'] = getattr(val, 'isoformat', lambda: str(val))()
            except Exception:
                # En cas d'erreur, on n'empêche pas le rendu du formulaire
                continue

    def clean(self):
        cleaned_data = super().clean()

        # Vérifier que les dates d'échéance sont cohérentes
        date_inscription = cleaned_data.get('date_echeance_inscription')
        date_tranche_1 = cleaned_data.get('date_echeance_tranche_1')
        date_tranche_2 = cleaned_data.get('date_echeance_tranche_2')
        date_tranche_3 = cleaned_data.get('date_echeance_tranche_3')

        dates = [date_inscription, date_tranche_1, date_tranche_2, date_tranche_3]
        dates_valides = [d for d in dates if d is not None]

        if len(dates_valides) > 1:
            dates_triees = sorted(dates_valides)
            if dates_valides != dates_triees:
                raise forms.ValidationError(
                    "Les dates d'échéance doivent être dans l'ordre chronologique."
                )

        return cleaned_data

class RechercheForm(forms.Form):
    """Formulaire de recherche pour les paiements.

    Accepte un paramètre ``user`` optionnel pour restreindre la liste des
    écoles visibles à l'école de l'utilisateur (sécurité multi-tenant).
    """

    STATUT_CHOICES = [('', 'Tous les statuts')] + Paiement.STATUT_CHOICES

    recherche = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Rechercher par nom, matricule, numéro de reçu...'
        })
    )

    statut = forms.ChoiceField(
        choices=STATUT_CHOICES,
        required=False,
        widget=forms.Select(attrs={
            'class': 'form-select'
        })
    )

    type_paiement = forms.ModelChoiceField(
        queryset=TypePaiement.objects.filter(actif=True),
        required=False,
        empty_label="Tous les types",
        widget=forms.Select(attrs={
            'class': 'form-select'
        })
    )

    date_debut = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        })
    )

    date_fin = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        })
    )

    ecole = forms.ModelChoiceField(
        queryset=Ecole.objects.none(),  # Sécurité: vide par défaut, rempli dans __init__
        required=False,
        empty_label="Toutes les écoles",
        widget=forms.Select(attrs={
            'class': 'form-select'
        })
    )

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        if user is not None:
            from utilisateurs.utils import user_is_admin, user_school
            if user_is_admin(user):
                # Les admins voient toutes les écoles
                self.fields['ecole'].queryset = Ecole.objects.all()
            else:
                # Les utilisateurs normaux voient uniquement leur école
                ecole_user = user_school(user)
                if ecole_user:
                    self.fields['ecole'].queryset = Ecole.objects.filter(pk=ecole_user.pk)
                    self.fields['ecole'].initial = ecole_user
                else:
                    self.fields['ecole'].queryset = Ecole.objects.none()
        else:
            # Fallback sécurisé: aucune école visible
            self.fields['ecole'].queryset = Ecole.objects.none()

    def clean(self):
        cleaned_data = super().clean()
        date_debut = cleaned_data.get('date_debut')
        date_fin = cleaned_data.get('date_fin')

        if date_debut and date_fin and date_debut > date_fin:
            raise forms.ValidationError(
                "La date de début doit être antérieure à la date de fin."
            )

        return cleaned_data

class RemiseForm(forms.ModelForm):
    """Formulaire pour créer/modifier une remise"""

    class Meta:
        model = RemiseReduction
        fields = [
            'nom', 'type_remise', 'valeur', 'motif', 'description',
            'date_debut', 'date_fin', 'actif'
        ]
        widgets = {
            'nom': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Nom de la remise'
            }),
            'type_remise': forms.Select(attrs={
                'class': 'form-select'
            }),
            'valeur': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Valeur (% ou montant)',
                'step': '0.01'
            }),
            'motif': forms.Select(attrs={
                'class': 'form-select'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Description de la remise'
            }),
            'date_debut': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'date_fin': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'actif': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
        }

    def clean_valeur(self):
        valeur = self.cleaned_data.get('valeur')
        type_remise = self.cleaned_data.get('type_remise')

        if valeur is not None:
            if type_remise == 'POURCENTAGE' and (valeur < 0 or valeur > 100):
                raise forms.ValidationError(
                    "Le pourcentage doit être entre 0 et 100."
                )
            elif type_remise == 'MONTANT_FIXE' and valeur < 0:
                raise forms.ValidationError(
                    "Le montant fixe doit être positif."
                )

        return valeur

    def clean(self):
        cleaned_data = super().clean()
        date_debut = cleaned_data.get('date_debut')
        date_fin = cleaned_data.get('date_fin')

        if date_debut and date_fin and date_debut > date_fin:
            raise forms.ValidationError(
                "La date de début doit être antérieure à la date de fin."
            )

        return cleaned_data


class PaiementModificationForm(forms.ModelForm):
    """Correction d'un paiement déjà enregistré (erreur ou oubli de saisie).

    L'élève et le numéro de reçu ne sont pas modifiables : corriger l'élève
    reviendrait à créer un autre paiement, et le numéro de reçu a déjà été
    remis à la famille.
    """

    montant = MontantGNFField(
        max_digits=10,
        decimal_places=0,
        min_value=Decimal('1'),
        localize=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'inputmode': 'numeric',
            'autocomplete': 'off',
            'placeholder': 'Ex. : 175000',
        }),
        label="Montant (GNF)",
        help_text="Les espaces et le sigle GNF sont acceptés (175 000 GNF).",
    )

    motif_modification = forms.CharField(
        max_length=255,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': "Ex : montant saisi à l'envers, mauvaise date, mode de paiement oublié…",
        }),
        label="Motif de la modification",
        help_text="Obligatoire : conservé dans la corbeille des modifications.",
    )

    class Meta:
        model = Paiement
        fields = [
            'type_paiement', 'mode_paiement', 'montant',
            'date_paiement', 'reference_externe', 'observations', 'frais_revision_inclus',
        ]
        widgets = {
            'frais_revision_inclus': forms.CheckboxInput(attrs={'class': 'form-check-input', 'role': 'switch'}),
            'type_paiement': forms.Select(attrs={'class': 'form-select'}),
            'mode_paiement': forms.Select(attrs={'class': 'form-select'}),
            'date_paiement': forms.DateInput(attrs={
                'class': 'form-control', 'type': 'date',
            }, format='%Y-%m-%d'),
            'reference_externe': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Référence externe (optionnel)',
            }),
            'observations': forms.Textarea(attrs={
                'class': 'form-control', 'rows': 3,
                'placeholder': 'Observations (optionnel)',
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['type_paiement'].queryset = self._choix_avec_actuel(
            TypePaiement, 'type_paiement_id'
        )
        self.fields['mode_paiement'].queryset = self._choix_avec_actuel(
            ModePaiement, 'mode_paiement_id'
        )
        self.fields['date_paiement'].input_formats = [
            '%Y-%m-%d', '%d/%m/%Y'
        ]
        # La révision portée par un autre reçu ne peut pas être reprise ici.
        self.revision_existante = None
        if self.instance.pk and not self.instance.frais_revision_inclus:
            from .revisions import paiement_revision_existant, message_revision_deja_payee
            self.revision_existante = paiement_revision_existant(
                self.instance.eleve, self.instance.annee_scolaire, exclude_pk=self.instance.pk,
            )
            if self.revision_existante:
                champ = self.fields['frais_revision_inclus']
                champ.disabled = True
                champ.help_text = message_revision_deja_payee(self.revision_existante)

    def _choix_avec_actuel(self, modele, champ_id):
        filtre = Q(actif=True)
        actuel = getattr(self.instance, champ_id, None)
        if actuel:
            filtre |= Q(pk=actuel)
        return modele.objects.filter(filtre)

    def clean_montant(self):
        montant = self.cleaned_data.get('montant')
        if montant is None or montant <= 0:
            raise forms.ValidationError("Le montant doit être supérieur à zéro.")
        return montant

    def clean_date_paiement(self):
        date_paiement = self.cleaned_data.get('date_paiement')
        if date_paiement and date_paiement > timezone.localdate():
            raise forms.ValidationError("La date de paiement ne peut pas être dans le futur.")
        return date_paiement
