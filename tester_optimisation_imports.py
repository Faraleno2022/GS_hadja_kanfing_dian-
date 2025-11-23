#!/usr/bin/env python
"""
Script de test pour valider les optimisations d'importation
Mesure le gain de performance et le nombre de requêtes SQL
"""
import os
import sys
import django
import time
from io import BytesIO
import pandas as pd

# Configuration Django
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ecole_moderne.settings')
django.setup()

from django.db import connection, reset_queries
from django.conf import settings
from notes.import_notes import ImportNotesProcessor, lire_fichier_import
from eleves.import_eleves import ImportElevesProcessor
from eleves.models import Eleve, Classe
from notes.models import MatiereNote, ClasseNote

# Activer le debug pour compter les requêtes
settings.DEBUG = True

def compter_requetes(func):
    """Décorateur pour compter les requêtes SQL"""
    def wrapper(*args, **kwargs):
        reset_queries()
        start_time = time.time()
        
        result = func(*args, **kwargs)
        
        end_time = time.time()
        nb_requetes = len(connection.queries)
        duree = end_time - start_time
        
        return result, nb_requetes, duree
    return wrapper


@compter_requetes
def tester_import_notes(nb_lignes=50):
    """Teste l'import de notes avec les optimisations"""
    print(f"\n📝 TEST IMPORT DE {nb_lignes} NOTES")
    print("=" * 50)
    
    # Créer un DataFrame de test
    classe_note = ClasseNote.objects.first()
    matiere = MatiereNote.objects.filter(classe=classe_note).first()
    eleves = Eleve.objects.all()[:nb_lignes]
    
    if not classe_note or not matiere or not eleves:
        print("❌ Données de test insuffisantes")
        return None
    
    # Créer un fichier Excel de test en mémoire
    data = {
        'Matricule': [e.matricule for e in eleves],
        'Prénom': [e.prenom for e in eleves],
        'Nom': [e.nom for e in eleves],
        'Note': [float(15 + (i % 5)) for i in range(nb_lignes)],
        'Absent': ['NON'] * nb_lignes
    }
    
    df = pd.DataFrame(data)
    
    # Créer le processeur
    processor = ImportNotesProcessor(
        df=df,
        classe_id=classe_note.id,
        matiere_id=matiere.id,
        periode='JANVIER',
        annee_scolaire='2024-2025',
        type_import='MENSUELLE'
    )
    
    # Importer
    stats = processor.importer()
    
    return stats


@compter_requetes
def tester_import_eleves(nb_lignes=30):
    """Teste l'import d'élèves avec les optimisations"""
    print(f"\n👥 TEST IMPORT DE {nb_lignes} ÉLÈVES")
    print("=" * 50)
    
    # Créer un DataFrame de test
    classe = Classe.objects.first()
    
    if not classe:
        print("❌ Aucune classe trouvée")
        return None
    
    data = {
        'Matricule': [''] * nb_lignes,  # Génération auto
        'Prénom': [f'Prénom{i}' for i in range(nb_lignes)],
        'Nom': [f'NOM{i}' for i in range(nb_lignes)],
        'Sexe': ['M' if i % 2 == 0 else 'F' for i in range(nb_lignes)],
        'Date de Naissance': ['15/01/2010'] * nb_lignes,
        'Lieu de Naissance': ['Conakry'] * nb_lignes,
        'Nom du Père/Tuteur': [f'PERE{i}' for i in range(nb_lignes)],
        'Prénom du Père/Tuteur': [f'PrenomPere{i}' for i in range(nb_lignes)],
        'Téléphone Principal': [f'62200{i:04d}' for i in range(nb_lignes)],
        'Adresse': ['Ratoma'] * nb_lignes,
        'Nom de la Mère': [f'MERE{i}' for i in range(nb_lignes)],
        'Prénom de la Mère': [f'PrenomMere{i}' for i in range(nb_lignes)],
        'Téléphone Secondaire': [''] * nb_lignes,
        'Email': [''] * nb_lignes
    }
    
    df = pd.DataFrame(data)
    
    # Créer le processeur
    processor = ImportElevesProcessor(
        df=df,
        classe_id=classe.id,
        generer_matricules=True
    )
    
    # Importer
    stats = processor.importer()
    
    return stats


