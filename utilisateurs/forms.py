from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.password_validation import validate_password
from django.contrib.auth.models import User
from django.core.validators import RegexValidator
from django.core.exceptions import ValidationError
from django.db import transaction
import re

from .models import MENUS, Profil
from eleves.models import Ecole


class ComptableCreationForm(UserCreationForm):
    """Formulaire de création d'un utilisateur Comptable avec son Profil."""

    # Champs User supplémentaires
    first_name = forms.CharField(label="Prénom", max_length=150, required=False)
    last_name = forms.CharField(label="Nom", max_length=150, required=False)
    email = forms.EmailField(label="Email", required=False)

    # Champs Profil
    telephone = forms.CharField(
        label="Téléphone",
        max_length=20,
        validators=[RegexValidator(r'^\+224\d{8,9}$', 'Format attendu: +224XXXXXXXXX')],
    )
    ecole = forms.ModelChoiceField(
        label="École",
        queryset=Ecole.objects.all(),
        required=True,
        help_text="Sélectionnez l'école du comptable",
        widget=forms.Select(attrs={
            'class': 'form-select',
        }),
    )

    # Permissions spécifiques existantes
    peut_valider_paiements = forms.BooleanField(label="Peut valider les paiements", required=False, initial=True)
    peut_valider_depenses = forms.BooleanField(label="Peut valider les dépenses", required=False, initial=False)
    peut_generer_rapports = forms.BooleanField(label="Peut générer des rapports", required=False, initial=True)
    peut_gerer_utilisateurs = forms.BooleanField(label="Peut gérer les utilisateurs", required=False, initial=False)
    
    # Nouvelles permissions granulaires
    peut_ajouter_paiements = forms.BooleanField(
        label="Peut ajouter des paiements", 
        required=False, 
        initial=False,  # Par défaut, les comptables ne peuvent PAS ajouter de paiements
        help_text="Autoriser l'ajout de nouveaux paiements"
    )
    peut_ajouter_depenses = forms.BooleanField(
        label="Peut ajouter des dépenses", 
        required=False, 
        initial=False,  # Par défaut, les comptables ne peuvent PAS ajouter de dépenses
        help_text="Autoriser l'ajout de nouvelles dépenses"
    )
    peut_ajouter_enseignants = forms.BooleanField(
        label="Peut ajouter des enseignants", 
        required=False, 
        initial=False,  # Par défaut, les comptables ne peuvent PAS ajouter d'enseignants
        help_text="Autoriser l'ajout de nouveaux enseignants"
    )
    peut_modifier_paiements = forms.BooleanField(
        label="Peut modifier les paiements", 
        required=False, 
        initial=True,
        help_text="Autoriser la modification des paiements existants"
    )
    peut_modifier_depenses = forms.BooleanField(
        label="Peut modifier les dépenses", 
        required=False, 
        initial=True,
        help_text="Autoriser la modification des dépenses existantes"
    )
    peut_supprimer_paiements = forms.BooleanField(
        label="Peut supprimer les paiements", 
        required=False, 
        initial=False,
        help_text="Autoriser la suppression des paiements"
    )
    peut_supprimer_depenses = forms.BooleanField(
        label="Peut supprimer les dépenses", 
        required=False, 
        initial=False,
        help_text="Autoriser la suppression des dépenses"
    )
    peut_consulter_rapports = forms.BooleanField(
        label="Peut consulter les rapports", 
        required=False, 
        initial=True,
        help_text="Autoriser la consultation des rapports"
    )

    class Meta(UserCreationForm.Meta):
        model = User
        # Ne lister ici que les champs du modèle User
        fields = (
            'username', 'first_name', 'last_name', 'email',
            'password1', 'password2',
        )

    def __init__(self, *args, **kwargs):
        request = kwargs.pop('request', None)
        super().__init__(*args, **kwargs)
        # Ordonner les écoles par nom si le champ existe
        all_ecoles = Ecole.objects.all()
        try:
            all_ecoles = all_ecoles.order_by('nom')
        except Exception:
            pass
        # Si non-superuser, restreindre à l'école de l'utilisateur
        if request and request.user.is_authenticated and not request.user.is_superuser:
            profil = getattr(request.user, 'profil', None)
            if profil and profil.ecole_id:
                self.fields['ecole'].queryset = all_ecoles.filter(pk=profil.ecole_id)
                self.fields['ecole'].initial = profil.ecole_id
            else:
                # Aucun profil/école: ne proposer aucune école pour éviter fuite
                self.fields['ecole'].queryset = all_ecoles.none()
        else:
            self.fields['ecole'].queryset = all_ecoles
        # Placeholder explicite pour la liste déroulante
        self.fields['ecole'].empty_label = "--------- Sélectionnez une école ---------"
        # Harmoniser un minimum le rendu Bootstrap
        text_like = ['username', 'first_name', 'last_name', 'email', 'telephone']
        for name in text_like:
            if name in self.fields and not isinstance(self.fields[name].widget, forms.CheckboxInput):
                css = self.fields[name].widget.attrs.get('class', '')
                self.fields[name].widget.attrs['class'] = (css + ' form-control').strip()

    @transaction.atomic
    def save(self, commit=True):
        # Crée l'utilisateur
        user = super().save(commit=False)
        user.first_name = self.cleaned_data.get('first_name', '')
        user.last_name = self.cleaned_data.get('last_name', '')
        user.email = self.cleaned_data.get('email', '')
        user.is_active = True
        if commit:
            user.save()
        # Crée le profil lié avec toutes les permissions (éviter les doublons)
        profil, created = Profil.objects.get_or_create(
            user=user,
            defaults={
                'role': 'COMPTABLE',
                'telephone': self.cleaned_data['telephone'],
                'ecole': self.cleaned_data.get('ecole'),
                # Permissions existantes
                'peut_valider_paiements': self.cleaned_data.get('peut_valider_paiements', False),
                'peut_valider_depenses': self.cleaned_data.get('peut_valider_depenses', False),
                'peut_generer_rapports': self.cleaned_data.get('peut_generer_rapports', False),
                'peut_gerer_utilisateurs': self.cleaned_data.get('peut_gerer_utilisateurs', False),
                # Nouvelles permissions granulaires
                'peut_ajouter_paiements': self.cleaned_data.get('peut_ajouter_paiements', False),
                'peut_ajouter_depenses': self.cleaned_data.get('peut_ajouter_depenses', False),
                'peut_ajouter_enseignants': self.cleaned_data.get('peut_ajouter_enseignants', False),
                'peut_modifier_paiements': self.cleaned_data.get('peut_modifier_paiements', True),
                'peut_modifier_depenses': self.cleaned_data.get('peut_modifier_depenses', True),
                'peut_supprimer_paiements': self.cleaned_data.get('peut_supprimer_paiements', False),
                'peut_supprimer_depenses': self.cleaned_data.get('peut_supprimer_depenses', False),
                'peut_consulter_rapports': self.cleaned_data.get('peut_consulter_rapports', True),
                # Validation immédiate pour les comptes créés par un administrateur
                'is_validated': True,
                'actif': True,
            }
        )
        # Si le profil existait déjà, on s'assure qu'il est validé et actif
        if not created:
            changed = False
            if not profil.is_validated:
                profil.is_validated = True
                changed = True
            if not profil.actif:
                profil.actif = True
                changed = True
            # Toujours mettre à jour l'école si fournie
            ecole = self.cleaned_data.get('ecole')
            if ecole and profil.ecole != ecole:
                profil.ecole = ecole
                changed = True
            if changed:
                profil.save()
        return user


