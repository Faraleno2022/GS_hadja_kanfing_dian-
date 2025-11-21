"""
Script de test final pour vérifier la cohérence des rangs
entre le classement général et les bulletins individuels
"""
import os
import sys
import django

# Configuration Django
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ecole_moderne.settings')
django.setup()

from eleves.models import Eleve
from notes.models import ClasseNote, MatiereNote, Evaluation, NoteEleve
from notes.export_classement import _generer_classement_general
from decimal import Decimal

print("=" * 80)
print("TEST DE COHÉRENCE : CLASSEMENT vs BULLETINS")
print("=" * 80)

# 1. Récupérer la classe
try:
    # Chercher la classe 12 SÉRIE SCIENTIFIQUE
    classe_note = ClasseNote.objects.filter(nom__icontains='12').filter(nom__icontains='SCIEN').first()
    if not classe_note:
        print("\n❌ Classe 12 SÉRIE SCIENTIFIQUE non trouvée")
        print("\nClasses disponibles :")
        for cn in ClasseNote.objects.all()[:10]:
            print(f"  - ID {cn.id}: {cn.nom}")
        sys.exit(1)
    
    print(f"\n✓ Classe trouvée : {classe_note.nom} (ID: {classe_note.id})")
except Exception as e:
    print(f"\n❌ Erreur lors de la recherche de la classe : {e}")
    sys.exit(1)

# 2. Récupérer les élèves de cette classe
try:
    # Trouver la ClasseEleve correspondante
    from eleves.models import Classe as ClasseEleve
    classe_eleve = ClasseEleve.objects.filter(
        nom__icontains='12'
    ).filter(
        nom__icontains='SCIEN'
    ).first()
    
    if not classe_eleve:
        print("\n❌ ClasseEleve 12 SÉRIE SCIENTIFIQUE non trouvée")
        sys.exit(1)
    
    eleves = Eleve.objects.filter(classe=classe_eleve, statut='ACTIF')
    print(f"✓ ClasseEleve : {classe_eleve.nom} (ID: {classe_eleve.id})")
    print(f"✓ Élèves actifs : {eleves.count()}")
except Exception as e:
    print(f"\n❌ Erreur lors de la recherche des élèves : {e}")
    sys.exit(1)

# 3. Générer le classement général
print("\n" + "-" * 80)
print("GÉNÉRATION DU CLASSEMENT GÉNÉRAL")
print("-" * 80)

try:
    classement_data, titre = _generer_classement_general(
        eleves, classe_note, 'mensuelle', 'OCTOBRE'
    )
    print(f"✓ Classement généré : {len(classement_data)} élèves")
    print(f"✓ Titre : {titre}\n")
    
    # Afficher le classement
    print("CLASSEMENT GÉNÉRAL :")
    print(f"{'Rang':<12} {'Matricule':<15} {'Nom Complet':<35} {'Moyenne':<10}")
    print("-" * 80)
    
    classement_dict = {}
    for i, eleve_data in enumerate(classement_data[:18], 1):
        rang = eleve_data.get('rang', 'N/A') or 'N/A'
        matricule = eleve_data.get('matricule', 'N/A') or 'N/A'
        nom_complet = eleve_data.get('nom_complet', 'N/A') or 'N/A'
        moyenne = eleve_data.get('moyenne')
        moyenne_str = f"{moyenne:.2f}" if moyenne is not None else 'N/A'
        eleve_id = eleve_data.get('eleve_id')
        
        # Stocker pour comparaison
        if eleve_id:
            classement_dict[eleve_id] = {
                'rang': rang,
                'moyenne': moyenne,
                'nom': nom_complet
            }
        
        print(f"{rang:<12} {matricule:<15} {nom_complet:<35} {moyenne_str:<10}")
    
