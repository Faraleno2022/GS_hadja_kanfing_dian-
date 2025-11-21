#!/bin/bash
# Script pour créer et appliquer la migration sur le serveur

echo "=========================================="
echo "  🔧 FIX MIGRATION CLASSEMENT"
echo "=========================================="

# Créer la migration
echo ""
echo "📝 Création de la migration..."
python manage.py makemigrations notes

# Appliquer la migration
echo ""
echo "⚙️  Application de la migration..."
python manage.py migrate notes

# Calculer les classements
echo ""
echo "📊 Calcul des classements..."
python calculer_classements.py

# Redémarrer l'application
echo ""
echo "🔄 Redémarrage de l'application..."
touch ecole_moderne/wsgi.py

echo ""
echo "=========================================="
echo "✅ TERMINÉ"
echo "=========================================="
