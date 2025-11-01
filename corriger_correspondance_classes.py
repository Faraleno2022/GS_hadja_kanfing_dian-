#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Script pour vérifier et corriger les correspondances entre ClasseNote et ClasseEleve
"""

import os
import sys
import django
import unicodedata

# Configuration Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ecole_moderne.settings')
django.setup()

from notes.models import ClasseNote
from eleves.models import Classe as ClasseEleve, Eleve

def normaliser(texte):
    """Normalise un texte (supprime accents, minuscules, espaces)"""
    nfkd = unicodedata.normalize('NFKD', texte)
    return ''.join([c for c in nfkd if not unicodedata.combining(c)]).lower().strip()

def verifier_correspondances():
    """Vérifie les correspondances entre ClasseNote et ClasseEleve"""
    
    print("\n" + "="*80)
    print(" "*15 + "🔍 VÉRIFICATION DES CORRESPONDANCES CLASSES")
    print("="*80)
    
    classes_notes = ClasseNote.objects.filter(actif=True).order_by('nom')
    
    if not classes_notes.exists():
        print("\n❌ Aucune classe active dans le module Notes")
        return
    
    print(f"\n📚 {classes_notes.count()} classe(s) à vérifier\n")
    
    correspondances_ok = []
    correspondances_approx = []
    aucune_correspondance = []
    
    for classe_note in classes_notes:
        print(f"Classe Notes : '{classe_note.nom}' ({classe_note.annee_scolaire})")
        
        try:
            # Tentative de correspondance exacte
            classe_eleve = ClasseEleve.objects.get(
                nom=classe_note.nom,
                annee_scolaire=classe_note.annee_scolaire
            )
            
            # Compter les élèves
            nb_eleves = Eleve.objects.filter(classe=classe_eleve, statut='ACTIF').count()
            
            print(f"   ✅ Correspondance EXACTE : '{classe_eleve.nom}'")
            print(f"      → {nb_eleves} élève(s) actif(s)")
            correspondances_ok.append((classe_note, classe_eleve, nb_eleves))
            
        except ClasseEleve.DoesNotExist:
            # Recherche flexible
            classes_eleves = ClasseEleve.objects.filter(
                annee_scolaire=classe_note.annee_scolaire
            )
            
            correspondance = None
            for ce in classes_eleves:
                if normaliser(ce.nom) == normaliser(classe_note.nom):
                    correspondance = ce
                    break
            
            if correspondance:
                nb_eleves = Eleve.objects.filter(classe=correspondance, statut='ACTIF').count()
                print(f"   ⚠️  Correspondance APPROXIMATIVE : '{correspondance.nom}'")
                print(f"      Différence : '{classe_note.nom}' ≠ '{correspondance.nom}'")
                print(f"      → {nb_eleves} élève(s) actif(s)")
                print(f"      💡 SOLUTION : Renommer en '{classe_note.nom}' dans le module Élèves")
                correspondances_approx.append((classe_note, correspondance, nb_eleves))
            else:
                print(f"   ❌ AUCUNE CORRESPONDANCE")
                
                # Afficher les classes disponibles
                if classes_eleves.exists():
                    print(f"      Classes disponibles pour {classe_note.annee_scolaire} :")
                    for ce in classes_eleves[:5]:
                        nb = Eleve.objects.filter(classe=ce, statut='ACTIF').count()
                        print(f"      - '{ce.nom}' ({nb} élèves)")
                else:
                    print(f"      Aucune classe pour l'année {classe_note.annee_scolaire}")
                
                aucune_correspondance.append(classe_note)
        
        print()
    
    # Résumé
    print("="*80)
    print(" "*25 + "📊 RÉSUMÉ")
    print("="*80)
    
    print(f"\n✅ Correspondances EXACTES : {len(correspondances_ok)}")
    for cn, ce, nb in correspondances_ok:
        print(f"   - '{cn.nom}' → {nb} élèves")
    
    if correspondances_approx:
        print(f"\n⚠️  Correspondances APPROXIMATIVES : {len(correspondances_approx)}")
        for cn, ce, nb in correspondances_approx:
            print(f"   - Notes: '{cn.nom}' ≠ Élèves: '{ce.nom}' ({nb} élèves)")
    
    if aucune_correspondance:
        print(f"\n❌ AUCUNE correspondance : {len(aucune_correspondance)}")
        for cn in aucune_correspondance:
            print(f"   - '{cn.nom}' ({cn.annee_scolaire})")
    
    # Recommandations
    print("\n" + "="*80)
    print(" "*25 + "💡 RECOMMANDATIONS")
    print("="*80)
    
    if correspondances_approx:
        print("\n🔧 Correspondances APPROXIMATIVES à corriger :")
        print("\n   Option 1 : Renommer dans le module Élèves")
        print("   ─────────────────────────────────────────")
        for cn, ce, nb in correspondances_approx:
            print(f"\n   Classe : '{ce.nom}'")
            print(f"   → Renommer en : '{cn.nom}'")
            print(f"   Menu : Élèves > Gestion des Classes > Modifier")
    
    if aucune_correspondance:
        print("\n🆕 Classes à CRÉER dans le module Élèves :")
        print("   ────────────────────────────────────────")
        for cn in aucune_correspondance:
            print(f"\n   Nom : {cn.nom}")
            print(f"   Année : {cn.annee_scolaire}")
            print(f"   Niveau : {cn.get_niveau_display()}")
            print(f"   Menu : Élèves > Gestion des Classes > Ajouter")
    
    if not correspondances_approx and not aucune_correspondance:
        print("\n✅ TOUT EST PARFAIT !")
        print("   Toutes les classes ont une correspondance exacte.")
        print("   Si le bulletin reste vide, le problème est ailleurs.")
    
    # Générer URL de test
    if correspondances_ok:
        print("\n" + "="*80)
        print(" "*25 + "🔗 URLS DE TEST")
        print("="*80)
        
        for cn, ce, nb in correspondances_ok[:3]:
            if nb > 0:
                eleve = Eleve.objects.filter(classe=ce, statut='ACTIF').first()
                if eleve:
                    print(f"\nClasse '{cn.nom}' - Élève '{eleve.prenom} {eleve.nom}' :")
                    print(f"http://127.0.0.1:8000/notes/bulletin-dynamique/?classe_id={cn.id}&eleve_id={eleve.id}&periode=TRIMESTRE_1&system_type=trimestre")
    
    print("\n" + "="*80 + "\n")

if __name__ == '__main__':
    try:
        verifier_correspondances()
    except Exception as e:
        print(f"\n❌ Erreur : {e}")
        import traceback
        traceback.print_exc()
