#!/bin/bash
# Script de mise à jour GitHub - Export PDF des classements
# Date: 17 Novembre 2024

echo "═══════════════════════════════════════════════════════════════"
echo "   MISE À JOUR GITHUB - Export PDF des classements"
echo "═══════════════════════════════════════════════════════════════"
echo ""

# 1. Vérifier le statut actuel
echo "📊 Vérification du statut Git..."
git status
echo ""

# 2. Ajouter tous les fichiers modifiés et créés
echo "➕ Ajout des fichiers modifiés..."

# Fichiers principaux modifiés
git add notes/export_classement.py
git add notes/urls.py
git add templates/notes/consulter_notes.html

# Fichiers de documentation
git add EXPORT_CLASSEMENT_PDF_17_NOV_2024.md
git add RESUME_EXPORT_PDF_CLASSEMENT.txt
git add EXPORT_PDF_SIMPLE.txt
git add COMMIT_MESSAGE_EXPORT_PDF.txt

# Fichiers de la correction précédente
git add FIX_EXPORT_CLASSEMENT_17_NOV_2024.md
git add RESUME_FIX_EXPORT_CLASSEMENT.txt
git add SOLUTION_RAPIDE_EXPORT_CLASSEMENT.txt
git add COMMIT_MESSAGE_EXPORT_CLASSEMENT.txt

# Scripts de test
git add test_export_classement_diagnostic.py
git add test_export_classement_fixed.py
git add test_export_simple.py
git add verifier_correction_complete.py
git add test_export_classement_pdf.py

echo "✅ Fichiers ajoutés"
echo ""

# 3. Afficher les fichiers à commiter
echo "📋 Fichiers à commiter:"
git status --short
echo ""

# 4. Commit avec le message
echo "💾 Création du commit..."
git commit -F COMMIT_MESSAGE_EXPORT_PDF.txt

if [ $? -eq 0 ]; then
    echo "✅ Commit créé avec succès"
else
    echo "⚠️  Aucun changement à commiter ou erreur"
    exit 1
fi
echo ""

# 5. Afficher le dernier commit
echo "📝 Dernier commit:"
git log -1 --oneline
echo ""

# 6. Push vers GitHub
echo "🚀 Push vers GitHub..."
git push origin main

if [ $? -eq 0 ]; then
    echo ""
    echo "═══════════════════════════════════════════════════════════════"
    echo "   ✅ ✅ ✅ MISE À JOUR GITHUB RÉUSSIE ✅ ✅ ✅"
    echo "═══════════════════════════════════════════════════════════════"
    echo ""
    echo "Modifications poussées sur GitHub:"
    echo "  • Export PDF des classements avec en-tête officiel"
    echo "  • Logo et filigrane dans les PDF"
    echo "  • Correction de la recherche des classes"
    echo "  • Documentation complète"
    echo ""
else
    echo ""
    echo "❌ Erreur lors du push vers GitHub"
    echo "Vérifiez votre connexion internet et vos identifiants GitHub"
    exit 1
fi
