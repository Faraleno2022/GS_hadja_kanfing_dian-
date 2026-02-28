"""
Vue pour démarrer une nouvelle année scolaire :
- Duplique les classes (eleves + notes), matières, grilles tarifaires
- Fait passer automatiquement les élèves admis en classe supérieure
"""

import logging
from typing import Optional
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import transaction

from .models import Ecole, Classe, Eleve, HistoriqueEleve
from utilisateurs.utils import user_school, user_is_admin

logger = logging.getLogger(__name__)

# ── Mapping : classe actuelle → classe supérieure (par nom normalisé) ──────────
PROGRESSION_CLASSES = {
    # Maternelle
    'PETITE SECTION':  'MOYENNE SECTION',
    'PS':              'MS',
    'MOYENNE SECTION': 'GRANDE SECTION',
    'MS':              'GS',
    'GRANDE SECTION':  None,   # sortie de maternelle → primaire (manuel)
    'GS':              None,

    # Primaire
    '1ÈRE ANNÉE':  '2ÈME ANNÉE',
    '1ERE ANNEE':  '2EME ANNEE',
    '2ÈME ANNÉE':  '3ÈME ANNÉE',
    '2EME ANNEE':  '3EME ANNEE',
    '3ÈME ANNÉE':  '4ÈME ANNÉE',
    '3EME ANNEE':  '4EME ANNEE',
    '4ÈME ANNÉE':  '5ÈME ANNÉE',
    '4EME ANNEE':  '5EME ANNEE',
    '5ÈME ANNÉE':  '6ÈME ANNÉE',
    '5EME ANNEE':  '6EME ANNEE',
    '6ÈME ANNÉE':  '7ÈME ANNÉE',
    '6EME ANNEE':  '7EME ANNEE',

    # Collège
    '7ÈME ANNÉE':  '8ÈME ANNÉE',
    '7EME ANNEE':  '8EME ANNEE',
    '8ÈME ANNÉE':  '9ÈME ANNÉE',
    '8EME ANNEE':  '9EME ANNEE',
    '9ÈME ANNÉE':  '10ÈME ANNÉE',
    '9EME ANNEE':  '10EME ANNEE',
    '10ÈME ANNÉE': '11ÈME ANNÉE',
    '10EME ANNEE': '11EME ANNEE',

    # Lycée
    '11ÈME ANNÉE': '12ÈME ANNÉE',
    '11EME ANNEE': '12EME ANNEE',
    '12ÈME ANNÉE': 'TERMINALE',
    '12EME ANNEE': 'TERMINALE',
}


def _annee_suivante(annee: str) -> str:
    """Calcule l'année scolaire suivante. Ex: '2024-2025' → '2025-2026'"""
    try:
        debut, fin = annee.split('-')
        return f"{int(debut)+1}-{int(fin)+1}"
    except Exception:
        return annee


def _nom_base(nom_classe: str) -> str:
    """Retourne le radical du nom de classe sans suffixe lettre (A, B, C…).
    Ex: '3ÈME ANNÉE A' → '3ÈME ANNÉE'
    """
    parts = nom_classe.strip().rsplit(' ', 1)
    if len(parts) == 2 and len(parts[1]) == 1 and parts[1].isalpha():
        return parts[0].strip()
    return nom_classe.strip()


def _classe_superieure_nom(nom_classe: str) -> Optional[str]:
    """Retourne le nom de la classe supérieure correspondante ou None."""
    base = _nom_base(nom_classe.upper())
    return PROGRESSION_CLASSES.get(base)


