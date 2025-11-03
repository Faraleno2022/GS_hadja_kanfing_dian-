@echo off
echo ========================================
echo   DEMARRAGE RAPIDE - EXPORT CLASSEMENTS
echo ========================================
echo.

echo [1/3] Verification du repertoire...
cd /d "%~dp0"
echo OK - Repertoire: %CD%
echo.

echo [2/3] Demarrage du serveur Django...
echo.
echo IMPORTANT: 
echo - Le serveur va demarrer
echo - Ouvrez votre navigateur
echo - Allez sur: http://127.0.0.1:8000/notes/consulter/
echo - Cliquez sur "Exporter Classement" (bouton jaune avec trophee)
echo.
echo Pour arreter le serveur: Appuyez sur Ctrl+C
echo.
pause

echo [3/3] Lancement...
python manage.py runserver

pause
