"""Outils communs pour la corbeille des élèves et la corbeille mémoire.

Deux mécanismes complémentaires :

* ``mettre_eleve_en_corbeille`` : archive un instantané complet de l'élève
  (identité, responsables, paiements, abonnements, échéancier, historique)
  avant de le supprimer de la base active. ``restaurer_eleve`` recrée l'élève
  et ses données à partir de cet instantané.
* ``enregistrer_modification`` : journalise le détail (avant / après) d'un
  changement sur n'importe quel objet du système.
"""

import threading
from contextlib import contextmanager
from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from django.db import models, transaction
from django.utils import timezone

from .models import CorbeilleElement, CorbeilleEleve, JournalModification


# ── Neutralisation ponctuelle du journal ─────────────────────────────────────
_etat_journal = threading.local()


def journal_est_suspendu():
    return bool(getattr(_etat_journal, 'suspendu', False))


@contextmanager
def suspendre_journal():
    """Suspend la journalisation automatique (suppressions en cascade massives).

    Utile lorsque l'opération est déjà tracée globalement : archiver un élève
    dans la corbeille ou supprimer une école produirait sinon des milliers
    d'entrées sans valeur ajoutée.
    """
    precedent = journal_est_suspendu()
    _etat_journal.suspendu = True
    try:
        yield
    finally:
        _etat_journal.suspendu = precedent


# ── Sérialisation ────────────────────────────────────────────────────────────

def valeur_json(valeur):
    """Convertit une valeur de champ en quelque chose de stockable en JSON."""
    if valeur is None or isinstance(valeur, (bool, int, float, str)):
        return valeur
    if isinstance(valeur, Decimal):
        return str(valeur)
    if isinstance(valeur, (datetime, date)):
        return valeur.isoformat()
    if isinstance(valeur, UUID):
        return str(valeur)
    if isinstance(valeur, models.Model):
        return valeur.pk
    if hasattr(valeur, 'name'):  # FieldFile
        return valeur.name or ''
    return str(valeur)


CHAMPS_TECHNIQUES = {
    'sync_uuid', 'sync_created_at', 'sync_updated_at', 'sync_deleted_at',
    'sync_version', 'is_synced',
}


def capturer_etat(instance, champs=None):
    """Retourne un dict {champ: valeur} sérialisable pour l'instance donnée."""
    etat = {}
    for field in instance._meta.concrete_fields:
        if field.name in CHAMPS_TECHNIQUES:
            continue
        if champs is not None and field.name not in champs:
            continue
        nom = field.attname if isinstance(field, models.ForeignKey) else field.name
        etat[nom] = valeur_json(getattr(instance, nom, None))
    return etat


def coercer_valeurs(modele, donnees):
    """Reconvertit un instantané JSON vers les types attendus par le modèle.

    L'instantané stocke les décimaux et les dates sous forme de texte ; sans
    cette conversion, l'objet recréé porterait des chaînes et son ``__str__``
    (qui formate souvent des montants) échouerait.
    """
    valeurs = {}
    for nom, valeur in donnees.items():
        if valeur is None:
            valeurs[nom] = None
            continue
        try:
            field = modele._meta.get_field(nom[:-3] if nom.endswith('_id') else nom)
        except Exception:
            valeurs[nom] = valeur
            continue
        if nom.endswith('_id') and isinstance(field, models.ForeignKey):
            valeurs[nom] = valeur
            continue
        try:
            valeurs[nom] = field.to_python(valeur)
        except Exception:
            valeurs[nom] = valeur
    return valeurs


def comparer_etats(avant, apres):
    """Retourne {champ: {'avant': x, 'apres': y}} pour les champs modifiés."""
    changements = {}
    for champ in set(avant) | set(apres):
        val_avant = avant.get(champ)
        val_apres = apres.get(champ)
        if val_avant != val_apres:
            changements[champ] = {'avant': val_avant, 'apres': val_apres}
    return changements


