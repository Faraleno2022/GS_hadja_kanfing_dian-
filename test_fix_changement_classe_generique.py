#!/usr/bin/env python
"""
Script de test générique pour valider le correctif du bug de changement de classe.

Ce script s'adapte automatiquement aux données de votre base.
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ecole_moderne.settings')
django.setup()

from django.contrib.auth import get_user_model
from eleves.models import Eleve, Classe

User = get_user_model()


def lister_classes_avec_eleves():
    """Liste les classes ayant au moins 2 élèves."""
    print("\n" + "="*70)
    print("CLASSES DISPONIBLES (avec au moins 2 élèves)")
    print("="*70)
    
    classes_valides = []
    for classe in Classe.objects.all().order_by('nom'):
        nb_eleves = Eleve.objects.filter(classe=classe).count()
        if nb_eleves >= 2:
            print(f"\n  [{len(classes_valides) + 1}] {classe.nom}")
            print(f"      Année: {classe.annee_scolaire}")
            print(f"      Élèves: {nb_eleves}")
            classes_valides.append(classe)
    
    print("\n" + "="*70)
    return classes_valides


def choisir_eleve(classe):
    """Affiche les élèves d'une classe et permet d'en choisir un."""
    eleves = list(Eleve.objects.filter(classe=classe).order_by('nom')[:10])
    
    if not eleves:
        print(f"\n✗ Aucun élève dans la classe {classe.nom}")
        return None
    
    print(f"\n📋 Élèves de la classe {classe.nom} (10 premiers):")
    for i, eleve in enumerate(eleves, 1):
        print(f"  [{i}] {eleve.matricule} - {eleve.prenom} {eleve.nom}")
    
    return eleves


def test_changement_classe_interactif():
    """Test interactif du changement de classe."""
    
    print("\n" + "="*70)
    print("TEST INTERACTIF: Changement de classe")
    print("="*70)
    
    # 1. Lister les classes
    classes = lister_classes_avec_eleves()
    
    if len(classes) < 2:
        print("\n✗ Il faut au moins 2 classes avec des élèves pour tester")
        return
    
    # 2. Choisir la classe source
    try:
        choix = int(input(f"\nChoisissez la classe SOURCE (1-{len(classes)}): "))
        if choix < 1 or choix > len(classes):
            print("✗ Choix invalide")
            return
        classe_source = classes[choix - 1]
    except (ValueError, KeyboardInterrupt):
        print("\n✗ Annulé")
        return
    
    # 3. Afficher les élèves et choisir
    eleves = choisir_eleve(classe_source)
    if not eleves:
        return
    
    try:
        choix_eleve = int(input(f"\nChoisissez l'élève à transférer (1-{len(eleves)}): "))
        if choix_eleve < 1 or choix_eleve > len(eleves):
            print("✗ Choix invalide")
            return
        eleve = eleves[choix_eleve - 1]
    except (ValueError, KeyboardInterrupt):
        print("\n✗ Annulé")
        return
    
    # 4. Choisir la classe destination
    print("\n" + "-"*70)
    print("Classes DESTINATION disponibles:")
    print("-"*70)
    classes_dest = [c for c in classes if c.id != classe_source.id]
    
    for i, classe in enumerate(classes_dest, 1):
        nb = Eleve.objects.filter(classe=classe).count()
        print(f"  [{i}] {classe.nom} ({nb} élèves)")
    
    try:
        choix_dest = int(input(f"\nChoisissez la classe DESTINATION (1-{len(classes_dest)}): "))
        if choix_dest < 1 or choix_dest > len(classes_dest):
            print("✗ Choix invalide")
            return
        classe_dest = classes_dest[choix_dest - 1]
    except (ValueError, KeyboardInterrupt):
        print("\n✗ Annulé")
        return
    
    # 5. Afficher le résumé et confirmer
    print("\n" + "="*70)
    print("RÉSUMÉ DU TRANSFERT")
    print("="*70)
    print(f"\n  Élève: {eleve.matricule} - {eleve.prenom} {eleve.nom}")
    print(f"  De: {classe_source.nom}")
    print(f"  Vers: {classe_dest.nom}")
    
    confirmation = input("\n⚠️  Confirmer le transfert? (oui/non): ")
    if confirmation.lower() not in ['oui', 'o', 'yes', 'y']:
        print("\n✗ Transfert annulé")
        return
    
    # 6. Effectuer le transfert
    print("\n" + "="*70)
    print("EXÉCUTION DU TRANSFERT")
    print("="*70)
    
    ancien_matricule = eleve.matricule
    ancienne_classe = classe_source
    
    # Compter avant
    nb_avant_source = Eleve.objects.filter(classe=classe_source).count()
    nb_avant_dest = Eleve.objects.filter(classe=classe_dest).count()
    
    print(f"\n📊 État AVANT:")
    print(f"  Classe source: {nb_avant_source} élèves")
    print(f"  Classe destination: {nb_avant_dest} élèves")
    
    # Afficher les 3 premiers matricules de la classe source
    print(f"\n📋 Matricules classe source (3 premiers):")
    for e in Eleve.objects.filter(classe=classe_source).order_by('matricule')[:3]:
        print(f"  - {e.matricule}: {e.prenom} {e.nom}")
    
    try:
        # Récupérer un utilisateur pour le contexte
        user = User.objects.filter(is_superuser=True).first()
        if not user:
            user = User.objects.first()
        if user:
            eleve._current_user = user
        
        # Effectuer le changement
        print(f"\n🔄 Changement en cours...")
        eleve.classe = classe_dest
        eleve.save()
        
        print(f"\n✅ SUCCÈS: Transfert effectué sans erreur!")
        print(f"  Ancien matricule: {ancien_matricule}")
        print(f"  Nouveau matricule: {eleve.matricule}")
        
    except Exception as e:
        print(f"\n❌ ERREUR lors du transfert:")
        print(f"  Type: {type(e).__name__}")
        print(f"  Message: {str(e)}")
        
        # Afficher la traceback complète
        import traceback
        print(f"\n📜 Traceback complet:")
        traceback.print_exc()
        return
    
    # 7. Vérifier l'état après
    nb_apres_source = Eleve.objects.filter(classe=ancienne_classe).count()
    nb_apres_dest = Eleve.objects.filter(classe=classe_dest).count()
    
    print(f"\n📊 État APRÈS:")
    print(f"  Classe source: {nb_apres_source} élèves (était {nb_avant_source})")
    print(f"  Classe destination: {nb_apres_dest} élèves (était {nb_avant_dest})")
    
    # Vérifier que les comptes sont cohérents
    if nb_apres_source == nb_avant_source - 1 and nb_apres_dest == nb_avant_dest + 1:
        print(f"\n✓ Comptages cohérents")
    else:
        print(f"\n⚠️ ATTENTION: Comptages incohérents!")
    
    # Afficher les matricules de la classe source après réaffectation
    print(f"\n📋 Matricules classe source (après réaffectation, 3 premiers):")
    for e in Eleve.objects.filter(classe=ancienne_classe).order_by('matricule')[:3]:
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
        print(f"\n⚠️ ATTENTION: {doublons.count()} matricule(s) en double!")
        for doublon in doublons:
            print(f"  - {doublon['matricule']}: {doublon['count']} fois")
    else:
        print(f"\n✓ Aucun matricule en double détecté")
    
    # 9. Proposer la reversion
    print("\n" + "="*70)
    revert = input(f"\n🔙 Remettre l'élève dans sa classe d'origine? (oui/non): ")
    
    if revert.lower() in ['oui', 'o', 'yes', 'y']:
        print(f"\n🔄 Reversion en cours...")
        try:
            eleve.classe = ancienne_classe
            eleve.save()
            print(f"✅ Élève remis dans {ancienne_classe.nom}")
            print(f"   Matricule: {eleve.matricule}")
        except Exception as e:
            print(f"❌ Erreur: {e}")
    
    print("\n" + "="*70)
    print("FIN DU TEST")
    print("="*70 + "\n")


def test_automatique_rapide():
    """Test automatique rapide sans interaction."""
    print("\n" + "="*70)
    print("TEST AUTOMATIQUE RAPIDE")
    print("="*70)
    
    # Trouver deux classes avec des élèves
    classes_avec_eleves = []
    for classe in Classe.objects.all():
        if Eleve.objects.filter(classe=classe).count() >= 2:
            classes_avec_eleves.append(classe)
            if len(classes_avec_eleves) == 2:
                break
    
    if len(classes_avec_eleves) < 2:
        print("\n✗ Pas assez de classes pour le test automatique")
        return
    
    classe_source = classes_avec_eleves[0]
    classe_dest = classes_avec_eleves[1]
    
    # Prendre le dernier élève de la classe source
    eleve = Eleve.objects.filter(classe=classe_source).order_by('-id').first()
    
    if not eleve:
        print("\n✗ Aucun élève trouvé")
        return
    
    print(f"\n✓ Élève: {eleve.matricule} - {eleve.prenom} {eleve.nom}")
    print(f"✓ De: {classe_source.nom}")
    print(f"✓ Vers: {classe_dest.nom}")
    
    ancien_matricule = eleve.matricule
    ancienne_classe = classe_source
    
    try:
        user = User.objects.filter(is_superuser=True).first() or User.objects.first()
        if user:
            eleve._current_user = user
        
        print(f"\n🔄 Transfert...")
        eleve.classe = classe_dest
        eleve.save()
        
        print(f"✅ SUCCÈS")
        print(f"   Ancien: {ancien_matricule}")
        print(f"   Nouveau: {eleve.matricule}")
        
        # Reversion immédiate
        print(f"\n🔄 Reversion...")
        eleve.classe = ancienne_classe
        eleve.save()
        print(f"✅ Remis dans la classe d'origine")
        
    except Exception as e:
        print(f"\n❌ ERREUR: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "="*70 + "\n")


if __name__ == '__main__':
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == '--auto':
        test_automatique_rapide()
    else:
        test_changement_classe_interactif()
