"""Audite et répare les années scolaires mal saisies.

Une année comme « 2025-2027 » passe sans erreur dans une base ancienne (le
validateur de format n'existait pas). Elle casse pourtant tout le calcul des
soldes : le moteur d'allocation n'apparie un paiement à un échéancier que si les
deux portent la même année. Un échéancier en « 2025-2027 » face à des paiements
en « 2025-2026 » ne retient donc aucun encaissement, et reçus, relances et
rapports affichent le dû intégral.

    python manage.py corriger_annees_scolaires            # rapport seul
    python manage.py corriger_annees_scolaires --apply    # correction
"""
from django.core.management.base import BaseCommand
from django.db import IntegrityError, models, transaction

from ecole_moderne.validators import (
    annee_scolaire_est_valide,
    normaliser_annee_scolaire,
)


class Command(BaseCommand):
    help = "Détecte et corrige les années scolaires au format invalide."

    def add_arguments(self, parser):
        parser.add_argument(
            '--apply',
            action='store_true',
            help="Écrit les corrections. Sans cette option, rien n'est modifié.",
        )

    def handle(self, *args, **options):
        from eleves.models import Classe, GrilleTarifaire
        from paiements.models import EcheancierPaiement, Paiement
        from paiements.payment_engine import recalculer_echeancier

        appliquer = options['apply']
        cibles = [
            (GrilleTarifaire, "Grille tarifaire"),
            (Classe, "Classe"),
            (EcheancierPaiement, "Échéancier"),
            (Paiement, "Paiement"),
        ]

        total = 0
        eleves_touches = set()
        classes_touchees = set()
        conflits = []

        for modele, libelle in cibles:
            invalides = [
                objet
                for objet in modele.objects.all()
                if not annee_scolaire_est_valide(objet.annee_scolaire)
            ]
            if not invalides:
                continue

            self.stdout.write(self.style.WARNING(
                f"\n{libelle} : {len(invalides)} enregistrement(s) à corriger"
            ))
            for objet in invalides:
                ancienne = objet.annee_scolaire
                nouvelle = normaliser_annee_scolaire(ancienne)
                if not nouvelle:
                    self.stdout.write(self.style.ERROR(
                        f"  #{objet.pk} : {ancienne!r} illisible, correction manuelle requise"
                    ))
                    continue

                if appliquer:
                    try:
                        with transaction.atomic():
                            objet.annee_scolaire = nouvelle
                            objet.save(update_fields=['annee_scolaire'])
                    except IntegrityError:
                        objet.annee_scolaire = ancienne
                        # Un enregistrement porte déjà l'année corrigée (même
                        # école, même nom/niveau). Les deux lignes font double
                        # emploi : seul un humain peut décider laquelle garder
                        # et où rattacher les élèves.
                        conflits.append((libelle, objet.pk, ancienne, nouvelle, str(objet)))
                        self.stdout.write(self.style.ERROR(
                            f"  #{objet.pk} : {ancienne!r} -> {nouvelle!r} IMPOSSIBLE, "
                            f"un doublon existe déjà en {nouvelle!r}  ({objet})"
                        ))
                        continue

                self.stdout.write(f"  #{objet.pk} : {ancienne!r} -> {nouvelle!r}  ({objet})")
                total += 1
                if hasattr(objet, 'eleve_id'):
                    eleves_touches.add(objet.eleve_id)
                elif modele is Classe:
                    classes_touchees.add(objet.pk)

        if not total and not conflits:
            self.stdout.write(self.style.SUCCESS(
                "Aucune année scolaire invalide. Rien à corriger."
            ))
            return

        if not appliquer:
            self.stdout.write(self.style.WARNING(
                f"\n{total} correction(s) identifiée(s). "
                "Relancer avec --apply pour les écrire."
            ))
            return

        # Les soldes sont recalculés à la lecture, mais les cumuls et statuts
        # stockés sur l'échéancier doivent être resynchronisés pour que les
        # listes et tableaux de bord repartent sur des chiffres justes.
        a_rejouer = EcheancierPaiement.objects.filter(eleve_id__in=eleves_touches)
        if classes_touchees:
            a_rejouer = EcheancierPaiement.objects.filter(
                models.Q(eleve_id__in=eleves_touches)
                | models.Q(eleve__classe_id__in=classes_touchees)
            )
        rejoues = 0
        for echeancier in a_rejouer:
            recalculer_echeancier(echeancier)
            rejoues += 1

        self.stdout.write(self.style.SUCCESS(
            f"\n{total} correction(s) écrite(s), {rejoues} échéancier(s) recalculé(s)."
        ))

        if conflits:
            self.stdout.write(self.style.ERROR(
                f"\n{len(conflits)} enregistrement(s) NON corrigé(s) : un doublon "
                "porte déjà l'année cible. À traiter à la main (fusionner les "
                "deux lignes, puis relancer la commande) :"
            ))
            for libelle, pk, ancienne, nouvelle, texte in conflits:
                self.stdout.write(self.style.ERROR(
                    f"  {libelle} #{pk} : {ancienne!r} -> {nouvelle!r}  ({texte})"
                ))
