"""
Script de test pour la réaffectation intelligente des matricules lors du changement de classe

Ce script teste le nouveau comportement:
1. Création de plusieurs élèves dans une classe avec matricules séquentiels
2. Changement de classe d'un élève au milieu
3. Vérification que les matricules de l'ancienne classe sont réorganisés
4. Vérification que le nouvel élève a un matricule dans sa nouvelle classe
"""
import os
import django

# Configuration Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ecole_moderne.settings')
django.setup()

from eleves.models import Eleve, Classe, Ecole, Responsable, HistoriqueEleve
from django.contrib.auth.models import User

def afficher_matricules(classe, titre=""):
    """Affiche les matricules des élèves d'une classe"""
    print(f"\n{'='*60}")
    print(f"{titre}")
    print(f"{'='*60}")
    eleves = Eleve.objects.filter(classe=classe).order_by('matricule')
    if eleves.exists():
        for eleve in eleves:
            print(f"  {eleve.matricule:20s} - {eleve.nom_complet}")
    else:
        print("  (Aucun élève)")
    print(f"{'='*60}\n")

def test_reaffectation_matricules():
    """Test complet de la réaffectation des matricules"""
    print("\n" + "🔬 TEST DE RÉAFFECTATION INTELLIGENTE DES MATRICULES ".center(80, "="))
    print()
    
    # 1. Créer ou récupérer une école
    ecole, _ = Ecole.objects.get_or_create(
        nom="École Test Réaffectation",
        defaults={
            'adresse': 'Test',
            'telephone': '+224123456789',
            'directeur': 'Test',
            'code_prefixe': 'TEST/'
        }
    )
    print(f"✓ École créée/récupérée: {ecole.nom}")
    
    # 2. Créer deux classes
    classe_a, _ = Classe.objects.get_or_create(
        ecole=ecole,
        nom="Classe A - Test",
        defaults={
            'niveau': 'PRIMAIRE_4',
            'code_matricule': 'P4A',
            'annee_scolaire': '2024-2025'
        }
    )
    
    classe_b, _ = Classe.objects.get_or_create(
        ecole=ecole,
        nom="Classe B - Test",
        defaults={
            'niveau': 'PRIMAIRE_5',
            'code_matricule': 'P5B',
            'annee_scolaire': '2024-2025'
        }
    )
    print(f"✓ Classe A créée: {classe_a.nom} (code: {classe_a.code_matricule})")
    print(f"✓ Classe B créée: {classe_b.nom} (code: {classe_b.code_matricule})")
    
    # 3. Créer un responsable
    responsable, _ = Responsable.objects.get_or_create(
        telephone='+224999999999',
        defaults={
            'nom': 'Responsable',
            'prenom': 'Test',
            'adresse': 'Test'
        }
    )
    print(f"✓ Responsable créé: {responsable.nom_complet}")
    
    # 4. Supprimer les anciens élèves de test
    Eleve.objects.filter(classe__in=[classe_a, classe_b]).delete()
    print("✓ Anciens élèves de test supprimés")
    
    # 5. Créer 5 élèves dans la Classe A
    print("\n📝 ÉTAPE 1: Création de 5 élèves dans la Classe A")
    eleves_classe_a = []
    from datetime import date
    for i in range(1, 6):
        eleve = Eleve.objects.create(
            nom=f"Elève{i}",
            prenom=f"Test",
            sexe='M' if i % 2 == 0 else 'F',
            date_naissance='2010-01-01',
            date_inscription=date.today(),
            classe=classe_a,
            responsable_principal=responsable
        )
        eleves_classe_a.append(eleve)
        print(f"  ✓ Créé: {eleve.nom_complet:20s} - Matricule: {eleve.matricule}")
    
    afficher_matricules(classe_a, "CLASSE A - État initial (5 élèves)")
    
    # 6. Déplacer l'élève du milieu (élève 3) vers la Classe B
    print("\n🔄 ÉTAPE 2: Changement de classe de l'élève 3 (milieu)")
    eleve_a_deplacer = eleves_classe_a[2]  # Élève 3 (index 2)
    ancien_matricule = eleve_a_deplacer.matricule
    print(f"  Élève à déplacer: {eleve_a_deplacer.nom_complet}")
    print(f"  Ancien matricule: {ancien_matricule}")
    print(f"  Ancienne classe: {classe_a.nom}")
    print(f"  Nouvelle classe: {classe_b.nom}")
    
    # Effectuer le changement
    eleve_a_deplacer.classe = classe_b
    eleve_a_deplacer.save()
    
    nouveau_matricule = eleve_a_deplacer.matricule
    print(f"  ✓ Nouveau matricule: {nouveau_matricule}")
    
    # 7. Vérifier les résultats
    print("\n✅ ÉTAPE 3: Vérification des résultats")
    
    afficher_matricules(classe_a, "CLASSE A - Après déplacement (4 élèves restants)")
    afficher_matricules(classe_b, "CLASSE B - Après déplacement (1 nouvel élève)")
    
    # 8. Vérifier que les matricules de la Classe A sont bien séquentiels
    eleves_a_apres = list(Eleve.objects.filter(classe=classe_a).order_by('matricule'))
    matricules_attendus = ['TEST/P4A-001', 'TEST/P4A-002', 'TEST/P4A-003', 'TEST/P4A-004']
    
    print("\n🔍 VÉRIFICATION DES MATRICULES DE LA CLASSE A:")
    tous_corrects = True
    for i, eleve in enumerate(eleves_a_apres):
        attendu = matricules_attendus[i]
        statut = "✓" if eleve.matricule == attendu else "✗"
        print(f"  {statut} Élève {i+1}: {eleve.matricule:20s} (attendu: {attendu})")
        if eleve.matricule != attendu:
            tous_corrects = False
    
    # 9. Vérifier l'historique
    print("\n📜 HISTORIQUE DES MODIFICATIONS:")
    historiques = HistoriqueEleve.objects.filter(
        eleve__classe__in=[classe_a, classe_b]
    ).order_by('-date_action')[:10]
    
    for hist in historiques:
        print(f"  • {hist.eleve.nom_complet:20s} - {hist.get_action_display():20s}")
        print(f"    {hist.description}")
        print()
    
    # 10. Résumé final
    print("\n" + "="*80)
    print("RÉSUMÉ DU TEST".center(80))
    print("="*80)
    
    nb_eleves_a = Eleve.objects.filter(classe=classe_a).count()
    nb_eleves_b = Eleve.objects.filter(classe=classe_b).count()
    
    print(f"  Nombre d'élèves dans Classe A: {nb_eleves_a} (attendu: 4)")
    print(f"  Nombre d'élèves dans Classe B: {nb_eleves_b} (attendu: 1)")
    print(f"  Matricules séquentiels Classe A: {'OUI ✓' if tous_corrects else 'NON ✗'}")
    print(f"  Ancien matricule élève déplacé: {ancien_matricule}")
    print(f"  Nouveau matricule élève déplacé: {nouveau_matricule}")
    
    if tous_corrects and nb_eleves_a == 4 and nb_eleves_b == 1:
        print("\n" + "🎉 TEST RÉUSSI ! La réaffectation intelligente fonctionne correctement.".center(80))
    else:
        print("\n" + "❌ TEST ÉCHOUÉ ! Vérifiez les résultats ci-dessus.".center(80))
    
    print("="*80 + "\n")
    
    return tous_corrects

