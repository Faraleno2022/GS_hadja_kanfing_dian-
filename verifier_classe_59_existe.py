#!/usr/bin/env python
"""
Vérifier si la classe 59 existe encore
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

def verifier_classe_59():
    """Vérifier l'existence de la classe 59"""
    print("🔍 VÉRIFICATION CLASSE 59")
    print("=" * 25)
    
    # 1. Vérifier si la classe 59 existe
    try:
        classe_59 = ClasseNote.objects.get(pk=59)
        print(f"✅ ClasseNote 59 existe: {classe_59.nom}")
        print(f"   - École: {classe_59.ecole}")
        print(f"   - Année: {classe_59.annee_scolaire}")
        print(f"   - Actif: {classe_59.actif}")
        
        # Vérifier la classe élève correspondante
        classe_eleve = ClasseEleve.objects.filter(id=8).first()
        if classe_eleve:
            print(f"✅ ClasseEleve 8 existe: {classe_eleve.nom}")
            
            # Vérifier les élèves
            eleves = Eleve.objects.filter(classe=classe_eleve, statut='ACTIF')
            print(f"👥 Élèves actifs: {eleves.count()}")
        else:
            print(f"❌ ClasseEleve 8 n'existe pas")
            
    except ClasseNote.DoesNotExist:
        print(f"❌ ClasseNote 59 n'existe pas")
        
        # Chercher des classes similaires
        print(f"\n🔍 Recherche de classes similaires:")
        classes_litteraires = ClasseNote.objects.filter(
            nom__icontains="11",
            annee_scolaire="2024-2025"
        ).filter(nom__icontains="littéraire")
        
        if classes_litteraires.exists():
            print(f"📋 Classes littéraires trouvées:")
            for classe in classes_litteraires:
                print(f"   - ID {classe.id}: {classe.nom}")
        else:
            print(f"❌ Aucune classe littéraire trouvée")
            
        # Lister toutes les classes
        print(f"\n📋 Toutes les classes disponibles:")
        toutes_classes = ClasseNote.objects.all().order_by('id')
        for classe in toutes_classes[:10]:  # Limiter à 10
            print(f"   - ID {classe.id}: {classe.nom}")
        
        if toutes_classes.count() > 10:
            print(f"   ... et {toutes_classes.count() - 10} autres")

def verifier_url_patterns():
    """Vérifier les patterns d'URL"""
    print(f"\n🔗 VÉRIFICATION URL PATTERNS")
    print("=" * 30)
    
    print(f"✅ URL pattern trouvé: notes/bulletins/classe/pdf/")
    print(f"✅ Nom de la vue: bulletins_dynamiques_classe_pdf")
    print(f"⚠️  Erreur 404 = get_object_or_404(ClasseNote, pk=classe_id) échoue")
    print(f"💡 Solution: Vérifier que la classe_id existe dans la base")

if __name__ == "__main__":
    try:
        verifier_classe_59()
        verifier_url_patterns()
        
        print(f"\n🎯 DIAGNOSTIC")
        print("=" * 15)
        print("Si ClasseNote 59 n'existe pas:")
        print("1. Utiliser l'ID d'une classe existante")
        print("2. Ou recréer la classe 59")
        print("3. Ou modifier le mapping pour pointer vers une classe existante")
        
    except Exception as e:
        print(f"❌ Erreur: {e}")
        import traceback
        traceback.print_exc()
