"""
Script d'initialisation des abonnements
Crée les types d'abonnements et les itinéraires de base
"""

import os
import django

# Configuration Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ecole_moderne.settings')
django.setup()

from abonnements.models import TypeAbonnement, Itineraire, MenuCantine
from datetime import time, date, timedelta

def creer_types_abonnements():
    """Créer les types d'abonnements"""
    print("\n" + "=" * 70)
    print("CRÉATION DES TYPES D'ABONNEMENTS")
    print("=" * 70)
    
    types = [
        {
            'nom': 'BUS',
            'description': 'Transport scolaire aller-retour',
            'tarif_mensuel': 50000,
            'tarif_trimestriel': 135000,
            'tarif_annuel': 450000
        },
        {
            'nom': 'CANTINE',
            'description': 'Repas à la cantine scolaire',
            'tarif_mensuel': 40000,
            'tarif_trimestriel': 108000,
            'tarif_annuel': 360000
        },
        {
            'nom': 'GARDERIE',
            'description': 'Garderie après les cours',
            'tarif_mensuel': 30000,
            'tarif_trimestriel': 81000,
            'tarif_annuel': 270000
        },
        {
            'nom': 'ETUDE',
            'description': 'Étude surveillée',
            'tarif_mensuel': 25000,
            'tarif_trimestriel': 67500,
            'tarif_annuel': 225000
        },
    ]
    
    created_count = 0
    for type_data in types:
        type_abo, created = TypeAbonnement.objects.get_or_create(
            nom=type_data['nom'],
            defaults=type_data
        )
        if created:
            print(f"   ✅ Type créé: {type_abo.get_nom_display()} - {type_abo.tarif_mensuel} GNF/mois")
            created_count += 1
        else:
            print(f"   ℹ️  Type existant: {type_abo.get_nom_display()}")
    
    print(f"\n✅ {created_count} type(s) créé(s)")
    print(f"✅ Total types disponibles: {TypeAbonnement.objects.count()}")

def creer_itineraires():
    """Créer les itinéraires de bus"""
    print("\n" + "=" * 70)
    print("CRÉATION DES ITINÉRAIRES DE BUS")
    print("=" * 70)
    
    itineraires = [
        {
            'nom': 'Itinéraire 1 - Centre-ville',
            'description': 'Dessert le centre-ville et les quartiers proches',
            'quartiers': '''Kaloum
Coléah
Almamya
Boulbinet
Tombo''',
            'heure_depart_matin': time(7, 0),
            'heure_retour_soir': time(16, 30),
            'capacite': 40
        },
        {
            'nom': 'Itinéraire 2 - Matoto',
            'description': 'Dessert la commune de Matoto',
            'quartiers': '''Matoto Centre
Sangoyah
Kipé
Sonfonia
Yimbaya''',
            'heure_depart_matin': time(6, 45),
            'heure_retour_soir': time(16, 45),
            'capacite': 40
        },
        {
            'nom': 'Itinéraire 3 - Ratoma',
            'description': 'Dessert la commune de Ratoma',
            'quartiers': '''Ratoma Centre
Koléah
Hamdallaye
Cosa
Bambeto''',
            'heure_depart_matin': time(7, 15),
            'heure_retour_soir': time(16, 15),
            'capacite': 35
        },
        {
            'nom': 'Itinéraire 4 - Dixinn',
            'description': 'Dessert la commune de Dixinn',
            'quartiers': '''Dixinn Centre
Teminetaye
Landréah
Bonfi
Cameroun''',
            'heure_depart_matin': time(7, 10),
            'heure_retour_soir': time(16, 20),
            'capacite': 35
        },
        {
            'nom': 'Itinéraire 5 - Kaloum-Matam',
            'description': 'Dessert Kaloum et Matam',
            'quartiers': '''Kaloum
Matam
Sandervalia
Coronthie
Taouyah''',
            'heure_depart_matin': time(6, 50),
            'heure_retour_soir': time(16, 40),
            'capacite': 40
        },
    ]
    
    created_count = 0
    for itin_data in itineraires:
        itineraire, created = Itineraire.objects.get_or_create(
            nom=itin_data['nom'],
            defaults=itin_data
        )
        if created:
            print(f"   ✅ Itinéraire créé: {itineraire.nom}")
            print(f"      Départ: {itineraire.heure_depart_matin} - Retour: {itineraire.heure_retour_soir}")
            print(f"      Capacité: {itineraire.capacite} places")
            created_count += 1
        else:
            print(f"   ℹ️  Itinéraire existant: {itineraire.nom}")
    
    print(f"\n✅ {created_count} itinéraire(s) créé(s)")
    print(f"✅ Total itinéraires disponibles: {Itineraire.objects.count()}")

