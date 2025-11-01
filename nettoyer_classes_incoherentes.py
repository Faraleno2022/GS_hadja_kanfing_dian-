"""
Script pour nettoyer les classes incohérentes et les doublons
Supprime les classes avec des niveaux incorrects (ex: "2ème Année - Collège 7ème")
"""

import os
import django

# Configuration Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ecole_moderne.settings')
django.setup()

from eleves.models import Classe, Eleve
from notes.models import ClasseNote
from collections import defaultdict

def identifier_classes_incoherentes():
    """Identifier les classes avec des niveaux incohérents"""
    print("\n" + "=" * 70)
    print("IDENTIFICATION DES CLASSES INCOHÉRENTES")
    print("=" * 70)
    
    incoherentes = []
    
    # Patterns incohérents à détecter
    patterns_incoherents = [
        ('1ère année', 'COLLEGE'),
        ('2ème année', 'COLLEGE'),
        ('3ème année', 'COLLEGE'),
        ('7ème année', 'COLLEGE'),
        ('garderie', 'COLLEGE'),
        ('petite section', 'COLLEGE'),
    ]
    
    for classe in Classe.objects.all():
        nom_lower = classe.nom.lower()
        niveau_upper = classe.niveau.upper() if classe.niveau else ''
        
        # Vérifier les patterns incohérents
        for pattern_nom, pattern_niveau in patterns_incoherents:
            if pattern_nom in nom_lower and pattern_niveau in niveau_upper:
                incoherentes.append(classe)
                print(f"   ⚠️  Incohérent: {classe.nom} - {classe.niveau}")
                break
    
    print(f"\n✅ {len(incoherentes)} classe(s) incohérente(s) trouvée(s)")
    return incoherentes

def identifier_doublons():
    """Identifier les classes en double"""
    print("\n" + "=" * 70)
    print("IDENTIFICATION DES DOUBLONS")
    print("=" * 70)
    
    # Grouper par nom et année
    classes_par_cle = defaultdict(list)
    
    for classe in Classe.objects.all():
        cle = (classe.nom, classe.annee_scolaire)
        classes_par_cle[cle].append(classe)
    
    doublons = []
    for (nom, annee), classes in classes_par_cle.items():
        if len(classes) > 1:
            print(f"\n   ⚠️  Doublon: {nom} ({annee}) - {len(classes)} occurrences")
            for i, classe in enumerate(classes, 1):
                nb_eleves = Eleve.objects.filter(classe=classe).count()
                print(f"      {i}. ID={classe.id}, Niveau={classe.niveau}, Élèves={nb_eleves}")
            doublons.extend(classes)
    
    print(f"\n✅ {len(doublons)} classe(s) en double trouvée(s)")
    return classes_par_cle

def supprimer_classes_incoherentes(incoherentes, dry_run=True):
    """Supprimer les classes incohérentes"""
    print("\n" + "=" * 70)
    if dry_run:
        print("SIMULATION DE SUPPRESSION DES CLASSES INCOHÉRENTES")
    else:
        print("SUPPRESSION DES CLASSES INCOHÉRENTES")
    print("=" * 70)
    
    supprimees = 0
    
    for classe in incoherentes:
        nb_eleves = Eleve.objects.filter(classe=classe).count()
        
        if nb_eleves > 0:
            print(f"   ⚠️  CONSERVÉE (a {nb_eleves} élève(s)): {classe.nom} - {classe.niveau}")
        else:
            if dry_run:
                print(f"   ℹ️  À supprimer: {classe.nom} - {classe.niveau} (ID={classe.id})")
            else:
                print(f"   ✅ Supprimée: {classe.nom} - {classe.niveau} (ID={classe.id})")
                classe.delete()
            supprimees += 1
    
    if dry_run:
        print(f"\n✅ {supprimees} classe(s) seraient supprimée(s)")
    else:
        print(f"\n✅ {supprimees} classe(s) supprimée(s)")

def supprimer_doublons(classes_par_cle, dry_run=True):
    """Supprimer les doublons en gardant celui avec le plus d'élèves"""
    print("\n" + "=" * 70)
    if dry_run:
        print("SIMULATION DE SUPPRESSION DES DOUBLONS")
    else:
        print("SUPPRESSION DES DOUBLONS")
    print("=" * 70)
    
    supprimees = 0
    
    for (nom, annee), classes in classes_par_cle.items():
        if len(classes) <= 1:
            continue
        
        # Trier par nombre d'élèves (décroissant)
        classes_avec_eleves = []
        for classe in classes:
            nb_eleves = Eleve.objects.filter(classe=classe).count()
            classes_avec_eleves.append((classe, nb_eleves))
        
        classes_avec_eleves.sort(key=lambda x: x[1], reverse=True)
        
        # Garder la première (avec le plus d'élèves)
        a_garder = classes_avec_eleves[0][0]
        a_supprimer = [c for c, _ in classes_avec_eleves[1:]]
        
        print(f"\n   Doublon: {nom} ({annee})")
        print(f"      ✅ À GARDER: ID={a_garder.id}, Élèves={classes_avec_eleves[0][1]}")
        
        for classe, nb_eleves in classes_avec_eleves[1:]:
            if dry_run:
                print(f"      ℹ️  À supprimer: ID={classe.id}, Élèves={nb_eleves}")
            else:
                if nb_eleves > 0:
                    # Déplacer les élèves vers la classe à garder
                    print(f"      ⚠️  Déplacement de {nb_eleves} élève(s) vers ID={a_garder.id}")
                    Eleve.objects.filter(classe=classe).update(classe=a_garder)
                
                print(f"      ✅ Supprimée: ID={classe.id}")
                classe.delete()
            supprimees += 1
    
    if dry_run:
        print(f"\n✅ {supprimees} doublon(s) seraient supprimé(s)")
    else:
        print(f"\n✅ {supprimees} doublon(s) supprimé(s)")

