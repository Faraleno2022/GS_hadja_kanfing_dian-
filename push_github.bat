@echo off
echo ================================================================================
echo                    MISE A JOUR SUR GITHUB
echo ================================================================================
echo.

echo [1/4] Verification du statut Git...
git status

echo.
echo [2/4] Ajout de tous les fichiers modifies...
git add .

echo.
echo [3/4] Creation du commit...
git commit -m "🔧 Corrections et améliorations majeures

✅ Corrections bulletins:
- Correction bulletin vide (recherche flexible classes)
- Ajout scripts diagnostic (diagnostiquer_bulletin.py)
- Ajout scripts correction (corriger_correspondance_classes.py)
- Générateur de données test (generer_donnees_bulletin.py)

✅ Corrections statistiques notes:
- Ajout liste des classes dans la vue statistiques
- Sélecteur de classes maintenant fonctionnel
- Documentation complète

✅ Cartes scolaires améliorées:
- Taille augmentée: 105×74mm
- Nouvelles informations: sexe, contact urgence, adresse école
- Photo et logo agrandis
- Design professionnel

✅ Notes mensuelles:
- 9 périodes mensuelles ajoutées (OCTOBRE à JUIN)
- Migration 0007 appliquée
- Documentation complète

✅ Scripts et documentation:
- Scripts de vérification et test
- Documentation technique détaillée
- Guides de correction

📅 Date: 1er novembre 2025
👤 Par: Faraleno
🎯 Version: Production Ready"

echo.
echo [4/4] Envoi vers GitHub...
git push origin main

echo.
echo ================================================================================
echo                    ✅ MISE A JOUR TERMINEE
echo ================================================================================
echo.
echo Vos modifications sont maintenant sur GitHub !
echo.

pause
