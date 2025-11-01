#!/usr/bin/env python
"""
Script pour ajouter des élèves de test dans les deux écoles
pour tester l'interface multi-écoles
"""
import os
import sys
import django
from datetime import date, timedelta
from decimal import Decimal
import random

# Configuration Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ecole_moderne.settings')
django.setup()

from django.contrib.auth.models import User
from eleves.models import Ecole, Classe, Eleve, Responsable

def creer_responsables_test():
    """Créer des responsables de test"""
    print("👨‍👩‍👧‍👦 Création des responsables de test...")
    
    responsables_data = [
        # Responsables pour Sonfonia
        {
            'prenom': 'Mamadou', 'nom': 'DIALLO', 'relation': 'PERE',
            'telephone': '+22462001001', 'email': 'mamadou.diallo@gmail.com',
            'adresse': 'Sonfonia Gare, Conakry', 'profession': 'Commerçant'
        },
        {
            'prenom': 'Fatoumata', 'nom': 'BARRY', 'relation': 'MERE',
            'telephone': '+22462001002', 'email': 'fatoumata.barry@gmail.com',
            'adresse': 'Sonfonia Centre, Conakry', 'profession': 'Enseignante'
        },
        {
            'prenom': 'Ibrahima', 'nom': 'CAMARA', 'relation': 'PERE',
            'telephone': '+22462001003', 'email': 'ibrahima.camara@gmail.com',
            'adresse': 'Sonfonia Rail, Conakry', 'profession': 'Mécanicien'
        },
        {
            'prenom': 'Aminata', 'nom': 'TOURE', 'relation': 'MERE',
            'telephone': '+22462001004', 'email': 'aminata.toure@gmail.com',
            'adresse': 'Sonfonia Port, Conakry', 'profession': 'Couturière'
        },
        
        # Responsables pour Somayah
        {
            'prenom': 'Alpha', 'nom': 'CONDE', 'relation': 'PERE',
            'telephone': '+22462002001', 'email': 'alpha.conde@gmail.com',
            'adresse': 'Somayah Centre, Conakry', 'profession': 'Chauffeur'
        },
        {
            'prenom': 'Mariama', 'nom': 'SOW', 'relation': 'MERE',
            'telephone': '+22462002002', 'email': 'mariama.sow@gmail.com',
            'adresse': 'Somayah Marché, Conakry', 'profession': 'Vendeuse'
        },
        {
            'prenom': 'Ousmane', 'nom': 'BAH', 'relation': 'PERE',
            'telephone': '+22462002003', 'email': 'ousmane.bah@gmail.com',
            'adresse': 'Somayah Mosquée, Conakry', 'profession': 'Maçon'
        },
        {
            'prenom': 'Hadja', 'nom': 'DIAKITE', 'relation': 'MERE',
            'telephone': '+22462002004', 'email': 'hadja.diakite@gmail.com',
            'adresse': 'Somayah École, Conakry', 'profession': 'Ménagère'
        },
    ]
    
    responsables_crees = []
    for data in responsables_data:
        responsable, created = Responsable.objects.get_or_create(
            telephone=data['telephone'],
            defaults=data
        )
        
        if created:
            print(f"✅ Responsable créé: {responsable.prenom} {responsable.nom} ({responsable.telephone})")
        else:
            print(f"ℹ️  Responsable existant: {responsable.prenom} {responsable.nom}")
        
        responsables_crees.append(responsable)
    
    return responsables_crees