@login_required
def nouvelle_annee_apercu(request):
    """Affiche un aperçu de ce qui sera créé pour la nouvelle année."""
    ecole = user_school(request.user)
    if not ecole:
        messages.error(request, "Aucune école associée à votre compte.")
        return redirect('eleves:liste_eleves')

    # Détecter l'année courante (la plus récente)
    annees = (Classe.objects
              .filter(ecole=ecole)
              .values_list('annee_scolaire', flat=True)
              .distinct()
              .order_by('-annee_scolaire'))
    if not annees:
        messages.warning(request, "Aucune classe trouvée pour cet établissement.")
        return redirect('eleves:gestion_classes')

    annee_courante = annees[0]
    annee_nouvelle = _annee_suivante(annee_courante)

    # Vérifier si la nouvelle année existe déjà
    deja_existante = Classe.objects.filter(ecole=ecole, annee_scolaire=annee_nouvelle).exists()

    classes_actuelles = (Classe.objects
                         .filter(ecole=ecole, annee_scolaire=annee_courante)
                         .prefetch_related('eleves')
                         .order_by('niveau', 'nom'))

    preview_classes = []
    for cls in classes_actuelles:
        sup_nom = _classe_superieure_nom(cls.nom)
        nb_eleves = cls.eleves.filter(statut='ACTIF').count()
        preview_classes.append({
            'classe': cls,
            'nb_eleves': nb_eleves,
            'classe_superieure': sup_nom,
        })

    # Grilles tarifaires courantes
    from .models import GrilleTarifaire
    grilles = GrilleTarifaire.objects.filter(ecole=ecole, annee_scolaire=annee_courante)

    # Classes notes (du module notes)
    from notes.models import ClasseNote, MatiereNote
    classes_notes = ClasseNote.objects.filter(
        ecole=ecole, annee_scolaire=annee_courante, actif=True
    ).prefetch_related('matieres')
    preview_notes = []
    for cn in classes_notes:
        preview_notes.append({
            'classe_note': cn,
            'nb_matieres': cn.matieres.filter(actif=True).count(),
        })

    context = {
        'ecole': ecole,
        'annee_courante': annee_courante,
        'annee_nouvelle': annee_nouvelle,
        'deja_existante': deja_existante,
        'preview_classes': preview_classes,
        'grilles': grilles,
        'preview_notes': preview_notes,
        'nb_total_eleves': sum(p['nb_eleves'] for p in preview_classes),
        'titre_page': f'Nouvelle Année Scolaire {annee_nouvelle}',
    }
    return render(request, 'eleves/nouvelle_annee.html', context)