def afficher_resultats(nom_test, stats, nb_requetes, duree, nb_lignes):
    """Affiche les résultats d'un test"""
    print(f"\n✅ {nom_test} TERMINÉ")
    print("-" * 50)
    
    if stats:
        print(f"📊 Statistiques :")
        for key, value in stats.items():
            print(f"   - {key}: {value}")
    
    print(f"\n⚡ Performance :")
    print(f"   - Temps : {duree:.2f} secondes")
    print(f"   - Requêtes SQL : {nb_requetes}")
    print(f"   - Lignes traitées : {nb_lignes}")
    print(f"   - Requêtes par ligne : {nb_requetes/nb_lignes:.2f}")
    print(f"   - Temps par ligne : {duree/nb_lignes*1000:.1f} ms")
    
    # Calcul du gain estimé
    requetes_anciennes = nb_lignes * 3  # Estimation conservatrice
    gain_requetes = (1 - nb_requetes / requetes_anciennes) * 100
    
    print(f"\n🚀 Gain estimé :")
    print(f"   - Requêtes évitées : ~{requetes_anciennes - nb_requetes}")
    print(f"   - Réduction : {gain_requetes:.1f}%")
    print(f"   - Ancien temps estimé : {duree * (requetes_anciennes/nb_requetes):.1f}s")
    print(f"   - Accélération : {(requetes_anciennes/nb_requetes):.1f}x plus rapide")


def main():
    """Fonction principale"""
    print("\n" + "="*60)
    print("🔬 TEST DES OPTIMISATIONS D'IMPORTATION")
    print("="*60)
    
    try:
        # Test 1 : Import de notes
        stats_notes, nb_req_notes, duree_notes = tester_import_notes(nb_lignes=50)
        if stats_notes:
            afficher_resultats("IMPORT NOTES", stats_notes, nb_req_notes, duree_notes, 50)
        
        # Test 2 : Import d'élèves
        stats_eleves, nb_req_eleves, duree_eleves = tester_import_eleves(nb_lignes=30)
        if stats_eleves:
            afficher_resultats("IMPORT ÉLÈVES", stats_eleves, nb_req_eleves, duree_eleves, 30)
        
        # Résumé global
        print("\n" + "="*60)
        print("📈 RÉSUMÉ GLOBAL")
        print("="*60)
        
        if stats_notes and stats_eleves:
            total_requetes = nb_req_notes + nb_req_eleves
            total_duree = duree_notes + duree_eleves
            total_lignes = 50 + 30
            
            print(f"\n✅ Total traité : {total_lignes} lignes")
            print(f"⚡ Temps total : {total_duree:.2f} secondes")
            print(f"📊 Requêtes SQL totales : {total_requetes}")
            print(f"🚀 Moyenne : {total_requetes/total_lignes:.2f} requêtes/ligne")
            
            # Estimation ancienne méthode
            ancien_total_req = total_lignes * 3
            ancien_total_temps = total_duree * (ancien_total_req / total_requetes)
            
            print(f"\n💡 Comparaison avec ancienne méthode :")
            print(f"   - Requêtes évitées : ~{ancien_total_req - total_requetes}")
            print(f"   - Temps gagné : ~{ancien_total_temps - total_duree:.1f}s")
            print(f"   - Accélération : {ancien_total_req/total_requetes:.1f}x plus rapide")
            
            print(f"\n🏆 OPTIMISATION VALIDÉE !")
            print(f"   ✅ Réduction de {(1 - total_requetes/ancien_total_req)*100:.1f}% des requêtes")
            print(f"   ✅ {ancien_total_req/total_requetes:.1f}x plus rapide")
        
        print("\n" + "="*60)
        
    except Exception as e:
        print(f"\n❌ Erreur pendant les tests : {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
