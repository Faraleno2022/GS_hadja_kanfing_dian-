"""
Test pour vérifier la cohérence du calcul des rangs après le fix
"""

from decimal import Decimal

def calculer_rang_avec_exaequo(moyennes_classe, eleve_id):
    """
    Simule le calcul du rang avec la nouvelle logique corrigée
    """
    # Trier par moyenne décroissante
    moyennes_classe.sort(key=lambda x: x[1], reverse=True)
    
    # Trouver le rang avec gestion des ex-aequo
    rang_num = None
    rang_actuel = 1
    prev_moy = None
    
    for idx, (eid, moy) in enumerate(moyennes_classe, start=1):
        # Déterminer le rang de cet élève
        if prev_moy is not None and abs(moy - prev_moy) < Decimal('0.01'):
            # Ex-aequo : garde le même rang que le précédent
            pass  # rang_actuel ne change pas
        else:
            # Nouveau rang : utilise la position réelle
            rang_actuel = idx
        
        # Vérifier si c'est notre élève
        if eid == eleve_id:
            rang_num = rang_actuel
            break
        
        prev_moy = moy
    
    return rang_num

def test_cas_normal():
    """Test sans ex-aequo"""
    print("\n📝 TEST 1 : Cas normal (sans ex-aequo)")
    print("-" * 50)
    
    moyennes = [
        ('L12SC-021', Decimal('9.92')),
        ('L12SC-019', Decimal('9.42')),
        ('L12SC-022', Decimal('9.38')),  # Notre élève test
        ('L12SC-012', Decimal('9.33')),
    ]
    
    # Tester pour l'élève L12SC-022 (DIALLO Alpha Ousmane)
    rang = calculer_rang_avec_exaequo(moyennes.copy(), 'L12SC-022')
    
    print("Classement :")
    moyennes_triees = sorted(moyennes, key=lambda x: x[1], reverse=True)
    for i, (eid, moy) in enumerate(moyennes_triees, 1):
        marker = " ⭐" if eid == 'L12SC-022' else ""
        print(f"  {i}. {eid} : {moy}/20{marker}")
    
    print(f"\nRang calculé pour L12SC-022 : {rang}ème")
    
    # Vérification
    if rang == 3:
        print("✅ TEST RÉUSSI : Le rang est correct (3ème)")
    else:
        print(f"❌ TEST ÉCHOUÉ : Rang attendu 3, obtenu {rang}")
    
    return rang == 3

def test_avec_exaequo_avant():
    """Test avec ex-aequo avant notre élève"""
    print("\n📝 TEST 2 : Ex-aequo avant l'élève")
    print("-" * 50)
    
    moyennes = [
        ('L12SC-001', Decimal('15.50')),
        ('L12SC-002', Decimal('15.50')),  # Ex-aequo avec le 1er
        ('L12SC-003', Decimal('14.00')),
        ('L12SC-022', Decimal('9.38')),   # Notre élève test
        ('L12SC-004', Decimal('9.00')),
    ]
    
    rang = calculer_rang_avec_exaequo(moyennes.copy(), 'L12SC-022')
    
    print("Classement avec ex-aequo :")
    moyennes_triees = sorted(moyennes, key=lambda x: x[1], reverse=True)
    
    rang_affiche = 1
    prev_moy = None
    for i, (eid, moy) in enumerate(moyennes_triees, 1):
        if prev_moy is not None and abs(moy - prev_moy) < Decimal('0.01'):
            pass  # Garde le même rang
        else:
            rang_affiche = i
        
        marker = " ⭐" if eid == 'L12SC-022' else ""
        ex_marker = " (ex-aequo)" if prev_moy and abs(moy - prev_moy) < Decimal('0.01') else ""
        print(f"  {rang_affiche}. {eid} : {moy}/20{marker}{ex_marker}")
        prev_moy = moy
    
    print(f"\nRang calculé pour L12SC-022 : {rang}ème")
    
    # Vérification : avec 2 ex-aequo 1ers, le 3ème élève est 3ème, notre élève est 4ème
    if rang == 4:
        print("✅ TEST RÉUSSI : Le rang est correct avec ex-aequo")
    else:
        print(f"❌ TEST ÉCHOUÉ : Rang attendu 4, obtenu {rang}")
    
    return rang == 4

