#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Script de diagnostic pour vérifier l'affichage de la section bus dans le formulaire de paiement
"""
import os
import django

# Configuration Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ecole_moderne.settings')
django.setup()

from paiements.models import TypePaiement
from paiements.forms import PaiementForm

def debug_bus_form():
    """Diagnostic du formulaire de paiement avec section bus"""
    print("=== Diagnostic du formulaire de paiement - Section Bus ===\n")
    
    # 1. Vérifier le type de paiement "Abonnement Bus"
    print("1. Vérification du type de paiement 'Abonnement Bus'...")
    try:
        type_bus = TypePaiement.objects.get(nom="Abonnement Bus")
        print(f"OK Type trouve: ID={type_bus.id}, Nom='{type_bus.nom}', Actif={type_bus.actif}")
    except TypePaiement.DoesNotExist:
        print("ERREUR: Type 'Abonnement Bus' non trouve!")
        return
    
    # 2. Vérifier tous les types de paiement actifs
    print("\n2. Liste de tous les types de paiement actifs:")
    types_actifs = TypePaiement.objects.filter(actif=True).order_by('id')
    for i, tp in enumerate(types_actifs):
        marker = " <-- ABONNEMENT BUS" if tp.nom == "Abonnement Bus" else ""
        print(f"  {i+1}. ID={tp.id} - '{tp.nom}'{marker}")
    
    # 3. Tester le formulaire PaiementForm
    print("\n3. Test du formulaire PaiementForm...")
    form = PaiementForm()
    
    # Vérifier les champs bus
    bus_fields = ['bus_periodicite', 'bus_date_debut', 'bus_date_expiration', 'bus_zone', 'bus_point_arret', 'bus_observations']
    print("   Champs bus dans le formulaire:")
    for field_name in bus_fields:
        if field_name in form.fields:
            field = form.fields[field_name]
            print(f"   OK {field_name}: {field.label}")
        else:
            print(f"   ERREUR {field_name}: MANQUANT")
    
    # 4. Vérifier les choix du type de paiement dans le formulaire
    print("\n4. Choix disponibles dans le formulaire:")
    type_field = form.fields.get('type_paiement')
    if type_field:
        queryset = type_field.queryset
        print(f"   Nombre de types disponibles: {queryset.count()}")
        for tp in queryset:
            marker = " <-- CIBLE" if tp.nom == "Abonnement Bus" else ""
            print(f"   - ID={tp.id}: '{tp.nom}'{marker}")
    else:
        print("   ERREUR: Champ type_paiement non trouve!")
    
    # 5. Générer le HTML du formulaire pour inspection
    print("\n5. Génération du HTML du select type_paiement...")
    type_field_html = str(form['type_paiement'])
    
    # Extraire les options du select
    import re
    options = re.findall(r'<option value="(\d+)"[^>]*>([^<]+)</option>', type_field_html)
    print("   Options dans le HTML:")
    for value, text in options:
        marker = " <-- ABONNEMENT BUS" if "Abonnement Bus" in text else ""
        print(f"   - value='{value}': '{text.strip()}'{marker}")
    
    # 6. Vérifier la présence de la section bus dans le template
    print("\n6. Vérification du template...")
    template_path = "templates/paiements/form_paiement.html"
    try:
        with open(template_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
        if 'id="bus-section"' in content:
            print("   OK Section bus trouvee dans le template")
        else:
            print("   ERREUR Section bus manquante dans le template")
            
        if 'toggleBusSection' in content:
            print("   OK Fonction JavaScript toggleBusSection trouvee")
        else:
            print("   ERREUR Fonction JavaScript manquante")
            
        if 'Abonnement Bus' in content:
            print("   OK Reference 'Abonnement Bus' trouvee dans le template")
        else:
            print("   ATTENTION Aucune reference 'Abonnement Bus' dans le template")
            
    except FileNotFoundError:
        print(f"   ERREUR Template non trouve: {template_path}")
    
    print("\n=== Résumé du diagnostic ===")
    print("Si la section bus ne s'affiche pas:")
    print("1. Vérifiez la console du navigateur (F12)")
    print("2. Sélectionnez 'Abonnement Bus' et regardez les logs")
    print("3. Vérifiez que l'ID 'bus-section' existe dans le HTML généré")
    print("4. Testez manuellement: document.getElementById('bus-section').style.display = 'block'")

if __name__ == '__main__':
    try:
        debug_bus_form()
    except Exception as e:
        print(f"ERREUR lors du diagnostic: {e}")
        import traceback
        traceback.print_exc()
