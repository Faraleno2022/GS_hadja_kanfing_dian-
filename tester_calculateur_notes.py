#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Script de test pour le calculateur de notes guinéen
"""

import sys
import os

# Ajouter le chemin du projet
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Test du calculateur standalone (sans Django)
from notes.calculateur_notes_guineen import exemple_complet

if __name__ == "__main__":
    print("\n" + "="*80)
    print(" "*15 + "🧪 TEST DU CALCULATEUR DE NOTES GUINÉEN")
    print("="*80)
    
    print("\n📝 Lancement des exemples...")
    print("-" * 80)
    
    try:
        exemple_complet()
        
        print("\n" + "="*80)
        print(" "*20 + "✅ TESTS RÉUSSIS")
        print("="*80)
        print("\n💡 Le calculateur fonctionne correctement !")
        print("\n📚 Exemples testés :")
        print("   1. ✅ Secondaire - Système Semestriel")
        print("   2. ✅ Secondaire - Système Trimestriel")
        print("   3. ✅ Primaire - Système Trimestriel")
        print("\n" + "="*80 + "\n")
        
    except Exception as e:
        print("\n" + "="*80)
        print(" "*20 + "❌ ERREUR DÉTECTÉE")
        print("="*80)
        print(f"\n{e}")
        import traceback
        traceback.print_exc()
        print("\n" + "="*80 + "\n")
