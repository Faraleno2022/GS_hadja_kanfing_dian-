#!/bin/bash
# Script de déploiement pour corriger l'erreur evaluations_qs

echo "🚀 Déploiement du correctif pour les bulletins PDF..."

# Aller dans le répertoire du projet
cd /home/myschoolgn/GS_hadja_kanfing_dian- || exit 1

# Récupérer les dernières modifications
echo "📥 Récupération des modifications depuis GitHub..."
git fetch origin
git reset --hard origin/main

# Nettoyer les caches Python
echo "🧹 Nettoyage des caches Python..."
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null
find . -type f -name "*.pyc" -delete 2>/dev/null

# Redémarrer le serveur
echo "🔄 Redémarrage du serveur uWSGI..."
touch ecole_moderne/wsgi.py

echo "✅ Déploiement terminé avec succès!"
echo ""
echo "📋 Version déployée:"
git log -1 --oneline
echo ""
echo "🔗 Testez sur: https://www.myschoolgn.space/notes/bulletins/classe/pdf/"
