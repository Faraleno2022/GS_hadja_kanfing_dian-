#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Crée toutes les classes secondaires (Collège + Lycée) avec détection intelligente
"""

import os
import sys
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ecole_moderne.settings')
django.setup()

from notes.models import ClasseNote
from notes.classifier import classify

# Définition complète des classes secondaires guinéennes
CLASSES_SECONDAIRES = [
    # Collège
    "7ème Année",
    "7ème Année A",
    "7ème Année B",
    "8ème Année",
    "8ème Année A",
    "8ème Année B",
    "9ème Année",
    "9ème Année A",
    "9ème Année B",
    "10ème Année",
    "10ème Année A",
    "10ème Année B",
    
    # Lycée - 11ème
    "11ème Année",
    "11ème Série littéraire",
    "11ème Série scientifique",
    
    # Lycée - 12ème
    "12ème Année",
    "12ème Série littéraire",
    "12ème Série scientifique",
    
    # Terminale
    "Terminale",
    "Terminale SE",  # Sciences Économiques
    "Terminale SM",  # Sciences Mathématiques
    "Terminale SS",  # Sciences Sociales
]


def creer_classes_secondaires():
    """Crée toutes les classes secondaires avec détection intelligente"""
    print("\n" + "="*80)
    print("   🏫 CRÉATION DES CLASSES SECONDAIRES")
    print("="*80)
    
    created_count = 0
    updated_count = 0
    
    for nom_classe in CLASSES_SECONDAIRES:
        # Classifier intelligemment
        niveau, serie, section = classify(nom_classe)
        
        # Déterminer le niveau_enseignement pour la DB
        if "7" in nom_classe or "8" in nom_classe or "9" in nom_classe or "10" in nom_classe:
            niveau_db = "COLLEGE"
        else:
            niveau_db = "LYCEE"
        
        # Déterminer le niveau pour le champ 'niveau'
        if "7" in nom_classe:
            niveau_field = 'COLLEGE_7'
        elif "8" in nom_classe:
            niveau_field = 'COLLEGE_8'
        elif "9" in nom_classe:
            niveau_field = 'COLLEGE_9'
        elif "10" in nom_classe:
            niveau_field = 'COLLEGE_10'
        elif "11" in nom_classe:
            niveau_field = 'LYCEE_11'
        elif "12" in nom_classe:
            niveau_field = 'LYCEE_12'
        elif "terminale" in nom_classe.lower():
            niveau_field = 'TERMINALE'
        else:
            niveau_field = 'COLLEGE_7'  # Par défaut
        
        # Récupérer la première école (ou créer une logique pour sélectionner l'école)
        from eleves.models import Ecole
        ecole = Ecole.objects.first()
        
        if not ecole:
            print(f"   ❌ Aucune école trouvée. Créez d'abord une école.")
            continue
        
        # Créer ou mettre à jour
        classe, created = ClasseNote.objects.get_or_create(
            nom=nom_classe,
            ecole=ecole,
            annee_scolaire='2024-2025',
            defaults={
                'niveau': niveau_field,
                'niveau_enseignement': niveau_db
            }
        )
        
        if created:
            created_count += 1
            status = "✅ CRÉÉE"
        else:
            # Mettre à jour si nécessaire
            if classe.niveau_enseignement != niveau_db:
                classe.niveau_enseignement = niveau_db
                classe.save()
                updated_count += 1
                status = "🔄 MISE À JOUR"
            else:
                status = "✓ Existe déjà"
        
        # Afficher
        info = f"   {status:<15} {nom_classe:<35}"
        info += f" → {niveau_db:<10}"
        
        if serie:
            info += f" Série: {serie:<25}"
        if section:
            info += f" Section: {section}"
        
        print(info)
    
    print("\n" + "="*80)
    print(f"   📊 RÉSUMÉ")
    print("="*80)
    print(f"   ✅ Classes créées: {created_count}")
    print(f"   🔄 Classes mises à jour: {updated_count}")
    print(f"   📚 Total classes secondaires: {ClasseNote.objects.filter(niveau_enseignement__in=['COLLEGE', 'LYCEE']).count()}")
    print("="*80)


if __name__ == "__main__":
    try:
        creer_classes_secondaires()
        print("\n✅ Opération terminée avec succès!\n")
    except Exception as e:
        print(f"\n❌ Erreur: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
