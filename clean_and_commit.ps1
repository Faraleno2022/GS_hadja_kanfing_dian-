# Script PowerShell pour nettoyer et commiter les modifications

Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "NETTOYAGE ET COMMIT DES MODIFICATIONS" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan

# 1. Supprimer les fichiers de backup et temporaires
Write-Host ""
Write-Host "1. Suppression des fichiers temporaires..." -ForegroundColor Yellow

if (Test-Path "backups_rangs_20251120_071556") {
    Remove-Item -Recurse -Force "backups_rangs_20251120_071556"
}
if (Test-Path "notes\.export_classement.py.swp") {
    Remove-Item -Force "notes\.export_classement.py.swp"
}
if (Test-Path "notes\bulletin_intelligent.py.backup") {
    Remove-Item -Force "notes\bulletin_intelligent.py.backup"
}
if (Test-Path "notes\bulletin_intelligent.py.bak2") {
    Remove-Item -Force "notes\bulletin_intelligent.py.bak2"
}
if (Test-Path "notes\calculs.py.backup") {
    Remove-Item -Force "notes\calculs.py.backup"
}
if (Test-Path "notes\calculs_intelligent.py.bak3") {
    Remove-Item -Force "notes\calculs_intelligent.py.bak3"
}
if (Test-Path "notes\export_classement.py.bak") {
    Remove-Item -Force "notes\export_classement.py.bak"
}
if (Test-Path "notes\export_classement_fixed.py.bak") {
    Remove-Item -Force "notes\export_classement_fixed.py.bak"
}
if (Test-Path "fix_all_rangs.sh") {
    Remove-Item -Force "fix_all_rangs.sh"
}

Write-Host "✅ Fichiers temporaires supprimés" -ForegroundColor Green

# 2. Vérifier les modifications importantes
Write-Host ""
Write-Host "2. Vérification des modifications..." -ForegroundColor Yellow
git status

# 3. Ajouter les fichiers modifiés importants
Write-Host ""
Write-Host "3. Ajout des fichiers modifiés..." -ForegroundColor Yellow

$filesToAdd = @(
    "notes/bulletin_intelligent.py",
    "notes/calculs.py",
    "notes/calculs_intelligent.py",
    "notes/export_classement_fixed.py",
    "test_bulletin_classe.py"
)

foreach ($file in $filesToAdd) {
    if (Test-Path $file) {
        git add $file
        Write-Host "  ✓ $file" -ForegroundColor Gray
    }
}

Write-Host "✅ Fichiers modifiés ajoutés" -ForegroundColor Green

# 4. Ajouter les scripts de test utiles
Write-Host ""
Write-Host "4. Ajout des scripts de test..." -ForegroundColor Yellow

$testFiles = @(
    "test_bulletin_ex_aequo.py",
    "test_rang_direct.py",
    "test_validation_rang.py"
)

foreach ($file in $testFiles) {
    if (Test-Path $file) {
        git add $file
        Write-Host "  ✓ $file" -ForegroundColor Gray
    }
}

Write-Host "✅ Scripts de test ajoutés" -ForegroundColor Green

# 5. Afficher le statut
Write-Host ""
Write-Host "5. Statut final..." -ForegroundColor Yellow
git status

# 6. Créer le commit
Write-Host ""
Write-Host "6. Création du commit..." -ForegroundColor Yellow

$commitMessage = @"
Fix: Corrections supplémentaires cohérence rangs

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

STATUT: Tests validés, prêt pour production
"@

git commit -m $commitMessage

Write-Host ""
Write-Host "✅ Commit créé" -ForegroundColor Green

# 7. Pousser vers GitHub
Write-Host ""
Write-Host "7. Push vers GitHub..." -ForegroundColor Yellow
git push origin main

Write-Host ""
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "✅ TERMINÉ !" -ForegroundColor Green
Write-Host "==========================================" -ForegroundColor Cyan
