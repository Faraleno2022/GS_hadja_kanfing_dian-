#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import sqlite3
import unicodedata
from difflib import SequenceMatcher

ELEVES_SYSTEME = [
    ("PN6-032", "ABOUBACAR CAMARA"),
    ("PN6-055", "ABOUBACAR SIDIKI DIARRA"),
    ("PN6-035", "ALEXANDRE TRAORE"),
    ("PN6-048", "ALHASSANE BANGOURA"),
    ("PN6-063", "ALI BADRA SANGARE"),
    ("PN6-040", "AMADOU KOUYATE"),
    ("PN6-049", "AMINATA FOFANA"),
    ("PN6-054", "BEATRICE JUNIOR SANDOUNO"),
    ("PN6-007", "BOUNTOURABY DIALLO"),
    ("PN6-051", "BOUNTOURABY SYLLA"),
    ("PN6-036", "CHEICK DJIBRIL HADY DIANE"),
    ("PN6-031", "DOUSOUBA CONDE"),
    ("PN6-041", "ELHADJ AMADOU FOULAH BALDE"),
    ("PN6-050", "FATOUMATA CAMARA"),
    ("PN6-043", "FATOUMATA CONTE"),
    ("PN6-005", "FATOUMATA DJARAYE TOURE"),
    ("PN6-061", "FATOUMATA BINTA SYLLA"),
    ("PN6-045", "HASSANATOU BAH"),
    ("PN6-038", "KALAGBAN KAZADI DIALLO"),
    ("PN6-033", "KANY DIARRA"),
    ("PN6-046", "LEONIE NEMA KOUROUMA"),
    ("PN6-062", "MAMADOU MAGASSOUBA"),
    ("PN6-057", "MAMADOU SALIOU BALDE"),
    ("P6-002", "MARIAME DOUMBOUYA"),
    ("PN6-053", "MARIAME DOUMBOUYA"),
    ("PN6-060", "MOHAMED KANTE"),
    ("PN6-065", "MOHAMED KANTÉ"),
    ("PN6-047", "MOHAMED LAMINE BANGOURA"),
    ("PN6-039", "MOHAMED LAMINE SOUMAH"),
    ("PN6-006", "MORIBA GUILAVO GUILAVOGUI"),
    ("PN6-037", "MOUSSA DIARRA"),
    ("PN6-030", "NANA TRAORE"),
    ("PN6-056", "NENE ADAMA CAMARA"),
    ("PN6-058", "OUMAR YAYA CAMARA"),
    ("PN6-059", "OUMERKIL DIABY"),
    ("PN6-042", "ROUGOUIATA DIALLO"),
    ("PN6-064", "SANSSSO CAMARA"),
    ("PN6-052", "SONNAH KEITA"),
    ("PN6-034", "TIGUIDANTKE DIALLO"),
]

MATIERES = {
    "Anglais": 1.0,
    "Calcul-problème": 1.0,
    "Dictée et Questions": 2.0,
    "Éducation Civique et Morale": 1.0,
    "Éducation Physique et Sportive": 1.0,
    "Géographie": 1.0,
    "Histoire": 1.0,
    "Lecture": 1.0,
    "Rédaction": 1.0,
    "Sciences d'observation": 1.0,
}

DB_FILE = "ecole_notes.db"

def normalize_name(name):
    name = name.upper()
    name = unicodedata.normalize('NFKD', name)
    name = name.encode('ASCII', 'ignore').decode('ASCII')
    name = ' '.join(name.split())
    return name

def similarity(a, b):
    return SequenceMatcher(None, a, b).ratio()

def find_best_match(nom_importé, eleves_systeme_dict):
    nom_norm = normalize_name(nom_importé)
    best_match = None
    best_score = 0.0
    for matricule, nom_systeme in eleves_systeme_dict.items():
        nom_sys_norm = normalize_name(nom_systeme)
        score = similarity(nom_norm, nom_sys_norm)
        if score > best_score:
            best_score = score
            best_match = (matricule, nom_systeme, score)
    return best_match if best_score > 0.6 else None

