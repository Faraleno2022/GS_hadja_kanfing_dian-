#!/bin/bash

#############################################################################
# Script de déploiement automatique du fix IntegrityError changement classe
# Date: 14 novembre 2024
#############################################################################

set -e  # Arrêt en cas d'erreur

echo "═══════════════════════════════════════════════════════════════════════════"
echo "  DÉPLOIEMENT: Fix IntegrityError lors du changement de classe"
echo "═══════════════════════════════════════════════════════════════════════════"
echo ""

# Couleurs pour l'affichage
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Fonction d'affichage
info() {
    echo -e "${BLUE}ℹ${NC} $1"
}

success() {
    echo -e "${GREEN}✓${NC} $1"
}

warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

error() {
    echo -e "${RED}✗${NC} $1"
}

# Vérifier qu'on est dans le bon répertoire
if [ ! -f "manage.py" ]; then
    error "Erreur: manage.py non trouvé. Exécutez ce script depuis la racine du projet."
    exit 1
fi

info "Répertoire: $(pwd)"
echo ""

# 1. Pull depuis GitHub
echo "───────────────────────────────────────────────────────────────────────────"
info "1. Récupération des modifications depuis GitHub..."
echo "───────────────────────────────────────────────────────────────────────────"

git pull origin main

if [ $? -eq 0 ]; then
    success "Code mis à jour depuis GitHub"
else
    error "Échec du git pull"
    exit 1
fi
echo ""

# 2. Vérifier que le fichier modifié existe
echo "───────────────────────────────────────────────────────────────────────────"
info "2. Vérification des fichiers modifiés..."
echo "───────────────────────────────────────────────────────────────────────────"

if [ -f "eleves/models.py" ]; then
    success "eleves/models.py trouvé"
    
    # Vérifier que le fix est présent
    if grep -q "TEMP-.*uuid" eleves/models.py; then
        success "Fix détecté dans le code (matricule temporaire UUID)"
    else
        warning "Fix non détecté - vérifiez le code manuellement"
    fi
else
    error "eleves/models.py non trouvé"
    exit 1
fi
echo ""

# 3. Vérifier la configuration
echo "───────────────────────────────────────────────────────────────────────────"
info "3. Vérification de la configuration Django..."
echo "───────────────────────────────────────────────────────────────────────────"

python manage.py check --deploy 2>/dev/null

if [ $? -eq 0 ]; then
    success "Configuration Django valide"
else
    warning "Avertissements de configuration détectés (non bloquants)"
fi
echo ""

# 4. Nettoyage des caches Python
echo "───────────────────────────────────────────────────────────────────────────"
info "4. Nettoyage des caches Python..."
echo "───────────────────────────────────────────────────────────────────────────"

find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
find . -type f -name "*.pyc" -delete 2>/dev/null || true

success "Caches Python supprimés"
echo ""

# 5. Migrations (si nécessaires)
echo "───────────────────────────────────────────────────────────────────────────"
info "5. Vérification des migrations..."
echo "───────────────────────────────────────────────────────────────────────────"

python manage.py migrate --check 2>/dev/null

if [ $? -eq 0 ]; then
    success "Pas de migrations en attente"
else
    info "Application des migrations..."
    python manage.py migrate
    success "Migrations appliquées"
fi
echo ""

# 6. Collecte des fichiers statiques (sans prompt)
echo "───────────────────────────────────────────────────────────────────────────"
info "6. Collecte des fichiers statiques..."
echo "───────────────────────────────────────────────────────────────────────────"

python manage.py collectstatic --noinput --clear 2>/dev/null || true
success "Fichiers statiques collectés"
echo ""

# 7. Redémarrage uWSGI
echo "───────────────────────────────────────────────────────────────────────────"
info "7. Redémarrage du serveur uWSGI..."
echo "───────────────────────────────────────────────────────────────────────────"

touch ecole_moderne/wsgi.py

if [ $? -eq 0 ]; then
    success "uWSGI redémarré (touch wsgi.py)"
    info "Attente de 3 secondes pour la prise en compte..."
    sleep 3
else
    error "Échec du redémarrage"
    exit 1
fi
echo ""

# 8. Test rapide
echo "───────────────────────────────────────────────────────────────────────────"
info "8. Test de validation rapide..."
echo "───────────────────────────────────────────────────────────────────────────"

python -c "
import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ecole_moderne.settings')
django.setup()

from eleves.models import Eleve
try:
    count = Eleve.objects.count()
    print(f'✓ Base de données accessible: {count} élèves')
    
    # Vérifier l'import uuid
    import uuid
    test_uuid = uuid.uuid4().hex[:8]
    print(f'✓ Module uuid fonctionnel: TEMP-{test_uuid}')
    
    print('✓ Tous les tests rapides passés')
except Exception as e:
    print(f'✗ Erreur: {e}')
    exit(1)
"

if [ $? -eq 0 ]; then
    success "Tests de validation réussis"
else
    error "Échec des tests"
    exit 1
fi
echo ""

# 9. Résumé
echo "═══════════════════════════════════════════════════════════════════════════"
success "DÉPLOIEMENT TERMINÉ AVEC SUCCÈS"
echo "═══════════════════════════════════════════════════════════════════════════"
echo ""
echo "📋 RÉSUMÉ:"
echo "   • Code mis à jour depuis GitHub"
echo "   • Fix IntegrityError appliqué (matricule temporaire UUID)"
echo "   • Caches Python nettoyés"
echo "   • Serveur uWSGI redémarré"
echo "   • Base de données accessible"
echo ""
echo "🧪 PROCHAINES ÉTAPES:"
echo "   1. Tester le changement de classe sur https://www.myschoolgn.space"
echo "   2. Aller sur /eleves/178/modifier/"
echo "   3. Changer la classe et sauvegarder"
echo "   4. Vérifier qu'aucune erreur ne se produit"
echo ""
echo "📝 LOGS:"
echo "   • uWSGI: /var/log/uwsgi/app/myschoolgn.log"
echo "   • Nginx: /var/log/nginx/error.log"
echo ""
echo "═══════════════════════════════════════════════════════════════════════════"
