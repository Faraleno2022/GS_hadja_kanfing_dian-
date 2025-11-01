"""
Script pour ajouter plus d'élèves dans la base de données
Crée 20 élèves par classe pour toutes les classes
"""

import os
import django

# Configuration Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ecole_moderne.settings')
django.setup()

from eleves.models import Classe, Eleve, Responsable
from datetime import date
import random

def creer_responsables():
    """Créer plusieurs responsables"""
    print("\n" + "=" * 70)
    print("CRÉATION DES RESPONSABLES")
    print("=" * 70)
    
    responsables_data = [
        {'nom': 'DIALLO', 'prenom': 'Mamadou', 'tel': '+224 622 111 111', 'profession': 'Commerçant'},
        {'nom': 'BARRY', 'prenom': 'Ibrahima', 'tel': '+224 622 222 222', 'profession': 'Enseignant'},
        {'nom': 'BAH', 'prenom': 'Abdoulaye', 'tel': '+224 622 333 333', 'profession': 'Médecin'},
        {'nom': 'SOW', 'prenom': 'Mohamed', 'tel': '+224 622 444 444', 'profession': 'Ingénieur'},
        {'nom': 'CAMARA', 'prenom': 'Ousmane', 'tel': '+224 622 555 555', 'profession': 'Fonctionnaire'},
        {'nom': 'SYLLA', 'prenom': 'Thierno', 'tel': '+224 622 666 666', 'profession': 'Commerçant'},
        {'nom': 'CONDE', 'prenom': 'Alpha', 'tel': '+224 622 777 777', 'profession': 'Entrepreneur'},
        {'nom': 'TOURE', 'prenom': 'Boubacar', 'tel': '+224 622 888 888', 'profession': 'Avocat'},
        {'nom': 'KEITA', 'prenom': 'Saliou', 'tel': '+224 622 999 999', 'profession': 'Comptable'},
        {'nom': 'BANGOURA', 'prenom': 'Amadou', 'tel': '+224 623 111 111', 'profession': 'Pharmacien'},
    ]
    
    responsables = []
    created_count = 0
    
    for resp_data in responsables_data:
        responsable, created = Responsable.objects.get_or_create(
            nom=resp_data['nom'],
            prenom=resp_data['prenom'],
            defaults={
                'telephone': resp_data['tel'],
                'email': f"{resp_data['prenom'].lower()}.{resp_data['nom'].lower()}@example.gn",
                'adresse': 'Conakry, Guinée',
                'profession': resp_data['profession']
            }
        )
        responsables.append(responsable)
        if created:
            print(f"   ✅ Responsable créé: {responsable.nom_complet}")
            created_count += 1
        else:
            print(f"   ℹ️  Responsable existant: {responsable.nom_complet}")
    
    print(f"\n✅ {created_count} responsable(s) créé(s)")
    print(f"✅ Total responsables disponibles: {Responsable.objects.count()}")
    
    return responsables

