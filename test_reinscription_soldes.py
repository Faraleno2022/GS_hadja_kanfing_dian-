#!/usr/bin/env python
import os
import sys
import django

# Configuration Django
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ecole_moderne.settings')
django.setup()

from paiements.models import EcheancierPaiement
from eleves.models import GrilleTarifaire, Eleve
from django.db.models import Q, F, Sum, Count, Value, DecimalField, ExpressionWrapper, Case, When, OuterRef, Subquery
from django.db.models.functions import Coalesce, Greatest
from datetime import date
from django.utils import timezone as _tz
from django.contrib.auth.models import User
from utilisateurs.utils import filter_by_user_school

def test_calcul_reinscription():
    print("=== TEST CALCUL FRAIS DE RÉINSCRIPTION ===")
    
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
    
    # Année scolaire actuelle
    today = _tz.localdate() if hasattr(_tz, 'localdate') else date.today()
    annee_dyn = f"{today.year}-{today.year+1}" if today.month >= 9 else f"{today.year-1}-{today.year}"
    annee = annee_dyn
    print(f"Année scolaire: {annee}")
    
    # Vérifier s'il y a des grilles tarifaires avec frais de réinscription
    try:
        grilles = GrilleTarifaire.objects.filter(annee_scolaire=annee)
        print(f"Grilles tarifaires trouvées: {grilles.count()}")
        
        grilles_avec_reinsc = grilles.exclude(frais_reinscription__isnull=True).exclude(frais_reinscription=0)
        print(f"Grilles avec frais de réinscription: {grilles_avec_reinsc.count()}")
        
        if grilles_avec_reinsc.exists():
            for grille in grilles_avec_reinsc[:3]:
                print(f"  - {grille.ecole.nom} / {grille.niveau}: {grille.frais_reinscription} GNF")
    except Exception as e:
        print(f"Erreur grilles tarifaires: {e}")
    
    # Base queryset
    qs = EcheancierPaiement.objects.select_related('eleve', 'eleve__classe', 'eleve__classe__ecole')
    qs = qs.filter(annee_scolaire=annee)
    qs = filter_by_user_school(qs, user, 'eleve__classe__ecole')
    
    print(f"Échéanciers pour {annee}: {qs.count()}")
    
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
    
    # Appliquer la logique de réinscription
    try:
        reinsc_subq = GrilleTarifaire.objects.filter(
            ecole=OuterRef('eleve__classe__ecole'),
            niveau=OuterRef('eleve__classe__niveau'),
            annee_scolaire=OuterRef('annee_scolaire'),
        ).values('frais_reinscription')[:1]
        
        qs = qs.annotate(
            reinsc_due=Case(
                When(frais_inscription_du=Subquery(reinsc_subq), then=F('frais_inscription_du')),
                default=Value(0),
                output_field=DecimalField(max_digits=12, decimal_places=0),
            )
        )
        print("Annotation réinscription appliquée")
    except Exception as e:
        print(f"Erreur annotation réinscription: {e}")
        qs = qs.annotate(
            reinsc_due=Value(0, output_field=DecimalField(max_digits=12, decimal_places=0))
        )
    
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
    
    # Analyser quelques cas avec frais de réinscription
    print("\n=== ANALYSE FRAIS DE RÉINSCRIPTION ===")
    qs_avec_reinsc = qs.exclude(reinsc_due=0)
    print(f"Échéanciers avec frais de réinscription: {qs_avec_reinsc.count()}")
    
    if qs_avec_reinsc.exists():
        for ech in qs_avec_reinsc[:5]:
            print(f"- {ech.eleve.prenom} {ech.eleve.nom} ({ech.eleve.classe.nom})")
            print(f"  Inscription dû: {ech.frais_inscription_du} GNF")
            print(f"  Réinscription détectée: {ech.reinsc_due} GNF")
            print(f"  Total dû: {ech.total_du_calc} GNF")
            print(f"  Solde: {ech.solde_calcule} GNF")
            print()
    
    # Vérifier les élèves avec inscription vs réinscription
    qs_inscription_normale = qs.filter(reinsc_due=0).exclude(frais_inscription_du=0)
    print(f"Élèves avec inscription normale: {qs_inscription_normale.count()}")
    
    if qs_inscription_normale.exists():
        print("Exemples inscription normale:")
        for ech in qs_inscription_normale[:3]:
            print(f"  - {ech.eleve.prenom} {ech.eleve.nom}: {ech.frais_inscription_du} GNF")

if __name__ == "__main__":
    test_calcul_reinscription()
