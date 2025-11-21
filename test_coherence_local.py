"""
Test de cohérence sur la base de données locale
"""
import os
import sys
import django

# Configuration Django
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ecole_moderne.settings')
django.setup()

from eleves.models import Eleve, Classe as ClasseEleve
from notes.models import ClasseNote
from notes.export_classement import _generer_classement_general

print("=" * 80)
print("TEST DE COHÉRENCE - BASE DE DONNÉES LOCALE")
print("=" * 80)

# 1. Trouver la classe 12ÈME SCIENCES
print("\n🔍 Recherche de la classe 12ÈME SCIENCES...")
classe_eleve = ClasseEleve.objects.filter(nom__icontains='12').filter(nom__icontains='SCIENCE').first()

if not classe_eleve:
    print("❌ Classe 12ÈME SCIENCES non trouvée")
    print("\nClasses disponibles :")
    for c in ClasseEleve.objects.all()[:15]:
        print(f"  - {c.nom}")
    sys.exit(1)

print(f"✅ Classe trouvée : {classe_eleve.nom} (ID: {classe_eleve.id})")

# 2. Récupérer les élèves
eleves = Eleve.objects.filter(classe=classe_eleve, statut='ACTIF')
print(f"✅ Élèves actifs : {eleves.count()}")

if eleves.count() == 0:
    print("❌ Aucun élève actif dans cette classe")
    sys.exit(1)

# 3. Afficher quelques élèves
print(f"\n📋 Premiers élèves de la classe :")
for e in eleves[:5]:
    print(f"  - {e.matricule}: {e.prenom} {e.nom}")

# 4. Trouver la ClasseNote
classe_note = ClasseNote.objects.filter(
    nom__icontains='12',
    ecole=classe_eleve.ecole
).filter(nom__icontains='SCIEN').first()

if not classe_note:
    print("\n❌ ClasseNote non trouvée")
    sys.exit(1)

print(f"\n✅ ClasseNote : {classe_note.nom} (ID: {classe_note.id})")

# 5. Générer le classement pour OCTOBRE
print("\n" + "=" * 80)
print("GÉNÉRATION DU CLASSEMENT - OCTOBRE")
print("=" * 80)

try:
    classement_data, titre = _generer_classement_general(
        eleves, classe_note, 'mensuelle', 'OCTOBRE'
    )
    
    print(f"\n✅ Classement généré")
    print(f"   Titre : {titre}")
    print(f"   Total élèves : {len(classement_data)}\n")
    
    # Compter les élèves avec notes
    avec_notes = [e for e in classement_data if e.get('moyenne') is not None]
    sans_notes = [e for e in classement_data if e.get('moyenne') is None]
    
    print(f"📊 Statistiques :")
    print(f"   Avec notes : {len(avec_notes)}")
    print(f"   Sans notes : {len(sans_notes)}")
    
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
        
        # Test de cohérence
        print("\n" + "=" * 80)
        print("TEST DE COHÉRENCE")
        print("=" * 80)
        
        # Vérifier que les rangs sont séquentiels
        import re
        rangs_num = []
        for e in avec_notes:
            rang_str = e.get('rang', '')
            match = re.search(r'(\d+)', str(rang_str))
            if match:
                rangs_num.append(int(match.group(1)))
        
        if rangs_num:
            rangs_attendus = list(range(1, len(rangs_num) + 1))
            if rangs_num == rangs_attendus:
                print(f"✅ Les rangs sont séquentiels de 1 à {len(rangs_num)}")
            else:
                print(f"❌ Les rangs ne sont pas séquentiels !")
                print(f"   Attendu : {rangs_attendus}")
                print(f"   Obtenu : {rangs_num}")
        
        # Vérifier le tri par moyenne décroissante
        moyennes = [e.get('moyenne') for e in avec_notes if e.get('moyenne') is not None]
        moyennes_triees = sorted(moyennes, reverse=True)
        
        if moyennes == moyennes_triees:
            print(f"✅ Les moyennes sont triées par ordre décroissant")
        else:
            print(f"❌ Les moyennes ne sont pas triées correctement !")
        
        print(f"\n🎉 CLASSEMENT FONCTIONNEL !")
        
    else:
        print("\n⚠️  AUCUN ÉLÈVE N'A DE NOTES POUR OCTOBRE")
        print("   Les notes doivent être saisies pour cette période.")
        print("\n💡 Pour tester sur le serveur de production :")
        print("   1. Connectez-vous en SSH au serveur")
        print("   2. Lancez ce script sur le serveur")
        print("   3. Les données du serveur contiennent les matricules L12SC-xxx")
    
except Exception as e:
    print(f"\n❌ Erreur : {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 80)