# ── Corbeille mémoire des modifications ──────────────────────────────────────

def enregistrer_modification(instance, changements, utilisateur=None, request=None,
                             action=JournalModification.ACTION_MODIFICATION,
                             commentaire=''):
    """Journalise un changement. Ne lève jamais d'exception."""
    if journal_est_suspendu():
        return None
    if action == JournalModification.ACTION_MODIFICATION and not changements:
        return None
    try:
        if utilisateur is None and request is not None:
            utilisateur = getattr(request, 'user', None)
        if utilisateur is not None and not getattr(utilisateur, 'is_authenticated', False):
            utilisateur = None
        return JournalModification.objects.create(
            app_label=instance._meta.app_label,
            model_name=instance._meta.object_name,
            objet_id=getattr(instance, 'pk', None),
            objet_repr=str(instance)[:255],
            action=action,
            changements=changements or {},
            commentaire=commentaire,
            utilisateur=utilisateur,
            ip_address=(request.META.get('REMOTE_ADDR') if request else None) or None,
        )
    except Exception:
        return None


class SuiviModification:
    """Context manager qui journalise automatiquement les champs modifiés.

    Utilisation ::

        with SuiviModification(paiement, request, "Correction d'un oubli"):
            form.save()
    """

    def __init__(self, instance, request=None, commentaire='', champs=None):
        self.instance = instance
        self.request = request
        self.commentaire = commentaire
        self.champs = champs
        self.avant = {}

    def __enter__(self):
        self.avant = capturer_etat(self.instance, self.champs)
        return self

    def __exit__(self, exc_type, exc, tb):
        if exc_type is not None:
            return False
        try:
            self.instance.refresh_from_db()
        except Exception:
            pass
        apres = capturer_etat(self.instance, self.champs)
        enregistrer_modification(
            self.instance,
            comparer_etats(self.avant, apres),
            request=self.request,
            commentaire=self.commentaire,
        )
        return False


# ── Corbeille générique (paiements, échéanciers, abonnements, ...) ───────────

# Lignes filles à archiver avec l'objet principal, par modèle.
RELATIONS_CORBEILLE = {
    'paiements.Paiement': ['remises'],
    'paiements.EcheancierPaiement': [],
    'paiements.RemiseReduction': ['paiementremise_set'],
    'bus.AbonnementBus': [],
    'bus.AbonnementCantine': [],
    'eleves.Responsable': [],
}


def _contexte_objet(instance):
    """Décrit à quel élève / à quelle école se rattache l'objet supprimé."""
    eleve = getattr(instance, 'eleve', None)
    if eleve is not None:
        classe = getattr(eleve, 'classe', None)
        ecole = getattr(classe, 'ecole', None)
        contexte = f"{eleve.prenom} {eleve.nom} ({eleve.matricule})"
        return contexte, getattr(ecole, 'nom', '') or ''

    ecole = getattr(instance, 'ecole', None)
    if ecole is not None:
        return '', getattr(ecole, 'nom', '') or ''
    return '', ''


def construire_snapshot_objet(instance):
    """Instantané d'un objet et de ses lignes filles déclarées."""
    label = f'{instance._meta.app_label}.{instance._meta.object_name}'
    donnees = {'principal': capturer_etat(instance), 'relations': {}}

    for accesseur in RELATIONS_CORBEILLE.get(label, []):
        manager = getattr(instance, accesseur, None)
        if manager is None:
            continue
        try:
            lignes = list(manager.all())
        except Exception:
            continue
        if not lignes:
            continue
        cle = f'{lignes[0]._meta.app_label}.{lignes[0]._meta.object_name}'
        donnees['relations'].setdefault(cle, []).extend(
            capturer_etat(ligne) for ligne in lignes
        )

    return donnees


