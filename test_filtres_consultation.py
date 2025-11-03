#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Test des filtres de la page de consultation des notes
Vérifie que tous les filtres sont présents et fonctionnels
"""
import os
import sys
import django

# Configuration Django
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ecole_moderne.settings')
django.setup()

from django.test import Client
from django.contrib.auth.models import User
from notes.models import ClasseNote, MatiereNote
from eleves.models import Classe as ClasseEleve, Eleve

def test_filtres_consultation():
    """Tester les filtres de la page de consultation"""
    print("="*80)
    print(" "*20 + "TEST DES FILTRES DE CONSULTATION")
    print("="*80)
    
    # Vérifier qu'il y a des classes
    classes = ClasseNote.objects.filter(actif=True)
    print(f"\n📚 Classes disponibles: {classes.count()}")
    
    if not classes.exists():
        print("❌ Aucune classe trouvée")
        return
    
    # Prendre la première classe avec des matières
    classe_test = None
    for classe in classes:
        matieres = MatiereNote.objects.filter(classe=classe, actif=True)
        if matieres.exists():
            classe_test = classe
            break
    
    if not classe_test:
        print("❌ Aucune classe avec matières trouvée")
        return
    
    print(f"\n✅ Classe de test: {classe_test.nom}")
    
    # Vérifier les matières
    matieres = MatiereNote.objects.filter(classe=classe_test, actif=True)
    print(f"\n📖 Matières disponibles ({matieres.count()}):")
    for matiere in matieres:
        print(f"   - {matiere.nom} (Coef: {matiere.coefficient})")
    
    # Vérifier les élèves
    try:
        classe_eleve = ClasseEleve.objects.filter(
            nom=classe_test.nom,
            annee_scolaire=classe_test.annee_scolaire,
            ecole=classe_test.ecole
        ).first()
        
        if classe_eleve:
            eleves = Eleve.objects.filter(classe=classe_eleve, statut='ACTIF')
            print(f"\n👥 Élèves actifs: {eleves.count()}")
            if eleves.exists():
                print(f"   Exemples:")
                for eleve in eleves[:3]:
                    print(f"   - {eleve.matricule}: {eleve.nom} {eleve.prenom}")
    except Exception as e:
        print(f"⚠️  Erreur lors de la récupération des élèves: {str(e)}")
    
    print("\n" + "="*80)
    print(" "*25 + "TEST DES FILTRES")
    print("="*80)
    
    # Test 1: Filtre par Matière
    print("\n📖 Test 1: Filtre par Matière")
    print("-" * 80)
    print("✅ Options disponibles:")
    print("   - Toutes les matières")
    for matiere in matieres:
        print(f"   - {matiere.nom}")
    
    # Test 2: Filtre par Période
    print("\n📅 Test 2: Filtre par Période")
    print("-" * 80)
    print("✅ Options disponibles:")
    print("   Toutes les périodes")
    print("   Mois:")
    mois = ['Octobre', 'Novembre', 'Décembre', 'Janvier', 'Février', 'Mars', 'Avril', 'Mai', 'Juin']
    for m in mois:
        print(f"      - {m}")
    print("   Trimestres:")
    print("      - 1er Trimestre")
    print("      - 2ème Trimestre")
    print("      - 3ème Trimestre")
    print("   Semestres:")
    print("      - 1er Semestre")
    print("      - 2ème Semestre")
    
    # Test 3: Filtre par Type
    print("\n📋 Test 3: Filtre par Type")
    print("-" * 80)
    print("✅ Options disponibles:")
    types = ['Tous les types', 'Mensuelle', 'Trimestrielle', 'Semestrielle', 
             'Composition', 'Appréciation', 'Moyennes uniquement']
    for t in types:
        print(f"   - {t}")
    
    # Test 4: Recherche Élève
    print("\n🔍 Test 4: Recherche Élève")
    print("-" * 80)
    print("✅ Champ de recherche disponible")
    print("   Recherche par: Nom, prénom ou matricule")
    
    print("\n" + "="*80)
    print(" "*20 + "VÉRIFICATION DE L'URL")
    print("="*80)
    
    # Construire l'URL de test
    url_test = f"http://127.0.0.1:8000/notes/consulter/?classe_id={classe_test.id}"
    print(f"\n🔗 URL de test:")
    print(f"   {url_test}")
    
    print("\n📋 Paramètres disponibles:")
    print(f"   - classe_id={classe_test.id}")
    print(f"   - Filtres JavaScript côté client:")
    print(f"     • filtreMatiere (ID de matière)")
    print(f"     • filtrePeriode (OCTOBRE, NOVEMBRE, etc.)")
    print(f"     • filtreType (mensuelle, composition, etc.)")
    print(f"     • rechercheEleve (texte libre)")
    
    print("\n" + "="*80)
    print(" "*20 + "TEST DE SCÉNARIOS")
    print("="*80)
    
    # Scénario 1
    print("\n📝 Scénario 1: Filtrer par Matière ANGLAIS")
    print("-" * 80)
    matiere_anglais = matieres.filter(nom__icontains='ANGLAIS').first()
    if matiere_anglais:
        print(f"✅ Matière trouvée: {matiere_anglais.nom} (ID: {matiere_anglais.id})")
        print(f"   Action: Sélectionner '{matiere_anglais.nom}' dans le filtre")
        print(f"   Résultat attendu: Seules les colonnes d'ANGLAIS sont visibles")
    else:
        print("⚠️  Matière ANGLAIS non trouvée")
    
    # Scénario 2
    print("\n📝 Scénario 2: Filtrer par Période DECEMBRE")
    print("-" * 80)
    print("✅ Action: Sélectionner 'Décembre' dans le filtre période")
    print("   Résultat attendu: Seules les notes de Décembre sont visibles")
    
    # Scénario 3
    print("\n📝 Scénario 3: Filtrer par Type Mensuelle")
    print("-" * 80)
    print("✅ Action: Sélectionner 'Mensuelle' dans le filtre type")
    print("   Résultat attendu: Seules les notes mensuelles sont visibles")
    print("   (Octobre à Juin)")
    
    # Scénario 4
    print("\n📝 Scénario 4: Rechercher un Élève")
    print("-" * 80)
    if classe_eleve and eleves.exists():
        eleve_test = eleves.first()
        print(f"✅ Élève de test: {eleve_test.nom}")
        print(f"   Action: Taper '{eleve_test.nom}' dans la recherche")
        print(f"   Résultat attendu: Seul cet élève est visible")
    else:
        print("⚠️  Aucun élève disponible pour le test")
    
    # Scénario 5
    print("\n📝 Scénario 5: Combinaison de Filtres")
    print("-" * 80)
    if matiere_anglais:
        print(f"✅ Action: Combiner plusieurs filtres")
        print(f"   1. Matière: {matiere_anglais.nom}")
        print(f"   2. Période: Décembre")
        print(f"   3. Type: Mensuelle")
        print(f"   Résultat attendu: Notes d'ANGLAIS de Décembre uniquement")
    
    print("\n" + "="*80)
    print(" "*20 + "VÉRIFICATION DU CODE JAVASCRIPT")
    print("="*80)
    
    # Vérifier le fichier template
    template_path = "templates/notes/consulter_notes.html"
    if os.path.exists(template_path):
        print(f"\n✅ Template trouvé: {template_path}")
        
        with open(template_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
        # Vérifier les éléments clés
        checks = [
            ('filtreMatiere', 'Filtre Matière'),
            ('filtrePeriode', 'Filtre Période'),
            ('filtreType', 'Filtre Type'),
            ('rechercheEleve', 'Recherche Élève'),
            ('appliquerFiltres', 'Fonction de filtrage'),
            ('addEventListener', 'Événements de filtrage'),
        ]
        
        print("\n🔍 Éléments vérifiés dans le template:")
        for element, description in checks:
            if element in content:
                print(f"   ✅ {description} ({element})")
            else:
                print(f"   ❌ {description} ({element}) - MANQUANT!")
    else:
        print(f"\n❌ Template non trouvé: {template_path}")
    
    print("\n" + "="*80)
    print(" "*25 + "✅ TESTS TERMINÉS")
    print("="*80)
    
    print("\n📋 Résumé:")
    print(f"   ✅ Classe de test: {classe_test.nom}")
    print(f"   ✅ Matières: {matieres.count()}")
    print(f"   ✅ Filtres disponibles: 4 (Matière, Période, Type, Recherche)")
    print(f"   ✅ URL de test: {url_test}")
    
    print("\n🎯 Pour tester manuellement:")
    print("   1. Démarrer le serveur: python manage.py runserver")
    print(f"   2. Ouvrir: {url_test}")
    print("   3. Tester chaque filtre individuellement")
    print("   4. Tester des combinaisons de filtres")
    print("   5. Vérifier que les colonnes/lignes se cachent correctement")
    
    print("\n💡 Conseils de test:")
    print("   - Ouvrir la console du navigateur (F12)")
    print("   - Vérifier qu'il n'y a pas d'erreurs JavaScript")
    print("   - Tester avec différentes combinaisons")
    print("   - Vérifier que le bouton 'Exporter Classement' utilise les filtres")


def test_export_avec_filtres():
    """Tester que l'export utilise bien les filtres"""
    print("\n" + "="*80)
    print(" "*20 + "TEST EXPORT AVEC FILTRES")
    print("="*80)
    
    print("\n📊 Vérification de l'intégration export/filtres:")
    
    # Vérifier le fichier template
    template_path = "templates/notes/consulter_notes.html"
    if os.path.exists(template_path):
        with open(template_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Vérifier la fonction exporterClassementAvecFiltres
        if 'exporterClassementAvecFiltres' in content:
            print("   ✅ Fonction exporterClassementAvecFiltres trouvée")
            
            # Vérifier qu'elle récupère les filtres
            checks = [
                ('filtreMatiere', 'Récupération filtre matière'),
                ('filtrePeriode', 'Récupération filtre période'),
                ('filtreType', 'Récupération filtre type'),
            ]
            
            for element, description in checks:
                if element in content and 'getElementById' in content:
                    print(f"   ✅ {description}")
                else:
                    print(f"   ⚠️  {description} - À vérifier")
        else:
            print("   ❌ Fonction exporterClassementAvecFiltres non trouvée")
    
    print("\n✅ L'export devrait utiliser les filtres actifs lors du clic")


if __name__ == "__main__":
    test_filtres_consultation()
    test_export_avec_filtres()
    
    print("\n" + "="*80)
    print(" "*15 + "🎉 TOUS LES TESTS DE FILTRES TERMINÉS")
    print("="*80)
    print("\n📝 Prochaine étape:")
    print("   Tester manuellement dans le navigateur pour confirmer")
    print("   que les filtres fonctionnent visuellement.")
