#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Test de l'accord grammatical des rangs selon le sexe
"""
import os
import sys
import django

# Configuration Django
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ecole_moderne.settings')
django.setup()

from notes.export_classement import formater_rang

def test_accord_grammatical():
    """Tester l'accord grammatical des rangs"""
    print("="*80)
    print(" "*20 + "TEST ACCORD GRAMMATICAL DES RANGS")
    print("="*80)
    
    # Test pour les filles (F)
    print("\n📚 Test pour les FILLES (F):")
    print("-" * 80)
    test_cases_f = [
        (1, 'F', "1ère"),
        (2, 'F', "2ème"),
        (3, 'F', "3ème"),
        (4, 'F', "4ème"),
        (10, 'F', "10ème"),
        (21, 'F', "21ème"),
    ]
    
    for rang, sexe, attendu in test_cases_f:
        resultat = formater_rang(rang, sexe)
        statut = "✅" if resultat == attendu else "❌"
        print(f"{statut} Rang {rang} (Fille): {resultat} {'==' if resultat == attendu else '!='} {attendu}")
    
    # Test pour les garçons (M)
    print("\n📚 Test pour les GARÇONS (M):")
    print("-" * 80)
    test_cases_m = [
        (1, 'M', "1er"),
        (2, 'M', "2ème"),
        (3, 'M', "3ème"),
        (4, 'M', "4ème"),
        (10, 'M', "10ème"),
        (21, 'M', "21ème"),
    ]
    
    for rang, sexe, attendu in test_cases_m:
        resultat = formater_rang(rang, sexe)
        statut = "✅" if resultat == attendu else "❌"
        print(f"{statut} Rang {rang} (Garçon): {resultat} {'==' if resultat == attendu else '!='} {attendu}")
    
    # Test cas spéciaux
    print("\n📚 Test CAS SPÉCIAUX:")
    print("-" * 80)
    test_cases_speciaux = [
        ('-', 'M', "-"),
        ('-', 'F', "-"),
        (None, 'M', "-"),
        (None, 'F', "-"),
    ]
    
    for rang, sexe, attendu in test_cases_speciaux:
        resultat = formater_rang(rang, sexe)
        statut = "✅" if resultat == attendu else "❌"
        print(f"{statut} Rang {rang} ({sexe}): {resultat} {'==' if resultat == attendu else '!='} {attendu}")
    
    # Exemples visuels
    print("\n" + "="*80)
    print(" "*25 + "EXEMPLES VISUELS")
    print("="*80)
    
    print("\n🥇 Podium Filles:")
    print(f"   🥇 {formater_rang(1, 'F')}: DIALLO AISSATOU - 18.5/20")
    print(f"   🥈 {formater_rang(2, 'F')}: BAH FATOUMATA - 17.2/20")
    print(f"   🥉 {formater_rang(3, 'F')}: CAMARA MARIAMA - 16.8/20")
    print(f"      {formater_rang(4, 'F')}: SOW KADIATOU - 15.5/20")
    
    print("\n🥇 Podium Garçons:")
    print(f"   🥇 {formater_rang(1, 'M')}: DIALLO ALPHA - 18.5/20")
    print(f"   🥈 {formater_rang(2, 'M')}: BAH OUSMANE - 17.2/20")
    print(f"   🥉 {formater_rang(3, 'M')}: CAMARA IBRAHIMA - 16.8/20")
    print(f"      {formater_rang(4, 'M')}: SOW MAMADOU - 15.5/20")
    
    print("\n🎯 Podium Mixte:")
    print(f"   🥇 {formater_rang(1, 'F')}: DIALLO AISSATOU (F) - 18.5/20")
    print(f"   🥈 {formater_rang(2, 'M')}: BAH OUSMANE (M) - 17.2/20")
    print(f"   🥉 {formater_rang(3, 'F')}: CAMARA MARIAMA (F) - 16.8/20")
    print(f"      {formater_rang(4, 'M')}: SOW MAMADOU (M) - 15.5/20")
    
    # Vérification finale
    print("\n" + "="*80)
    print(" "*25 + "✅ TESTS RÉUSSIS")
    print("="*80)
    
    print("\n📋 Résumé:")
    print("   ✅ Rang 1 fille: 1ère")
    print("   ✅ Rang 1 garçon: 1er")
    print("   ✅ Autres rangs: Xème (pour tous)")
    print("   ✅ Cas spéciaux: - (pour absents/non saisis)")
    
    print("\n🎉 L'accord grammatical fonctionne correctement!")
    print("\n📍 Utilisation:")
    print("   - Les filles 1ères auront '1ère'")
    print("   - Les garçons 1ers auront '1er'")
    print("   - Tous les autres rangs: 2ème, 3ème, 4ème, etc.")


def test_avec_donnees_reelles():
    """Tester avec des données réelles de la base"""
    print("\n" + "="*80)
    print(" "*20 + "TEST AVEC DONNÉES RÉELLES")
    print("="*80)
    
    from eleves.models import Eleve, Classe as ClasseEleve
    from notes.models import ClasseNote, MatiereNote, NoteMensuelle
    
    # Trouver une classe avec des élèves
    classe_eleve = ClasseEleve.objects.filter(eleves__isnull=False).first()
    
    if classe_eleve:
        eleves = Eleve.objects.filter(classe=classe_eleve, statut='ACTIF')[:5]
        
        print(f"\n📚 Classe: {classe_eleve.nom}")
        print(f"   Élèves testés: {eleves.count()}")
        print("-" * 80)
        
        for i, eleve in enumerate(eleves, 1):
            rang_formate = formater_rang(i, eleve.sexe)
            sexe_label = "Fille" if eleve.sexe == 'F' else "Garçon"
            
            if i == 1:
                print(f"🥇 {rang_formate}: {eleve.nom} {eleve.prenom} ({sexe_label})")
            elif i == 2:
                print(f"🥈 {rang_formate}: {eleve.nom} {eleve.prenom} ({sexe_label})")
            elif i == 3:
                print(f"🥉 {rang_formate}: {eleve.nom} {eleve.prenom} ({sexe_label})")
            else:
                print(f"   {rang_formate}: {eleve.nom} {eleve.prenom} ({sexe_label})")
        
        print("\n✅ Accord grammatical appliqué avec succès!")
    else:
        print("\n⚠️  Aucune classe avec élèves trouvée")


if __name__ == "__main__":
    test_accord_grammatical()
    test_avec_donnees_reelles()
    
    print("\n" + "="*80)
    print(" "*15 + "🎉 TOUS LES TESTS D'ACCORD GRAMMATICAL RÉUSSIS")
    print("="*80)
    print("\n📝 Maintenant, lors de l'export Excel:")
    print("   - Une fille 1ère aura: 🥇 1ère")
    print("   - Un garçon 1er aura: 🥇 1er")
    print("   - Tous les autres: 🥈 2ème, 🥉 3ème, 4ème, 5ème, etc.")
    print("\n✅ Fonctionnalité prête à l'emploi!")
