#!/usr/bin/env python
"""
Script de test pour vérifier le nouveau système de cartes scolaires
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ecole_moderne.settings')
django.setup()

from eleves.models import Eleve, Classe, Ecole
from eleves.carte_scolaire_generator import generer_carte_scolaire_moderne
from django.http import HttpResponse
import io

def test_carte_generation():
    """Test la génération d'une carte scolaire"""
    print("🧪 Test du système de cartes scolaires")
    print("="*50)
    
    # Récupérer un élève
    eleve = Eleve.objects.filter(statut='ACTIF').select_related(
        'classe', 'classe__ecole', 'responsable_principal'
    ).first()
    
    if not eleve:
        # Créer des données de test si nécessaire
        print("❌ Aucun élève trouvé. Création de données de test...")
        
        # Créer une école
        ecole, created = Ecole.objects.get_or_create(
            nom="École Test",
            defaults={
                'adresse': "123 Rue Test, Conakry",
                'telephone': "622000000"
            }
        )
        
        # Créer une classe
        classe, created = Classe.objects.get_or_create(
            nom="6ème A",
            ecole=ecole,
            defaults={
                'niveau': "COLLEGE",
                'annee_scolaire': "2024-2025",
                'effectif_max': 30
            }
        )
        
        # Créer un responsable
        from eleves.models import Responsable
        responsable, created = Responsable.objects.get_or_create(
            telephone="625123456",
            defaults={
                'nom': "DIALLO",
                'prenom': "Mamadou",
                'adresse': "Quartier Minière, Conakry"
            }
        )
        
        # Créer un élève
        from datetime import date
        eleve = Eleve.objects.create(
            matricule="TEST001",
            prenom="Fatou",
            nom="BAH",
            sexe="F",
            date_naissance=date(2010, 5, 15),
            lieu_naissance="Conakry",
            classe=classe,
            date_inscription=date.today(),
            statut="ACTIF",
            responsable_principal=responsable
        )
        
        print("✅ Données de test créées")
    
    print(f"\n📋 Élève sélectionné:")
    print(f"   Nom: {eleve.prenom} {eleve.nom}")
    print(f"   Matricule: {eleve.matricule}")
    print(f"   Classe: {eleve.classe.nom}")
    print(f"   École: {eleve.classe.ecole.nom}")
    
    # Tester la génération PDF
    print("\n🔨 Test de génération PDF...")
    try:
        # Créer une response simulée
        response = HttpResponse(content_type='application/pdf')
        
        # Générer la carte
        result = generer_carte_scolaire_moderne(eleve, response)
        
        # Récupérer le contenu
        pdf_content = result.content
        
        if len(pdf_content) > 0:
            print(f"✅ PDF généré avec succès ({len(pdf_content)} octets)")
            
            # Sauvegarder le PDF pour vérification
            output_file = f"carte_test_{eleve.matricule.replace('/', '_')}.pdf"
            with open(output_file, 'wb') as f:
                f.write(pdf_content)
            print(f"✅ PDF sauvegardé: {output_file}")
        else:
            print("❌ Erreur: PDF vide")
    except Exception as e:
        print(f"❌ Erreur lors de la génération: {e}")
        import traceback
        traceback.print_exc()
    
    # Vérifier les URLs
    print("\n🔗 URLs configurées:")
    from django.urls import reverse
    try:
        preview_url = reverse('eleves:carte_scolaire_preview', args=[eleve.id])
        pdf_url = reverse('eleves:carte_scolaire_pdf', args=[eleve.id])
        print(f"   Preview: http://127.0.0.1:8000{preview_url}")
        print(f"   PDF: http://127.0.0.1:8000{pdf_url}")
    except Exception as e:
        print(f"   ❌ Erreur URLs: {e}")
    
    print("\n" + "="*50)
    print("✅ Tests terminés!")
    print("\n📌 Pour tester visuellement:")
    print("   1. Assurez-vous que le serveur tourne (python manage.py runserver)")
    print(f"   2. Ouvrez: http://127.0.0.1:8000/eleves/{eleve.id}/carte-scolaire-preview/")
    
    return eleve

if __name__ == '__main__':
    test_carte_generation()