def test_eleve_exaequo():
    """Test où notre élève est ex-aequo avec un autre"""
    print("\n📝 TEST 3 : Élève en ex-aequo")
    print("-" * 50)
    
    moyennes = [
        ('L12SC-001', Decimal('15.50')),
        ('L12SC-002', Decimal('14.00')),
        ('L12SC-022', Decimal('9.38')),   # Notre élève test
        ('L12SC-003', Decimal('9.38')),   # Ex-aequo avec notre élève
        ('L12SC-004', Decimal('9.00')),
    ]
    
    rang = calculer_rang_avec_exaequo(moyennes.copy(), 'L12SC-022')
    
    print("Classement avec notre élève ex-aequo :")
    moyennes_triees = sorted(moyennes, key=lambda x: x[1], reverse=True)
    
    rang_affiche = 1
    prev_moy = None
    for i, (eid, moy) in enumerate(moyennes_triees, 1):
        if prev_moy is not None and abs(moy - prev_moy) < Decimal('0.01'):
            pass  # Garde le même rang
        else:
            rang_affiche = i
        
        marker = " ⭐" if eid == 'L12SC-022' else ""
        ex_marker = " (ex-aequo)" if prev_moy and abs(moy - prev_moy) < Decimal('0.01') else ""
        print(f"  {rang_affiche}. {eid} : {moy}/20{marker}{ex_marker}")
        prev_moy = moy
    
    print(f"\nRang calculé pour L12SC-022 : {rang}ème")
    
    # Vérification : notre élève doit être 3ème (ex-aequo)
    if rang == 3:
        print("✅ TEST RÉUSSI : L'élève ex-aequo a le bon rang")
    else:
        print(f"❌ TEST ÉCHOUÉ : Rang attendu 3, obtenu {rang}")
    
    return rang == 3

def test_classe_complete():
    """Test avec la vraie classe 12ème Scientifique"""
    print("\n📝 TEST 4 : Classe complète 12ème Scientifique")
    print("-" * 50)
    
    moyennes = [
        ('L12SC-009', Decimal('15.38')),
        ('L12SC-011', Decimal('14.81')),
        ('L12SC-020', Decimal('14.39')),
        ('L12SC-010', Decimal('13.12')),
        ('L12SC-015', Decimal('10.54')),
        ('L12SC-017', Decimal('10.17')),
        ('L12SC-021', Decimal('9.92')),
        ('L12SC-019', Decimal('9.42')),
        ('L12SC-022', Decimal('9.38')),  # DIALLO Alpha Ousmane
        ('L12SC-012', Decimal('9.33')),
        ('L12SC-018', Decimal('9.12')),
        ('L12SC-023', Decimal('9.04')),
        ('L12SC-007', Decimal('8.54')),
        ('L12SC-016', Decimal('8.44')),
        ('L12SC-008', Decimal('7.42')),
        ('L12SC-006', Decimal('6.62')),
        ('L12SC-013', Decimal('6.00')),
        ('L12SC-014', Decimal('4.67')),
    ]
    
    rang = calculer_rang_avec_exaequo(moyennes.copy(), 'L12SC-022')
    
    print("Extrait du classement autour de L12SC-022 :")
    moyennes_triees = sorted(moyennes, key=lambda x: x[1], reverse=True)
    
    # Afficher seulement les positions 6 à 11
    for i, (eid, moy) in enumerate(moyennes_triees, 1):
        if 6 <= i <= 11:
            marker = " ⭐" if eid == 'L12SC-022' else ""
            print(f"  {i}. {eid} : {moy}/20{marker}")
    
    print(f"\nRang calculé pour L12SC-022 : {rang}ème")
    
    # Vérification : DIALLO doit être 9ème
    if rang == 9:
        print("✅ TEST RÉUSSI : DIALLO Alpha Ousmane est bien 9ème")
    else:
        print(f"❌ TEST ÉCHOUÉ : Rang attendu 9, obtenu {rang}")
    
    return rang == 9

if __name__ == "__main__":
    print("=" * 60)
    print("🔧 TEST DE COHÉRENCE DU CALCUL DES RANGS")
    print("=" * 60)
    
    tests_reussis = 0
    tests_total = 0
    
    # Exécuter tous les tests
    tests = [
        test_cas_normal,
        test_avec_exaequo_avant,
        test_eleve_exaequo,
        test_classe_complete
    ]
    
    for test_func in tests:
        tests_total += 1
        if test_func():
            tests_reussis += 1
    
    # Résumé
    print("\n" + "=" * 60)
    print("📊 RÉSUMÉ DES TESTS")
    print("=" * 60)
    print(f"Tests réussis : {tests_reussis}/{tests_total}")
    
    if tests_reussis == tests_total:
        print("\n🎉 TOUS LES TESTS SONT PASSÉS !")
        print("Le calcul des rangs est maintenant cohérent.")
    else:
        print(f"\n⚠️ {tests_total - tests_reussis} test(s) ont échoué")
        print("Vérifier la logique de calcul des rangs.")
