#!/bin/bash
# Script de déploiement du fix import NoteMensuelle

echo "=========================================="
echo "🔧 DÉPLOIEMENT FIX IMPORT NoteMensuelle"
echo "=========================================="
echo ""

# Naviguer vers le répertoire du projet
cd ~/GS_hadja_kanfing_dian- || exit 1

# Récupérer les dernières modifications
echo "📥 Récupération des modifications depuis GitHub..."
git pull origin main

if [ $? -eq 0 ]; then
    echo "✅ Git pull réussi"
else
    echo "❌ Erreur lors du git pull"
    exit 1
fi

# Redémarrer Django
echo ""
echo "🔄 Redémarrage de Django..."
touch ecole_moderne/wsgi.py

if [ $? -eq 0 ]; then
    echo "✅ Django redémarré"
else
    echo "❌ Erreur lors du redémarrage"
    exit 1
fi

echo ""
echo "=========================================="
echo "✅ DÉPLOIEMENT TERMINÉ AVEC SUCCÈS !"
echo "=========================================="
echo ""
echo "🧪 Testez maintenant :"
echo "   https://www.myschoolgn.space/notes/bulletins/"
echo ""