def nettoyer_classes_notes():
    """Nettoyer aussi les ClasseNote"""
    print("\n" + "=" * 70)
    print("NETTOYAGE DES CLASSES NOTES")
    print("=" * 70)
    
    # Doublons ClasseNote
    classes_par_cle = defaultdict(list)
    
    for classe in ClasseNote.objects.all():
        cle = (classe.nom, classe.annee_scolaire)
        classes_par_cle[cle].append(classe)
    
    doublons = 0
    for (nom, annee), classes in classes_par_cle.items():
        if len(classes) > 1:
            print(f"\n   ⚠️  Doublon ClasseNote: {nom} ({annee}) - {len(classes)} occurrences")
            # Garder le premier, supprimer les autres
            for classe in classes[1:]:
                print(f"      ✅ Supprimée: ID={classe.id}")
                classe.delete()
                doublons += 1
    
    print(f"\n✅ {doublons} doublon(s) ClasseNote supprimé(s)")

def afficher_statistiques():
    """Afficher les statistiques finales"""
    print("\n" + "=" * 70)
    print("STATISTIQUES FINALES")
    print("=" * 70)
    
    print(f"\n📊 Classes (Eleves): {Classe.objects.count()}")
    print(f"📊 Classes (Notes): {ClasseNote.objects.count()}")
    
    # Par niveau
    print("\n📊 Par niveau (Eleves):")
    for niveau in ['MATERNELLE', 'PRIMAIRE', 'COLLEGE', 'LYCEE']:
        count = Classe.objects.filter(niveau=niveau).count()
        if count > 0:
            print(f"   {niveau}: {count}")
    
    # Vérifier les doublons restants
    classes_par_cle = defaultdict(list)
    for classe in Classe.objects.all():
        cle = (classe.nom, classe.annee_scolaire)
        classes_par_cle[cle].append(classe)
    
    doublons_restants = sum(1 for classes in classes_par_cle.values() if len(classes) > 1)
    
    if doublons_restants > 0:
        print(f"\n⚠️  {doublons_restants} doublon(s) restant(s)")
    else:
        print(f"\n✅ Aucun doublon restant")

def main():
    """Fonction principale"""
    print("\n" + "=" * 70)
    print("NETTOYAGE DES CLASSES INCOHÉRENTES ET DOUBLONS")
    print("=" * 70)
    
    try:
        # 1. Identifier les problèmes
        incoherentes = identifier_classes_incoherentes()
        classes_par_cle = identifier_doublons()
        
        # 2. Simulation
        print("\n" + "=" * 70)
        print("SIMULATION (DRY RUN)")
        print("=" * 70)
        supprimer_classes_incoherentes(incoherentes, dry_run=True)
        supprimer_doublons(classes_par_cle, dry_run=True)
        
        # 3. Demander confirmation
        print("\n" + "=" * 70)
        print("CONFIRMATION")
        print("=" * 70)
        reponse = input("\nVoulez-vous vraiment supprimer ces classes ? (oui/non): ")
        
        if reponse.lower() in ['oui', 'o', 'yes', 'y']:
            print("\n" + "=" * 70)
            print("SUPPRESSION RÉELLE")
            print("=" * 70)
            
            # Supprimer les incohérentes
            supprimer_classes_incoherentes(incoherentes, dry_run=False)
            
            # Réidentifier les doublons (au cas où)
            classes_par_cle = defaultdict(list)
            for classe in Classe.objects.all():
                cle = (classe.nom, classe.annee_scolaire)
                classes_par_cle[cle].append(classe)
            
            # Supprimer les doublons
            supprimer_doublons(classes_par_cle, dry_run=False)
            
            # Nettoyer ClasseNote
            nettoyer_classes_notes()
            
            # Statistiques
            afficher_statistiques()
            
            print("\n" + "=" * 70)
            print("✅ NETTOYAGE TERMINÉ AVEC SUCCÈS !")
            print("=" * 70)
        else:
            print("\n❌ Opération annulée")
        
    except Exception as e:
        print(f"\n❌ ERREUR: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    main()
