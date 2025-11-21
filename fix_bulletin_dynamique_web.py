"""
Script pour corriger le bug de rang dans bulletin_dynamique (vue web)
À exécuter sur le serveur de production
"""
import sys

# Lire le fichier
with open('notes/views.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

print("Correction du bug de rang dans bulletin_dynamique...")

# Trouver et corriger la section autour de la ligne 5371
corrections = 0
in_bulletin_dynamique = False
in_rang_section = False

for i, line in enumerate(lines, 1):
    # Détecter le début de la fonction bulletin_dynamique
    if 'def bulletin_dynamique(' in line:
        in_bulletin_dynamique = True
        print(f"✓ Fonction bulletin_dynamique trouvée à la ligne {i}")
    
    # Détecter la fin de la fonction (prochaine fonction)
    if in_bulletin_dynamique and i > 5000 and line.startswith('def ') and 'bulletin_dynamique' not in line:
        in_bulletin_dynamique = False
    
    # Chercher la section de calcul du rang dans bulletin_dynamique
    if in_bulletin_dynamique and 'for idx, (eid, moy) in enumerate(all_moyennes' in line:
        in_rang_section = True
        print(f"✓ Section de calcul du rang trouvée à la ligne {i}")
    
    # Corriger le bug rang_actuel = idx
    if in_rang_section and 'rang_actuel = idx' in line and i < 5400:
        # Vérifier que c'est bien dans le else après ex-aequo
        if i > 0 and 'else:' in lines[i-2]:
            print(f"\n❌ Bug trouvé à la ligne {i}: {line.strip()}")
            print(f"   Contexte: {lines[i-2].strip()}")
            
            # Remplacer par le calcul correct
            indent = len(line) - len(line.lstrip())
            lines[i-1] = ' ' * indent + "# Calculer le rang avec gestion ex-aequo\n"
            lines[i] = ' ' * indent + "rang_actuel = idx\n"
            
            corrections += 1
            print(f"✓ Correction appliquée")
            in_rang_section = False

if corrections > 0:
    # Sauvegarder le fichier corrigé
    with open('notes/views.py', 'w', encoding='utf-8') as f:
        f.writelines(lines)
    print(f"\n✅ {corrections} correction(s) appliquée(s)")
    print("Fichier notes/views.py mis à jour")
else:
    print("\n⚠️  Aucune correction nécessaire (déjà corrigé ou pattern non trouvé)")

print("\nProchaines étapes:")
print("1. Redémarrer le serveur: touch ecole_moderne/wsgi.py")
print("2. Tester le bulletin web")