@login_required
def nouvelle_annee_creer(request):
    """Exécute la création de la nouvelle année scolaire."""
    if request.method != 'POST':
        return redirect('eleves:nouvelle_annee_apercu')

    ecole = user_school(request.user)
    if not ecole:
        messages.error(request, "Aucune école associée à votre compte.")
        return redirect('eleves:liste_eleves')

    annee_courante = request.POST.get('annee_courante', '').strip()
    annee_nouvelle = request.POST.get('annee_nouvelle', '').strip()
    dupliquer_grilles = request.POST.get('dupliquer_grilles') == '1'
    dupliquer_notes_classes = request.POST.get('dupliquer_notes_classes') == '1'
    faire_passer_eleves = request.POST.get('faire_passer_eleves') == '1'

    if not annee_courante or not annee_nouvelle:
        messages.error(request, "Paramètres manquants.")
        return redirect('eleves:nouvelle_annee_apercu')

    resultats = {
        'classes_creees': 0,
        'grilles_creees': 0,
        'classes_notes_creees': 0,
        'matieres_creees': 0,
        'eleves_passes': 0,
        'eleves_conserves': 0,
        'erreurs': [],
    }

    try:
        with transaction.atomic():
            # 1. Dupliquer les classes (eleves.Classe)
            classes_actuelles = Classe.objects.filter(
                ecole=ecole, annee_scolaire=annee_courante
            ).order_by('niveau', 'nom')

            map_anciennes_nouvelles = {}  # ancienne classe → nouvelle classe

            for cls in classes_actuelles:
                nouvelle_cls, created = Classe.objects.get_or_create(
                    ecole=ecole,
                    nom=cls.nom,
                    annee_scolaire=annee_nouvelle,
                    defaults={
                        'niveau': cls.niveau,
                        'capacite_max': cls.capacite_max,
                        'code_matricule': cls.code_matricule,
                    }
                )
                if created:
                    resultats['classes_creees'] += 1
                map_anciennes_nouvelles[cls.pk] = nouvelle_cls

            # 2. Dupliquer les grilles tarifaires
            if dupliquer_grilles:
                from .models import GrilleTarifaire
                grilles = GrilleTarifaire.objects.filter(
                    ecole=ecole, annee_scolaire=annee_courante
                )
                for g in grilles:
                    _, created = GrilleTarifaire.objects.get_or_create(
                        ecole=ecole,
                        niveau=g.niveau,
                        annee_scolaire=annee_nouvelle,
                        defaults={
                            'frais_inscription': g.frais_inscription,
                            'frais_reinscription': g.frais_reinscription,
                            'tranche_1': g.tranche_1,
                            'tranche_2': g.tranche_2,
                            'tranche_3': g.tranche_3,
                            'periode_1': g.periode_1,
                            'periode_2': g.periode_2,
                            'periode_3': g.periode_3,
                        }
                    )
                    if created:
                        resultats['grilles_creees'] += 1

            # 3. Dupliquer les ClasseNote + MatiereNote (module notes)
            if dupliquer_notes_classes:
                from notes.models import ClasseNote, MatiereNote
                classes_notes = ClasseNote.objects.filter(
                    ecole=ecole, annee_scolaire=annee_courante, actif=True
                )
                for cn in classes_notes:
                    nouvelle_cn, created = ClasseNote.objects.get_or_create(
                        ecole=ecole,
                        nom=cn.nom,
                        annee_scolaire=annee_nouvelle,
                        defaults={
                            'niveau': cn.niveau,
                            'niveau_enseignement': cn.niveau_enseignement,
                            'effectif': cn.effectif,
                            'description': cn.description,
                            'actif': True,
                            'cree_par': request.user,
                        }
                    )
                    if created:
                        resultats['classes_notes_creees'] += 1
                        # Dupliquer les matières
                        for m in cn.matieres.filter(actif=True):
                            _, m_created = MatiereNote.objects.get_or_create(
                                classe=nouvelle_cn,
                                code=m.code,
                                defaults={
                                    'nom': m.nom,
                                    'coefficient': m.coefficient,
                                    'description': m.description,
                                    'actif': True,
                                    'cree_par': request.user,
                                }
                            )
                            if m_created:
                                resultats['matieres_creees'] += 1

            # 4. Faire passer les élèves en classe supérieure
            if faire_passer_eleves:
                eleves_actifs = Eleve.objects.filter(
                    classe__ecole=ecole,
                    classe__annee_scolaire=annee_courante,
                    statut='ACTIF'
                ).select_related('classe')

                for eleve in eleves_actifs:
                    ancienne_classe = eleve.classe
                    sup_nom = _classe_superieure_nom(ancienne_classe.nom)

                    if sup_nom:
                        # Chercher la classe supérieure dans la nouvelle année (nom contient le 1er mot)
                        sup_cls = Classe.objects.filter(
                            ecole=ecole,
                            annee_scolaire=annee_nouvelle,
                            nom__icontains=sup_nom.split()[0],
                        ).first()
                        if not sup_cls:
                            # Fallback : même classe dupliquée dans la nouvelle année
                            sup_cls = map_anciennes_nouvelles.get(ancienne_classe.pk)

                        if sup_cls:
                            eleve._current_user = request.user
                            eleve.classe = sup_cls
                            eleve.save()
                            HistoriqueEleve.objects.create(
                                eleve=eleve,
                                action='CHANGEMENT_CLASSE',
                                description=(
                                    f"Passage automatique nouvelle année {annee_nouvelle}: "
                                    f"{ancienne_classe.nom} → {sup_cls.nom}"
                                ),
                                utilisateur=request.user,
                            )
                            resultats['eleves_passes'] += 1
                        else:
                            # Laisser dans la même classe mais nouvelle année
                            nouvelle_meme = map_anciennes_nouvelles.get(ancienne_classe.pk)
                            if nouvelle_meme:
                                eleve.classe = nouvelle_meme
                                eleve.save()
                                resultats['eleves_conserves'] += 1
                    else:
                        # Classe terminale ou maternelle → garder dans même classe de la nouvelle année
                        nouvelle_meme = map_anciennes_nouvelles.get(ancienne_classe.pk)
                        if nouvelle_meme:
                            eleve.classe = nouvelle_meme
                            eleve.save()
                            resultats['eleves_conserves'] += 1

    except Exception as e:
        logger.error(f"Erreur création nouvelle année: {e}", exc_info=True)
        messages.error(request, f"Erreur lors de la création : {e}")
        return redirect('eleves:nouvelle_annee_apercu')

    # Message de succès
    msg_parts = []
    if resultats['classes_creees']:
        msg_parts.append(f"{resultats['classes_creees']} classe(s) créée(s)")
    if resultats['grilles_creees']:
        msg_parts.append(f"{resultats['grilles_creees']} grille(s) tarifaire(s) copiée(s)")
    if resultats['classes_notes_creees']:
        msg_parts.append(f"{resultats['classes_notes_creees']} classe(s) notes avec {resultats['matieres_creees']} matière(s)")
    if resultats['eleves_passes']:
        msg_parts.append(f"{resultats['eleves_passes']} élève(s) passé(s) en classe supérieure")
    if resultats['eleves_conserves']:
        msg_parts.append(f"{resultats['eleves_conserves']} élève(s) conservé(s) dans leur classe")

    messages.success(
        request,
        f"✅ Année scolaire {annee_nouvelle} créée avec succès ! "
        + ((' | '.join(msg_parts)) if msg_parts else '')
    )
    return redirect('eleves:gestion_classes')
