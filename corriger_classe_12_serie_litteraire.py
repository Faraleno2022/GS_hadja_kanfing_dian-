#!/usr/bin/env python
"""
Correction spécifique pour 12 SÉRIE LITTÉRAIRE
"""

import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ecole_moderne.settings')
django.setup()

def corriger_classe_12_serie_litteraire():
    """Correction spécifique pour 12 SÉRIE LITTÉRAIRE"""
    
    try:
        from notes.models import ClasseNote
        
        print("🔧 RECHERCHE ET CORRECTION 12 SÉRIE LITTÉRAIRE")
        
        # Chercher la classe 12 SÉRIE LITTÉRAIRE
        classes = ClasseNote.objects.filter(nom__icontains='12').filter(nom__icontains='littéraire')
        
        print(f"📚 Classes trouvées : {classes.count()}")
        
        classe_cible = None
        
        for classe in classes:
            print(f"  • {classe.nom} (ID: {classe.id})")
            
            if '12' in classe.nom.upper() and 'LITTÉRAIRE' in classe.nom.upper():
                print(f"    ✅ CIBLE TROUVÉE : {classe.nom} (ID: {classe.id})")
                classe_cible = classe
                break
        
        if not classe_cible:
            # Recherche élargie
            print(f"\n🔍 Recherche élargie :")
            toutes_classes = ClasseNote.objects.filter(nom__icontains='12')
            
            for classe in toutes_classes:
                print(f"  • {classe.nom} (ID: {classe.id})")
                
                if 'LITTÉRAIRE' in classe.nom.upper():
                    print(f"    ✅ CIBLE TROUVÉE : {classe.nom} (ID: {classe.id})")
                    classe_cible = classe
                    break
        
        if not classe_cible:
            print(f"  ❌ Classe 12 SÉRIE LITTÉRAIRE non trouvée")
            return
        
        print(f"\n🔧 CORRECTION DE LA CLASSE :")
        print(f"  • Nom : {classe_cible.nom}")
        print(f"  • ID : {classe_cible.id}")
        
        # Utiliser le script de correction
        from corriger_classement_classe_specifique import corriger_classement_classe_specifique
        
        print(f"\n🚀 LANCEMENT DE LA CORRECTION...")
        corriger_classement_classe_specifique(classe_id=classe_cible.id)
        
        print(f"\n🎉 CORRECTION TERMINÉE !")
        print(f"  ✅ Les données OCTOBRE sont maintenant disponibles")
        print(f"  ✅ Le classement devrait afficher les vraies moyennes")
        
        print(f"\n🌐 URL DE TEST :")
        print(f"  • Vue normale : /notes/consulter/?classe_id={classe_cible.id}&periode=OCTOBRE")
        print(f"  • Export PDF fix : /notes/exporter-classement-pdf-fix/?classe_id={classe_cible.id}&matiere_id=XX&periode=OCTOBRE")
        
    except Exception as e:
        print(f"❌ Erreur : {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    corriger_classe_12_serie_litteraire()
