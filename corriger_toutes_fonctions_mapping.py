#!/usr/bin/env python
"""
Identifier et corriger toutes les fonctions qui ont besoin du mapping
"""
import os
import sys
import django

# Configuration Django
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ecole_moderne.settings')
django.setup()

def identifier_fonctions_a_corriger():
    """Identifier les fonctions qui ont besoin du mapping"""
    print("🔍 IDENTIFICATION DES FONCTIONS À CORRIGER")
    print("=" * 45)
    
    # Lire le fichier views.py
    with open('notes/views.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Chercher les patterns problématiques
    import re
    
    # Pattern pour trouver les fonctions qui utilisent ClasseEleve.objects.filter avec nom=
    pattern = r'def\s+(\w+)\(.*?\):.*?ClasseEleve\.objects\.filter\(\s*nom='
    matches = re.findall(pattern, content, re.DOTALL)
    
    print("📋 Fonctions utilisant ClasseEleve.objects.filter(nom=...")
    
    # Fonctions déjà corrigées
    fonctions_corrigees = [
        'consulter_notes',
        'saisir_notes', 
        'liste_saisie_pdf'
    ]
    
    # Chercher manuellement les lignes avec ClasseEleve.objects.filter
    lines = content.split('\n')
    fonctions_problematiques = []
    
    current_function = None
    for i, line in enumerate(lines):
        # Détecter le début d'une fonction
        if line.strip().startswith('def ') and '(request' in line:
            current_function = line.strip().split('(')[0].replace('def ', '')
        
        # Détecter l'usage problématique
        if 'ClasseEleve.objects.filter(' in line and 'nom=' in line:
            if current_function and current_function not in fonctions_corrigees:
                if current_function not in [f[0] for f in fonctions_problematiques]:
                    fonctions_problematiques.append((current_function, i+1))
    
    print("❌ Fonctions à corriger:")
    for func, line_num in fonctions_problematiques:
        print(f"   - {func} (ligne ~{line_num})")
    
    print(f"\n✅ Fonctions déjà corrigées:")
    for func in fonctions_corrigees:
        print(f"   - {func}")
    
    return fonctions_problematiques

def creer_mapping_centralise():
    """Créer une fonction centralisée pour le mapping"""
    print(f"\n💡 SOLUTION: FONCTION CENTRALISÉE")
    print("=" * 35)
    
    mapping_code = '''
def get_classe_eleve_from_classe_note(classe_note):
    """
    Fonction centralisée pour récupérer la ClasseEleve correspondant à une ClasseNote.
    Gère les cas spéciaux avec mapping et la logique normale.
    """
    # Mapping spécial pour les classes avec noms différents
    mapping_classes = {
        61: 56,  # ClasseNote '12ème Année' -> ClasseEleve '12ÈME ANNÉE'
        59: 8,   # ClasseNote '11ème Série littéraire' -> ClasseEleve '11ème série littéraire'
    }
    
    if classe_note.id in mapping_classes:
        return ClasseEleve.objects.filter(
            id=mapping_classes[classe_note.id]
        ).first()
    else:
        return ClasseEleve.objects.filter(
            nom=classe_note.nom,
            annee_scolaire=classe_note.annee_scolaire,
            ecole=classe_note.ecole
        ).first()
'''
    
    print("📝 Code de la fonction centralisée:")
    print(mapping_code)
    
    return mapping_code

def proposer_corrections():
    """Proposer les corrections à appliquer"""
    print(f"\n🔧 CORRECTIONS À APPLIQUER")
    print("=" * 30)
    
    corrections = [
        {
            'fonction': 'statistiques_notes',
            'ligne': '~3435',
            'probleme': 'Statistiques ne fonctionnent pas pour classe 59/61',
            'priorite': 'MOYENNE'
        },
        {
            'fonction': 'gerer_eleves',
            'ligne': '~3994',
            'probleme': 'Gestion élèves ne trouve pas les élèves',
            'priorite': 'HAUTE'
        },
        {
            'fonction': 'bulletins_pdf',
            'ligne': '~4946',
            'probleme': 'Bulletins PDF vides pour classe 59/61',
            'priorite': 'HAUTE'
        },
        {
            'fonction': 'bulletin_dynamique_single',
            'ligne': '~5332',
            'probleme': 'Bulletin individuel ne fonctionne pas',
            'priorite': 'HAUTE'
        },
        {
            'fonction': 'bulletin_dynamique',
            'ligne': '~5666',
            'probleme': 'Bulletin dynamique ne fonctionne pas',
            'priorite': 'HAUTE'
        }
    ]
    
    print("📋 Liste des corrections par priorité:")
    
    for priorite in ['HAUTE', 'MOYENNE', 'BASSE']:
        corrections_priorite = [c for c in corrections if c['priorite'] == priorite]
        if corrections_priorite:
            print(f"\n🔴 PRIORITÉ {priorite}:")
            for correction in corrections_priorite:
                print(f"   - {correction['fonction']} ({correction['ligne']})")
                print(f"     Problème: {correction['probleme']}")

def tester_impact_corrections():
    """Tester l'impact des corrections"""
    print(f"\n🧪 TEST IMPACT CORRECTIONS")
    print("=" * 30)
    
    from notes.models import ClasseNote
    from eleves.models import Classe as ClasseEleve, Eleve
    
    # Tester les classes problématiques
    classes_test = [59, 61]
    
    for classe_id in classes_test:
        try:
            classe_note = ClasseNote.objects.get(pk=classe_id)
            print(f"\n📋 Test classe {classe_id}: {classe_note.nom}")
            
            # Test mapping
            mapping_classes = {61: 56, 59: 8}
            
            if classe_id in mapping_classes:
                classe_eleve = ClasseEleve.objects.filter(
                    id=mapping_classes[classe_id]
                ).first()
                
                if classe_eleve:
                    eleves = Eleve.objects.filter(classe=classe_eleve, statut='ACTIF')
                    print(f"   ✅ Mapping fonctionne: {eleves.count()} élèves")
                    
                    # URLs qui bénéficieraient des corrections
                    urls_impactees = [
                        f"/notes/consulter/?classe_id={classe_id}&periode=OCTOBRE",
                        f"/notes/saisir/?classe_id={classe_id}&matiere_id=134&type_note=mensuelle&periode=OCTOBRE",
                        f"/notes/liste-saisie-pdf/?classe_id={classe_id}&matiere_id=134&periode=OCTOBRE&type_note=mensuelle",
                        f"/notes/bulletins/?classe_id={classe_id}&system_type=mensuel&periode=OCTOBRE",
                        f"/notes/gerer-eleves/?classe_id={classe_id}",
                    ]
                    
                    print(f"   🔗 URLs qui fonctionneraient après correction:")
                    for url in urls_impactees[:3]:
                        print(f"      - {url}")
                else:
                    print(f"   ❌ ClasseEleve {mapping_classes[classe_id]} non trouvée")
            else:
                print(f"   ⚠️  Pas de mapping défini")
                
        except Exception as e:
            print(f"   ❌ Erreur: {e}")

if __name__ == "__main__":
    try:
        # 1. Identifier les fonctions problématiques
        fonctions_problematiques = identifier_fonctions_a_corriger()
        
        # 2. Proposer une solution centralisée
        mapping_code = creer_mapping_centralise()
        
        # 3. Lister les corrections nécessaires
        proposer_corrections()
        
        # 4. Tester l'impact
        tester_impact_corrections()
        
        print(f"\n🎯 RÉSUMÉ")
        print("=" * 15)
        print(f"✅ 3 fonctions déjà corrigées (consulter, saisir, export PDF)")
        print(f"⚠️  ~5 fonctions supplémentaires à corriger")
        print(f"🔧 Solution: Appliquer le même mapping partout")
        print(f"📈 Impact: Toutes les fonctionnalités marcheront pour classes 59 et 61")
        
        print(f"\n💡 PROCHAINES ÉTAPES:")
        print(f"1. Corriger les fonctions priorité HAUTE")
        print(f"2. Tester chaque correction")
        print(f"3. Vérifier la non-régression")
        
    except Exception as e:
        print(f"❌ Erreur: {e}")
        import traceback
        traceback.print_exc()
