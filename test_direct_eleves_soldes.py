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
from django.core.paginator import Paginator
from django.contrib.auth.models import User
from utilisateurs.utils import filter_by_user_school

def test_logique_eleves_soldes():
    print("=== TEST LOGIQUE ÉLÈVES SOLDÉS (SANS VUE) ===")
    
    # Récupérer un utilisateur admin
    try:
        user = User.objects.filter(is_superuser=True).first()
        if not user:
            print("Aucun utilisateur admin trouvé")
            return
        print(f"Utilisateur: {user.username}")
    except Exception as e:
        print(f"Erreur utilisateur: {e}")
        return
    
    # Reproduire la logique de la vue
    today = _tz.localdate() if hasattr(_tz, 'localdate') else date.today()
    annee_dyn = f"{today.year}-{today.year+1}" if today.month >= 9 else f"{today.year-1}-{today.year}"
    annee = annee_dyn
    
    print(f"Année scolaire: {annee}")
    
    # Base queryset
    qs = EcheancierPaiement.objects.select_related('eleve', 'eleve__classe', 'eleve__classe__ecole')
    print(f"Total échéanciers: {qs.count()}")
    
    # Filtrer par année
    qs = qs.filter(annee_scolaire=annee)
    print(f"Échéanciers pour {annee}: {qs.count()}")
    
    # Filtrer par école utilisateur
    qs_before_school = qs.count()
    qs = filter_by_user_school(qs, user, 'eleve__classe__ecole')
    qs_after_school = qs.count()
    print(f"Après filtrage école: {qs_after_school} (était {qs_before_school})")
    
    if qs.count() == 0:
        print("Aucun échéancier après filtrage - problème de permissions")
        return
    
    # Période
    try:
        annee_debut = int(annee.split('-')[0])
        periode_debut = date(annee_debut, 9, 1)
        periode_fin = date(annee_debut + 1, 8, 31)
    except Exception:
        annee_debut = today.year if today.month >= 9 else today.year - 1
        periode_debut = date(annee_debut, 9, 1)
        periode_fin = date(annee_debut + 1, 8, 31)
    
    if annee == "2025-2026":
        periode_debut = date(2025, 8, 14)
        
    if today < periode_debut:
        periode_fin = periode_debut
    elif periode_fin > today:
        periode_fin = today
        
    print(f"Période: {periode_debut} à {periode_fin}")
    
    # Expressions de calcul (reproduire exactement la vue)
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
    qs = qs.annotate(
        total_du_calc=net_du,
        total_paye_calc=paye_effectif,
        solde_calcule=solde_calc,
        total_remises_calc=remises_total,
    ).order_by('eleve__classe__nom', 'eleve__nom', 'eleve__prenom')
    
    print(f"Échéanciers annotés: {qs.count()}")
    
    # Élèves soldés
    qs_soldes = qs.filter(solde_calcule__lte=0)
    print(f"Élèves soldés: {qs_soldes.count()}")
    
    # Test pagination
    paginator = Paginator(qs_soldes, 25)
    page_obj = paginator.get_page(1)
    
    print(f"Page 1: {len(page_obj.object_list)} élèves")
    print(f"Total pages: {paginator.num_pages}")
    print(f"Total élèves (paginator): {paginator.count}")
    
    # Afficher quelques exemples
    if page_obj.object_list:
        print("\n=== PREMIERS ÉLÈVES SOLDÉS ===")
        for i, ech in enumerate(page_obj.object_list[:5]):
            print(f"{i+1}. {ech.eleve.prenom} {ech.eleve.nom} ({ech.eleve.classe.nom})")
            print(f"   Dû: {ech.total_du_calc}, Payé: {ech.total_paye_calc}, Solde: {ech.solde_calcule}")
    else:
        print("Aucun élève dans page_obj.object_list")
        
    # Vérifier s'il y a des élèves avec solde > 0 pour comparaison
    qs_non_soldes = qs.filter(solde_calcule__gt=0)
    print(f"\nÉlèves NON soldés: {qs_non_soldes.count()}")

if __name__ == "__main__":
    test_logique_eleves_soldes()
