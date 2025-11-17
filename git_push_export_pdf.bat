@echo off
REM Script de mise à jour GitHub - Export PDF des classements
REM Date: 17 Novembre 2024

echo ===================================================================
echo    MISE A JOUR GITHUB - Export PDF des classements
echo ===================================================================
echo.

REM 1. Vérifier le statut actuel
echo [36m Verification du statut Git...[0m
git status
echo.

REM 2. Ajouter tous les fichiers modifiés et créés
echo [32m Ajout des fichiers modifies...[0m

REM Fichiers principaux modifiés
git add notes/export_classement.py
git add notes/urls.py
git add templates/notes/consulter_notes.html

REM Fichiers de documentation
git add EXPORT_CLASSEMENT_PDF_17_NOV_2024.md
git add RESUME_EXPORT_PDF_CLASSEMENT.txt
git add EXPORT_PDF_SIMPLE.txt
git add COMMIT_MESSAGE_EXPORT_PDF.txt

REM Fichiers de la correction précédente
git add FIX_EXPORT_CLASSEMENT_17_NOV_2024.md
git add RESUME_FIX_EXPORT_CLASSEMENT.txt
git add SOLUTION_RAPIDE_EXPORT_CLASSEMENT.txt
git add COMMIT_MESSAGE_EXPORT_CLASSEMENT.txt

REM Scripts de test
git add test_export_classement_diagnostic.py
git add test_export_classement_fixed.py
git add test_export_simple.py
git add verifier_correction_complete.py
git add test_export_classement_pdf.py

REM Scripts Git
git add git_push_export_pdf.sh
git add git_push_export_pdf.bat

echo [32m Fichiers ajoutes[0m
echo.

REM 3. Afficher les fichiers à commiter
echo [36m Fichiers a commiter:[0m
git status --short
echo.

REM 4. Commit avec le message
echo [33m Creation du commit...[0m
git commit -F COMMIT_MESSAGE_EXPORT_PDF.txt

if %ERRORLEVEL% EQU 0 (
    echo [32m Commit cree avec succes[0m
) else (
    echo [31m Aucun changement a commiter ou erreur[0m
    pause
    exit /b 1
)
echo.

REM 5. Afficher le dernier commit
echo [36m Dernier commit:[0m
git log -1 --oneline
echo.

REM 6. Push vers GitHub
echo [33m Push vers GitHub...[0m
git push origin main

if %ERRORLEVEL% EQU 0 (
    echo.
    echo ===================================================================
    echo    [32m MISE A JOUR GITHUB REUSSIE[0m
    echo ===================================================================
    echo.
    echo Modifications poussees sur GitHub:
    echo   * Export PDF des classements avec en-tete officiel
    echo   * Logo et filigrane dans les PDF
    echo   * Correction de la recherche des classes
    echo   * Documentation complete
    echo.
) else (
    echo.
    echo [31m Erreur lors du push vers GitHub[0m
    echo Verifiez votre connexion internet et vos identifiants GitHub
    pause
    exit /b 1
)

echo.
echo Appuyez sur une touche pour fermer...
pause > nul