def creer_eleves_test():
    """Créer des élèves de test pour les deux écoles"""
    print("🎓 Création des élèves de test...")
    
    # Récupérer les écoles
    ecole_sonfonia = Ecole.objects.get(nom="myschool - Sonfonia")
    ecole_somayah = Ecole.objects.get(nom="myschool - Somayah")
    
    # Récupérer les responsables
    responsables = list(Responsable.objects.all())
    
    # Récupérer l'utilisateur admin pour cree_par
    admin_user = User.objects.filter(is_superuser=True).first()
    
    # Données des élèves de test
    eleves_data = [
        # Élèves pour École Sonfonia
        {
            'ecole': ecole_sonfonia,
            'matricule': 'SON2024001',
            'prenom': 'Amadou',
            'nom': 'DIALLO',
            'sexe': 'M',
            'date_naissance': date(2018, 3, 15),
            'lieu_naissance': 'Conakry',
            'classe_niveau': 'PRIMAIRE_1'
        },
        {
            'ecole': ecole_sonfonia,
            'matricule': 'SON2024002',
            'prenom': 'Aissatou',
            'nom': 'BARRY',
            'sexe': 'F',
            'date_naissance': date(2017, 7, 22),
            'lieu_naissance': 'Conakry',
            'classe_niveau': 'PRIMAIRE_2'
        },
        {
            'ecole': ecole_sonfonia,
            'matricule': 'SON2024003',
            'prenom': 'Mohamed',
            'nom': 'CAMARA',
            'sexe': 'M',
            'date_naissance': date(2010, 11, 8),
            'lieu_naissance': 'Kindia',
            'classe_niveau': 'COLLEGE_9'
        },
        {
            'ecole': ecole_sonfonia,
            'matricule': 'SON2024004',
            'prenom': 'Kadiatou',
            'nom': 'TOURE',
            'sexe': 'F',
            'date_naissance': date(2019, 5, 12),
            'lieu_naissance': 'Conakry',
            'classe_niveau': 'MATERNELLE'
        },
        
        # Élèves pour École Somayah
        {
            'ecole': ecole_somayah,
            'matricule': 'SOM2024001',
            'prenom': 'Sekou',
            'nom': 'CONDE',
            'sexe': 'M',
            'date_naissance': date(2016, 9, 3),
            'lieu_naissance': 'Conakry',
            'classe_niveau': 'PRIMAIRE_3'
        },
        {
            'ecole': ecole_somayah,
            'matricule': 'SOM2024002',
            'prenom': 'Fatou',
            'nom': 'SOW',
            'sexe': 'F',
            'date_naissance': date(2015, 1, 18),
            'lieu_naissance': 'Labé',
            'classe_niveau': 'PRIMAIRE_4'
        },
        {
            'ecole': ecole_somayah,
            'matricule': 'SOM2024003',
            'prenom': 'Thierno',
            'nom': 'BAH',
            'sexe': 'M',
            'date_naissance': date(2008, 12, 25),
            'lieu_naissance': 'Conakry',
            'classe_niveau': 'LYCEE_11'
        },
        {
            'ecole': ecole_somayah,
            'matricule': 'SOM2024004',
            'prenom': 'Mariam',
            'nom': 'DIAKITE',
            'sexe': 'F',
            'date_naissance': date(2013, 4, 7),
            'lieu_naissance': 'Kankan',
            'classe_niveau': 'PRIMAIRE_6'
        },
    ]
    
    eleves_crees = []
    for i, data in enumerate(eleves_data):
        # Trouver la classe correspondante
        try:
            classe = Classe.objects.get(
                ecole=data['ecole'],
                niveau=data['classe_niveau']
            )
        except Classe.DoesNotExist:
            print(f"❌ Classe non trouvée: {data['classe_niveau']} pour {data['ecole'].nom}")
            continue
        
        # Assigner des responsables (principal et parfois secondaire)
        responsable_principal = responsables[i % len(responsables)]
        responsable_secondaire = None
        if i % 3 == 0:  # Un tiers des élèves ont un responsable secondaire
            responsable_secondaire = responsables[(i + 1) % len(responsables)]
            if responsable_secondaire == responsable_principal:
                responsable_secondaire = responsables[(i + 2) % len(responsables)]
        
        # Créer l'élève
        eleve_data = {
            'matricule': data['matricule'],
            'prenom': data['prenom'],
            'nom': data['nom'],
            'sexe': data['sexe'],
            'date_naissance': data['date_naissance'],
            'lieu_naissance': data['lieu_naissance'],
            'classe': classe,
            'date_inscription': date.today(),  # Ajouter la date d'inscription
            'responsable_principal': responsable_principal,
            'responsable_secondaire': responsable_secondaire,
            'cree_par': admin_user,
            'statut': 'ACTIF'
        }
        
        eleve, created = Eleve.objects.get_or_create(
            matricule=data['matricule'],
            defaults=eleve_data
        )
        
        if created:
            print(f"✅ Élève créé: {eleve.prenom} {eleve.nom} ({eleve.matricule}) - {eleve.classe.ecole.nom}")
        else:
            print(f"ℹ️  Élève existant: {eleve.prenom} {eleve.nom}")
        
        eleves_crees.append(eleve)
    
    return eleves_crees

def afficher_resume():
    """Afficher un résumé des données créées"""
    print("\n" + "=" * 80)
    print("📊 RÉSUMÉ DES DONNÉES DE TEST")
    print("=" * 80)
    
    # Statistiques par école
    for ecole in Ecole.objects.all():
        eleves_count = Eleve.objects.filter(classe__ecole=ecole).count()
        classes_count = Classe.objects.filter(ecole=ecole).count()
        
        print(f"\n🏫 {ecole.nom}")
        print(f"   📚 Classes: {classes_count}")
        print(f"   🎓 Élèves: {eleves_count}")
        
        # Détail par niveau
        for classe in Classe.objects.filter(ecole=ecole).order_by('niveau'):
            eleves_classe = Eleve.objects.filter(classe=classe).count()
            if eleves_classe > 0:
                print(f"      - {classe.nom}: {eleves_classe} élève(s)")
    
    # Statistiques globales
    total_responsables = Responsable.objects.count()
    total_eleves = Eleve.objects.count()
    total_classes = Classe.objects.count()
    total_ecoles = Ecole.objects.count()
    
    print(f"\n📈 STATISTIQUES GLOBALES:")
    print(f"   🏫 Écoles: {total_ecoles}")
    print(f"   📚 Classes: {total_classes}")
    print(f"   🎓 Élèves: {total_eleves}")
    print(f"   👨‍👩‍👧‍👦 Responsables: {total_responsables}")

def main():
    """Fonction principale"""
    print("🚀 Ajout d'élèves de test pour les deux écoles")
    print("=" * 80)
    
    try:
        # Créer les responsables
        responsables = creer_responsables_test()
        
        # Créer les élèves
        eleves = creer_eleves_test()
        
        # Afficher le résumé
        afficher_resume()
        
        print(f"\n✅ Ajout terminé avec succès !")
        print(f"🎯 Vous pouvez maintenant tester l'interface multi-écoles")
        print(f"🌐 Accédez à: http://127.0.0.1:8000/eleves/")
        
    except Exception as e:
        print(f"❌ Erreur lors de l'ajout: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == '__main__':
    main()