def creer_menus_semaine():
    """Créer des menus pour la semaine en cours"""
    print("\n" + "=" * 70)
    print("CRÉATION DES MENUS DE LA SEMAINE")
    print("=" * 70)
    
    # Obtenir le lundi de la semaine en cours
    today = date.today()
    monday = today - timedelta(days=today.weekday())
    
    menus = [
        {
            'jour': 'LUNDI',
            'entree': 'Salade verte',
            'plat_principal': 'Riz au poulet',
            'accompagnement': 'Haricots verts',
            'dessert': 'Fruit de saison',
            'boisson': 'Jus de fruits'
        },
        {
            'jour': 'MARDI',
            'entree': 'Soupe de légumes',
            'plat_principal': 'Poisson grillé',
            'accompagnement': 'Riz blanc',
            'dessert': 'Yaourt',
            'boisson': 'Eau'
        },
        {
            'jour': 'MERCREDI',
            'entree': 'Salade de tomates',
            'plat_principal': 'Poulet yassa',
            'accompagnement': 'Riz',
            'dessert': 'Banane',
            'boisson': 'Jus de bissap'
        },
        {
            'jour': 'JEUDI',
            'entree': 'Salade mixte',
            'plat_principal': 'Mafé de boeuf',
            'accompagnement': 'Riz',
            'dessert': 'Orange',
            'boisson': 'Eau'
        },
        {
            'jour': 'VENDREDI',
            'entree': 'Salade de concombre',
            'plat_principal': 'Poisson braisé',
            'accompagnement': 'Attiéké',
            'dessert': 'Mangue',
            'boisson': 'Jus de gingembre'
        },
    ]
    
    created_count = 0
    semaine = monday.isocalendar()[1]
    
    for i, menu_data in enumerate(menus):
        date_menu = monday + timedelta(days=i)
        menu_data['semaine'] = semaine
        menu_data['date_menu'] = date_menu
        
        menu, created = MenuCantine.objects.get_or_create(
            jour=menu_data['jour'],
            semaine=semaine,
            date_menu=date_menu,
            defaults=menu_data
        )
        if created:
            print(f"   ✅ Menu créé: {menu.get_jour_display()} - {menu.plat_principal}")
            created_count += 1
        else:
            print(f"   ℹ️  Menu existant: {menu.get_jour_display()}")
    
    print(f"\n✅ {created_count} menu(s) créé(s)")
    print(f"✅ Total menus disponibles: {MenuCantine.objects.count()}")

def afficher_statistiques():
    """Afficher les statistiques"""
    print("\n" + "=" * 70)
    print("STATISTIQUES")
    print("=" * 70)
    
    print(f"\n📊 Types d'abonnements: {TypeAbonnement.objects.count()}")
    for type_abo in TypeAbonnement.objects.all():
        print(f"   - {type_abo.get_nom_display()}: {type_abo.tarif_mensuel} GNF/mois")
    
    print(f"\n🚌 Itinéraires de bus: {Itineraire.objects.count()}")
    for itin in Itineraire.objects.all():
        print(f"   - {itin.nom}: {itin.capacite} places")
    
    print(f"\n🍽️  Menus cantine: {MenuCantine.objects.count()}")

def main():
    """Fonction principale"""
    print("\n" + "=" * 70)
    print("INITIALISATION DES ABONNEMENTS")
    print("=" * 70)
    
    try:
        # 1. Types d'abonnements
        creer_types_abonnements()
        
        # 2. Itinéraires
        creer_itineraires()
        
        # 3. Menus
        creer_menus_semaine()
        
        # 4. Statistiques
        afficher_statistiques()
        
        print("\n" + "=" * 70)
        print("✅ INITIALISATION TERMINÉE AVEC SUCCÈS !")
        print("=" * 70)
        
        print("\n📝 PROCHAINES ÉTAPES:")
        print("   1. Accéder à l'admin: http://127.0.0.1:8000/admin/abonnements/")
        print("   2. Créer des abonnements pour les élèves")
        print("   3. Gérer les présences cantine")
        print("   4. Suivre les itinéraires de bus")
        
    except Exception as e:
        print(f"\n❌ ERREUR: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    main()
