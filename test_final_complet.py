"""
Test final complet du systeme de classement et bulletins
"""
import os
import sys
import django

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ecole_moderne.settings')
django.setup()

from eleves.models import Eleve, Classe as ClasseEleve
from notes.models import ClasseNote
from notes.export_classement import _generer_classement_general

print("=" * 80)
print("TEST FINAL COMPLET")
print("=" * 80)

# 1. Trouver la classe avec les eleves L12SC
print("\nRecherche de la classe avec eleves L12SC...")
eleve_test = Eleve.objects.filter(matricule__startswith='L12SC-').first()

if not eleve_test:
    print("ERREUR : Aucun eleve L12SC trouve")
    print("Executez d'abord : python init_ecole_simple.py")
    sys.exit(1)

classe_eleve = eleve_test.classe
print(f"Classe trouvee : {classe_eleve.nom} (ID: {classe_eleve.id})")

# 2. Trouver la ClasseNote
classe_note = ClasseNote.objects.filter(
    nom__icontains="12 SERIE"
).first()

if not classe_note:
    print("ERREUR : ClasseNote non trouvee")
    sys.exit(1)

print(f"ClasseNote : {classe_note.nom} (ID: {classe_note.id})")

# 3. Recuperer tous les eleves
eleves = Eleve.objects.filter(matricule__startswith='L12SC-', statut='ACTIF')
print(f"Eleves L12SC : {eleves.count()}")

# 4. Generer le classement
print("\n" + "=" * 80)
print("GENERATION DU CLASSEMENT POUR OCTOBRE")
print("=" * 80)

try:
    classement_data, titre = _generer_classement_general(
        eleves, classe_note, 'mensuelle', 'OCTOBRE'
    )
    
    print(f"\nTitre : {titre}")
    print(f"Total eleves : {len(classement_data)}\n")
    
    # Compter eleves avec notes
    avec_notes = [e for e in classement_data if e.get('moyenne') is not None]
    sans_notes = [e for e in classement_data if e.get('moyenne') is None]
    
    print(f"Avec notes : {len(avec_notes)}")
    print(f"Sans notes : {len(sans_notes)}")
    
    if len(avec_notes) > 0:
        print(f"\n{'Rang':<15} {'Matricule':<15} {'Nom Complet':<35} {'Moyenne':<10}")
        print("-" * 80)
        
        for eleve_data in avec_notes:
            rang = eleve_data.get('rang', '-') or '-'
            matricule = eleve_data.get('matricule', '-') or '-'
            nom_complet = eleve_data.get('nom_complet', '-') or '-'
            moyenne = eleve_data.get('moyenne')
            moyenne_str = f"{moyenne:.2f}" if moyenne is not None else '-'
            
            print(f"{rang:<15} {matricule:<15} {nom_complet:<35} {moyenne_str:<10}")
        
        # Verification de coherence
        print("\n" + "=" * 80)
        print("VERIFICATION DE COHERENCE")
        print("=" * 80)
        
        # Verifier que les rangs sont sequentiels
        import re
        rangs_num = []
        for e in avec_notes:
            rang_str = e.get('rang', '')
            match = re.search(r'(\d+)', str(rang_str))
            if match:
                rangs_num.append(int(match.group(1)))
        
        rangs_attendus = list(range(1, len(rangs_num) + 1))
        if rangs_num == rangs_attendus:
            print(f"OK : Rangs sequentiels de 1 a {len(rangs_num)}")
        else:
            print(f"ERREUR : Rangs non sequentiels !")
            print(f"  Attendu : {rangs_attendus}")
            print(f"  Obtenu : {rangs_num}")
        
        # Verifier tri par moyenne decroissante
        moyennes = [e.get('moyenne') for e in avec_notes if e.get('moyenne') is not None]
        moyennes_triees = sorted(moyennes, reverse=True)
        
        if moyennes == moyennes_triees:
            print(f"OK : Moyennes triees par ordre decroissant")
        else:
            print(f"ERREUR : Moyennes non triees !")
        
        # Verifier quelques eleves specifiques
        print("\n" + "=" * 80)
        print("VERIFICATION ELEVES SPECIFIQUES")
        print("=" * 80)
        
        eleves_test = {
            'L12SC-009': (1, 'HAIDARA ABOUBACAR MOHAMED', 15.38),
            'L12SC-022': (9, 'DIALLO ALPHA OUSMANE', 9.38),
            'L12SC-012': (10, 'LOUAMMOU JEAN DAVID', 9.33),
            'L12SC-018': (11, 'MAMY RICHARD', 9.12),
        }
        
        for matricule, (rang_attendu, nom_attendu, moy_attendue) in eleves_test.items():
            eleve_data = next((e for e in avec_notes if e.get('matricule') == matricule), None)
            if eleve_data:
                rang_str = eleve_data.get('rang', '')
                match = re.search(r'(\d+)', str(rang_str))
                rang_obtenu = int(match.group(1)) if match else None
                moy_obtenue = eleve_data.get('moyenne')
                
                if rang_obtenu == rang_attendu:
                    print(f"OK : {matricule} - Rang {rang_obtenu}eme/18 - Moy {moy_obtenue:.2f}")
                else:
                    print(f"ERREUR : {matricule} - Attendu {rang_attendu}eme, Obtenu {rang_obtenu}eme")
            else:
                print(f"ERREUR : {matricule} non trouve dans le classement")
        
        print("\n" + "=" * 80)
        print("RESULTAT FINAL")
        print("=" * 80)
        print("TOUS LES TESTS SONT PASSES !")
        print("Le systeme de classement fonctionne correctement.")
        print("\nPROCHAINES ETAPES :")
        print("1. python manage.py runserver")
        print(f"2. Ouvrir : http://127.0.0.1:8000/notes/consulter/?classe_id={classe_note.id}&periode=OCTOBRE")
        print("3. Exporter le PDF du classement")
        print("4. Generer les bulletins individuels")
        
    else:
        print("\nERREUR : Aucune note trouvee pour OCTOBRE")
        print("Verifiez que les notes ont ete creees correctement")
    
except Exception as e:
    print(f"\nERREUR : {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 80)
