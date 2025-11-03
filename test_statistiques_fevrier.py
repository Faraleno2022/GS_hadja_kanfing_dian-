#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Diagnostic du problème: Aucune donnée pour classe_id=2 et période=FEVRIER
"""
import os
import sys
import django

# Configuration Django
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ecole_moderne.settings')
django.setup()

from notes.models import ClasseNote, MatiereNote, NoteMensuelle, CompositionNote
from eleves.models import Eleve, Classe as ClasseEleve

def diagnostiquer_fevrier():
    """Diagnostiquer pourquoi il n'y a pas de données pour février"""
    print("="*80)
    print(" "*20 + "DIAGNOSTIC STATISTIQUES FÉVRIER")
    print("="*80)
    
    # 1. Vérifier la classe
    print("\n📚 ÉTAPE 1: Vérification de la classe")
    print("-" * 80)
    
    try:
        classe_note = ClasseNote.objects.get(id=2)
        print(f"✅ Classe trouvée:")
        print(f"   ID: {classe_note.id}")
        print(f"   Nom: {classe_note.nom}")
        print(f"   Année scolaire: {classe_note.annee_scolaire}")
        print(f"   École: {classe_note.ecole.nom}")
        print(f"   Actif: {classe_note.actif}")
    except ClasseNote.DoesNotExist:
        print("❌ Classe avec ID=2 non trouvée!")
        return
    
    # 2. Vérifier les matières
    print("\n📖 ÉTAPE 2: Vérification des matières")
    print("-" * 80)
    
    matieres = MatiereNote.objects.filter(classe=classe_note, actif=True)
    print(f"Matières actives: {matieres.count()}")
    
    if matieres.exists():
        for matiere in matieres:
            print(f"   - {matiere.nom} (Coef: {matiere.coefficient})")
    else:
        print("❌ Aucune matière trouvée pour cette classe!")
        return
    
    # 3. Vérifier les élèves
    print("\n👥 ÉTAPE 3: Vérification des élèves")
    print("-" * 80)
    
    try:
        classe_eleve = ClasseEleve.objects.filter(
            nom=classe_note.nom,
            annee_scolaire=classe_note.annee_scolaire,
            ecole=classe_note.ecole
        ).first()
        
        if classe_eleve:
            print(f"✅ Classe élève trouvée: {classe_eleve.nom}")
            eleves = Eleve.objects.filter(classe=classe_eleve, statut='ACTIF')
            print(f"   Élèves actifs: {eleves.count()}")
            
            if eleves.exists():
                print(f"   Exemples:")
                for eleve in eleves[:5]:
                    print(f"      - {eleve.matricule}: {eleve.nom} {eleve.prenom}")
            else:
                print("❌ Aucun élève actif dans cette classe!")
                return
        else:
            print("❌ Classe élève correspondante non trouvée!")
            return
    except Exception as e:
        print(f"❌ Erreur: {str(e)}")
        return
    
    # 4. Vérifier les notes de FÉVRIER
    print("\n📊 ÉTAPE 4: Vérification des notes de FÉVRIER")
    print("-" * 80)
    
    # Notes mensuelles de février
    notes_fevrier = NoteMensuelle.objects.filter(
        matiere__classe=classe_note,
        mois='FEVRIER',
        annee_scolaire=classe_note.annee_scolaire
    )
    
    print(f"Notes mensuelles de FÉVRIER: {notes_fevrier.count()}")
    
    if notes_fevrier.exists():
        print(f"✅ {notes_fevrier.count()} notes trouvées")
        
        # Détails par matière
        print("\n   Détails par matière:")
        for matiere in matieres:
            notes_matiere = notes_fevrier.filter(matiere=matiere)
            print(f"   - {matiere.nom}: {notes_matiere.count()} notes")
            
            if notes_matiere.exists():
                # Afficher quelques exemples
                for note in notes_matiere[:3]:
                    eleve = note.eleve
                    valeur = "ABS" if note.absent else (note.note if note.note else "-")
                    print(f"      • {eleve.nom} {eleve.prenom}: {valeur}")
    else:
        print("❌ Aucune note mensuelle de FÉVRIER trouvée!")
        
        # Vérifier les autres mois
        print("\n   Vérification des autres mois disponibles:")
        mois_disponibles = NoteMensuelle.objects.filter(
            matiere__classe=classe_note,
            annee_scolaire=classe_note.annee_scolaire
        ).values_list('mois', flat=True).distinct()
        
        if mois_disponibles:
            print(f"   Mois avec des notes:")
            for mois in mois_disponibles:
                count = NoteMensuelle.objects.filter(
                    matiere__classe=classe_note,
                    mois=mois,
                    annee_scolaire=classe_note.annee_scolaire
                ).count()
                print(f"      - {mois}: {count} notes")
        else:
            print("   ❌ Aucune note mensuelle pour cette classe!")
    
    # 5. Vérifier les compositions de février (si applicable)
    print("\n📝 ÉTAPE 5: Vérification des compositions")
    print("-" * 80)
    
    # Compositions du 2ème trimestre (qui inclut février)
    compositions_t2 = CompositionNote.objects.filter(
        matiere__classe=classe_note,
        periode='TRIMESTRE_2',
        annee_scolaire=classe_note.annee_scolaire
    )
    
    print(f"Compositions 2ème Trimestre: {compositions_t2.count()}")
    
    if compositions_t2.exists():
        print(f"✅ {compositions_t2.count()} compositions trouvées")
        for matiere in matieres:
            compos = compositions_t2.filter(matiere=matiere)
            if compos.exists():
                print(f"   - {matiere.nom}: {compos.count()} compositions")
    
    # 6. Diagnostic final
    print("\n" + "="*80)
    print(" "*25 + "DIAGNOSTIC FINAL")
    print("="*80)
    
    problemes = []
    
    if not matieres.exists():
        problemes.append("❌ Aucune matière configurée")
    
    if not eleves.exists():
        problemes.append("❌ Aucun élève dans la classe")
    
    if not notes_fevrier.exists():
        problemes.append("❌ Aucune note de FÉVRIER saisie")
    
    if problemes:
        print("\n🔴 PROBLÈMES IDENTIFIÉS:")
        for p in problemes:
            print(f"   {p}")
        
        print("\n💡 SOLUTIONS:")
        if not notes_fevrier.exists():
            print("   1. Saisir des notes pour le mois de FÉVRIER")
            print("   2. Aller sur: http://127.0.0.1:8000/notes/saisie/")
            print(f"   3. Sélectionner la classe: {classe_note.nom}")
            print("   4. Sélectionner le mois: FÉVRIER")
            print("   5. Saisir les notes pour chaque élève")
    else:
        print("\n✅ Tout semble correct!")
        print("   Le problème pourrait être dans la vue des statistiques")
    
    # 7. Tester la requête de la vue statistiques
    print("\n" + "="*80)
    print(" "*20 + "TEST DE LA REQUÊTE STATISTIQUES")
    print("="*80)
    
    print("\n🔍 Simulation de la requête de la vue:")
    print(f"   classe_id = {classe_note.id}")
    print(f"   periode = 'FEVRIER'")
    
    # Simuler la logique de la vue
    periode = 'FEVRIER'
    
    # Vérifier si c'est un mois
    mois_valides = ['OCTOBRE', 'NOVEMBRE', 'DECEMBRE', 'JANVIER', 'FEVRIER', 
                    'MARS', 'AVRIL', 'MAI', 'JUIN']
    
    if periode in mois_valides:
        print(f"\n✅ FEVRIER est un mois valide")
        
        # Requête pour les notes mensuelles
        notes = NoteMensuelle.objects.filter(
            matiere__classe=classe_note,
            mois=periode,
            annee_scolaire=classe_note.annee_scolaire
        )
        
        print(f"   Notes trouvées: {notes.count()}")
        
        if notes.exists():
            print("\n   ✅ Des notes existent, la vue devrait afficher des données")
            
            # Calculer quelques statistiques
            notes_avec_valeur = notes.filter(absent=False, note__isnull=False)
            if notes_avec_valeur.exists():
                from django.db.models import Avg, Max, Min, Count
                stats = notes_avec_valeur.aggregate(
                    moyenne=Avg('note'),
                    max=Max('note'),
                    min=Min('note'),
                    count=Count('id')
                )
                print(f"\n   📊 Statistiques calculées:")
                print(f"      Moyenne: {stats['moyenne']:.2f}/20")
                print(f"      Maximum: {stats['max']}/20")
                print(f"      Minimum: {stats['min']}/20")
                print(f"      Nombre de notes: {stats['count']}")
        else:
            print("\n   ❌ Aucune note trouvée, d'où le message 'Aucune donnée disponible'")
            print("\n   💡 SOLUTION: Saisir des notes pour FÉVRIER")


