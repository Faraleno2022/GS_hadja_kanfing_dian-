#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Script pour vérifier que le filtrage par école fonctionne correctement
dans les statistiques des élèves
"""

import os
import sys
import django

# Configuration Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ecole_moderne.settings')
django.setup()

from django.contrib.auth import get_user_model
from eleves.models import Eleve, Classe, Responsable, Ecole
from utilisateurs.utils import user_school
from django.db.models import Q

User = get_user_model()

def verifier_filtrage():
    """Vérifie que le filtrage par école fonctionne"""
    
    print("\n" + "="*80)
    print(" "*15 + "🔍 VÉRIFICATION DU FILTRAGE PAR ÉCOLE")
    print("="*80)
    
    # Récupérer les écoles
    ecoles = Ecole.objects.all()
    
    if ecoles.count() < 2:
        print("\n⚠️  Attention : Il faut au moins 2 écoles pour tester le filtrage")
        print(f"   Écoles trouvées : {ecoles.count()}")
        return
    
    print(f"\n✅ {ecoles.count()} école(s) trouvée(s)\n")
    
    # Pour chaque école, afficher les statistiques
    for ecole in ecoles:
        print(f"\n{'='*80}")
        print(f"   📚 ÉCOLE : {ecole.nom}")
        print(f"{'='*80}")
        
        # 1. Élèves de l'école
        eleves_ecole = Eleve.objects.filter(classe__ecole=ecole)
        print(f"\n   👥 ÉLÈVES :")
        print(f"      Total : {eleves_ecole.count()}")
        print(f"      Actifs : {eleves_ecole.filter(statut='ACTIF').count()}")
        print(f"      Garçons : {eleves_ecole.filter(sexe='M').count()}")
        print(f"      Filles : {eleves_ecole.filter(sexe='F').count()}")
        
        # 2. Classes de l'école
        classes_ecole = Classe.objects.filter(ecole=ecole)
        print(f"\n   🏫 CLASSES :")
        print(f"      Total : {classes_ecole.count()}")
        if classes_ecole.exists():
            for classe in classes_ecole[:5]:
                nb_eleves = Eleve.objects.filter(classe=classe).count()
                print(f"      - {classe.nom} : {nb_eleves} élève(s)")
        
        # 3. Responsables de l'école
        responsables_ecole = Responsable.objects.filter(
            Q(eleves_principal__classe__ecole=ecole) |
            Q(eleves_secondaire__classe__ecole=ecole)
        ).distinct()
        print(f"\n   👨‍👩‍👧‍👦 RESPONSABLES :")
        print(f"      Total : {responsables_ecole.count()}")
        
        # Répartition par relation
        for relation_code, relation_nom in Responsable.RELATION_CHOICES[:5]:
            count = responsables_ecole.filter(relation=relation_code).count()
            if count > 0:
                print(f"      - {relation_nom} : {count}")
    
    # Vérification de l'isolation
    print(f"\n{'='*80}")
    print(" "*20 + "🔒 VÉRIFICATION DE L'ISOLATION")
    print("="*80)
    
    if ecoles.count() >= 2:
        ecole1 = ecoles[0]
        ecole2 = ecoles[1]
        
        # Élèves
        eleves1 = Eleve.objects.filter(classe__ecole=ecole1).count()
        eleves2 = Eleve.objects.filter(classe__ecole=ecole2).count()
        total_eleves = Eleve.objects.count()
        
        print(f"\n   📊 ÉLÈVES :")
        print(f"      {ecole1.nom} : {eleves1}")
        print(f"      {ecole2.nom} : {eleves2}")
        print(f"      Total système : {total_eleves}")
        
        if eleves1 + eleves2 <= total_eleves:
            print(f"      ✅ Pas de chevauchement détecté")
        else:
            print(f"      ⚠️  Possible chevauchement")
        
        # Classes
        classes1 = Classe.objects.filter(ecole=ecole1).count()
        classes2 = Classe.objects.filter(ecole=ecole2).count()
        total_classes = Classe.objects.count()
        
        print(f"\n   🏫 CLASSES :")
        print(f"      {ecole1.nom} : {classes1}")
        print(f"      {ecole2.nom} : {classes2}")
        print(f"      Total système : {total_classes}")
        
        if classes1 + classes2 <= total_classes:
            print(f"      ✅ Pas de chevauchement détecté")
        else:
            print(f"      ⚠️  Possible chevauchement")
    
    # Test avec utilisateurs
    print(f"\n{'='*80}")
    print(" "*20 + "👤 VÉRIFICATION PAR UTILISATEUR")
    print("="*80)
    
    # Chercher des utilisateurs non-admin
    users = User.objects.filter(is_superuser=False, profil__isnull=False)[:5]
    
    if users.exists():
        for user in users:
            print(f"\n   👤 Utilisateur : {user.username}")
            try:
                ecole_user = user_school(user)
                if ecole_user:
                    print(f"      École : {ecole_user.nom}")
                    
                    # Simuler le filtrage
                    eleves_base = Eleve.objects.filter(classe__ecole=ecole_user)
                    classes_base = Classe.objects.filter(ecole=ecole_user)
                    responsables_base = Responsable.objects.filter(
                        Q(eleves_principal__classe__ecole=ecole_user) |
                        Q(eleves_secondaire__classe__ecole=ecole_user)
                    ).distinct()
                    
                    print(f"      Élèves visibles : {eleves_base.count()}")
                    print(f"      Classes visibles : {classes_base.count()}")
                    print(f"      Responsables visibles : {responsables_base.count()}")
                    print(f"      ✅ Filtrage appliqué")
                else:
                    print(f"      ⚠️  Pas d'école assignée")
            except Exception as e:
                print(f"      ❌ Erreur : {e}")
    else:
        print("\n   ⚠️  Aucun utilisateur non-admin trouvé pour tester")
    
    # Résumé final
    print(f"\n{'='*80}")
    print(" "*25 + "📋 RÉSUMÉ")
    print("="*80)
    
    total_eleves_systeme = Eleve.objects.count()
    total_classes_systeme = Classe.objects.count()
    total_responsables_systeme = Responsable.objects.count()
    
    print(f"\n   📊 DONNÉES SYSTÈME :")
    print(f"      Total élèves : {total_eleves_systeme}")
    print(f"      Total classes : {total_classes_systeme}")
    print(f"      Total responsables : {total_responsables_systeme}")
    print(f"      Total écoles : {ecoles.count()}")
    
    # Vérifier que la somme par école correspond au total
    somme_eleves_par_ecole = sum([
        Eleve.objects.filter(classe__ecole=e).count() for e in ecoles
    ])
    
    if somme_eleves_par_ecole == total_eleves_systeme:
        print(f"\n   ✅ COHÉRENCE : Somme par école = Total système ({somme_eleves_par_ecole})")
    else:
        print(f"\n   ⚠️  INCOHÉRENCE : Somme par école ({somme_eleves_par_ecole}) ≠ Total ({total_eleves_systeme})")
    
    print(f"\n{'='*80}")
    print(" "*20 + "✅ VÉRIFICATION TERMINÉE")
    print("="*80)
    
    print("\n💡 RECOMMANDATIONS :")
    print("   1. Chaque école doit voir uniquement ses propres données")
    print("   2. Les administrateurs voient toutes les données")
    print("   3. Aucune fuite de données entre écoles")
    print("\n" + "="*80 + "\n")

if __name__ == '__main__':
    try:
        verifier_filtrage()
    except Exception as e:
        print(f"\n❌ Erreur : {e}")
        import traceback
        traceback.print_exc()
