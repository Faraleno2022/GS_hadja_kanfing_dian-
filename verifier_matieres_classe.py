#!/usr/bin/env python
"""
Vérifier quelles matières existent pour la classe 11ème Série scientifique
"""

import os
import sys
import django

# Configuration Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ecole_moderne.settings')
django.setup()

from notes.models import MatiereNote, ClasseNote
from django.db.models import Q

print("\n" + "="*80)
print("VÉRIFICATION DES MATIÈRES POUR 11ÈME SÉRIE SCIENTIFIQUE")
print("="*80)

# Rechercher la classe
print("\n1. CLASSES DISPONIBLES:")
print("-" * 40)

classes = ClasseNote.objects.filter(
    Q(nom__icontains='11')
).order_by('nom')

for classe in classes:
    print(f"\nClasse: {classe.nom} (ID: {classe.id})")
    print(f"  Année scolaire: {classe.annee_scolaire}")
    print(f"  Niveau: {classe.niveau}")
    print(f"  Actif: {classe.actif}")
    
    # Compter les matières
    matieres = MatiereNote.objects.filter(classe=classe)
    print(f"  Matières: {matieres.count()}")
    
    if matieres.exists():
        print("  Liste des matières:")
        for mat in matieres.order_by('nom'):
            print(f"    - {mat.nom} (Coef: {mat.coefficient}, Actif: {mat.actif})")

# Rechercher spécifiquement 11ème Série scientifique
print("\n2. RECHERCHE SPÉCIFIQUE '11ème Série scientifique':")
print("-" * 40)

classe_sci = ClasseNote.objects.filter(
    Q(nom__icontains='11') & Q(nom__icontains='scientifique')
).first()

if classe_sci:
    print(f"✅ Classe trouvée: {classe_sci.nom} (ID: {classe_sci.id})")
    
    matieres = MatiereNote.objects.filter(classe=classe_sci)
    if matieres.exists():
        print(f"✅ {matieres.count()} matières trouvées:")
        for mat in matieres:
            print(f"  - {mat.nom} (ID: {mat.id})")
    else:
        print("❌ AUCUNE MATIÈRE trouvée pour cette classe!")
        print("\n⚠️ C'EST LE PROBLÈME!")
        print("Les matières doivent être créées pour cette classe.")
        
        # Suggestion: voir les matières d'autres classes similaires
        print("\n3. MATIÈRES D'AUTRES CLASSES SIMILAIRES (pour référence):")
        print("-" * 40)
        
        autres_classes = ClasseNote.objects.filter(
            Q(nom__icontains='11') | Q(nom__icontains='scientifique'),
            actif=True
        ).exclude(id=classe_sci.id if classe_sci else 0)[:3]
        
        for autre in autres_classes:
            mats = MatiereNote.objects.filter(classe=autre)
            if mats.exists():
                print(f"\n{autre.nom}:")
                for m in mats[:5]:  # Limiter l'affichage
                    print(f"  - {m.nom} (Coef: {m.coefficient})")
else:
    print("❌ Classe '11ème Série scientifique' non trouvée!")

print("\n" + "="*80)
print("SOLUTION PROPOSÉE:")
print("-" * 40)
print("1. Créer les matières manquantes pour la classe '11ème Série scientifique'")
print("2. Via l'interface admin Django ou l'interface de l'application")
print("3. Ou utiliser un script pour créer automatiquement les matières")
print("="*80)