@transaction.atomic
def mettre_en_corbeille(instance, utilisateur=None, request=None, motif=''):
    """Archive un objet puis le supprime. Retourne l'entrée de corbeille."""
    if utilisateur is None and request is not None:
        utilisateur = getattr(request, 'user', None)
    if utilisateur is not None and not getattr(utilisateur, 'is_authenticated', False):
        utilisateur = None

    opts = instance._meta
    contexte, ecole_nom = _contexte_objet(instance)

    entree = CorbeilleElement.objects.create(
        app_label=opts.app_label,
        model_name=opts.object_name,
        modele_libelle=str(opts.verbose_name).capitalize(),
        objet_id_origine=instance.pk,
        objet_repr=str(instance)[:255],
        contexte=contexte[:255],
        ecole_nom=ecole_nom[:200],
        donnees=construire_snapshot_objet(instance),
        motif=motif,
        supprime_par=utilisateur,
    )

    enregistrer_modification(
        instance, {}, utilisateur=utilisateur, request=request,
        action=JournalModification.ACTION_SUPPRESSION,
        commentaire=motif or f"Mise à la corbeille de {instance}",
    )

    with suspendre_journal():
        instance.delete()

    return entree


@transaction.atomic
def restaurer_element(entree, utilisateur=None, request=None):
    """Recrée un objet archivé dans la corbeille générique.

    Retourne (objet, message). Lève ValueError si la restauration échoue.
    """
    from django.apps import apps

    if entree.restaure:
        raise ValueError("Cet élément a déjà été restauré.")

    modele = apps.get_model(entree.app_label, entree.model_name)
    donnees = entree.donnees or {}
    principal = dict(donnees.get('principal') or {})
    if not principal:
        raise ValueError("L'instantané de cet élément est vide : restauration impossible.")

    principal.pop('id', None)
    principal.pop('date_creation', None)
    principal.pop('date_modification', None)
    principal.pop('created_at', None)
    principal.pop('updated_at', None)

    with suspendre_journal():
        try:
            objet = modele.objects.create(**coercer_valeurs(modele, principal))
        except Exception as exc:
            raise ValueError(
                f"Impossible de recréer cet élément : {exc}. "
                "L'objet parent (élève, classe...) a peut-être été supprimé."
            )

        nb_lignes = 0
        for cle, lignes in (donnees.get('relations') or {}).items():
            try:
                modele_lie = apps.get_model(*cle.split('.'))
            except Exception:
                continue
            champ_parent = None
            for field in modele_lie._meta.fields:
                if getattr(field, 'related_model', None) is modele:
                    champ_parent = field.attname
                    break
            if champ_parent is None:
                continue
            nb_lignes += _restaurer_lignes(modele_lie, lignes, {champ_parent: objet.pk})

    if utilisateur is None and request is not None:
        utilisateur = getattr(request, 'user', None)
    if utilisateur is not None and not getattr(utilisateur, 'is_authenticated', False):
        utilisateur = None

    entree.restaure = True
    entree.date_restauration = timezone.now()
    entree.restaure_par = utilisateur
    entree.save(update_fields=['restaure', 'date_restauration', 'restaure_par'])

    enregistrer_modification(
        objet, {}, utilisateur=utilisateur, request=request,
        action=JournalModification.ACTION_RESTAURATION,
        commentaire=f"Restauration depuis la corbeille (élément #{entree.pk})",
    )

    complement = f" ({nb_lignes} ligne(s) liée(s))" if nb_lignes else ""
    return objet, f"{entree.modele_libelle or entree.model_name} « {objet} » restauré{complement}."


# ── Corbeille des élèves ─────────────────────────────────────────────────────

def _snapshot_responsable(responsable):
    if responsable is None:
        return None
    return capturer_etat(responsable)


