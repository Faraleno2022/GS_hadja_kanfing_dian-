"""
Script de debug pour le serveur de production
À exécuter sur le serveur pour diagnostiquer le problème
"""

import os
import sys
import django

# Configuration Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ecole_moderne.settings')
django.setup()

from notes.models import NoteMensuelle, ClasseNote, MatiereNote
from eleves.models import Eleve, Classe

def debug_production():
    print("\n" + "="*80)
    print("🔍 DEBUG PRODUCTION - NOTES MENSUELLES")
    print("="*80)
    
    # 1. Trouver l'élève CL9-011
    print("\n1️⃣ RECHERCHE ÉLÈVE CL9-011...")
    try:
        eleve = Eleve.objects.get(matricule='CL9-011')
        print(f"✅ Élève trouvé : {eleve.nom} {eleve.prenom}")
        print(f"   • Classe : {eleve.classe.nom} (ID: {eleve.classe.id})")
        print(f"   • Année scolaire : {eleve.classe.annee_scolaire}")
        print(f"   • Statut : {eleve.statut}")
        
        # 2. Trouver la ClasseNote correspondante
        print("\n2️⃣ RECHERCHE CLASSENOTE...")
        classe_note = ClasseNote.objects.filter(
            nom__icontains='9',
            annee_scolaire=eleve.classe.annee_scolaire
        ).first()
        
        if classe_note:
            print(f"✅ ClasseNote trouvée : {classe_note.nom} (ID: {classe_note.id})")
            
            # 3. Vérifier les matières
            print("\n3️⃣ MATIÈRES CONFIGURÉES...")
            matieres = MatiereNote.objects.filter(classe=classe_note)
            print(f"Total matières : {matieres.count()}")
            
            if matieres.exists():
                for mat in matieres[:5]:
                    print(f"   • {mat.nom} (Coef: {mat.coefficient})")
            
            # 4. Vérifier les notes mensuelles
            print("\n4️⃣ NOTES MENSUELLES OCTOBRE...")
            notes = NoteMensuelle.objects.filter(
                eleve=eleve,
                mois='OCTOBRE',
                annee_scolaire=eleve.classe.annee_scolaire
            )
            
            print(f"Total notes pour cet élève : {notes.count()}")
            
            if notes.exists():
                print("\n📊 Détail des notes :")
                for note in notes:
                    if note.absent:
                        print(f"   • {note.matiere.nom:25} : ABSENT")
                    else:
                        print(f"   • {note.matiere.nom:25} : {note.note}/20")
            else:
                print("❌ AUCUNE NOTE trouvée pour OCTOBRE")
                
                # Vérifier si des notes existent pour d'autres mois
                print("\n📅 Vérification autres mois...")
                mois_list = ['NOVEMBRE', 'DECEMBRE', 'JANVIER', 'FEVRIER', 'MARS', 'AVRIL', 'MAI']
                for mois in mois_list:
                    nb = NoteMensuelle.objects.filter(
                        eleve=eleve,
                        mois=mois,
                        annee_scolaire=eleve.classe.annee_scolaire
                    ).count()
                    if nb > 0:
                        print(f"   • {mois} : {nb} notes")
            
            # 5. URL correcte
            print("\n5️⃣ URL CORRECTE POUR LE BULLETIN :")
            url = f"/notes/bulletins/?classe_id={classe_note.id}&eleve_id={eleve.id}&periode=OCTOBRE&system_type=mensuel"
            print(f"   {url}")
            
        else:
            print("❌ ClasseNote non trouvée")
            
            # Lister toutes les ClasseNote de 2025-2026
            print("\n📋 Toutes les ClasseNote 2025-2026 :")
            classes_2025 = ClasseNote.objects.filter(annee_scolaire='2025-2026')
            for c in classes_2025:
                print(f"   • ID: {c.id} - {c.nom}")
            
    except Eleve.DoesNotExist:
        print("❌ Élève CL9-011 non trouvé")
        
        # Chercher des élèves similaires
        print("\n🔍 Recherche d'élèves similaires...")
        eleves_cl9 = Eleve.objects.filter(matricule__startswith='CL9-')[:10]
        if eleves_cl9.exists():
            print("Élèves avec matricule commençant par CL9- :")
            for e in eleves_cl9:
                print(f"   • {e.matricule} - {e.nom} {e.prenom} ({e.classe.nom})")
    
    print("\n" + "="*80)
    print("📋 RÉSUMÉ DU DIAGNOSTIC")
    print("="*80)
    
    print("\n💡 SI LES NOTES NE S'AFFICHENT PAS :")
    print("   1. Vérifier que les notes sont saisies (ci-dessus)")
    print("   2. Vérifier que l'import NoteMensuelle est présent dans views.py ligne 17")
    print("   3. Vérifier l'URL utilisée (doit correspondre aux IDs trouvés)")
    print("   4. Redémarrer Django : touch ecole_moderne/wsgi.py")
    
    print("\n💡 SI LES NOTES NE SONT PAS SAISIES :")
    print("   1. Se connecter à l'interface web")
    print("   2. Notes → Notes Mensuelles")
    print("   3. Sélectionner la bonne classe et OCTOBRE")
    print("   4. Saisir les notes ou importer via Excel")

if __name__ == "__main__":
    debug_production()