def main():
    print("\n" + "="*70)
    print("FUSION INTELLIGENTE - Detection par Similarite de Noms")
    print("="*70 + "\n")
    
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    try:
        cursor.execute("ALTER TABLE etudiants ADD COLUMN matricule TEXT UNIQUE;")
        print("OK: Colonne 'matricule' creee")
    except:
        print("OK: Colonne 'matricule' existe deja")
    
    try:
        cursor.execute("ALTER TABLE matieres ADD COLUMN coefficient REAL DEFAULT 1.0;")
        print("OK: Colonne 'coefficient' creee")
    except:
        print("OK: Colonne 'coefficient' existe deja")
    
    print("\nVerification des matieres...")
    for nom, coef in MATIERES.items():
        cursor.execute("SELECT id_matiere FROM matieres WHERE nom_matiere = ?", (nom,))
        if not cursor.fetchone():
            cursor.execute("INSERT INTO matieres (nom_matiere, coefficient) VALUES (?, ?)", (nom, coef))
            print(f"  + Matiere ajoutee: {nom} (Coef: {coef})")
        else:
            cursor.execute("UPDATE matieres SET coefficient = ? WHERE nom_matiere = ?", (coef, nom))
            print(f"  * Coefficient maj: {nom} (Coef: {coef})")
    
    conn.commit()
    
    cursor.execute("SELECT id_etudiant, nom_complet FROM etudiants WHERE id_classe = 2 ORDER BY id_etudiant")
    etudiants_existants = cursor.fetchall()
    
    eleves_systeme_dict = {mat: nom for mat, nom in ELEVES_SYSTEME}
    
    print(f"\nFusion des donnees:")
    print(f"   Etudiants existants: {len(etudiants_existants)}")
    print(f"   Eleves du systeme: {len(eleves_systeme_dict)}")
    
    print("\nDetection intelligente par similarite...\n")
    
    matched = 0
    unmatched = []
    
    for id_etudiant, nom_existant in etudiants_existants:
        match = find_best_match(nom_existant, eleves_systeme_dict)
        
        if match:
            matricule, nom_systeme, score = match
            cursor.execute("UPDATE etudiants SET matricule = ? WHERE id_etudiant = ?", 
                         (matricule, id_etudiant))
            print(f"OK [{score:.0%}] {nom_existant:<30} -> {matricule} ({nom_systeme})")
            matched += 1
            del eleves_systeme_dict[matricule]
        else:
            print(f"NO {nom_existant}")
            unmatched.append((id_etudiant, nom_existant))
    
    conn.commit()
    
    print(f"\nResultats:")
    print(f"   Matched: {matched}/{len(etudiants_existants)}")
    print(f"   Non-matchés: {len(unmatched)}")
    print(f"   A ajouter: {len(eleves_systeme_dict)}")
    
    if eleves_systeme_dict:
        print(f"\nAjout des {len(eleves_systeme_dict)} eleves manquants:")
        
        cursor.execute("SELECT MAX(id_etudiant) FROM etudiants WHERE id_classe = 2")
        max_id = cursor.fetchone()[0] or 36
        
        for idx, (matricule, nom) in enumerate(eleves_systeme_dict.items(), 1):
            new_id = max_id + idx
            nom_norm = ' '.join(nom.split())
            norm_norm = normalize_name(nom)
            
            cursor.execute(
                "INSERT INTO etudiants (id_etudiant, id_classe, nom_complet, nom_normalise, matricule) VALUES (?, ?, ?, ?, ?)",
                (new_id, 2, nom, norm_norm, matricule)
            )
            print(f"   + Ajoute: {matricule} - {nom}")
        
        conn.commit()
    
    cursor.execute("SELECT COUNT(*) FROM etudiants WHERE id_classe = 2")
    total_final = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM matieres")
    total_matieres = cursor.fetchone()[0]
    
    print("\n" + "="*70)
    print("FUSION COMPLETE!")
    print("="*70)
    print(f"   Etudiants total: {total_final} (attendu: 39)")
    print(f"   Matieres: {total_matieres} (attendu: 10)")
    print(f"   Matricules assignes: {matched + len(eleves_systeme_dict)}")
    
    print(f"\nListe completes avec matricules:")
    print("-" * 70)
    cursor.execute("SELECT matricule, nom_complet FROM etudiants WHERE id_classe = 2 AND matricule IS NOT NULL ORDER BY matricule")
    
    for matricule, nom in cursor.fetchall():
        print(f"   {matricule} | {nom}")
    
    conn.close()
    print("\nFusion terminee!\n")

if __name__ == "__main__":
    main()
