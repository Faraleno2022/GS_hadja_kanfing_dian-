#!/usr/bin/env python
import os
import sys
import django

# Configuration Django
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ecole_moderne.settings')
django.setup()

from paiements.models import EcheancierPaiement
from django.db.models import Q, F, Sum, Count, Value, DecimalField, ExpressionWrapper
from django.db.models.functions import Coalesce, Greatest
from datetime import date
from django.utils import timezone as _tz

def debug_eleves_soldes():
    print("=== DEBUG ÉLÈVES SOLDÉS ===")
    
    # Test de base
    today = _tz.localdate() if hasattr(_tz, 'localdate') else date.today()
    print(f'Date actuelle: {today}')

    # Année scolaire par défaut
    annee_dyn = f'{today.year}-{today.year+1}' if today.month >= 9 else f'{today.year-1}-{today.year}'
    print(f'Année scolaire calculée: {annee_dyn}')

    # Compter les échéanciers
    total_echeanciers = EcheancierPaiement.objects.count()
    print(f'Total échéanciers: {total_echeanciers}')

    # Compter par année
    echeanciers_par_annee = EcheancierPaiement.objects.values('annee_scolaire').annotate(count=Count('id')).order_by('annee_scolaire')
    print('Échéanciers par année:')
    for item in echeanciers_par_annee:
        print(f'  {item["annee_scolaire"]}: {item["count"]}')

    # Test avec l'année par défaut
    qs_test = EcheancierPaiement.objects.filter(annee_scolaire=annee_dyn)
    print(f'Échéanciers pour {annee_dyn}: {qs_test.count()}')
    
    # Test de la logique de calcul des soldés
    if qs_test.exists():
        print("\n=== TEST CALCUL SOLDÉS ===")
        
        # Période
        try:
            annee_debut = int(annee_dyn.split('-')[0])
            periode_debut = date(annee_debut, 9, 1)
            periode_fin = date(annee_debut + 1, 8, 31)
        except Exception:
            annee_debut = today.year if today.month >= 9 else today.year - 1
            periode_debut = date(annee_debut, 9, 1)
            periode_fin = date(annee_debut + 1, 8, 31)
        
        # Spécifique 2025-2026
        if annee_dyn == "2025-2026":
            periode_debut = date(2025, 8, 14)
            
        # Ajustement période
        if today < periode_debut:
            periode_fin = periode_debut
        elif periode_fin > today:
            periode_fin = today
            
        print(f'Période: {periode_debut} à {periode_fin}')
        
        # Expressions de calcul
        dues_sco = (
            Coalesce(F('tranche_1_due'), Value(0, output_field=DecimalField(max_digits=12, decimal_places=0)))
            + Coalesce(F('tranche_2_due'), Value(0, output_field=DecimalField(max_digits=12, decimal_places=0)))
            + Coalesce(F('tranche_3_due'), Value(0, output_field=DecimalField(max_digits=12, decimal_places=0)))
        )
        
        remises_total = Coalesce(
            Sum(
                'eleve__paiements__remises__montant_remise',
                filter=(
                    Q(eleve__paiements__statut='VALIDE') &
                    Q(eleve__paiements__date_paiement__gte=periode_debut) &
                    Q(eleve__paiements__date_paiement__lte=periode_fin)
                ),
                output_field=DecimalField(max_digits=12, decimal_places=0),
            ),
            Value(0, output_field=DecimalField(max_digits=12, decimal_places=0)),
        )
        
        paye_effectif = ExpressionWrapper(
            Coalesce(F('frais_inscription_paye'), Value(0, output_field=DecimalField(max_digits=12, decimal_places=0)))
            + Coalesce(F('tranche_1_payee'), Value(0, output_field=DecimalField(max_digits=12, decimal_places=0)))
            + Coalesce(F('tranche_2_payee'), Value(0, output_field=DecimalField(max_digits=12, decimal_places=0)))
            + Coalesce(F('tranche_3_payee'), Value(0, output_field=DecimalField(max_digits=12, decimal_places=0)))
            + remises_total,
            output_field=DecimalField(max_digits=12, decimal_places=0),
        )
        
        net_sco_du = Greatest(
            Value(0, output_field=DecimalField(max_digits=12, decimal_places=0)),
            ExpressionWrapper(dues_sco - remises_total, output_field=DecimalField(max_digits=12, decimal_places=0))
        )
        
        net_du = ExpressionWrapper(
            Coalesce(F('frais_inscription_du'), Value(0, output_field=DecimalField(max_digits=12, decimal_places=0)))
            + net_sco_du,
            output_field=DecimalField(max_digits=12, decimal_places=0),
        )
        
        solde_calc = ExpressionWrapper(net_du - paye_effectif, output_field=DecimalField(max_digits=12, decimal_places=0))
        
        # Appliquer les annotations
        qs_annotated = qs_test.annotate(
            total_du_calc=net_du,
            total_paye_calc=paye_effectif,
            solde_calcule=solde_calc,
            total_remises_calc=remises_total,
        ).order_by('eleve__classe__nom', 'eleve__nom', 'eleve__prenom')
        
        print(f'Échéanciers annotés: {qs_annotated.count()}')
        
        # Élèves soldés
        qs_soldes = qs_annotated.filter(solde_calcule__lte=0)
        print(f'Élèves soldés: {qs_soldes.count()}')
        
        # Afficher quelques exemples
        if qs_soldes.exists():
            print("\n=== EXEMPLES D'ÉLÈVES SOLDÉS ===")
            for ech in qs_soldes[:5]:
                print(f"- {ech.eleve.prenom} {ech.eleve.nom} ({ech.eleve.classe.nom})")
                print(f"  Dû: {ech.total_du_calc}, Payé: {ech.total_paye_calc}, Solde: {ech.solde_calcule}")
        else:
            print("\n=== AUCUN ÉLÈVE SOLDÉ TROUVÉ ===")
            # Afficher quelques échéanciers pour debug
            print("Exemples d'échéanciers (non soldés):")
            for ech in qs_annotated[:5]:
                print(f"- {ech.eleve.prenom} {ech.eleve.nom} ({ech.eleve.classe.nom})")
                print(f"  Dû: {ech.total_du_calc}, Payé: {ech.total_paye_calc}, Solde: {ech.solde_calcule}")
    else:
        print(f"Aucun échéancier trouvé pour l'année {annee_dyn}")

if __name__ == "__main__":
    debug_eleves_soldes()
