#!/bin/bash

echo "=========================================="
echo "NETTOYAGE ET COMMIT DES MODIFICATIONS"
echo "=========================================="

# 1. Supprimer les fichiers de backup et temporaires
echo ""
echo "1. Suppression des fichiers temporaires..."
rm -rf backups_rangs_20251120_071556/
rm -f notes/.export_classement.py.swp
rm -f notes/bulletin_intelligent.py.backup
rm -f notes/bulletin_intelligent.py.bak2
rm -f notes/calculs.py.backup
rm -f notes/calculs_intelligent.py.bak3
rm -f notes/export_classement.py.bak
rm -f notes/export_classement_fixed.py.bak
rm -f fix_all_rangs.sh

echo "✅ Fichiers temporaires supprimés"

# 2. Vérifier les modifications importantes
echo ""
echo "2. Vérification des modifications..."
git status

# 3. Ajouter les fichiers modifiés importants
echo ""
echo "3. Ajout des fichiers modifiés..."
git add notes/bulletin_intelligent.py
git add notes/calculs.py
git add notes/calculs_intelligent.py
git add notes/export_classement_fixed.py
git add test_bulletin_classe.py

echo "✅ Fichiers modifiés ajoutés"

# 4. Ajouter les scripts de test utiles
echo ""
echo "4. Ajout des scripts de test..."
git add test_bulletin_ex_aequo.py
git add test_rang_direct.py
git add test_validation_rang.py

echo "✅ Scripts de test ajoutés"

# 5. Afficher le statut
echo ""
echo "5. Statut final..."
git status

# 6. Créer le commit
echo ""
echo "6. Création du commit..."
git commit -m "Fix: Corrections supplémentaires cohérence rangs

MODIFICATIONS:
- notes/bulletin_intelligent.py: Améliorations calcul rangs
- notes/calculs.py: Harmonisation fonctions
- notes/calculs_intelligent.py: Optimisations
- notes/export_classement_fixed.py: Corrections export
- test_bulletin_classe.py: Tests mis à jour

SCRIPTS DE TEST AJOUTÉS:
- test_bulletin_ex_aequo.py: Test gestion ex-aequo
- test_rang_direct.py: Test calcul direct rangs
- test_validation_rang.py: Validation complète rangs

NETTOYAGE:
- Suppression fichiers backup (.backup, .bak, .swp)
- Suppression dossiers temporaires

STATUT: Tests validés, prêt pour production"

echo ""
echo "✅ Commit créé"

# 7. Pousser vers GitHub
echo ""
echo "7. Push vers GitHub..."
git push origin main

echo ""
echo "=========================================="
echo "✅ TERMINÉ !"
echo "=========================================="
