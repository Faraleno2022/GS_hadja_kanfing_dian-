#!/bin/bash
# Script de déploiement rapide pour myschoolgn.space
# Usage: ./deploy_production.sh

set -e  # Arrêter en cas d'erreur

echo "════════════════════════════════════════════════════════════════"
echo "🚀 DÉPLOIEMENT MYSCHOOLGN.SPACE"
echo "════════════════════════════════════════════════════════════════"
echo ""

# Couleurs
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
PROJECT_DIR="/home/myschoolgn/GS_hadja_kanfing_dian-"
VENV_DIR="/home/myschoolgn/venv"
UWSGI_SERVICE="uwsgi"

# Fonction pour afficher les messages
log_info() {
    echo -e "${BLUE}ℹ${NC} $1"
}

log_success() {
    echo -e "${GREEN}✓${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

log_error() {
    echo -e "${RED}✗${NC} $1"
}

# Vérifier que nous sommes dans le bon répertoire
if [ ! -d "$PROJECT_DIR" ]; then
    log_error "Le répertoire du projet n'existe pas: $PROJECT_DIR"
    exit 1
fi

cd "$PROJECT_DIR" || exit 1
log_success "Répertoire du projet: $PROJECT_DIR"

# Étape 1: Sauvegarder les modifications locales
echo ""
log_info "Sauvegarde des modifications locales..."
if git diff --quiet && git diff --cached --quiet; then
    log_success "Aucune modification locale à sauvegarder"
else
    git stash
    log_warning "Modifications locales sauvegardées avec git stash"
fi

# Étape 2: Récupérer la dernière version
echo ""
log_info "Récupération de la dernière version depuis GitHub..."
git fetch origin
git pull origin main
log_success "Code mis à jour"

# Afficher le dernier commit
LAST_COMMIT=$(git log --oneline -1)
log_info "Dernier commit: $LAST_COMMIT"

# Étape 3: Vérifier le fichier views.py
echo ""
log_info "Vérification du fichier eleves/views.py..."
if grep -q "from django.shortcuts import render" eleves/views.py; then
    log_success "Import 'render' trouvé dans eleves/views.py"
else
    log_error "Import 'render' MANQUANT dans eleves/views.py"
    log_error "Le problème n'est pas résolu. Vérifiez le fichier manuellement."
    exit 1
fi

# Étape 4: Nettoyer les caches Python
echo ""
log_info "Nettoyage des caches Python (.pyc et __pycache__)..."
find . -type f -name "*.pyc" -delete
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
log_success "Caches Python supprimés"

# Étape 5: Activer le virtualenv
echo ""
log_info "Activation du virtualenv..."
if [ ! -d "$VENV_DIR" ]; then
    log_error "Virtualenv introuvable: $VENV_DIR"
    exit 1
fi
source "$VENV_DIR/bin/activate"
log_success "Virtualenv activé"

# Étape 6: Installer/Mettre à jour les dépendances
echo ""
log_info "Vérification des dépendances..."
if [ -f "requirements.txt" ]; then
    pip install -q -r requirements.txt
    log_success "Dépendances à jour"
else
    log_warning "Fichier requirements.txt introuvable"
fi

# Étape 7: Collecter les fichiers statiques
echo ""
log_info "Collecte des fichiers statiques..."
python manage.py collectstatic --noinput > /dev/null 2>&1
log_success "Fichiers statiques collectés"

# Étape 8: Appliquer les migrations
echo ""
log_info "Application des migrations de base de données..."
python manage.py migrate --noinput
log_success "Migrations appliquées"

# Étape 9: Vérifier l'import dans Python
echo ""
log_info "Test de l'import de render dans Python..."
python -c "from django.shortcuts import render; print('OK')" > /dev/null 2>&1
if [ $? -eq 0 ]; then
    log_success "Import 'render' fonctionne correctement"
else
    log_error "Problème avec l'import 'render'"
    exit 1
fi

# Étape 10: Redémarrer uWSGI
echo ""
log_info "Redémarrage d'uWSGI..."
if command -v systemctl &> /dev/null; then
    sudo systemctl restart "$UWSGI_SERVICE"
    sleep 2
    if sudo systemctl is-active --quiet "$UWSGI_SERVICE"; then
        log_success "uWSGI redémarré avec succès"
    else
        log_error "Échec du redémarrage d'uWSGI"
        log_info "Vérifiez les logs: sudo journalctl -u $UWSGI_SERVICE -n 50"
        exit 1
    fi
else
    log_warning "systemctl non disponible, tentative avec touch-reload..."
    if [ -f "reload.txt" ]; then
        touch reload.txt
        log_success "Signal de rechargement envoyé"
    else
        log_error "Impossible de redémarrer uWSGI"
        exit 1
    fi
fi

# Étape 11: Vérifier le statut
echo ""
log_info "Vérification du statut d'uWSGI..."
if sudo systemctl is-active --quiet "$UWSGI_SERVICE"; then
    log_success "uWSGI est actif"
else
    log_error "uWSGI n'est pas actif"
    exit 1
fi

# Étape 12: Test HTTP
echo ""
log_info "Test de l'application..."
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" -L https://www.myschoolgn.space/eleves/liste/ || echo "000")
if [ "$HTTP_CODE" = "200" ] || [ "$HTTP_CODE" = "302" ]; then
    log_success "Application accessible (HTTP $HTTP_CODE)"
else
    log_warning "Code HTTP: $HTTP_CODE (peut nécessiter une authentification)"
fi

# Résumé
echo ""
echo "════════════════════════════════════════════════════════════════"
echo -e "${GREEN}✓ DÉPLOIEMENT TERMINÉ AVEC SUCCÈS !${NC}"
echo "════════════════════════════════════════════════════════════════"
echo ""
log_info "Dernier commit: $LAST_COMMIT"
log_info "Date: $(date '+%Y-%m-%d %H:%M:%S')"
echo ""
log_info "Pour vérifier les logs:"
echo "  sudo tail -f /var/log/uwsgi/myschoolgn.log"
echo "  sudo journalctl -u $UWSGI_SERVICE -f"
echo ""
log_info "Pour tester l'application:"
echo "  https://www.myschoolgn.space/eleves/liste/"
echo ""
echo "════════════════════════════════════════════════════════════════"
