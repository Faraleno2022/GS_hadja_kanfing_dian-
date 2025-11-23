#!/usr/bin/env python
"""
Diagnostiquer l'erreur 404 dans bulletins_dynamiques_classe_pdf
"""
import os
import sys
import django

# Configuration Django
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ecole_moderne.settings')
django.setup()

from notes.models import ClasseNote
from eleves.models import Classe as ClasseEleve, Eleve

def diagnostiquer_erreur_404():
    """Diagnostiquer l'erreur 404 dans bulletins_dynamiques_classe_pdf"""
    print("🔍 DIAGNOSTIC ERREUR 404 BULLETINS CLASSE")
    print("=" * 45)
    
    # Paramètres de la requête problématique
    classe_id_str = '59'
    periode = 'OCTOBRE'
    system_type = 'mensuel'
    
    print(f"📋 Paramètres de la requête:")
    print(f"   - classe_id: '{classe_id_str}'")
    print(f"   - periode: '{periode}'")
    print(f"   - system_type: '{system_type}'")
    
    # 1. Test validation paramètres
    print(f"\n🔧 TEST 1: VALIDATION PARAMÈTRES")
    if not classe_id_str or not periode:
        print(f"❌ Paramètres manquants")
        return
    print(f"✅ Paramètres présents")
    
    # 2. Test conversion classe_id
    print(f"\n🔧 TEST 2: CONVERSION CLASSE_ID")
    try:
        classe_id = int(classe_id_str)
        print(f"✅ Conversion réussie: '{classe_id_str}' -> {classe_id}")
    except (ValueError, TypeError) as e:
        print(f"❌ Erreur conversion: {e}")
        return
    
    # 3. Test existence ClasseNote
    print(f"\n🔧 TEST 3: EXISTENCE CLASSENOTE")
    try:
        classe_selectionnee = ClasseNote.objects.get(pk=classe_id)
        print(f"✅ ClasseNote trouvée: {classe_selectionnee.nom}")
        print(f"   - ID: {classe_selectionnee.id}")
        print(f"   - École: {classe_selectionnee.ecole}")
        print(f"   - Année: {classe_selectionnee.annee_scolaire}")
        print(f"   - Actif: {classe_selectionnee.actif}")
    except ClasseNote.DoesNotExist:
        print(f"❌ ClasseNote {classe_id} n'existe pas")
        
        # Chercher des classes similaires
        print(f"\n🔍 Recherche de classes similaires:")
        classes_similaires = ClasseNote.objects.filter(
            nom__icontains="11",
            annee_scolaire="2024-2025"
        )
        
        if classes_similaires.exists():
            print(f"📋 Classes trouvées:")
            for classe in classes_similaires:
                print(f"   - ID {classe.id}: {classe.nom} ({'Actif' if classe.actif else 'Inactif'})")
        else:
            print(f"❌ Aucune classe similaire trouvée")
        return
    
    # 4. Test mapping ClasseEleve
    print(f"\n🔧 TEST 4: MAPPING CLASSEELEVE")
    
    mapping_classes = {
        61: 56,  # ClasseNote '12ème Année' -> ClasseEleve '12ÈME ANNÉE'
        59: 8,   # ClasseNote '11ème Série littéraire' -> ClasseEleve '11ème série littéraire'
    }
    
    if classe_selectionnee.id in mapping_classes:
        classe_eleve = ClasseEleve.objects.filter(
            id=mapping_classes[classe_selectionnee.id]
        ).first()
        print(f"✅ Mapping utilisé: ClasseEleve {mapping_classes[classe_selectionnee.id]}")
    else:
        classe_eleve = ClasseEleve.objects.filter(
            nom=classe_selectionnee.nom,
            annee_scolaire=classe_selectionnee.annee_scolaire,
            ecole=classe_selectionnee.ecole
        ).first()
        print(f"✅ Recherche normale utilisée")
    
    if classe_eleve:
        print(f"✅ ClasseEleve trouvée: {classe_eleve.nom} (ID: {classe_eleve.id})")
        
        # Test élèves
        eleves = Eleve.objects.filter(classe=classe_eleve, statut='ACTIF')
        print(f"👥 Élèves actifs: {eleves.count()}")
        
        if eleves.count() > 0:
            print(f"📝 Premiers élèves:")
            for eleve in eleves[:3]:
                print(f"   - {eleve.prenom} {eleve.nom} ({eleve.matricule})")
    else:
        print(f"❌ ClasseEleve non trouvée")
    
    # 5. Diagnostic final
    print(f"\n🎯 DIAGNOSTIC FINAL")
    print("=" * 20)
    
    if classe_selectionnee and classe_eleve and eleves.count() > 0:
        print(f"✅ Tous les éléments sont présents")
        print(f"✅ La fonction devrait fonctionner")
        print(f"⚠️  L'erreur 404 pourrait venir d'autre chose")
        
        # Vérifier si la classe est active
        if not classe_selectionnee.actif:
            print(f"⚠️  ATTENTION: La classe n'est pas active")
        
        print(f"\n💡 Suggestions:")
        print(f"1. Vérifier que la classe est active")
        print(f"2. Vérifier les permissions utilisateur")
        print(f"3. Regarder les logs Django pour plus de détails")
        
    else:
        print(f"❌ Des éléments manquent:")
        if not classe_selectionnee:
            print(f"   - ClasseNote manquante")
        if not classe_eleve:
            print(f"   - ClasseEleve manquante")
        if eleves.count() == 0:
            print(f"   - Aucun élève actif")

def tester_urls_alternatives():
    """Tester des URLs alternatives"""
    print(f"\n🔗 URLS ALTERNATIVES À TESTER")
    print("=" * 35)
    
    urls_alternatives = [
        "http://127.0.0.1:8000/notes/consulter/?classe_id=59&periode=OCTOBRE",
        "http://127.0.0.1:8000/notes/saisir/?classe_id=59&matiere_id=134&type_note=mensuelle&periode=OCTOBRE",
        "http://127.0.0.1:8000/notes/exporter-classement/?classe_id=59&type_note=mensuelle&periode=OCTOBRE",
    ]
    
    print("📋 URLs qui devraient fonctionner:")
    for url in urls_alternatives:
        print(f"   ✅ {url}")

if __name__ == "__main__":
    try:
        diagnostiquer_erreur_404()
        tester_urls_alternatives()
        
        print(f"\n🎯 RÉSUMÉ")
        print("=" * 15)
        print("Si tous les tests passent mais l'erreur 404 persiste:")
        print("1. Vérifier que la classe est active")
        print("2. Vérifier les permissions utilisateur")
        print("3. Regarder les logs Django détaillés")
        print("4. Tester avec une autre classe")
        
    except Exception as e:
        print(f"❌ Erreur: {e}")
        import traceback
        traceback.print_exc()
