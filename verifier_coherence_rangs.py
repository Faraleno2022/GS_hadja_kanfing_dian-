"""
Script de vérification de la cohérence des rangs
Vérifie que toutes les fonctions utilisent calculer_rang_intelligent()
"""
import os
import sys

# Chercher toutes les occurrences de calcul de rang dans le code
print("\n" + "="*80)
print("VÉRIFICATION DE LA COHÉRENCE DES RANGS")
print("="*80)

# Fichiers à vérifier
fichiers_a_verifier = [
    'notes/views.py',
    'notes/export_classement.py',
    'notes/calculs_intelligent.py'
]

print("\n🔍 Recherche des fonctions qui calculent des rangs...\n")

import re

fonctions_avec_rang = {}

for fichier in fichiers_a_verifier:
    chemin = os.path.join(os.path.dirname(__file__), fichier)
    if not os.path.exists(chemin):
        print(f"⚠️  Fichier non trouvé : {fichier}")
        continue
    
    with open(chemin, 'r', encoding='utf-8') as f:
        contenu = f.read()
        lignes = contenu.split('\n')
    
    # Chercher les fonctions qui utilisent calculer_rang_intelligent
    for i, ligne in enumerate(lignes, 1):
        if 'calculer_rang_intelligent' in ligne and 'import' not in ligne and 'def calculer_rang_intelligent' not in ligne:
            # Trouver le nom de la fonction englobante
            for j in range(i-1, max(0, i-50), -1):
                if lignes[j].startswith('def '):
                    nom_fonction = lignes[j].split('(')[0].replace('def ', '').strip()
                    if fichier not in fonctions_avec_rang:
                        fonctions_avec_rang[fichier] = []
                    fonctions_avec_rang[fichier].append({
                        'fonction': nom_fonction,
                        'ligne': i,
                        'code': ligne.strip()
                    })
                    break

print("✅ FONCTIONS UTILISANT calculer_rang_intelligent() :")
print("-"*80)
for fichier, fonctions in fonctions_avec_rang.items():
    print(f"\n📄 {fichier}")
    for func in fonctions:
        print(f"   ✓ {func['fonction']}() - ligne {func['ligne']}")
        print(f"     {func['code'][:70]}...")

# Chercher les fonctions qui calculent les rangs SANS utiliser calculer_rang_intelligent
print("\n" + "="*80)
print("⚠️  RECHERCHE DE CALCULS DE RANGS MANUELS (À ÉVITER)")
print("="*80)

patterns_suspects = [
    r'rang\s*=\s*\d+',
    r'enumerate.*start\s*=\s*1',
    r'\.sort\(.*moyenne.*reverse',
    r'rang_num\s*=\s*idx',
    r'rang_actuel\s*=',
]

calculs_manuels = {}

for fichier in fichiers_a_verifier:
    chemin = os.path.join(os.path.dirname(__file__), fichier)
    if not os.path.exists(chemin):
        continue
    
    with open(chemin, 'r', encoding='utf-8') as f:
        lignes = f.readlines()
    
    for i, ligne in enumerate(lignes, 1):
        # Ignorer les commentaires et la fonction calculer_rang_intelligent elle-même
        if ligne.strip().startswith('#') or 'def calculer_rang_intelligent' in ligne:
            continue
        
        for pattern in patterns_suspects:
            if re.search(pattern, ligne):
                # Vérifier si c'est dans une fonction qui utilise déjà calculer_rang_intelligent
                est_dans_fonction_ok = False
                for func_info in fonctions_avec_rang.get(fichier, []):
                    if abs(i - func_info['ligne']) < 50:
                        est_dans_fonction_ok = True
                        break
                
                if not est_dans_fonction_ok:
                    if fichier not in calculs_manuels:
                        calculs_manuels[fichier] = []
                    calculs_manuels[fichier].append({
                        'ligne': i,
                        'code': ligne.strip()
                    })
                break

if calculs_manuels:
    print("\n⚠️  CALCULS MANUELS DÉTECTÉS (à vérifier) :")
    for fichier, occurrences in calculs_manuels.items():
        print(f"\n📄 {fichier}")
        for occ in occurrences[:5]:  # Limiter à 5 pour ne pas surcharger
            print(f"   Ligne {occ['ligne']}: {occ['code'][:70]}")
else:
    print("\n✅ Aucun calcul manuel détecté !")

print("\n" + "="*80)
print("RÉSUMÉ")
print("="*80)
print(f"\n✅ Fonctions utilisant calculer_rang_intelligent() : {sum(len(f) for f in fonctions_avec_rang.values())}")
print(f"⚠️  Calculs manuels potentiels : {sum(len(c) for c in calculs_manuels.values())}")

print("\n" + "="*80)
print("RECOMMANDATIONS")
print("="*80)
print("""
✅ BONNES PRATIQUES :
1. Toujours utiliser calculer_rang_intelligent() pour calculer les rangs
2. Ne jamais recalculer les rangs manuellement
3. Utiliser la même période pour le classement et les bulletins
4. Traiter les absences comme 0 partout

⚠️  FONCTIONS À VÉRIFIER :
- consulter_notes() : Affichage classement web
- bulletin_dynamique_pdf() : Génération bulletin PDF individuel
- bulletins_dynamiques_classe_pdf() : Génération bulletins classe PDF
- _calculer_rangs() : Export classement Excel/PDF
""")

print("\n" + "="*80 + "\n")