SOUS_UTILISATEUR_ROLES = [
    ('COMPTABLE', 'Comptable'),
    ('SECRETAIRE', 'Secrétaire'),
    ('ENSEIGNANT', 'Enseignant'),
    ('SURVEILLANT', 'Surveillant'),
]

SOUS_UTILISATEUR_PERMISSIONS = [
    ('peut_ajouter_paiements', 'Ajouter des paiements'),
    ('peut_modifier_paiements', 'Modifier des paiements'),
    ('peut_valider_paiements', 'Valider des paiements'),
    ('peut_ajouter_depenses', 'Ajouter des dépenses'),
    ('peut_modifier_depenses', 'Modifier des dépenses'),
    ('peut_valider_depenses', 'Valider des dépenses'),
    ('peut_ajouter_enseignants', 'Ajouter des enseignants'),
    ('peut_generer_rapports', 'Générer des rapports'),
    ('peut_consulter_rapports', 'Consulter les rapports'),
    ('peut_gerer_notes', 'Gérer les notes et matières'),
    ('peut_gerer_classes', 'Créer et modifier les classes'),
    ('peut_gerer_grilles_tarifaires', 'Gérer les grilles tarifaires'),
]


def _configurer_champs_sous_utilisateur(form):
    for field_name in ('username', 'first_name', 'last_name', 'email', 'telephone', 'nouveau_mot_de_passe'):
        if field_name in form.fields:
            css = form.fields[field_name].widget.attrs.get('class', '')
            form.fields[field_name].widget.attrs['class'] = (css + ' form-control').strip()
    if 'role' in form.fields:
        form.fields['role'].widget.attrs['class'] = 'form-select'
    for field_name, label in SOUS_UTILISATEUR_PERMISSIONS:
        form.fields[field_name] = forms.BooleanField(label=label, required=False)


