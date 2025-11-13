#!/bin/bash
# Script de déploiement du fix PyPDF2 sur le serveur de production

echo "========================================="
echo "📦 Déploiement du fix PyPDF2"
echo "========================================="

# Affichage du répertoire courant
echo "📂 Répertoire actuel : $(pwd)"

# Pull des derniers changements
echo "🔄 Récupération des dernières modifications..."
git pull origin main

# Vérifier le statut
echo "📊 Status Git :"
git status

# Nettoyage des caches Python
echo "🧹 Nettoyage des caches Python..."
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null
find . -type f -name "*.pyc" -delete 2>/dev/null

# Collecte des fichiers statiques
echo "📁 Collecte des fichiers statiques..."
python manage.py collectstatic --noinput

# Application des migrations
echo "🗃️ Application des migrations..."
python manage.py migrate

# Redémarrage du serveur
echo "🔄 Redémarrage du serveur uWSGI..."
touch /home/myschoolgn/GS_hadja_kanfing_dian-/ecole_moderne/wsgi.py

echo "========================================="
echo "✅ Déploiement terminé avec succès !"
echo "========================================="
echo ""
echo "📝 Changements appliqués :"
echo "  - Suppression de la dépendance PyPDF2"
echo "  - Utilisation de WeasyPrint uniquement"
echo "  - Nouveau template bulletin_dynamique_single.html"
echo ""
echo "🌐 Test de la fonctionnalité :"
echo "  https://www.myschoolgn.space/notes/bulletins/classe/pdf/"
echo ""
echo "⚠️ Note : Si des erreurs persistent, vérifiez que WeasyPrint est bien installé :"
echo "  pip install weasyprint"
echo "========================================="
