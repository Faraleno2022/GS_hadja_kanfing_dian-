#!/bin/bash

DB_FILE="ecole_notes.db"
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m'

if [ ! -f "$DB_FILE" ]; then
    echo -e "${RED}[✗] Erreur: ecole_notes.db non trouvée!${NC}"
    echo -e "${YELLOW}Téléchargez ecole_notes.db depuis Claude d'abord${NC}"
    exit 1
fi

show_menu() {
    echo -e "\n${BLUE}╔════════════════════════════════════════╗${NC}"
    echo -e "${BLUE}║  GESTIONNAIRE DE NOTES 6ème ANNÉE     ║${NC}"
    echo -e "${BLUE}╚════════════════════════════════════════╝${NC}\n"
    echo "1. Voir tous les étudiants"
    echo "2. Moyenne de la classe"
    echo "3. Étudiants par moyenne"
    echo "4. Quitter"
    echo ""
}

list_students() {
    echo -e "\n${BLUE}[*] Tous les étudiants:${NC}"
    sqlite3 -header -column "$DB_FILE" "SELECT nom_complet FROM etudiants ORDER BY nom_complet;"
}

avg_class() {
    echo -e "\n${BLUE}[*] Moyenne générale: ${NC}"
    sqlite3 "$DB_FILE" "SELECT ROUND(AVG(note), 2) FROM notes;"
}

avg_students() {
    echo -e "\n${BLUE}[*] Étudiants par moyenne:${NC}"
    sqlite3 -header -column "$DB_FILE" "
        SELECT e.nom_complet, ROUND(AVG(n.note), 2) as moyenne
        FROM etudiants e
        LEFT JOIN notes n ON e.id_etudiant = n.id_etudiant
        GROUP BY e.id_etudiant
        ORDER BY moyenne DESC;"
}

while true; do
    show_menu
    read -p "Option (1-4): " choice
    case $choice in
        1) list_students ;;
        2) avg_class ;;
        3) avg_students ;;
        4) echo -e "${GREEN}Au revoir!${NC}"; exit 0 ;;
        *) echo -e "${RED}Invalid!${NC}" ;;
    esac
done
