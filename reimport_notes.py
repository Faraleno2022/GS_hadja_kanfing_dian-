#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import sqlite3

DB_FILE = "ecole_notes.db"

# Mapping: (nom_matiere, id_matiere)
MATIERE_MAP = {
    "Dictée et Questions": 11,
    "Histoire": 2,
    "Rédaction": 15,
    "Géographie": 14,
    "Calcul": 5,
    "Sciences d'observation": 16,
    "Education Civique et Morale": 17,
    "Lecture": 8,
    "Anglais": 9,
}

# Données: (nom_etudiant, note_dictee, note_histoire, note_redaction, note_geo, note_calcul, note_sciences, note_educ_civ, note_lecture, note_anglais)
NOTES_DATA = [
    ("Nana Traore", 6, 7.5, 10, 9, 7, 9.5, 8.5, 10, 8),
    ("Oumerkyl Diaby", 6.5, 6.75, 8, 8, 5, 9, 7, 10, 9),
    ("Beatrice J. Sandouno", 2, 8, 6, 7, 5, 7.85, 9, 10, 7.5),
    ("Moriba J. Guilavigui", 4, 5.75, 6.75, 4, 6, 9.5, 6, 10, 8),
    ("Tiguidanke Diallo", 3.5, 6, 8, 4.15, 5, 9, 8.25, 10, 5),
    ("Doussouba Conde", 2, 5.75, 4, 7, 6.5, 7.5, 7, 10, 8.5),
    ("Mamadou S. Balde", 5, 5, 6, 6, 5, 5.5, 6.75, 10, 7),
    ("Cheick Dj. Hady Dianed", 3, 4, 5, 6.5, 5, 8.5, 6.15, 10, 8),
    ("Oumar Yaya Camara", 5, 4, 6, 6.5, 3, 6.5, 6.8, 10, 6),
    ("Kalagban K. Diallo", 3, 6.5, 6, 4, 2, 7, 7.7, 10, 7.5),
    ("Mariame Doumbouy", 3, 6, 5, 5, 2, 8, 6.8, 10, 7),
    ("Rouguiatou Diallo", 2, 4, 3, 5, 5, 7.75, 7.75, 10, 7.5),
    ("Elhadj Amadou F. Balde", 4, 7, 5, 2, 5, 6.5, 4.5, 10, 7.5),
    ("Sonna Keita", 7, 4, 6, 5.5, 5, 7.5, 7.85, 10, 8.5),
    ("Fatoumata Binta Sylla", 4, 3, 1, 6, 5, 3.5, 6.8, 10, 8),
    ("Hassanatou Bah", 2, 6.5, 3, 5, 2, 5, 8.5, 10, 7),
    ("Leoni Nema Kourouma", 5, 5.75, 3, 3.5, 2, 6.15, 5.15, 10, 7),
    ("Nen Adama Camara", 3.5, 3.5, 5, 7, 3.5, 6, 5, 8, 6),
    ("Mohamed L. Soumah", 5.6, 4, 3, 3, 4.5, 5.25, 6, 10, 6),
    ("Fatoumata Conte", 3, 5.75, 2, 2, 2, 7.5, 7, 10, 8),
    ("Ali Badra Sangare", 3.5, 3.5, 5, 3, 6, 3, 6, 10, 6.5),
    ("Aboubacar S. Diarra", 3, 5, 2, 5, 4, 7.5, 3.5, 10, 6),
    ("Alexandre Traore", 4.5, 4.75, 2, 2, 2, 7, 8, 10, 8),
    ("Aboubacar Camara", 2, 3, 5, 4, 3, 5.5, 6.6, 10, 6),
    ("Mohamed L Bangoura", 5.6, 4.5, 3, 5, 3, 5, 4, 7, 8),
    ("Sanso Camara", 2, 6.5, 2, 4, 3, 4, 7.8, 8, 7.5),
    ("Bountouraby Sylla", 2, 5.2, 2, 5, 2, 5.5, 5.5, 10, 6),
    ("Kanni Diarra", 2, 5, 4, 3, 3, 3, 5.75, 10, 7),
    ("Mamoudou Magassadou", 1, 4.5, 2, 3, 2, 5.5, 7, 10, 7),
    ("Amadou Kouyate", 3.5, 3.5, 4, 3, 2, 5.25, 4, 10, 6),
    ("Mohamed Kante", 3, 4, 3, 2, 1, 5, 4.75, 10, 7),
    ("Aminata Fofana", 3, 4.5, 2, 2, 3, 6.5, 3.7, 8, 7),
    ("Fatoumata Diarraye Tour", 3, 2, 3, 2, 2, 4, 5, 10, 8),
    ("Alhasane Bangoura", 2, 3, 2, 4, 5.5, 3.5, 2, 10, 5),
    ("Moussa Diarra", 1, 1, 2, 6, 2, 4, 2, 10, 8),
    ("Fatoumata Camara", 1, 2, 4, 2, 2, 2, 3, 5, 5),
    ("BOUNTOURABY DIALLO", 0, 0, 0, 0, 0, 0, 0, 0, 0),
    ("MARIAME DOUMBOUYA", 0, 0, 0, 0, 0, 0, 0, 0, 0),
    ("MOHAMED KANTÉ", 0, 0, 0, 0, 0, 0, 0, 0, 0),
]

def main():
    print("\n" + "="*70)
    print("REIMPORTATION DES 324 NOTES avec les bons IDs")
    print("="*70 + "\n")
    
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    # Supprimer les anciennes notes
    print("Suppression des 144 anciennes notes...")
    cursor.execute("DELETE FROM notes")
    conn.commit()
    
    # Réimporter les 324 notes
    print("Reimportation des 324 notes...\n")
    
    notes_count = 0
    noms_matieres = ["Dictée et Questions", "Histoire", "Rédaction", "Géographie", "Calcul", 
                     "Sciences d'observation", "Education Civique et Morale", "Lecture", "Anglais"]
    
    for nom_etudiant, *notes_values in NOTES_DATA:
        # Récupérer l'ID de l'étudiant
        cursor.execute("SELECT id_etudiant FROM etudiants WHERE nom_complet = ? OR matricule IS NOT NULL", (nom_etudiant,))
        result = cursor.fetchone()
        
        if not result:
            # Chercher par nom approché
            cursor.execute("SELECT id_etudiant FROM etudiants WHERE LOWER(nom_complet) LIKE ?", (f"%{nom_etudiant.lower()}%",))
            result = cursor.fetchone()
        
        if result:
            id_etudiant = result[0]
            
            # Ajouter les 9 notes
            for idx, (matiere, note_value) in enumerate(zip(noms_matieres, notes_values)):
                id_matiere = MATIERE_MAP[matiere]
                
                if note_value > 0:  # Ignorer les 0 (élèves ajoutés sans notes)
                    cursor.execute(
                        "INSERT INTO notes (id_etudiant, id_matiere, note) VALUES (?, ?, ?)",
                        (id_etudiant, id_matiere, note_value)
                    )
                    notes_count += 1
    
    conn.commit()
    
    # Vérifier
    print(f"Notes reimportees: {notes_count}")
    
    cursor.execute("SELECT COUNT(*) FROM notes")
    total = cursor.fetchone()[0]
    print(f"Total dans la BD: {total}")
    
    conn.close()
    print("\nReimportation terminee!\n")

if __name__ == "__main__":
    main()
