"""
Script de test automatique pour trouver et tester la classe avec les élèves L12SC-xxx
"""
import os
import sys
import django

# Configuration Django
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ecole_moderne.settings')
django.setup()

from eleves.models import Eleve
from notes.models import ClasseNote
from notes.export_classement import _generer_classement_general

print("=" * 80)
print("RECHERCHE AUTOMATIQUE DE LA CLASSE L12SC")
print("=" * 80)

# 1. Trouver un élève avec matricule L12SC-xxx
print("\n🔍 Recherche d'élèves avec matricule L12SC-xxx...")
eleves_l12sc = Eleve.objects.filter(matricule__startswith='L12SC-', statut='ACTIF')

if not eleves_l12sc.exists():
    print("❌ Aucun élève avec matricule L12SC-xxx trouvé")
    print("\nExemples de matricules dans la base :")
    for e in Eleve.objects.filter(statut='ACTIF')[:10]:
        print(f"  - {e.matricule}: {e.prenom} {e.nom} (Classe: {e.classe.nom if e.classe else 'N/A'})")
    sys.exit(1)

print(f"✅ {eleves_l12sc.count()} élèves L12SC trouvés")

# 2. Récupérer la classe de ces élèves
eleve_test = eleves_l12sc.first()
classe_eleve = eleve_test.classe

print(f"\n✅ Classe trouvée : {classe_eleve.nom} (ID: {classe_eleve.id})")
print(f"   École : {classe_eleve.ecole.nom if classe_eleve.ecole else 'N/A'}")

# 3. Trouver la ClasseNote correspondante
classe_note = ClasseNote.objects.filter(
    nom__icontains=classe_eleve.nom.split()[0],  # Premier mot (ex: "12")
    ecole=classe_eleve.ecole
).first()

if not classe_note:
    print(f"\n❌ ClasseNote correspondante non trouvée pour {classe_eleve.nom}")
    print("\nClasseNote disponibles :")
    for cn in ClasseNote.objects.filter(ecole=classe_eleve.ecole)[:10]:
        print(f"  - ID {cn.id}: {cn.nom}")
    sys.exit(1)

print(f"✅ ClasseNote : {classe_note.nom} (ID: {classe_note.id})")

# 4. Lister tous les élèves L12SC de cette classe
print(f"\n📋 Liste des {eleves_l12sc.count()} élèves L12SC :")
print(f"{'Matricule':<15} {'Nom Complet':<40}")
print("-" * 60)
for e in eleves_l12sc.order_by('matricule')[:20]:
    print(f"{e.matricule:<15} {e.nom} {e.prenom:<40}")

# 5. Générer le classement
print("\n" + "=" * 80)
print("GÉNÉRATION DU CLASSEMENT")
print("=" * 80)

try:
    classement_data, titre = _generer_classement_general(
        eleves_l12sc, classe_note, 'mensuelle', 'OCTOBRE'
    )
    
    print(f"\n✅ Classement généré : {len(classement_data)} élèves")
    print(f"   Titre : {titre}\n")
    
    # Afficher le classement
    print("CLASSEMENT GÉNÉRAL :")
    print(f"{'Rang':<15} {'Matricule':<15} {'Nom Complet':<35} {'Moyenne':<10}")
    print("-" * 80)
    
    eleves_avec_notes = 0
    for eleve_data in classement_data:
        rang = eleve_data.get('rang', '-') or '-'
        matricule = eleve_data.get('matricule', '-') or '-'
        nom_complet = eleve_data.get('nom_complet', '-') or '-'
        moyenne = eleve_data.get('moyenne')
        moyenne_str = f"{moyenne:.2f}" if moyenne is not None else '-'
        
        if moyenne is not None:
            eleves_avec_notes += 1
            print(f"{rang:<15} {matricule:<15} {nom_complet:<35} {moyenne_str:<10}")
    
    print("\n" + "=" * 80)
    print(f"📊 STATISTIQUES")
    print("=" * 80)
    print(f"Total élèves : {len(classement_data)}")
    print(f"Avec notes : {eleves_avec_notes}")
    print(f"Sans notes : {len(classement_data) - eleves_avec_notes}")
    
    if eleves_avec_notes == 0:
        print("\n⚠️  AUCUN ÉLÈVE N'A DE NOTES POUR OCTOBRE !")
        print("   Vérifiez que les notes ont bien été saisies pour cette période.")
    else:
        print(f"\n✅ {eleves_avec_notes} élèves ont des notes et sont classés")
    
except Exception as e:
    print(f"\n❌ Erreur : {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 80)
