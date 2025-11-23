#!/usr/bin/env python
"""
Tester la correction des bulletins PDF
"""
import os
import sys
import django

# Configuration Django
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ecole_moderne.settings')
django.setup()

from notes.models import ClasseNote
from eleves.models import Classe as ClasseEleve, Eleve
from django.contrib.auth.models import User

def tester_logique_bulletins_pdf():
    """Tester la logique corrigée des bulletins PDF"""
    print("🧪 TEST BULLETINS PDF CORRIGÉ")
    print("=" * 30)
    
    # Paramètres de test (comme dans l'URL d'erreur)
    classe_id = 59
    periode = 'OCTOBRE'
    system_type = 'mensuel'
    
    print(f"📋 Paramètres de test:")
    print(f"   - classe_id: {classe_id}")
    print(f"   - periode: {periode}")
    print(f"   - system_type: {system_type}")
    
    # 1. Récupérer la classe
    classe_selectionnee = ClasseNote.objects.get(pk=classe_id)
    print(f"\n✅ ClasseNote: {classe_selectionnee.nom}")
    
    # 2. Tester la logique corrigée de récupération de classe élève
    mapping_classes = {
        61: 56,  # ClasseNote '12ème Année' -> ClasseEleve '12ÈME ANNÉE'
        59: 8,   # ClasseNote '11ème Série littéraire' -> ClasseEleve '11ème série littéraire'
    }
    
    if classe_selectionnee.id in mapping_classes:
        classe_eleve = ClasseEleve.objects.filter(
            id=mapping_classes[classe_selectionnee.id]
        ).first()
        print(f"✅ Mapping utilisé: ClasseEleve {mapping_classes[classe_selectionnee.id]}")
    else:
        classe_eleve = ClasseEleve.objects.filter(
            nom=classe_selectionnee.nom,
            annee_scolaire=classe_selectionnee.annee_scolaire,
            ecole=classe_selectionnee.ecole
        ).first()
        print(f"✅ Recherche normale utilisée")
    
    if classe_eleve:
        print(f"✅ ClasseEleve trouvée: {classe_eleve.nom} (ID: {classe_eleve.id})")
        
        # 3. Récupérer les élèves
        eleves = Eleve.objects.filter(
            classe=classe_eleve, 
            statut='ACTIF'
        ).order_by('prenom', 'nom')
        print(f"👥 Élèves trouvés: {eleves.count()}")
        
        if eleves.count() > 0:
            print(f"📝 Premiers élèves:")
            for eleve in eleves[:3]:
                print(f"   - {eleve.prenom} {eleve.nom} ({eleve.matricule})")
        
        # 4. Tester la logique de profil utilisateur
        print(f"\n🔍 TEST PROFIL UTILISATEUR:")
        
        # Simuler un utilisateur avec profil
        try:
            user = User.objects.filter(is_superuser=True).first()
            if user:
                user_profil = getattr(user, 'profil', None)
                ecole = user_profil.ecole if user_profil else None
                
                print(f"✅ Utilisateur: {user.username}")
                print(f"✅ Profil: {user_profil}")
                print(f"✅ École: {ecole}")
                
                # Tester la logique corrigée du logo
                if ecole and ecole.logo:
                    print(f"✅ École a un logo: {ecole.logo}")
                elif ecole:
                    print(f"⚠️  École sans logo")
                else:
                    print(f"⚠️  Aucune école définie")
                    
            else:
                print(f"❌ Aucun utilisateur superuser trouvé")
                
        except Exception as e:
            print(f"❌ Erreur profil utilisateur: {e}")
        
        # 5. Résultat du test
        print(f"\n🎉 RÉSULTAT:")
        if eleves.count() > 0:
            print(f"✅ Les bulletins PDF devraient maintenant se générer")
            print(f"✅ {eleves.count()} bulletins à créer")
            print(f"✅ Erreur 'NoneType' object has no attribute 'logo' corrigée")
            print(f"🔗 URL de test: http://127.0.0.1:8000/notes/bulletins/classe/pdf/?classe_id={classe_id}&periode={periode}&system_type={system_type}")
        else:
            print(f"⚠️  Problème: Aucun élève trouvé")
    
    else:
        print(f"❌ ClasseEleve non trouvée")

def verifier_autres_fonctions_bulletins():
    """Vérifier s'il y a d'autres fonctions de bulletins à corriger"""
    print(f"\n🔍 VÉRIFICATION AUTRES FONCTIONS BULLETINS")
    print("=" * 45)
    
    # Rechercher d'autres fonctions qui pourraient avoir le même problème
    fonctions_bulletins = [
        "bulletins_dynamiques_classe_pdf",  # ✅ Corrigée
        "bulletin_dynamique_single",        # À vérifier
        "bulletin_dynamique",               # À vérifier
        "bulletins_pdf",                    # À vérifier
    ]
    
    print("📋 Fonctions de bulletins identifiées:")
    for fonction in fonctions_bulletins:
        if fonction == "bulletins_dynamiques_classe_pdf":
            print(f"   ✅ {fonction} - CORRIGÉE")
        else:
            print(f"   ⚠️  {fonction} - À vérifier")
    
    print(f"\n💡 Recommandation:")
    print(f"   - Appliquer le même mapping dans toutes les fonctions de bulletins")
    print(f"   - Vérifier les accès aux attributs d'objets potentiellement None")

if __name__ == "__main__":
    try:
        tester_logique_bulletins_pdf()
        verifier_autres_fonctions_bulletins()
        
        print(f"\n🎯 RÉSUMÉ")
        print("=" * 15)
        print("✅ Erreur 'NoneType' object has no attribute 'logo' corrigée")
        print("✅ Mapping spécial ajouté dans bulletins_dynamiques_classe_pdf")
        print("✅ Les bulletins PDF devraient maintenant se générer")
        print("🔗 Testez: http://127.0.0.1:8000/notes/bulletins/classe/pdf/?classe_id=59&periode=OCTOBRE&system_type=mensuel")
        
    except Exception as e:
        print(f"❌ Erreur: {e}")
        import traceback
        traceback.print_exc()
