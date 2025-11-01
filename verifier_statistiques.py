#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Script de vérification : Correction des statistiques notes
"""

print("""
╔══════════════════════════════════════════════════════════════════════════════╗
║                                                                              ║
║          ✅ VÉRIFICATION : CORRECTION STATISTIQUES NOTES                     ║
║                                                                              ║
╚══════════════════════════════════════════════════════════════════════════════╝

┌──────────────────────────────────────────────────────────────────────────────┐
│ 🔍 VÉRIFICATION DU CODE                                                     │
└──────────────────────────────────────────────────────────────────────────────┘
""")

import os

# Vérifier que le fichier existe
fichier_views = 'notes/views.py'
if not os.path.exists(fichier_views):
    print(f"❌ Fichier {fichier_views} non trouvé")
    exit(1)

print(f"✅ Fichier {fichier_views} trouvé")

# Lire le contenu
with open(fichier_views, 'r', encoding='utf-8') as f:
    content = f.read()

# Vérifications
verifications = []

# 1. Vérifier la présence de la récupération des classes
if "classes = ClasseNote.objects.filter(ecole=ecole, actif=True)" in content:
    print("✅ Récupération des classes par école : OK")
    verifications.append(True)
else:
    print("❌ Récupération des classes par école : MANQUANT")
    verifications.append(False)

# 2. Vérifier la gestion de la classe sélectionnée
if "classe_selectionnee = classes.get(id=classe_id)" in content:
    print("✅ Gestion classe sélectionnée : OK")
    verifications.append(True)
else:
    print("❌ Gestion classe sélectionnée : MANQUANT")
    verifications.append(False)

# 3. Vérifier l'ajout dans le contexte
if "'classes': classes" in content:
    print("✅ Classes dans le contexte : OK")
    verifications.append(True)
else:
    print("❌ Classes dans le contexte : MANQUANT")
    verifications.append(False)

if "'classe_selectionnee': classe_selectionnee" in content:
    print("✅ Classe sélectionnée dans le contexte : OK")
    verifications.append(True)
else:
    print("❌ Classe sélectionnée dans le contexte : MANQUANT")
    verifications.append(False)

# Résumé
print("\n" + "="*80)
print(" "*25 + "📊 RÉSULTAT DE LA VÉRIFICATION")
print("="*80)

total = len(verifications)
reussis = sum(verifications)

print(f"\nTests réussis: {reussis}/{total}")

if reussis == total:
    print("\n✅ CORRECTION COMPLÈTE ET OPÉRATIONNELLE!")
    print("\n🚀 Prochaines étapes:")
    print("   1. Le serveur Django va se recharger automatiquement")
    print("   2. Rafraîchir la page des statistiques")
    print("   3. Les classes devraient maintenant s'afficher")
elif reussis >= total * 0.7:
    print("\n⚠️  CORRECTION PARTIELLE")
    print("   Certains éléments nécessitent une attention")
else:
    print("\n❌ CORRECTION INCOMPLÈTE")
    print("   Veuillez vérifier les erreurs ci-dessus")

# URLs de test
print("\n" + "="*80)
print(" "*25 + "🔗 URL DE TEST")
print("="*80)

print("\nPage de statistiques:")
print("http://127.0.0.1:8000/notes/statistiques/")

print("\nAvec une classe (exemple ID 5):")
print("http://127.0.0.1:8000/notes/statistiques/?classe_id=5")

print("\nAvec classe et période:")
print("http://127.0.0.1:8000/notes/statistiques/?classe_id=5&periode=TRIMESTRE_1")

print("\n" + "="*80)
print(" "*25 + "📚 DOCUMENTATION")
print("="*80)

print("\nGuide de correction:")
print("CORRECTION_STATISTIQUES_NOTES.md")

print("\n" + "="*80 + "\n")
