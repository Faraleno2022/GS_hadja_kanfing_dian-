"""
Script de test pour les notes de rappel de paiement
"""

import os
import sys
import django

# Configuration Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ecole_moderne.settings')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
django.setup()

from django.contrib.auth import get_user_model
from eleves.models import Eleve, Classe, Ecole
from paiements.models import ConfigurationPaiement, Paiement, TypePaiement, ModePaiement
from paiements.note_rappel_generator import generer_note_rappel_eleve
from decimal import Decimal
from datetime import datetime

User = get_user_model()

def test_note_rappel():
    print("\n" + "="*60)
    print("TEST DES NOTES DE RAPPEL DE PAIEMENT")
    print("="*60)
    
    # Récupération d'un élève
    try:
        eleve = Eleve.objects.filter(statut='ACTIF').first()
        if not eleve:
            print("❌ Aucun élève actif trouvé dans la base de données.")
            return
    except Exception as e:
        print(f"❌ Erreur lors de la récupération de l'élève: {e}")
        return
    
    print(f"\n✅ Élève sélectionné: {eleve.nom_complet}")
    print(f"   Classe: {eleve.classe.nom}")
    print(f"   Matricule: {eleve.matricule}")
    
    # Création ou récupération de la configuration de paiement
    config, created = ConfigurationPaiement.objects.get_or_create(
        classe=eleve.classe,
        defaults={
            'montant_inscription': Decimal('500000'),
            'montant_scolarite': Decimal('1500000'),
            'nombre_tranches': 3
        }
    )
    
    if created:
        print(f"\n✅ Configuration de paiement créée pour la classe {eleve.classe.nom}")
    else:
        print(f"\n✅ Configuration existante pour la classe {eleve.classe.nom}")
    
    print(f"   Montant inscription: {config.montant_inscription:,.0f} GNF")
    print(f"   Montant scolarité: {config.montant_scolarite:,.0f} GNF")
    print(f"   Nombre de tranches: {config.nombre_tranches}")
    print(f"   Montant total: {config.montant_total:,.0f} GNF")
    
    # Création d'un paiement partiel pour tester
    type_paiement, _ = TypePaiement.objects.get_or_create(
        nom='Scolarité',
        defaults={'description': 'Frais de scolarité'}
    )
    
    mode_paiement, _ = ModePaiement.objects.get_or_create(
        nom='Espèces',
        defaults={'description': 'Paiement en espèces'}
    )
    
    # Créer un paiement partiel
    paiement = Paiement.objects.create(
        eleve=eleve,
        type_paiement=type_paiement,
        mode_paiement=mode_paiement,
        montant=Decimal('500000'),
        date_paiement=datetime.now().date(),
        statut='VALIDE',
        numero_recu=f"REC-{datetime.now().strftime('%Y%m%d%H%M%S')}",
        observations='Paiement partiel pour test'
    )
    
    print(f"\n✅ Paiement de test créé: {paiement.montant:,.0f} GNF")
    
    # Calcul du solde
    paiements_totaux = Paiement.objects.filter(
        eleve=eleve,
        statut='VALIDE'
    ).aggregate(total=models.Sum('montant'))['total'] or 0
    
    reste_a_payer = config.montant_total - paiements_totaux
    
    print(f"\n📊 Situation financière de {eleve.nom_complet}:")
    print(f"   Montant total dû: {config.montant_total:,.0f} GNF")
    print(f"   Montants payés: {paiements_totaux:,.0f} GNF")
    print(f"   Reste à payer: {reste_a_payer:,.0f} GNF")
    
    # Génération de la note de rappel
    print("\n" + "-"*50)
    print("GÉNÉRATION DE LA NOTE DE RAPPEL")
    print("-"*50)
    
    try:
        from io import BytesIO
        buffer = BytesIO()
        generer_note_rappel_eleve(eleve, buffer)
        buffer.seek(0)
        
        # Sauvegarder le PDF
        matricule_clean = eleve.matricule.replace('/', '_').replace('\\', '_')
        filename = f"note_rappel_{matricule_clean}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        # Créer le dossier si un chemin est présent
        out_dir = os.path.dirname(filename)
        if out_dir:
            os.makedirs(out_dir, exist_ok=True)
        with open(filename, 'wb') as f:
            f.write(buffer.read())
        
        print(f"✅ Note de rappel générée avec succès: {filename}")
        print(f"   Taille du fichier: {os.path.getsize(filename)} octets")
        
        # Ouvrir le PDF automatiquement (Windows)
        if os.name == 'nt':
            os.startfile(filename)
            print("✅ PDF ouvert automatiquement")
            
    except Exception as e:
        print(f"❌ Erreur lors de la génération de la note de rappel: {e}")
        import traceback
        traceback.print_exc()
    
    # Nettoyage
    print("\n" + "-"*50)
    reponse = input("Voulez-vous supprimer le paiement de test? (oui/non): ")
    if reponse.lower() in ['oui', 'o', 'yes', 'y']:
        paiement.delete()
        print("✅ Paiement de test supprimé")

if __name__ == '__main__':
    from django.db import models  # Import nécessaire pour l'agrégation
    try:
        test_note_rappel()
    except Exception as e:
        print(f"\n❌ Erreur lors de l'exécution du test: {e}")
        import traceback
        traceback.print_exc()