except Exception as e:
    print(f"❌ Erreur lors de la génération du classement : {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# 4. Simuler la génération de bulletins pour quelques élèves tests
print("\n" + "-" * 80)
print("SIMULATION DES BULLETINS INDIVIDUELS")
print("-" * 80)

# Élèves à tester
eleves_test = [
    ('L12SC-009', 'HAÏDARA ABOUBACAR MOHAMED', 1),
    ('L12SC-022', 'DIALLO ALPHA OUSMANE', 9),
    ('L12SC-012', 'LOUAMMOU JEAN DAVID', 10),
    ('L12SC-018', 'MAMY RICHARD', 11),
]

print(f"\nTest sur {len(eleves_test)} élèves :\n")

erreurs = []
succes = 0

for matricule, nom_attendu, rang_attendu in eleves_test:
    try:
        eleve = Eleve.objects.get(matricule=matricule)
        
        # Récupérer le rang du classement
        if eleve.id in classement_dict:
            rang_classement = classement_dict[eleve.id]['rang']
            moyenne_classement = classement_dict[eleve.id]['moyenne']
            
            # Extraire le numéro de rang (ex: "9ème/18" -> 9)
            import re
            match = re.search(r'(\d+)', rang_classement)
            rang_num = int(match.group(1)) if match else None
            
            # Vérifier la cohérence
            if rang_num == rang_attendu:
                print(f"✅ {matricule:<15} {nom_attendu:<35}")
                print(f"   Rang : {rang_classement} | Moyenne : {moyenne_classement}")
                succes += 1
            else:
                print(f"❌ {matricule:<15} {nom_attendu:<35}")
                print(f"   Attendu : {rang_attendu}ème/18 | Obtenu : {rang_classement}")
                erreurs.append({
                    'matricule': matricule,
                    'nom': nom_attendu,
                    'attendu': rang_attendu,
                    'obtenu': rang_num
                })
        else:
            print(f"⚠️  {matricule:<15} {nom_attendu:<35}")
            print(f"   Élève non trouvé dans le classement")
            erreurs.append({
                'matricule': matricule,
                'nom': nom_attendu,
                'attendu': rang_attendu,
                'obtenu': 'NON TROUVÉ'
            })
        
        print()
        
    except Eleve.DoesNotExist:
        print(f"❌ Élève {matricule} non trouvé dans la base")
        erreurs.append({
            'matricule': matricule,
            'nom': nom_attendu,
            'attendu': rang_attendu,
            'obtenu': 'ÉLÈVE INEXISTANT'
        })
        print()

# 5. Résumé final
print("=" * 80)
print("RÉSUMÉ DU TEST")
print("=" * 80)

print(f"\n✅ Tests réussis : {succes}/{len(eleves_test)}")
print(f"❌ Tests échoués : {len(erreurs)}/{len(eleves_test)}")

if erreurs:
    print("\n⚠️  ERREURS DÉTECTÉES :")
    for err in erreurs:
        print(f"  - {err['matricule']} : Attendu {err['attendu']}, Obtenu {err['obtenu']}")
    print("\n❌ Le système présente des incohérences !")
else:
    print("\n🎉 TOUS LES TESTS SONT PASSÉS !")
    print("✅ Les rangs sont cohérents entre le classement et les bulletins")

# 6. Test spécifique pour les ex-aequo
print("\n" + "-" * 80)
print("VÉRIFICATION DES EX-AEQUO")
print("-" * 80)

# Chercher les ex-aequo dans le classement
ex_aequo_found = False
for i in range(len(classement_data) - 1):
    moy1 = classement_data[i].get('moyenne')
    moy2 = classement_data[i + 1].get('moyenne')
    
    if moy1 is not None and moy2 is not None:
        if abs(float(moy1) - float(moy2)) < 0.01:
            rang1 = classement_data[i].get('rang')
            rang2 = classement_data[i + 1].get('rang')
            nom1 = classement_data[i].get('nom_complet')
            nom2 = classement_data[i + 1].get('nom_complet')
            
            print(f"\n📊 Ex-aequo détecté :")
            print(f"   {nom1:<35} : {rang1} ({moy1})")
            print(f"   {nom2:<35} : {rang2} ({moy2})")
            
            # Vérifier que les rangs sont identiques
            if rang1 == rang2:
                print(f"   ✅ Rangs identiques (correct)")
            else:
                print(f"   ❌ Rangs différents (erreur !)")
            
            ex_aequo_found = True

if not ex_aequo_found:
    print("\nℹ️  Aucun ex-aequo détecté dans cette classe")

print("\n" + "=" * 80)
print("FIN DU TEST")
print("=" * 80)
