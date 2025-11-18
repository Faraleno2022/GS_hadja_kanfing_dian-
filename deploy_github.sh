#!/bin/bash

# Script de déploiement sur GitHub
# Mise à jour des modifications locales vers le dépôt distant

echo "=========================================="
echo "🚀 DÉPLOIEMENT SUR GITHUB"
echo "=========================================="
echo ""

# Vérifier que nous sommes dans un dépôt git
if [ ! -d .git ]; then
    echo "❌ Erreur : Ce répertoire n'est pas un dépôt Git"
    exit 1
fi

# Afficher le statut actuel
echo "📊 Statut actuel du dépôt :"
echo "=================================="
git status
echo ""

# Ajouter tous les fichiers modifiés
echo "📝 Ajout des fichiers modifiés..."
git add -A

# Afficher les fichiers à commiter
echo ""
echo "📋 Fichiers à commiter :"
echo "=================================="
git diff --cached --name-only
echo ""

# Créer le commit
echo "💾 Création du commit..."
COMMIT_MESSAGE="Mise à jour : Permission d'importation d'élèves pour comptables + Génération matières par défaut"

git commit -m "$COMMIT_MESSAGE"

if [ $? -ne 0 ]; then
    echo "❌ Erreur lors du commit"
    exit 1
fi

echo ""
echo "✅ Commit créé avec succès"
echo ""

# Pousser vers GitHub
echo "🌐 Envoi vers GitHub..."
git push origin main

if [ $? -eq 0 ]; then
    echo ""
    echo "=========================================="
    echo "✅ DÉPLOIEMENT RÉUSSI !"
    echo "=========================================="
    echo ""
    echo "📊 Résumé des modifications :"
    echo "  • Permission d'importation d'élèves pour comptables"
    echo "  • Génération automatique des matières par défaut"
    echo "  • Scripts d'activation et de test"
    echo "  • Documentation complète"
    echo ""
    echo "🔗 Consultez le dépôt : https://github.com/Faraleno2022/GS_hadja_kanfing_dian-"
else
    echo ""
    echo "❌ Erreur lors de l'envoi vers GitHub"
    echo "Vérifiez votre connexion et vos credentials"
    exit 1
fi