def construire_snapshot_eleve(eleve):
    """Construit l'instantané complet d'un élève et de ses données liées."""
    donnees = {
        'eleve': capturer_etat(eleve),
        'classe': {
            'id': eleve.classe_id,
            'nom': getattr(eleve.classe, 'nom', ''),
            'niveau': getattr(eleve.classe, 'niveau', ''),
            'annee_scolaire': getattr(eleve.classe, 'annee_scolaire', ''),
            'ecole_id': getattr(eleve.classe, 'ecole_id', None),
            'ecole_nom': getattr(getattr(eleve.classe, 'ecole', None), 'nom', ''),
        },
        'responsable_principal': _snapshot_responsable(eleve.responsable_principal),
        'responsable_secondaire': _snapshot_responsable(eleve.responsable_secondaire),
        'paiements': [],
        'abonnements_bus': [],
        'abonnements_cantine': [],
        'echeancier': None,
        'historique': [],
    }

    for paiement in eleve.paiements.all():
        donnees['paiements'].append(capturer_etat(paiement))

    for abo in eleve.abonnements_bus.all():
        donnees['abonnements_bus'].append(capturer_etat(abo))

    for abo in eleve.abonnements_cantine.all():
        donnees['abonnements_cantine'].append(capturer_etat(abo))

    echeancier = getattr(eleve, 'echeancier', None)
    if echeancier is not None:
        donnees['echeancier'] = capturer_etat(echeancier)

    for item in eleve.historique.all()[:200]:
        donnees['historique'].append({
            'action': item.action,
            'description': item.description,
            'date_action': valeur_json(item.date_action),
        })

    return donnees


@transaction.atomic
def mettre_eleve_en_corbeille(eleve, utilisateur=None, request=None, motif=''):
    """Archive l'élève dans la corbeille puis le supprime de la base active."""
    if utilisateur is None and request is not None:
        utilisateur = getattr(request, 'user', None)
    if utilisateur is not None and not getattr(utilisateur, 'is_authenticated', False):
        utilisateur = None

    donnees = construire_snapshot_eleve(eleve)
    classe = eleve.classe

    entree = CorbeilleEleve.objects.create(
        eleve_id_origine=eleve.pk,
        matricule=eleve.matricule,
        nom=eleve.nom,
        prenom=eleve.prenom,
        classe_nom=getattr(classe, 'nom', '') or '',
        ecole_nom=getattr(getattr(classe, 'ecole', None), 'nom', '') or '',
        annee_scolaire=getattr(classe, 'annee_scolaire', '') or '',
        donnees=donnees,
        motif=motif,
        supprime_par=utilisateur,
    )

    enregistrer_modification(
        eleve,
        {},
        utilisateur=utilisateur,
        request=request,
        action=JournalModification.ACTION_SUPPRESSION,
        commentaire=motif or f"Mise à la corbeille de {eleve.prenom} {eleve.nom}",
    )

    # L'instantané ci-dessus rend inutile la journalisation de chaque objet
    # supprimé en cascade (paiements, abonnements, notes, ...).
    with suspendre_journal():
        eleve.delete()
    return entree


def _restaurer_responsable(snapshot):
    """Recrée (ou retrouve) un responsable à partir de son instantané."""
    from eleves.models import Responsable

    if not snapshot:
        return None
    telephone = snapshot.get('telephone')
    if telephone:
        existant = Responsable.objects.filter(telephone=telephone).first()
        if existant:
            return existant
    donnees = {k: v for k, v in snapshot.items() if k != 'id'}
    return Responsable.objects.create(**coercer_valeurs(Responsable, donnees))


def _restaurer_lignes(modele, snapshots, remplacements):
    """Recrée des objets liés en ignorant ceux qui échouent."""
    restaures = 0
    for snapshot in snapshots or []:
        donnees = {k: v for k, v in snapshot.items() if k != 'id'}
        donnees.update(remplacements)
        try:
            modele.objects.create(**coercer_valeurs(modele, donnees))
            restaures += 1
        except Exception:
            continue
    return restaures


