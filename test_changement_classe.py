"""
Script de test pour vérifier le changement automatique de matricule lors du changement de classe
"""
import os
import django

# Configuration Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ecole_moderne.settings')
django.setup()

from eleves.models import Eleve, Classe, Ecole, Responsable
from django.contrib.auth import get_user_model

User = get_user_model()

def test_changement_classe():
    print("=" * 70)
    print("TEST: Changement automatique de matricule lors du changement de classe")
    print("=" * 70)
    
    # Récupérer un élève existant
    try:
        eleve = Eleve.objects.select_related('classe', 'classe__ecole').first()
        if not eleve:
            print("❌ Aucun élève trouvé dans la base de données")
            return
        
        print(f"\n📋 Élève sélectionné: {eleve.nom_complet}")
        print(f"   Classe actuelle: {eleve.classe.nom}")
        print(f"   Matricule actuel: {eleve.matricule}")
        
        # Récupérer une autre classe de la même école
        autre_classe = Classe.objects.filter(
            ecole=eleve.classe.ecole
        ).exclude(id=eleve.classe.id).first()
        
        if not autre_classe:
            print(f"\n❌ Aucune autre classe trouvée dans l'école {eleve.classe.ecole.nom}")
            return
        
        print(f"\n🔄 Changement vers: {autre_classe.nom}")
        
        # Sauvegarder l'ancien matricule
        ancien_matricule = eleve.matricule
        ancienne_classe = eleve.classe.nom
        
        # Changer la classe
        eleve.classe = autre_classe
        eleve.save()
        
        # Recharger l'élève depuis la base de données
        eleve.refresh_from_db()
        
        print(f"\n✅ Changement effectué!")
        print(f"   Ancienne classe: {ancienne_classe}")
        print(f"   Nouvelle classe: {eleve.classe.nom}")
        print(f"   Ancien matricule: {ancien_matricule}")
        print(f"   Nouveau matricule: {eleve.matricule}")
        
        # Vérifier que le matricule a changé
        if ancien_matricule != eleve.matricule:
            print(f"\n✅ SUCCESS: Le matricule a été automatiquement mis à jour!")
            
            # Vérifier l'historique
            from eleves.models import HistoriqueEleve
            historique = HistoriqueEleve.objects.filter(
                eleve=eleve,
                action='CHANGEMENT_CLASSE'
            ).order_by('-date_action').first()
            
            if historique:
                print(f"\n📝 Historique créé:")
                print(f"   Date: {historique.date_action.strftime('%d/%m/%Y %H:%M')}")
                print(f"   Description: {historique.description}")
            else:
                print(f"\n⚠️  Aucun historique de changement de classe trouvé")
        else:
            print(f"\n⚠️  WARNING: Le matricule n'a pas changé")
            print(f"   Cela peut être normal si le code de classe est identique")
        
    except Exception as e:
        print(f"\n❌ ERREUR: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "=" * 70)

if __name__ == "__main__":
    test_changement_classe()
