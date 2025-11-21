#!/bin/bash
# Script rapide pour nettoyer et commiter

echo "🧹 Nettoyage..."
rm -rf backups_rangs_20251120_071556/
rm -f notes/.export_classement.py.swp notes/*.backup notes/*.bak* fix_all_rangs.sh

echo "📦 Ajout des fichiers..."
git add notes/bulletin_intelligent.py notes/calculs.py notes/calculs_intelligent.py notes/export_classement_fixed.py test_bulletin_classe.py
git add test_bulletin_ex_aequo.py test_rang_direct.py test_validation_rang.py 2>/dev/null

echo "💾 Commit..."
git commit -m "Fix: Corrections supplémentaires cohérence rangs

- Améliorations calcul rangs et gestion ex-aequo
- Harmonisation fonctions de calcul
- Optimisations export classement
- Tests de validation ajoutés
- Nettoyage fichiers temporaires"

echo "🚀 Push vers GitHub..."
git push origin main

echo "✅ Terminé !"