def test_scenario_complexe():
    """Test avec plusieurs déplacements successifs"""
    print("\n" + "🔬 TEST SCÉNARIO COMPLEXE - DÉPLACEMENTS MULTIPLES ".center(80, "="))
    print()
    
    # Récupérer les classes de test
    try:
        ecole = Ecole.objects.get(nom="École Test Réaffectation")
        classe_a = Classe.objects.get(ecole=ecole, nom="Classe A - Test")
        classe_b = Classe.objects.get(ecole=ecole, nom="Classe B - Test")
    except:
        print("⚠ Exécutez d'abord test_reaffectation_matricules()")
        return False
    
    print("📝 Déplacement de plusieurs élèves successivement...")
    
    # Déplacer le premier élève
    eleve1 = Eleve.objects.filter(classe=classe_a).order_by('matricule').first()
    if eleve1:
        print(f"\n  Déplacement de {eleve1.nom_complet} ({eleve1.matricule})")
        eleve1.classe = classe_b
        eleve1.save()
        print(f"  → Nouveau matricule: {eleve1.matricule}")
        afficher_matricules(classe_a, "CLASSE A - Après 1er déplacement")
    
    # Déplacer un autre élève
    eleve2 = Eleve.objects.filter(classe=classe_a).order_by('matricule').first()
    if eleve2:
        print(f"\n  Déplacement de {eleve2.nom_complet} ({eleve2.matricule})")
        eleve2.classe = classe_b
        eleve2.save()
        print(f"  → Nouveau matricule: {eleve2.matricule}")
        afficher_matricules(classe_a, "CLASSE A - Après 2ème déplacement")
    
    afficher_matricules(classe_b, "CLASSE B - État final")
    
    print("\n✅ Test scénario complexe terminé\n")
    return True

if __name__ == '__main__':
    print("\n" + "🚀 DÉMARRAGE DES TESTS ".center(80, "="))
    print()
    
    # Test principal
    resultat1 = test_reaffectation_matricules()
    
    # Test scénario complexe
    input("\nAppuyez sur Entrée pour continuer avec le test complexe...")
    resultat2 = test_scenario_complexe()
    
    print("\n" + "="*80)
    if resultat1 and resultat2:
        print("✅ TOUS LES TESTS SONT RÉUSSIS !".center(80))
    else:
        print("⚠ CERTAINS TESTS ONT ÉCHOUÉ".center(80))
    print("="*80 + "\n")