class SousUtilisateurCreationForm(UserCreationForm):
    first_name = forms.CharField(label="Prénom", max_length=150, required=False)
    last_name = forms.CharField(label="Nom", max_length=150, required=False)
    email = forms.EmailField(label="Email", required=False)
    telephone = forms.CharField(
        label="Téléphone",
        max_length=20,
        validators=[RegexValidator(r'^\+224\d{8,9}$', 'Format attendu: +224XXXXXXXXX')],
    )
    role = forms.ChoiceField(label="Fonction", choices=SOUS_UTILISATEUR_ROLES)
    allowed_menus = forms.MultipleChoiceField(
        label="Menus visibles",
        choices=MENUS,
        required=False,
        widget=forms.CheckboxSelectMultiple,
        help_text="Si aucun menu n'est coché, le sous-utilisateur verra uniquement son compte.",
    )
    lecture_seule = forms.BooleanField(label="Lecture seule", required=False)

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ('username', 'first_name', 'last_name', 'email', 'password1', 'password2')

    def __init__(self, *args, principal_profil, **kwargs):
        self.principal_profil = principal_profil
        super().__init__(*args, **kwargs)
        _configurer_champs_sous_utilisateur(self)
        for field_name in ('password1', 'password2'):
            self.fields[field_name].widget.attrs['class'] = 'form-control'

    def clean_username(self):
        username = (self.cleaned_data.get('username') or '').strip()
        if User.objects.filter(username__iexact=username).exists():
            raise ValidationError("Ce nom d'utilisateur existe déjà.")
        return username

    @property
    def action_permission_fields(self):
        return [self[name] for name, _label in SOUS_UTILISATEUR_PERMISSIONS]

    @transaction.atomic
    def save(self, commit=True):
        user = super().save(commit=False)
        user.first_name = self.cleaned_data.get('first_name', '')
        user.last_name = self.cleaned_data.get('last_name', '')
        user.email = self.cleaned_data.get('email', '')
        user.is_active = True
        user.is_staff = False
        if commit:
            user.save()

        profil, _created = Profil.objects.get_or_create(user=user)
        profil.role = self.cleaned_data['role']
        profil.telephone = self.cleaned_data['telephone']
        profil.ecole = self.principal_profil.ecole
        profil.compte_principal = self.principal_profil
        profil.est_compte_principal = False
        profil.allowed_menus = list(self.cleaned_data.get('allowed_menus') or [])
        profil.lecture_seule = self.cleaned_data.get('lecture_seule', False)
        profil.peut_gerer_utilisateurs = False
        profil.is_validated = True
        profil.actif = True
        for field_name, _label in SOUS_UTILISATEUR_PERMISSIONS:
            setattr(profil, field_name, self.cleaned_data.get(field_name, False))
        profil.save()
        return user


class SousUtilisateurModificationForm(forms.Form):
    username = forms.CharField(label="Nom d'utilisateur", max_length=150)
    first_name = forms.CharField(label="Prénom", max_length=150, required=False)
    last_name = forms.CharField(label="Nom", max_length=150, required=False)
    email = forms.EmailField(label="Email", required=False)
    telephone = forms.CharField(
        label="Téléphone",
        max_length=20,
        validators=[RegexValidator(r'^\+224\d{8,9}$', 'Format attendu: +224XXXXXXXXX')],
    )
    role = forms.ChoiceField(label="Fonction", choices=SOUS_UTILISATEUR_ROLES)
    allowed_menus = forms.MultipleChoiceField(
        label="Menus visibles",
        choices=MENUS,
        required=False,
        widget=forms.CheckboxSelectMultiple,
    )
    nouveau_mot_de_passe = forms.CharField(
        label="Nouveau mot de passe (facultatif)",
        required=False,
        min_length=12,
        widget=forms.PasswordInput,
        help_text="Laissez vide pour conserver le mot de passe actuel.",
    )
    actif = forms.BooleanField(label="Compte actif", required=False)
    lecture_seule = forms.BooleanField(label="Lecture seule", required=False)

    def __init__(self, *args, profil, **kwargs):
        self.profil = profil
        user = profil.user
        initial = kwargs.setdefault('initial', {})
        initial.update({
            'username': user.username,
            'first_name': user.first_name,
            'last_name': user.last_name,
            'email': user.email,
            'telephone': profil.telephone,
            'role': profil.role,
            'allowed_menus': profil.allowed_menus,
            'actif': user.is_active and profil.actif,
            'lecture_seule': profil.lecture_seule,
        })
        for field_name, _label in SOUS_UTILISATEUR_PERMISSIONS:
            initial[field_name] = getattr(profil, field_name, False)
        super().__init__(*args, **kwargs)
        _configurer_champs_sous_utilisateur(self)

    def clean_username(self):
        username = (self.cleaned_data.get('username') or '').strip()
        if User.objects.filter(username__iexact=username).exclude(pk=self.profil.user_id).exists():
            raise ValidationError("Ce nom d'utilisateur existe déjà.")
        return username

    def clean_nouveau_mot_de_passe(self):
        password = self.cleaned_data.get('nouveau_mot_de_passe') or ''
        if password:
            validate_password(password, user=self.profil.user)
        return password

    @property
    def action_permission_fields(self):
        return [self[name] for name, _label in SOUS_UTILISATEUR_PERMISSIONS]

    @transaction.atomic
    def save(self):
        user = self.profil.user
        user.username = self.cleaned_data['username']
        user.first_name = self.cleaned_data.get('first_name', '')
        user.last_name = self.cleaned_data.get('last_name', '')
        user.email = self.cleaned_data.get('email', '')
        user.is_active = self.cleaned_data.get('actif', False)
        password = self.cleaned_data.get('nouveau_mot_de_passe')
        if password:
            user.set_password(password)
        user.save()

        self.profil.role = self.cleaned_data['role']
        self.profil.telephone = self.cleaned_data['telephone']
        self.profil.allowed_menus = list(self.cleaned_data.get('allowed_menus') or [])
        self.profil.lecture_seule = self.cleaned_data.get('lecture_seule', False)
        self.profil.actif = user.is_active
        for field_name, _label in SOUS_UTILISATEUR_PERMISSIONS:
            setattr(self.profil, field_name, self.cleaned_data.get(field_name, False))
        self.profil.save()
        return user


