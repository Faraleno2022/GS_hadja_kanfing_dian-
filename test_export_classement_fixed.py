"""
Test du système d'export de classement corrigé
Vérifie que les notes sont bien récupérées et que les rangs sont calculés
"""
import os
import django
import sys

# Configuration Django
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ecole_moderne.settings')
django.setup()

from notes.models import ClasseNote
from notes.export_classement import _generer_classement_general, _generer_classement_matiere
from eleves.models import Eleve, Classe as ClasseEleve
import re

def tester_correspondance_classe():
    """Tester la logique de correspondance des classes"""
    
    print("\n" + "="*80)
    print("TEST DE CORRESPONDANCE DES CLASSES")
    print("="*80 + "\n")
    
    # Récupérer une classe note de 12ème
    classe_note = ClasseNote.objects.filter(nom__icontains='12').filter(nom__icontains='scien').first()
    
    if not classe_note:
        print("❌ Aucune classe note 12ème scientifique trouvée")
        return
    
    print(f"✅ ClasseNote trouvée: {classe_note.nom}")
    print(f"   ID: {classe_note.id}")
    print(f"   Année: {classe_note.annee_scolaire}")
    
    # Essai 1: Correspondance exacte
    classe_eleve = ClasseEleve.objects.filter(
        nom=classe_note.nom,
        annee_scolaire=classe_note.annee_scolaire,
        ecole=classe_note.ecole
    ).first()
    
    if classe_eleve:
        print(f"\n✅ Correspondance exacte trouvée: {classe_eleve.nom}")
    else:
        print(f"\n⚠️  Pas de correspondance exacte")
        
        # Essai 2: Correspondance insensible à la casse
        classe_eleve = ClasseEleve.objects.filter(
            nom__iexact=classe_note.nom,
            annee_scolaire=classe_note.annee_scolaire,
            ecole=classe_note.ecole
        ).first()
        
        if classe_eleve:
            print(f"✅ Correspondance insensible casse: {classe_eleve.nom}")
        else:
            print("⚠️  Pas de correspondance insensible casse")
            
            # Essai 3: Recherche par niveau
            match = re.search(r'(\d+)', classe_note.nom)
            if match:
                niveau_num = match.group(1)
                print(f"   Recherche avec niveau: {niveau_num}")
                
                classes_possibles = ClasseEleve.objects.filter(
                    nom__icontains=niveau_num,
                    annee_scolaire=classe_note.annee_scolaire,
                    ecole=classe_note.ecole
                )
                
                print(f"   {classes_possibles.count()} classe(s) trouvée(s):")
                for c in classes_possibles:
                    print(f"      - {c.nom}")
                
                # Affiner avec mots-clés
                if 'scientifique' in classe_note.nom.lower() or 'science' in classe_note.nom.lower():
                    for c in classes_possibles:
                        if 'SCIENCE' in c.nom.upper():
                            classe_eleve = c
                            break
                    
                    if classe_eleve:
                        print(f"\n✅ Correspondance par mots-clés: {classe_eleve.nom}")
    
    if classe_eleve:
        # Compter les élèves
        eleves = Eleve.objects.filter(classe=classe_eleve, statut='ACTIF')
        print(f"\n📊 Élèves actifs: {eleves.count()}")
        
        if eleves.count() > 0:
            print("\nPremiers élèves:")
            for eleve in eleves[:5]:
                print(f"   - {eleve.matricule}: {eleve.nom} {eleve.prenom} ({eleve.sexe})")
            
            # Tester la génération du classement
            print(f"\n{'='*80}")
            print("TEST DE GÉNÉRATION DU CLASSEMENT")
            print(f"{'='*80}\n")
            
            try:
                classement_data, titre = _generer_classement_general(
                    eleves, 
                    classe_note, 
                    type_note='mensuelle', 
                    periode='TRIMESTRE_1'
                )
                
                print(f"✅ Titre: {titre}")
                print(f"✅ Nombre d'élèves dans le classement: {len(classement_data)}")
                
                eleves_avec_notes = [e for e in classement_data if e.get('moyenne') is not None]
                eleves_sans_notes = [e for e in classement_data if e.get('moyenne') is None]
                
                print(f"\n📊 Statistiques:")
                print(f"   - Avec notes: {len(eleves_avec_notes)}")
                print(f"   - Sans notes: {len(eleves_sans_notes)}")
                
                if eleves_avec_notes:
                    print(f"\n🏆 Top 5:")
                    for i, eleve_data in enumerate(eleves_avec_notes[:5], 1):
                        rang = eleve_data.get('rang', '-')
                        sexe = eleve_data.get('sexe', 'M')
                        
                        # Formater le rang avec accord grammatical
                        if rang == 1:
                            rang_str = "1ère" if sexe == 'F' else "1er"
                        elif rang > 1:
                            rang_str = f"{rang}ème"
                        else:
                            rang_str = "-"
                        
                        print(f"   {rang_str}. {eleve_data['nom_complet']}: {eleve_data['moyenne']:.2f}/20")
                
                if eleves_sans_notes:
                    print(f"\n⚠️  Élèves sans notes:")
                    for eleve_data in eleves_sans_notes[:5]:
                        raison = "Absent" if eleve_data.get('absent') else "Pas de notes"
                        print(f"   - {eleve_data['nom_complet']}: {raison}")
                        
                    if len(eleves_sans_notes) > 5:
                        print(f"   ... et {len(eleves_sans_notes) - 5} autre(s)")
                
            except Exception as e:
                print(f"❌ Erreur lors de la génération: {e}")
                import traceback
                traceback.print_exc()
    else:
        print("\n❌ Impossible de trouver la classe élève correspondante")


if __name__ == '__main__':
    tester_correspondance_classe()