def verifier_toutes_periodes():
    """Vérifier toutes les périodes disponibles pour la classe 2"""
    print("\n" + "="*80)
    print(" "*20 + "PÉRIODES DISPONIBLES POUR CLASSE 2")
    print("="*80)
    
    try:
        classe_note = ClasseNote.objects.get(id=2)
        
        print(f"\n📚 Classe: {classe_note.nom}")
        print(f"   Année: {classe_note.annee_scolaire}")
        
        # Vérifier chaque mois
        print("\n📅 NOTES MENSUELLES:")
        mois = ['OCTOBRE', 'NOVEMBRE', 'DECEMBRE', 'JANVIER', 'FEVRIER', 
                'MARS', 'AVRIL', 'MAI', 'JUIN']
        
        for m in mois:
            count = NoteMensuelle.objects.filter(
                matiere__classe=classe_note,
                mois=m,
                annee_scolaire=classe_note.annee_scolaire
            ).count()
            
            statut = "✅" if count > 0 else "❌"
            print(f"   {statut} {m}: {count} notes")
        
        # Vérifier les trimestres
        print("\n📅 COMPOSITIONS TRIMESTRIELLES:")
        trimestres = ['TRIMESTRE_1', 'TRIMESTRE_2', 'TRIMESTRE_3']
        
        for t in trimestres:
            count = CompositionNote.objects.filter(
                matiere__classe=classe_note,
                periode=t,
                annee_scolaire=classe_note.annee_scolaire
            ).count()
            
            statut = "✅" if count > 0 else "❌"
            print(f"   {statut} {t}: {count} compositions")
        
        # Vérifier les semestres
        print("\n📅 COMPOSITIONS SEMESTRIELLES:")
        semestres = ['SEMESTRE_1', 'SEMESTRE_2']
        
        for s in semestres:
            count = CompositionNote.objects.filter(
                matiere__classe=classe_note,
                periode=s,
                annee_scolaire=classe_note.annee_scolaire
            ).count()
            
            statut = "✅" if count > 0 else "❌"
            print(f"   {statut} {s}: {count} compositions")
            
    except ClasseNote.DoesNotExist:
        print("❌ Classe 2 non trouvée")


if __name__ == "__main__":
    diagnostiquer_fevrier()
    verifier_toutes_periodes()
    
    print("\n" + "="*80)
    print(" "*15 + "🎯 RÉSUMÉ ET RECOMMANDATIONS")
    print("="*80)
    
    print("\n📋 Pour résoudre le problème:")
    print("   1. Vérifier si des notes de FÉVRIER ont été saisies")
    print("   2. Si non, aller sur la page de saisie des notes")
    print("   3. Sélectionner la classe et le mois FÉVRIER")
    print("   4. Saisir les notes pour tous les élèves")
    print("   5. Retourner sur la page des statistiques")
    
    print("\n🔗 Liens utiles:")
    print("   Saisie: http://127.0.0.1:8000/notes/saisie/")
    print("   Stats: http://127.0.0.1:8000/notes/statistiques/?classe_id=2&periode=FEVRIER")
