"""
Diagnostic automatique des notes mensuelles pour la classe 9ÈME ANNÉE
"""

import os
import sys
import django

# Configuration Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ecole_moderne.settings')
django.setup()

from notes.models import NoteMensuelle, ClasseNote, MatiereNote
from eleves.models import Eleve

def diagnostic_complet():
    print("\n" + "="*80)
    print("🔍 DIAGNOSTIC DES NOTES MENSUELLES - CLASSE 9ÈME ANNÉE")
    print("="*80)
    
    # 1. Vérifier la classe
    print("\n📚 RECHERCHE DE LA CLASSE...")
    classes_9eme = ClasseNote.objects.filter(nom__icontains="9")
    
    if not classes_9eme.exists():
        print("❌ Aucune classe de 9ème trouvée")
        return
    
    for classe in classes_9eme:
        print(f"✅ Classe trouvée : {classe.nom} (ID: {classe.id})")
        print(f"   Année scolaire : {classe.annee_scolaire}")
        
        # 2. Compter les élèves
        eleves = Eleve.objects.filter(classe__nom=classe.nom, statut='INSCRIT')
        print(f"\n👥 ÉLÈVES INSCRITS : {eleves.count()}")
        
        if eleves.count() > 0:
            # Afficher quelques élèves
            print("\n   Exemples d'élèves :")
            for eleve in eleves[:5]:
                print(f"   • {eleve.matricule} - {eleve.nom} {eleve.prenom}")
        
        # 3. Compter les matières
        matieres = MatiereNote.objects.filter(classe=classe)
        print(f"\n📖 MATIÈRES : {matieres.count()}")
        
        if matieres.count() > 0:
            print("\n   Liste des matières :")
            for matiere in matieres:
                print(f"   • {matiere.nom} (Coef: {matiere.coefficient})")
        
        # 4. Vérifier les notes mensuelles pour OCTOBRE
        print("\n📊 NOTES MENSUELLES POUR OCTOBRE :")
        
        notes_octobre = NoteMensuelle.objects.filter(
            eleve__in=eleves,
            mois='OCTOBRE',
            annee_scolaire=classe.annee_scolaire
        )
        
        print(f"   Total notes trouvées : {notes_octobre.count()}")
        
        if notes_octobre.exists():
            # Statistiques par matière
            print("\n   📈 Statistiques par matière :")
            for matiere in matieres:
                notes_matiere = notes_octobre.filter(matiere=matiere)
                if notes_matiere.exists():
                    notes_valides = notes_matiere.filter(absent=False, note__isnull=False)
                    if notes_valides.exists():
                        notes_list = [float(n.note) for n in notes_valides]
                        moyenne = sum(notes_list) / len(notes_list)
                        print(f"      • {matiere.nom:25} : {notes_valides.count()} notes, Moy: {moyenne:.2f}/20")
                    else:
                        print(f"      • {matiere.nom:25} : Aucune note valide")
                else:
                    print(f"      • {matiere.nom:25} : AUCUNE NOTE ❌")
                    
            # Afficher quelques notes
            print("\n   📝 Échantillon de notes :")
            for note in notes_octobre[:5]:
                if note.absent:
                    print(f"      • {note.eleve.matricule} - {note.matiere.nom} : ABSENT")
                elif note.note:
                    print(f"      • {note.eleve.matricule} - {note.matiere.nom} : {note.note}/20")
        else:
            print("   ❌ AUCUNE NOTE TROUVÉE POUR OCTOBRE")
            print("\n   ⚠️ PROBLÈME IDENTIFIÉ :")
            print("      Les notes mensuelles n'ont pas été saisies pour cette classe.")
            print("\n   💡 SOLUTIONS POSSIBLES :")
            print("      1. Saisir les notes via : /notes/mensuelles/")
            print("      2. Importer les notes via Excel : /notes/importer/")
            print("      3. Utiliser le script de création de notes de test")
        
        # 5. Vérifier les autres mois
        print("\n📅 AUTRES PÉRIODES :")
        mois_list = ['NOVEMBRE', 'DECEMBRE', 'JANVIER', 'FEVRIER', 'MARS', 'AVRIL', 'MAI']
        
        for mois in mois_list:
            notes_mois = NoteMensuelle.objects.filter(
                eleve__in=eleves,
                mois=mois,
                annee_scolaire=classe.annee_scolaire
            ).count()
            if notes_mois > 0:
                print(f"   • {mois:10} : {notes_mois} notes")
            else:
                print(f"   • {mois:10} : Aucune note")
    
    print("\n" + "="*80)
    print("📋 RÉSUMÉ DU DIAGNOSTIC")
    print("="*80)
    
    if not notes_octobre.exists():
        print("\n⚠️ DIAGNOSTIC : Les notes mensuelles d'OCTOBRE ne sont pas saisies")
        print("\n✅ SOLUTION RECOMMANDÉE :")
        print("   1. Connectez-vous à l'application")
        print("   2. Allez dans Notes → Notes Mensuelles")
        print("   3. Sélectionnez la classe 9ÈME ANNÉE")
        print("   4. Sélectionnez le mois OCTOBRE")
        print("   5. Saisissez les notes pour chaque élève et matière")
        print("\n   OU")
        print("\n   Utilisez l'import Excel :")
        print("   1. Notes → Importer Notes")
        print("   2. Type : Notes Mensuelles")
        print("   3. Téléchargez le template")
        print("   4. Remplissez et importez")
    else:
        print("\n✅ Des notes existent pour OCTOBRE")
        print(f"   Total : {notes_octobre.count()} notes")
        print("\n⚠️ Si elles ne s'affichent pas dans le bulletin :")
        print("   1. Vérifiez que le serveur a été redémarré")
        print("   2. Vérifiez que l'import NoteMensuelle est présent")
        print("   3. Videz le cache du navigateur")

if __name__ == "__main__":
    diagnostic_complet()
