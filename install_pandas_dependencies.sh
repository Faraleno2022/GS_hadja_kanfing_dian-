#!/bin/bash

# Script d'installation des dépendances pandas et openpyxl
# Pour le serveur de production www.myschoolgn.space
# Date: 15 novembre 2024

echo "========================================"
echo "Installation des dépendances pandas et openpyxl"
echo "Pour la fonctionnalité d'importation de notes"
echo "========================================"

# Couleurs pour l'affichage
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Vérifier qu'on est bien sur le serveur de production
if [ ! -d "/home/myschoolgn/GS_hadja_kanfing_dian-" ]; then
    echo -e "${RED}❌ Ce script doit être exécuté sur le serveur de production${NC}"
    exit 1
fi

# Se placer dans le bon répertoire
cd /home/myschoolgn/GS_hadja_kanfing_dian-

# Activer l'environnement virtuel
echo -e "${YELLOW}1. Activation de l'environnement virtuel...${NC}"
source /home/myschoolgn/venv/bin/activate

# Installer pandas
echo -e "${YELLOW}2. Installation de pandas (traitement de données)...${NC}"
pip install pandas==2.0.3

# Vérifier l'installation de pandas
if python -c "import pandas" 2>/dev/null; then
    echo -e "${GREEN}✅ pandas installé avec succès${NC}"
else
    echo -e "${RED}❌ Erreur lors de l'installation de pandas${NC}"
    exit 1
fi

# Installer openpyxl
echo -e "${YELLOW}3. Installation de openpyxl (support Excel)...${NC}"
pip install openpyxl==3.1.2

# Vérifier l'installation de openpyxl
if python -c "import openpyxl" 2>/dev/null; then
    echo -e "${GREEN}✅ openpyxl installé avec succès${NC}"
else
    echo -e "${RED}❌ Erreur lors de l'installation de openpyxl${NC}"
    exit 1
fi

# Nettoyer les caches Python
echo -e "${YELLOW}4. Nettoyage des caches Python...${NC}"
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null
find . -type f -name "*.pyc" -delete 2>/dev/null

# Redémarrer uWSGI
echo -e "${YELLOW}5. Redémarrage du serveur uWSGI...${NC}"
touch ecole_moderne/wsgi.py

echo -e "${GREEN}========================================"
echo -e "✅ Installation terminée avec succès!"
echo -e "========================================${NC}"
echo ""
echo "Les dépendances suivantes ont été installées :"
echo "- pandas 2.0.3 (traitement de fichiers Excel/CSV)"
echo "- openpyxl 3.1.2 (lecture/écriture Excel)"
echo ""
echo "La fonctionnalité d'importation de notes est maintenant disponible :"
echo "📊 URL: https://www.myschoolgn.space/notes/importer/"
echo ""
echo -e "${YELLOW}Note: Si le problème persiste, exécutez :${NC}"
echo "  systemctl restart nginx"
echo "  systemctl restart uwsgi"