@transaction.atomic
def restaurer_eleve(entree, utilisateur=None, request=None):
    """Restaure un élève depuis la corbeille.

    Retourne (eleve, message). Lève ValueError si la restauration est
    impossible (classe disparue, matricule déjà réutilisé, ...).
    """
    from eleves.models import Classe, Eleve
    from bus.models import AbonnementBus, AbonnementCantine
    from paiements.models import EcheancierPaiement, Paiement

    if entree.restaure:
        raise ValueError("Cet élève a déjà été restauré.")

    donnees = entree.donnees or {}
    snapshot_eleve = dict(donnees.get('eleve') or {})
    if not snapshot_eleve:
        raise ValueError("L'instantané de cet élève est vide : restauration impossible.")

    if Eleve.objects.filter(matricule=entree.matricule).exists():
        raise ValueError(
            f"Un élève portant le matricule {entree.matricule} existe déjà : "
            "renommez-le ou supprimez-le avant de restaurer."
        )

    infos_classe = donnees.get('classe') or {}
    classe = None
    if infos_classe.get('id'):
        classe = Classe.objects.filter(pk=infos_classe['id']).first()
    if classe is None and infos_classe.get('nom'):
        classe = Classe.objects.filter(
            nom=infos_classe['nom'],
            annee_scolaire=infos_classe.get('annee_scolaire') or '',
        ).first()
    if classe is None and infos_classe.get('nom'):
        classe = Classe.objects.filter(nom=infos_classe['nom']).first()
    if classe is None:
        raise ValueError(
            f"La classe « {infos_classe.get('nom', '?')} » n'existe plus : "
            "recréez-la avant de restaurer cet élève."
        )

    with suspendre_journal():
        responsable_principal = _restaurer_responsable(donnees.get('responsable_principal'))
        responsable_secondaire = _restaurer_responsable(donnees.get('responsable_secondaire'))

    snapshot_eleve.pop('id', None)
    snapshot_eleve.pop('date_creation', None)
    snapshot_eleve.pop('date_modification', None)
    snapshot_eleve['classe_id'] = classe.pk
    snapshot_eleve['responsable_principal_id'] = responsable_principal.pk if responsable_principal else None
    snapshot_eleve['responsable_secondaire_id'] = responsable_secondaire.pk if responsable_secondaire else None

    with suspendre_journal():
        eleve = Eleve.objects.create(**coercer_valeurs(Eleve, snapshot_eleve))

        nb_paiements = _restaurer_lignes(Paiement, donnees.get('paiements'), {'eleve_id': eleve.pk})
        nb_bus = _restaurer_lignes(AbonnementBus, donnees.get('abonnements_bus'), {'eleve_id': eleve.pk})
        nb_cantine = _restaurer_lignes(AbonnementCantine, donnees.get('abonnements_cantine'), {'eleve_id': eleve.pk})

        if donnees.get('echeancier'):
            _restaurer_lignes(EcheancierPaiement, [donnees['echeancier']], {'eleve_id': eleve.pk})

    if utilisateur is None and request is not None:
        utilisateur = getattr(request, 'user', None)
    if utilisateur is not None and not getattr(utilisateur, 'is_authenticated', False):
        utilisateur = None

    entree.restaure = True
    entree.date_restauration = timezone.now()
    entree.restaure_par = utilisateur
    entree.save(update_fields=['restaure', 'date_restauration', 'restaure_par'])

    enregistrer_modification(
        eleve, {}, utilisateur=utilisateur, request=request,
        action=JournalModification.ACTION_RESTAURATION,
        commentaire=f"Restauration depuis la corbeille (corbeille #{entree.pk})",
    )

    message = (
        f"Élève {eleve.prenom} {eleve.nom} restauré dans la classe {classe.nom} "
        f"({nb_paiements} paiement(s), {nb_bus} abonnement(s) bus, {nb_cantine} abonnement(s) cantine)."
    )
    return eleve, message
