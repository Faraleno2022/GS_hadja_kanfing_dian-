"""
Script pour créer des données de test pour le système de pointage
"""
import os
import django
from datetime import date, time, timedelta
from decimal import Decimal

# Configuration Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ecole_moderne.settings')
django.setup()

from django.contrib.auth import get_user_model
from salaires.models import Enseignant, PresenceEnseignant
from eleves.models import Ecole

User = get_user_model()

def creer_donnees_test():
    """Créer des données de test pour le pointage"""
    
    print("🔧 Création de données de test pour le pointage\n")
    print("=" * 60)
    
    # Récupérer les enseignants actifs
    enseignants = Enseignant.objects.filter(statut='ACTIF')
    
    if not enseignants.exists():
        print("❌ Aucun enseignant actif trouvé.")
        print("   Veuillez d'abord créer des enseignants dans le système.")
        return
    
    print(f"✅ {enseignants.count()} enseignant(s) actif(s) trouvé(s)\n")
    
    # Récupérer un utilisateur pour le champ pointe_par
    user = User.objects.filter(is_active=True).first()
    if not user:
        print("❌ Aucun utilisateur trouvé.")
        return
    
    print(f"✅ Utilisateur pour pointage: {user.username}\n")
    
    # Créer des présences pour les 7 derniers jours
    today = date.today()
    created_count = 0
    updated_count = 0
    
    print("📅 Création des pointages pour les 7 derniers jours...\n")
    
    for i in range(7):
        current_date = today - timedelta(days=i)
        print(f"   Date: {current_date.strftime('%d/%m/%Y')}")
        
        for enseignant in enseignants:
            # Varier les statuts pour avoir des données intéressantes
            if i == 0:  # Aujourd'hui - tous présents
                statut = 'PRESENT'
                heure_arrivee = time(8, 0)
                heure_depart = time(16, 0)
                heures_travaillees = Decimal('8.0')
                justifie = False
                observations = ""
            elif i == 1:  # Hier - un retard
                if enseignant == enseignants.first():
                    statut = 'RETARD'
                    heure_arrivee = time(8, 30)
                    heure_depart = time(16, 0)
                    heures_travaillees = Decimal('7.5')
                    justifie = True
                    observations = "Problème de transport"
                else:
                    statut = 'PRESENT'
                    heure_arrivee = time(8, 0)
                    heure_depart = time(16, 0)
                    heures_travaillees = Decimal('8.0')
                    justifie = False
                    observations = ""
            elif i == 2:  # Il y a 2 jours - une absence
                if enseignant == enseignants.last():
                    statut = 'ABSENT'
                    heure_arrivee = None
                    heure_depart = None
                    heures_travaillees = None
                    justifie = True
                    observations = "Rendez-vous médical"
                else:
                    statut = 'PRESENT'
                    heure_arrivee = time(8, 0)
                    heure_depart = time(16, 0)
                    heures_travaillees = Decimal('8.0')
                    justifie = False
                    observations = ""
            elif i == 5:  # Week-end - congé
                statut = 'CONGE'
                heure_arrivee = None
                heure_depart = None
                heures_travaillees = None
                justifie = True
                observations = "Week-end"
            else:  # Autres jours - présent
                statut = 'PRESENT'
                heure_arrivee = time(8, 0)
                heure_depart = time(16, 0)
                heures_travaillees = Decimal('8.0')
                justifie = False
                observations = ""
            
            # Créer ou mettre à jour la présence
            presence, created = PresenceEnseignant.objects.update_or_create(
                enseignant=enseignant,
                date=current_date,
                defaults={
                    'statut': statut,
                    'heure_arrivee': heure_arrivee,
                    'heure_depart': heure_depart,
                    'heures_travaillees': heures_travaillees,
                    'observations': observations,
                    'justifie': justifie,
                    'pointe_par': user,
                }
            )
            
            if created:
                created_count += 1
            else:
                updated_count += 1
    
    print(f"\n✅ Pointages créés: {created_count}")
    print(f"✅ Pointages mis à jour: {updated_count}")
    
    # Afficher les statistiques
    print("\n" + "=" * 60)
    print("\n📊 Statistiques des présences créées:\n")
    
    from django.db.models import Count, Q, Sum
    
    stats = PresenceEnseignant.objects.aggregate(
        total=Count('id'),
        presents=Count('id', filter=Q(statut='PRESENT')),
        absents=Count('id', filter=Q(statut='ABSENT')),
        retards=Count('id', filter=Q(statut='RETARD')),
        conges=Count('id', filter=Q(statut='CONGE')),
        total_heures=Sum('heures_travaillees')
    )
    
    print(f"   Total pointages: {stats['total']}")
    print(f"   - Présents: {stats['presents']}")
    print(f"   - Absents: {stats['absents']}")
    print(f"   - Retards: {stats['retards']}")
    print(f"   - Congés: {stats['conges']}")
    print(f"   - Total heures: {stats['total_heures'] or 0}h")
    
    print("\n" + "=" * 60)
    print("\n🎉 Données de test créées avec succès!")
    print("\n📍 Accédez au système via:")
    print("   http://127.0.0.1:8001/salaires/presences/")
    print("\n📖 Consultez GUIDE_POINTAGE_ENSEIGNANTS.md pour plus d'informations.\n")

if __name__ == '__main__':
    creer_donnees_test()