def creer_eleves_pour_toutes_classes():
    """Créer 20 élèves par classe"""
    print("\n" + "=" * 70)
    print("CRÉATION DES ÉLÈVES POUR TOUTES LES CLASSES")
    print("=" * 70)
    
    # Récupérer toutes les classes
    classes = Classe.objects.all().order_by('niveau', 'nom')
    
    if not classes.exists():
        print("   ❌ Aucune classe trouvée. Exécutez d'abord initialiser_donnees.py")
        return
    
    # Récupérer les responsables
    responsables = list(Responsable.objects.all())
    
    if not responsables:
        print("   ⚠️  Aucun responsable trouvé. Création des responsables...")
        responsables = creer_responsables()
    
    # Noms guinéens
    noms = [
        'DIALLO', 'BARRY', 'BAH', 'SOW', 'CAMARA', 'SYLLA', 'CONDE', 'TOURE', 
        'KEITA', 'BANGOURA', 'CISSE', 'SOUMAH', 'KABA', 'FOFANA', 'KOUROUMA',
        'BALDE', 'CHERIF', 'CONTE', 'DOUMBOUYA', 'KANTE'
    ]
    
    prenoms_garcons = [
        'Mamadou', 'Ibrahima', 'Abdoulaye', 'Mohamed', 'Ousmane', 
        'Thierno', 'Alpha', 'Boubacar', 'Saliou', 'Amadou',
        'Sekou', 'Lansana', 'Aboubacar', 'Souleymane', 'Moussa',
        'Alseny', 'Cellou', 'Elhadj', 'Facinet', 'Ibrahima'
    ]
    
    prenoms_filles = [
        'Fatoumata', 'Aissatou', 'Mariama', 'Kadiatou', 'Hawa', 
        'Aminata', 'Safiatou', 'Hadja', 'Ramata', 'Oumou',
        'Binta', 'Djénabou', 'Fanta', 'Aisata', 'Mariam',
        'Salematou', 'Tenin', 'Yacine', 'Zainab', 'Nene'
    ]
    
    total_created = 0
    
    for classe in classes:
        print(f"\n   Classe: {classe.nom} ({classe.niveau})")
        
        # Compter les élèves existants
        eleves_existants = Eleve.objects.filter(classe=classe).count()
        
        # Créer jusqu'à 20 élèves par classe
        nombre_a_creer = max(0, 20 - eleves_existants)
        
        if nombre_a_creer == 0:
            print(f"      ℹ️  Classe complète: {eleves_existants} élèves")
            continue
        
        print(f"      Création de {nombre_a_creer} élève(s)...")
        
        for i in range(nombre_a_creer):
            # Alterner garçons et filles
            sexe = 'M' if i % 2 == 0 else 'F'
            
            # Choisir un nom et prénom aléatoire
            nom = random.choice(noms)
            prenom = random.choice(prenoms_garcons) if sexe == 'M' else random.choice(prenoms_filles)
            
            # Générer un matricule unique
            annee = date.today().year
            # Utiliser l'ID de la classe et un compteur
            numero = f"{classe.id:02d}{(eleves_existants + i + 1):03d}"
            matricule = f"{annee}/{numero}"
            
            # Vérifier si le matricule existe déjà
            while Eleve.objects.filter(matricule=matricule).exists():
                numero = f"{classe.id:02d}{random.randint(100, 999)}"
                matricule = f"{annee}/{numero}"
            
            # Choisir un responsable aléatoire
            responsable = random.choice(responsables)
            
            # Date de naissance aléatoire selon le niveau
            if classe.niveau == 'MATERNELLE':
                annee_naissance = random.randint(2018, 2021)
            elif classe.niveau == 'PRIMAIRE':
                annee_naissance = random.randint(2012, 2017)
            elif classe.niveau == 'COLLEGE':
                annee_naissance = random.randint(2008, 2013)
            else:  # LYCEE
                annee_naissance = random.randint(2005, 2010)
            
            mois = random.randint(1, 12)
            jour = random.randint(1, 28)
            
            try:
                eleve = Eleve.objects.create(
                    matricule=matricule,
                    nom=nom,
                    prenom=prenom,
                    sexe=sexe,
                    date_naissance=date(annee_naissance, mois, jour),
                    lieu_naissance='Conakry',
                    classe=classe,
                    responsable_principal=responsable,
                    date_inscription=date.today(),
                    statut='ACTIF'
                )
                
                total_created += 1
                
                if (i + 1) % 5 == 0:  # Afficher tous les 5 élèves
                    print(f"      ✅ {i + 1}/{nombre_a_creer} élèves créés...")
                    
            except Exception as e:
                print(f"      ❌ Erreur pour {matricule}: {e}")
        
        # Afficher le total pour cette classe
        total_classe = Eleve.objects.filter(classe=classe).count()
        print(f"      ✅ Total élèves dans {classe.nom}: {total_classe}")
    
    print(f"\n✅ {total_created} élève(s) créé(s) au total")
    print(f"✅ Total élèves dans la base: {Eleve.objects.count()}")

def afficher_statistiques():
    """Afficher les statistiques finales"""
    print("\n" + "=" * 70)
    print("STATISTIQUES FINALES")
    print("=" * 70)
    
    # Par classe
    classes = Classe.objects.all().order_by('niveau', 'nom')
    
    print("\n📊 Élèves par classe:")
    for classe in classes:
        nb_eleves = Eleve.objects.filter(classe=classe).count()
        nb_garcons = Eleve.objects.filter(classe=classe, sexe='M').count()
        nb_filles = Eleve.objects.filter(classe=classe, sexe='F').count()
        print(f"   {classe.nom:20} : {nb_eleves:3} élèves (G:{nb_garcons:2} / F:{nb_filles:2})")
    
    # Par niveau
    print("\n📊 Élèves par niveau:")
    for niveau in ['MATERNELLE', 'PRIMAIRE', 'COLLEGE', 'LYCEE']:
        nb = Eleve.objects.filter(classe__niveau=niveau).count()
        print(f"   {niveau:15} : {nb:3} élèves")
    
    # Par sexe
    print("\n📊 Répartition par sexe:")
    nb_garcons = Eleve.objects.filter(sexe='M').count()
    nb_filles = Eleve.objects.filter(sexe='F').count()
    print(f"   Garçons : {nb_garcons}")
    print(f"   Filles  : {nb_filles}")
    print(f"   Total   : {nb_garcons + nb_filles}")
    
    # Par statut
    print("\n📊 Répartition par statut:")
    for statut in ['ACTIF', 'SUSPENDU', 'EXCLU']:
        nb = Eleve.objects.filter(statut=statut).count()
        print(f"   {statut:10} : {nb}")

def main():
    """Fonction principale"""
    print("\n" + "=" * 70)
    print("AJOUT MASSIF D'ÉLÈVES")
    print("=" * 70)
    
    try:
        # 1. Créer les responsables
        responsables = creer_responsables()
        
        # 2. Créer les élèves
        creer_eleves_pour_toutes_classes()
        
        # 3. Afficher les statistiques
        afficher_statistiques()
        
        print("\n" + "=" * 70)
        print("✅ AJOUT D'ÉLÈVES TERMINÉ AVEC SUCCÈS !")
        print("=" * 70)
        
        print("\n📝 PROCHAINES ÉTAPES:")
        print("   1. Vérifier les élèves: http://127.0.0.1:8000/eleves/liste/")
        print("   2. Créer des paiements")
        print("   3. Saisir des notes")
        print("   4. Générer des bulletins")
        
    except Exception as e:
        print(f"\n❌ ERREUR: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    main()
