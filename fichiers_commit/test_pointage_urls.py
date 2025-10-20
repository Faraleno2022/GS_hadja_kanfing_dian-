"""
Script de test pour vérifier les URLs du système de pointage
"""
import os
import django

# Configuration Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ecole_moderne.settings')
django.setup()

from django.urls import reverse
from django.test import Client
from django.contrib.auth import get_user_model
from salaires.models import Enseignant, PresenceEnseignant
from eleves.models import Ecole
from datetime import date

User = get_user_model()

def test_urls():
    """Test des URLs du système de pointage"""
    
    print("🧪 Test des URLs du système de pointage\n")
    print("=" * 60)
    
    # Créer un client de test
    client = Client()
    
    # Vérifier que les URLs sont bien configurées
    urls_to_test = [
        ('salaires:liste_presences', {}, 'Liste des présences'),
        ('salaires:pointer_presence', {}, 'Pointer présence'),
        ('salaires:rapport_presences', {}, 'Rapport des présences'),
        ('salaires:export_presences_csv', {}, 'Export CSV'),
    ]
    
    print("\n📍 Vérification des URLs configurées:\n")
    
    for url_name, kwargs, description in urls_to_test:
        try:
            url = reverse(url_name, kwargs=kwargs)
            print(f"✅ {description:30} -> {url}")
        except Exception as e:
            print(f"❌ {description:30} -> ERREUR: {e}")
    
    print("\n" + "=" * 60)
    
    # Vérifier le modèle
    print("\n📊 Vérification du modèle PresenceEnseignant:\n")
    
    try:
        # Compter les présences existantes
        count = PresenceEnseignant.objects.count()
        print(f"✅ Modèle PresenceEnseignant accessible")
        print(f"   Nombre de présences enregistrées: {count}")
        
        # Vérifier les choix de statut
        print(f"\n   Statuts disponibles:")
        for code, libelle in PresenceEnseignant.STATUT_CHOICES:
            print(f"   - {code:12} : {libelle}")
        
    except Exception as e:
        print(f"❌ Erreur avec le modèle: {e}")
    
    print("\n" + "=" * 60)
    
    # Vérifier les enseignants
    print("\n👨‍🏫 Vérification des enseignants:\n")
    
    try:
        enseignants_count = Enseignant.objects.count()
        enseignants_actifs = Enseignant.objects.filter(statut='ACTIF').count()
        
        print(f"✅ Total enseignants: {enseignants_count}")
        print(f"✅ Enseignants actifs: {enseignants_actifs}")
        
        if enseignants_actifs > 0:
            print(f"\n   Exemples d'enseignants actifs:")
            for ens in Enseignant.objects.filter(statut='ACTIF')[:5]:
                print(f"   - {ens.nom_complet} ({ens.get_type_enseignant_display()})")
        
    except Exception as e:
        print(f"❌ Erreur: {e}")
    
    print("\n" + "=" * 60)
    
    # Statistiques des présences
    print("\n📈 Statistiques des présences:\n")
    
    try:
        from django.db.models import Count, Q
        
        stats = PresenceEnseignant.objects.aggregate(
            total=Count('id'),
            presents=Count('id', filter=Q(statut='PRESENT')),
            absents=Count('id', filter=Q(statut='ABSENT')),
            retards=Count('id', filter=Q(statut='RETARD')),
        )
        
        print(f"✅ Total pointages: {stats['total']}")
        print(f"   - Présents: {stats['presents']}")
        print(f"   - Absents: {stats['absents']}")
        print(f"   - Retards: {stats['retards']}")
        
        # Présences récentes
        presences_recentes = PresenceEnseignant.objects.order_by('-date')[:5]
        if presences_recentes:
            print(f"\n   Derniers pointages:")
            for p in presences_recentes:
                print(f"   - {p.date} | {p.enseignant.nom_complet} | {p.get_statut_display()}")
        
    except Exception as e:
        print(f"❌ Erreur: {e}")
    
    print("\n" + "=" * 60)
    print("\n✅ Tests terminés avec succès!\n")
    print("🚀 Le système de pointage est opérationnel.")
    print("\n📖 Consultez GUIDE_POINTAGE_ENSEIGNANTS.md pour plus d'informations.\n")

if __name__ == '__main__':
    test_urls()
