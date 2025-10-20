from django.core.management.base import BaseCommand
from django.db import transaction
from eleves.models import Eleve, Classe, _code_classe_from_nom_ou_niveau


class Command(BaseCommand):
    help = (
        "Régularise les matricules des élèves en remplaçant les valeurs fallback 'CL{id}-###' "
        "par des codes corrects (ex: MPS/MS/GS/PNx/CNx/L11xx/L12xx/Txx) selon la classe.\n"
        "Par défaut en mode --dry-run (aucune écriture)."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run', action='store_true', default=False,
            help='Exécuter sans écrire en base, affiche uniquement les changements.'
        )
        parser.add_argument(
            '--ecole-id', type=int, default=None,
            help="Limiter aux élèves d'une école (id)."
        )
        parser.add_argument(
            '--classe-id', type=int, default=None,
            help="Limiter aux élèves d'une classe (id)."
        )
        parser.add_argument(
            '--startswith', type=str, default='CL',
            help="Préfixe des matricules à corriger (défaut: 'CL')."
        )

    def _next_available_for_code(self, code: str) -> str:
        """Retourne le prochain matricule disponible pour un préfixe de code donné."""
        base_prefix = f"{code}-"
        # Récupérer le plus grand suffixe numérique existant
        derniers = (
            Eleve.objects
            .filter(matricule__startswith=base_prefix)
            .order_by('-matricule')
        )
        next_num = 1
        if derniers.exists():
            # Essayer d'extraire le dernier compteur
            import re
            dernier = derniers.first().matricule
            m = re.search(rf"^(?:{code})-(\\d+)$", dernier)
            if m:
                try:
                    next_num = int(m.group(1)) + 1
                except Exception:
                    next_num = 1
        # Trouver un candidat libre
        for _ in range(10_000):  # large marge de sécurité
            candidat = f"{code}-{next_num:03d}"
            if not Eleve.objects.filter(matricule=candidat).exists():
                return candidat
            next_num += 1
        # En cas extrême, renvoyer un code timestampé
        import time
        return f"{code}-{int(time.time())}"

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        ecole_id = options['ecole_id']
        classe_id = options['classe_id']
        startswith = options['startswith']

        qs = Eleve.objects.filter(matricule__startswith=startswith)
        if classe_id:
            qs = qs.filter(classe_id=classe_id)
        if ecole_id:
            qs = qs.filter(classe__ecole_id=ecole_id)

        total = qs.count()
        if total == 0:
            self.stdout.write(self.style.WARNING(
                f"Aucun élève trouvé avec matricule commençant par '{startswith}'."
            ))
            return

        self.stdout.write(self.style.NOTICE(
            f"Élèves ciblés: {total} (dry_run={dry_run})"
        ))

        # Trier pour une attribution stable
        qs = qs.select_related('classe', 'classe__ecole').order_by('classe_id', 'date_inscription', 'nom', 'prenom')

        changes = []
        skipped = []
        errors = []

        def process():
            for e in qs:
                try:
                    code = _code_classe_from_nom_ou_niveau(e.classe)
                    if not code:
                        skipped.append((e.id, e.matricule, e.classe_id, getattr(e.classe, 'nom', ''), 'code_introuvable'))
                        continue
                    new_mat = self._next_available_for_code(code)
                    if new_mat == e.matricule:
                        continue
                    old = e.matricule
                    e.matricule = new_mat
                    if not dry_run:
                        e.save(update_fields=['matricule'])
                    changes.append((e.id, old, new_mat, code))
                except Exception as ex:
                    errors.append((e.id, e.matricule, str(ex)))

        if dry_run:
            process()
        else:
            with transaction.atomic():
                process()

        # Résumé
        self.stdout.write(self.style.SUCCESS(f"Modifications: {len(changes)}"))
        for eid, old, new, code in changes[:50]:  # limiter l'affichage
            self.stdout.write(f" - Eleve#{eid}: {old} -> {new} ({code})")
        if len(changes) > 50:
            self.stdout.write(f" ... et {len(changes)-50} autres")

        if skipped:
            self.stdout.write(self.style.WARNING(f"Ignorés (code introuvable): {len(skipped)}"))
        if errors:
            self.stdout.write(self.style.ERROR(f"Erreurs: {len(errors)}"))
            for eid, mat, msg in errors[:20]:
                self.stdout.write(f" - Eleve#{eid} [{mat}]: {msg}")
