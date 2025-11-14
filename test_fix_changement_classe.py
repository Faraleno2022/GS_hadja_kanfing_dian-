#!/usr/bin/env python
"""
Script de test pour valider le correctif du bug de changement de classe.

Bug corrigé: IntegrityError lors du changement de classe d'un élève
Erreur: UNIQUE constraint failed: eleves_eleve.matricule

Solution: Libération temporaire du matricule avec un UUID unique avant
la réaffectation des matricules de l'ancienne classe.
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ecole_moderne.settings')
django.setup()

from django.contrib.auth import get_user_model
from eleves.models import Eleve, Classe

User = get_user_model()


def test_changement_classe():
    """Test du changement de classe avec réaffectation des matricules."""
    
    print("\n" + "="*70)
    print("TEST: Changement de classe avec réaffectation matricules")
    print("="*70)
    
    # 1. Récupérer l'élève problématique
    try:
        eleve = Eleve.objects.get(id=178)
        print(f"\n✓ Élève trouvé: {eleve.matricule} - {eleve.prenom} {eleve.nom}")
        print(f"  Classe actuelle: {eleve.classe}")
    except Eleve.DoesNotExist:
        print("\n✗ Élève ID 178 non trouvé")
        return
    
    # 2. Récupérer les deux classes
    try:
        classe_actuelle = eleve.classe
        classe_cible = Classe.objects.get(nom="10ÈME ANNÉE (B)")
        print(f"✓ Classe cible: {classe_cible}")
    except Classe.DoesNotExist:
        print("\n✗ Classe 10ÈME ANNÉE (B) non trouvée")
        return
    
    # 3. Compter les élèves dans chaque classe avant
    nb_avant_ancienne = Eleve.objects.filter(classe=classe_actuelle).count()
    nb_avant_nouvelle = Eleve.objects.filter(classe=classe_cible).count()
    
    print(f"\n📊 État AVANT le changement:")
    print(f"  Ancienne classe ({classe_actuelle}): {nb_avant_ancienne} élèves")
    print(f"  Nouvelle classe ({classe_cible}): {nb_avant_nouvelle} élèves")
    
    # 4. Afficher les 5 premiers matricules de l'ancienne classe
    print(f"\n📋 Matricules dans l'ancienne classe:")
    eleves_ancienne = Eleve.objects.filter(classe=classe_actuelle).order_by('matricule')[:5]
    for e in eleves_ancienne:
        print(f"  - {e.matricule}: {e.prenom} {e.nom}")
    
    # 5. Simuler le changement de classe (comme dans views.py)
    ancien_matricule = eleve.matricule
    ancienne_classe_nom = classe_actuelle.nom
    
    print(f"\n🔄 Changement de classe en cours...")
    print(f"  De: {ancienne_classe_nom}")
    print(f"  Vers: {classe_cible.nom}")
    
    try:
        # Récupérer un utilisateur pour le contexte
        user = User.objects.filter(is_superuser=True).first()
        if user:
            eleve._current_user = user
        
        # Effectuer le changement
        eleve.classe = classe_cible
        eleve.save()
        
        print(f"\n✅ SUCCÈS: Changement effectué sans erreur!")
        print(f"  Ancien matricule: {ancien_matricule}")
        print(f"  Nouveau matricule: {eleve.matricule}")
        
    except Exception as e:
        print(f"\n❌ ERREUR lors du changement:")
        print(f"  Type: {type(e).__name__}")
        print(f"  Message: {str(e)}")
        return
    
    # 6. Vérifier l'état après
    nb_apres_ancienne = Eleve.objects.filter(classe=classe_actuelle).count()
    nb_apres_nouvelle = Eleve.objects.filter(classe=classe_cible).count()
    
    print(f"\n📊 État APRÈS le changement:")
    print(f"  Ancienne classe ({classe_actuelle}): {nb_apres_ancienne} élèves")
    print(f"  Nouvelle classe ({classe_cible}): {nb_apres_nouvelle} élèves")
    
    # 7. Vérifier que les matricules de l'ancienne classe ont été réaffectés
    print(f"\n📋 Matricules dans l'ancienne classe (après réaffectation):")
    eleves_ancienne_apres = Eleve.objects.filter(classe=classe_actuelle).order_by('matricule')[:5]
    for e in eleves_ancienne_apres:
        print(f"  - {e.matricule}: {e.prenom} {e.nom}")
    
    # 8. Vérifier qu'il n'y a pas de doublons
    from django.db.models import Count
    doublons = (
        Eleve.objects
        .values('matricule')
        .annotate(count=Count('id'))
        .filter(count__gt=1)
    )
    
    if doublons.exists():
        print(f"\n⚠️ ATTENTION: {doublons.count()} matricule(s) en double détecté(s)")
        for doublon in doublons:
            print(f"  - {doublon['matricule']}: {doublon['count']} fois")
    else:
        print(f"\n✓ Aucun matricule en double détecté")
    
    print("\n" + "="*70)
    print("FIN DU TEST")
    print("="*70 + "\n")


def test_reversion():
    """Remettre l'élève dans sa classe d'origine pour test répétable."""
    
    print("\n" + "="*70)
    print("REVERSION: Remettre l'élève dans sa classe d'origine")
    print("="*70)
    
    try:
        eleve = Eleve.objects.get(id=178)
        classe_origine = Classe.objects.get(nom="10ÈME ANNÉE (A)")
        
        print(f"\n🔄 Remise dans la classe d'origine...")
        print(f"  Élève: {eleve.prenom} {eleve.nom}")
        print(f"  De: {eleve.classe}")
        print(f"  Vers: {classe_origine}")
        
        user = User.objects.filter(is_superuser=True).first()
        if user:
            eleve._current_user = user
        
        eleve.classe = classe_origine
        eleve.save()
        
        print(f"\n✅ Élève remis dans sa classe d'origine")
        print(f"  Matricule: {eleve.matricule}")
        
    except Exception as e:
        print(f"\n❌ Erreur: {e}")
    
    print("\n" + "="*70 + "\n")


if __name__ == '__main__':
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == '--revert':
        test_reversion()
    else:
        test_changement_classe()
        
        # Proposer la reversion
        reponse = input("\nVoulez-vous remettre l'élève dans sa classe d'origine? (o/n): ")
        if reponse.lower() == 'o':
            test_reversion()
