#!/usr/bin/env python
"""
Script pour générer un template Excel pour la saisie manuelle des notes de 7ÈME ANNÉE (A)
"""

import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ecole_moderne.settings')
django.setup()

def generer_template_7eme_annee_a():
    """Générer un template Excel pour la saisie manuelle des notes"""
    
    try:
        from notes.models import ClasseNote, MatiereNote
        from eleves.models import Eleve, Classe as ClasseEleve
        import pandas as pd
        from datetime import datetime
        
        print("🔧 GÉNÉRATION TEMPLATE EXCEL - 7ÈME ANNÉE (A)")
        print("=" * 60)
        
        # Configuration
        classe_id = 11  # 7ÈME ANNÉE (A)
        matiere_id = 109  # Anglais
        periode = 'OCTOBRE'
        
        print(f"📚 Configuration :")
        print(f"  • Classe ID : {classe_id}")
        print(f"  • Matière ID : {matiere_id}")
        print(f"  • Période : {periode}")
        
        # 1. Trouver la classe et la matière
        classe = ClasseNote.objects.get(id=classe_id)
        matiere = MatiereNote.objects.get(id=matiere_id)
        
        print(f"\n✅ Classe : {classe.nom}")
        print(f"✅ Matière : {matiere.nom}")
        
        # 2. Trouver la classe élève
        classe_eleve = ClasseEleve.objects.filter(
            nom=classe.nom,
            annee_scolaire=classe.annee_scolaire,
            ecole=classe.ecole
        ).first()
        
        if not classe_eleve:
            print(f"❌ Classe élève non trouvée")
            return False
        
        # 3. Récupérer tous les élèves actifs
        eleves = Eleve.objects.filter(classe=classe_eleve, statut='ACTIF').order_by('nom', 'prenom')
        print(f"✅ Élèves trouvés : {eleves.count()}")
        
        # 4. Créer le DataFrame Excel
        print(f"\n📊 CRÉATION DU TEMPLATE EXCEL :")
        
        data = []
        for i, eleve in enumerate(eleves, 1):
            row = {
                'N°': i,
                'Matricule': eleve.matricule,
                'Prénom': eleve.prenom,
                'Nom': eleve.nom,
                'Note /20': '',  # À remplir manuellement
                'Absent': 'NON'  # Par défaut NON
            }
            data.append(row)
            print(f"  ✅ {i:2d}. {eleve.matricule} - {eleve.nom_complet}")
        
        # Créer le DataFrame
        df = pd.DataFrame(data)
        
        # 5. Générer le fichier Excel
        nom_fichier = f"template_notes_7eme_annee_a_anglais_{periode}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        chemin_fichier = f"/tmp/{nom_fichier}"
        
        # Écrire le fichier Excel avec formatage
        with pd.ExcelWriter(chemin_fichier, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='Notes', index=False)
            
            # Récupérer la feuille pour formatage
            worksheet = writer.sheets['Notes']
            
            # Ajuster la largeur des colonnes
            worksheet.column_dimensions['A'].width = 5   # N°
            worksheet.column_dimensions['B'].width = 12  # Matricule
            worksheet.column_dimensions['C'].width = 15  # Prénom
            worksheet.column_dimensions['D'].width = 15  # Nom
            worksheet.column_dimensions['E'].width = 10  # Note
            worksheet.column_dimensions['F'].width = 8   # Absent
            
            # Ajouter des instructions en haut
            worksheet.insert_rows(1)
            worksheet['A1'] = f"TEMPLATE DE SAISIE DES NOTES - {classe.nom} - {matiere.nom} - {periode}"
            worksheet['A2'] = f"Année scolaire : {classe.annee_scolaire}"
            worksheet['A3'] = f"Généré le : {datetime.now().strftime('%d/%m/%Y %H:%M')}"
            worksheet['A5'] = "INSTRUCTIONS :"
            worksheet['A6'] = "1. Remplir la colonne 'Note /20' avec une valeur entre 0 et 20"
            worksheet['A7'] = "2. Mettre 'OUI' dans 'Absent' si l'élève était absent (laisser la note vide)"
            worksheet['A8'] = "3. Ne pas modifier les autres colonnes"
            worksheet['A9'] = "4. Enregistrer et importer via : /notes/importer/"
        
        print(f"\n✅ Template Excel généré : {chemin_fichier}")
        print(f"  📊 Nombre d'élèves : {len(data)}")
        
        # 6. Instructions pour l'importation
        print(f"\n📋 INSTRUCTIONS POUR L'ENSEIGNANT :")
        print(f"  1. Télécharger le fichier : {nom_fichier}")
        print(f"  2. Remplir les notes manuellement (colonne 'Note /20')")
        print(f"  3. Mettre 'OUI' pour les absences (laisser la note vide)")
        print(f"  4. Enregistrer le fichier")
        print(f"  5. Importer via : https://www.myschoolgn.space/notes/importer/")
        
        # 7. URL d'importation directe
        print(f"\n🌟 URL D'IMPORTATION DIRECTE :")
        print(f"  https://www.myschoolgn.space/notes/importer/?classe_id={classe_id}&matiere_id={matiere_id}&periode={periode}&type=evaluation")
        
        # 8. Statistiques actuelles
        from notes.models import Evaluation, NoteEleve
        evaluations = Evaluation.objects.filter(matiere=matiere, periode=periode)
        
        if evaluations.exists():
            evaluation = evaluations.first()
            notes_existantes = NoteEleve.objects.filter(evaluation=evaluation)
            print(f"\n📊 SITUATION ACTUELLE :")
            print(f"  • Notes déjà saisies : {notes_existantes.count()}/{eleves.count()}")
            print(f"  • Notes manquantes : {eleves.count() - notes_existantes.count()}")
            
            if notes_existantes.exists():
                notes_values = [note.note for note in notes_existantes]
                moyenne = round(sum(notes_values) / len(notes_values), 2)
                print(f"  • Moyenne actuelle : {moyenne}/20")
        
        return True
        
    except Exception as e:
        print(f"❌ Erreur : {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    generer_template_7eme_annee_a()