class SignupInlineForm(UserCreationForm):
    """Formulaire d'inscription minimal (nom d'utilisateur + mot de passe) pour usage intégré.

    Utilisé lorsque l'utilisateur n'est pas connecté sur la page 'Créer une École'.
    """

    # Email optionnel
    email = forms.EmailField(required=False, label="Email (optionnel)")

    # Champ honeypot anti-bot (optionnel) — ne doit PAS être rempli par un humain
    website = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'autocomplete': 'off'}),
        help_text="",
        label=""
    )

    class Meta(UserCreationForm.Meta):
        model = User
        fields = (
            'username', 'email', 'password1', 'password2'
        )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Placeholders et classes pour un rendu propre
        self.fields['username'].widget.attrs.update({
            'placeholder': "Nom d'utilisateur (ex: myschool123)",
            'class': (self.fields['username'].widget.attrs.get('class', '') + ' form-control').strip(),
            'autocomplete': 'username'
        })
        self.fields['password1'].widget.attrs.update({
            'placeholder': 'Mot de passe (min 8, lettres + chiffres)',
            'class': (self.fields['password1'].widget.attrs.get('class', '') + ' form-control').strip(),
            'autocomplete': 'new-password'
        })
        self.fields['password2'].widget.attrs.update({
            'placeholder': 'Confirmer le mot de passe',
            'class': (self.fields['password2'].widget.attrs.get('class', '') + ' form-control').strip(),
            'autocomplete': 'new-password'
        })
        self.fields['email'].widget.attrs.update({
            'placeholder': 'ex: nom@domaine.com',
            'class': (self.fields['email'].widget.attrs.get('class', '') + ' form-control').strip(),
            'autocomplete': 'email'
        })
        # Masquer le champ honeypot visuellement
        self.fields['website'].widget.attrs.update({'style': 'display:none'})

        # Aide texte sur la politique MDP (affichage UI)
        self.fields['password1'].help_text = "Au moins 8 caractères, avec au moins 1 lettre et 1 chiffre."

    def clean_username(self):
        username = (self.cleaned_data.get('username') or '').strip()
        if not (4 <= len(username) <= 150):
            raise ValidationError("Le nom d'utilisateur doit contenir entre 4 et 150 caractères.")
        if not re.match(r'^[A-Za-z][A-Za-z0-9_\.\-]+$', username):
            raise ValidationError("Utilisez uniquement lettres, chiffres, point, tiret ou underscore, et commencez par une lettre.")
        # Unicité
        if User.objects.filter(username__iexact=username).exists():
            raise ValidationError("Ce nom d'utilisateur est déjà pris.")
        return username

    def clean_password2(self):
        pwd1 = self.cleaned_data.get('password1') or ''
        pwd2 = self.cleaned_data.get('password2') or ''
        if pwd1 != pwd2:
            raise ValidationError("Les mots de passe ne correspondent pas.")
        if len(pwd1) < 8:
            raise ValidationError("Le mot de passe doit contenir au moins 8 caractères.")
        if not re.search(r'[A-Za-z]', pwd1) or not re.search(r'\d', pwd1):
            raise ValidationError("Le mot de passe doit contenir au moins une lettre et un chiffre.")
        return pwd2

    def clean_website(self):
        # Honeypot: si rempli, considérer comme bot
        if (self.cleaned_data.get('website') or '').strip():
            raise ValidationError("Requête invalide.")
        return ''
