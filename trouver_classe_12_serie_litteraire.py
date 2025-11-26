#!/usr/bin/env python
"""
Trouver l'ID de la classe 12 SÉRIE LITTÉRAIRE
"""

import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ecole_moderne.settings')
django.setup()

def trouver_classe_12_serie_litteraire():
    """Trouver l'ID de la classe 12 SÉRIE LITTÉRAIRE"""
    
    try:
        from notes.models import ClasseNote
        
        print("🔧 RECHERCHE CLASSE 12 SÉRIE LITTÉRAIRE")
        
        # Chercher la classe
        classes = ClasseNote.objects.filter(nom__icontains='12').filter(nom__icontains='littéraire')
        
        print(f"📚 Classes trouvées : {classes.count()}")
        
        for classe in classes:
            print(f"  • {classe.nom} (ID: {classe.id})")
            
            if '12' in classe.nom.upper() and 'LITTÉRAIRE' in classe.nom.upper():
                print(f"    ✅ CIBLE TROUVÉE !")
                print(f"    🎯 Utiliser : corriger {classe.id}")
                return classe.id
        
        # Si pas trouvé avec la recherche exacte
        print(f"\n🔍 Recherche élargie :")
        toutes_classes = ClasseNote.objects.filter(nom__icontains='12')
        
        for classe in toutes_classes:
            print(f"  • {classe.nom} (ID: {classe.id})")
        
        print(f"\n💡 Si tu vois la classe 12 SÉRIE LITTÉRAIRE dans la liste, utilise son ID avec :")
        print(f"   corriger [ID]")
        
    except Exception as e:
        print(f"❌ Erreur : {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    trouver_classe_12_serie_litteraire()
