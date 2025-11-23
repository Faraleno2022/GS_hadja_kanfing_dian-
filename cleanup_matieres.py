#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import sqlite3

DB_FILE = "ecole_notes.db"

# Les 9 matières CORRECTES de l'en-tête
MATIERES_CORRECTES = {
    "Dictée et Questions": 1.0,
    "Histoire": 1.0,
    "Rédaction": 1.0,
    "Géographie": 1.0,
    "Calcul": 1.0,
    "Sciences d'observation": 1.0,
    "Education Civique et Morale": 1.0,
    "Lecture": 1.0,
    "Anglais": 1.0,
}

def main():
    print("\n" + "="*70)
    print("NETTOYAGE DES MATIERES - Garder que les 9 de l'en-tete")
    print("="*70 + "\n")
    
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    # Afficher les matières actuelles
    print("Matieres actuelles:")
    cursor.execute("SELECT id_matiere, nom_matiere FROM matieres ORDER BY id_matiere")
    matieres_actuelles = cursor.fetchall()
    
    for id_mat, nom in matieres_actuelles:
        print(f"  {id_mat}: {nom}")
    
    print(f"\nTotal: {len(matieres_actuelles)} matieres")
    
    # Identifier les matières à supprimer
    print("\n" + "-"*70)
    print("Identification des doublons et anciennes matieres a supprimer...")
    print("-"*70 + "\n")
    
    matieres_a_supprimer = []
    
    for id_mat, nom in matieres_actuelles:
        if nom not in MATIERES_CORRECTES:
            print(f"  SUPPRIMER: {nom} (ID: {id_mat})")
            matieres_a_supprimer.append(id_mat)
    
    if not matieres_a_supprimer:
        print("  Aucune matiere a supprimer")
    else:
        # Supprimer les notes associées
        print(f"\nSuppression des notes des matieres obsoletes...")
        for id_mat in matieres_a_supprimer:
            cursor.execute("DELETE FROM notes WHERE id_matiere = ?", (id_mat,))
            print(f"  OK: Notes supprimees pour matiere ID {id_mat}")
        
        # Supprimer les matières
        print(f"\nSuppression des matieres obsoletes...")
        for id_mat in matieres_a_supprimer:
            cursor.execute("DELETE FROM matieres WHERE id_matiere = ?", (id_mat,))
            print(f"  OK: Matiere ID {id_mat} supprimee")
        
        conn.commit()
    
    # Afficher le résumé final
    print("\n" + "="*70)
    print("RESULTAT FINAL")
    print("="*70 + "\n")
    
    cursor.execute("SELECT COUNT(*) FROM matieres")
    total_matieres = cursor.fetchone()[0]
    
    print(f"Matieres finales: {total_matieres} (attendu: 9)\n")
    
    print("Matieres finales:")
    print("-" * 70)
    cursor.execute("SELECT id_matiere, nom_matiere FROM matieres ORDER BY id_matiere")
    for id_mat, nom in cursor.fetchall():
        print(f"  {id_mat}: {nom}")
    
    conn.close()
    print("\nNettoyage termine!\n")

if __name__ == "__main__":
    main()
