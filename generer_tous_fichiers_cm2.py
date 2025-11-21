#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Génère tous les fichiers CSV pour l'import des notes CM2"""
import csv

# Données: (Matricule, Prénom, Nom, [9 notes pour les 9 matières])
ELEVES = [
    ("PN6-032", "ABOUBACAR", "CAMARA", [6, None, None, None, None, None, None, None, None]),
    ("PN6-055", "ABOUBACAR SIDIKI", "DIARRA", [6, None, None, None, None, None, None, None, None]),
    ("PN6-035", "ALEXANDRE", "TRAORE", [8, None, None, None, None, None, None, None, None]),
    ("PN6-048", "ALHASSANE", "BANGOURA", [8, None, None, None, None, None, None, None, None]),
    ("PN6-063", "ALI BADRA", "SANGARE", [6.5, None, None, None, None, None, None, None, None]),
    ("PN6-040", "AMADOU", "KOUYATE", [7, None, None, None, None, None, None, None, None]),
    ("PN6-049", "AMINATA", "FOFANA", [7, None, None, None, None, None, None, None, None]),
    ("PN6-054", "BEATRICE JUNIOR", "SANDOUNO", [7.5, None, None, None, None, None, None, None, None]),
    ("PN6-007", "BOUNTOURABY", "DIALLO", [5, None, None, None, None, None, None, None, None]),
    ("PN6-051", "BOUNTOURABY", "SYLLA", [8, None, None, None, None, None, None, None, None]),
    ("PN6-036", "CHEICK DJIBRIL HADY", "DIANE", [8, None, None, None, None, None, None, None, None]),
    ("PN6-031", "DOUSSOUBA", "CONDE", [None, None, None, None, None, None, None, None, None]),
    ("PN6-041", "ELHADJ AMADOU FOULAH", "BALDE", [7.5, None, None, None, None, None, None, None, None]),
    ("PN6-050", "FATOUMATA", "CAMARA", [6, None, None, None, None, None, None, None, None]),
    ("PN6-043", "FATOUMATA", "CONTE", [8, None, None, None, None, None, None, None, None]),
    ("PN6-005", "FATOUMATA DJARAYE", "TOURE", [8, None, None, None, None, None, None, None, None]),
    ("PN6-061", "FATOUMATA BINTA", "SYLLA", [8, None, None, None, None, None, None, None, None]),
    ("PN6-045", "HASSANATOU", "BAH", [7, None, None, None, None, None, None, None, None]),
    ("PN6-038", "KAIAGBAN KAZADI", "DIALLO", [5, None, None, None, None, None, None, None, None]),
    ("PN6-033", "KARNY", "DIARRA", [6, None, None, None, None, None, None, None, None]),
    ("PN6-046", "LEONIE NEMA", "KOUROUMA", [7, None, None, None, None, None, None, None, None]),
    ("PN6-062", "MAMADOU", "MAGASSOUBA", [7, None, None, None, None, None, None, None, None]),
    ("PN6-057", "MAMADOU SALIOU", "BALDE", [7, None, None, None, None, None, None, None, None]),
    ("P6-002", "MARIAME", "DOUMBOUYA", [7, None, None, None, None, None, None, None, None]),
    ("PN6-053", "MARIAME", "DOUMBOUYA", [7, None, None, None, None, None, None, None, None]),
    ("PN6-060", "MOHAMED", "KANTE", [6, None, None, None, None, None, None, None, None]),
    ("PN6-065", "MOHAMED", "KANTE", [6, None, None, None, None, None, None, None, None]),
    ("PN6-047", "MOHAMED LAMINE", "BANGOURA", [6, None, None, None, None, None, None, None, None]),
    ("PN6-039", "MOHAMED LAMINE", "SOUMAH", [6, None, None, None, None, None, None, None, None]),
    ("PN6-006", "MORIBA GUILAVO", "GUILAVOGUI", [8, None, None, None, None, None, None, None, None]),
    ("PN6-037", "MOUSSA", "DIARRA", [6, None, None, None, None, None, None, None, None]),
    ("PN6-030", "NANA", "TRAORE", [8, None, None, None, None, None, None, None, None]),
    ("PN6-056", "NENE ADAMA", "CAMARA", [6, None, None, None, None, None, None, None, None]),
    ("PN6-058", "OUMAR YAYA", "CAMARA", [6, None, None, None, None, None, None, None, None]),
    ("PN6-059", "OUMERKIL", "DIABY", [9, None, None, None, None, None, None, None, None]),
    ("PN6-042", "ROUGOUIATA", "DIALLO", [5, None, None, None, None, None, None, None, None]),
    ("PN6-064", "SANSSSO", "CAMARA", [6, None, None, None, None, None, None, None, None]),
    ("PN6-052", "SONNAH", "KEITA", [8.5, None, None, None, None, None, None, None, None]),
    ("PN6-034", "TIGUIDANTKE", "DIALLO", [5, None, None, None, None, None, None, None, None]),
]

MATIERES = [
    "Dictee_et_Questions",
    "Histoire",
    "Redaction",
    "Geographie",
    "Calcul",
    "Sciences_observation",
    "Education_Civique",
    "Lecture",
    "Anglais"
]

def generer_fichier(matiere_nom, index_matiere):
    """Génère un fichier CSV pour une matière"""
    filename = f"notes_cm2_{matiere_nom}.csv"
    
    with open(filename, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['Matricule', 'Prénom', 'Nom', 'Note', 'Absent'])
        
        for matricule, prenom, nom, notes in ELEVES:
            note = notes[index_matiere]
            if note is None:
                writer.writerow([matricule, prenom, nom, '', 'OUI'])
            else:
                writer.writerow([matricule, prenom, nom, note, 'NON'])
    
    print(f"✅ Créé: {filename}")

if __name__ == '__main__':
    print("=" * 60)
    print("  📚 GÉNÉRATION DES FICHIERS CSV - CM2")
    print("=" * 60)
    
    for i, matiere in enumerate(MATIERES):
        generer_fichier(matiere, i)
    
    print("\n✅ Tous les fichiers ont été générés !")
    print("\n📋 Prochaines étapes:")
    print("1. Accédez à /notes/importer/")
    print("2. Pour chaque matière, uploadez le fichier correspondant")
    print("3. Les notes seront importées automatiquement")
