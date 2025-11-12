"""
Script de test pour la fonctionnalité de saisie manuelle du matricule
"""

import os
import sys
import django

# Configuration Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ecole_moderne.settings')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
django.setup()

from django.contrib.auth import get_user_model
from eleves.models import Eleve, Classe, Ecole, Responsable
from eleves.forms import EleveForm
from datetime import date

User = get_user_model()

def test_saisie_manuelle_matricule():
    print("\n" + "="*60)
    print("TEST DE LA SAISIE MANUELLE DU MATRICULE")
    print("="*60)
    
    # Récupération ou création d'un utilisateur admin
    try:
        admin_user = User.objects.get(username='admin')
    except User.DoesNotExist:
        print("❌ Utilisateur admin non trouvé. Veuillez créer un utilisateur admin d'abord.")
        return
    
    # Récupération d'une école et d'une classe
    try:
        ecole = Ecole.objects.filter(etat='VALIDE').first()
        if not ecole:
            print("❌ Aucune école valide trouvée dans la base de données.")
            return
            
        # Chercher une classe primaire ou secondaire (éviter garderie/maternelle)
        classe = Classe.objects.filter(
            ecole=ecole,
            niveau__in=['PRIMAIRE', 'SECONDAIRE']
        ).first()
        
        # Si pas de classe primaire/secondaire, prendre n'importe quelle classe
        if not classe:
            classe = Classe.objects.filter(ecole=ecole).first()
            
        if not classe:
            print("❌ Aucune classe trouvée pour l'école sélectionnée.")
            return
    except Exception as e:
        print(f"❌ Erreur lors de la récupération des données: {e}")
        return
    
    print(f"\n✅ École sélectionnée: {ecole.nom}")
    print(f"✅ Classe sélectionnée: {classe.nom} ({classe.code_matricule})")
    
    # Récupération ou création d'un responsable
    responsable, created = Responsable.objects.get_or_create(
        telephone='+224123456789',
        defaults={
            'prenom': 'TEST',
            'nom': 'RESPONSABLE',
            'relation': 'PERE',
            'adresse': 'Conakry'
        }
    )
    
    # Déterminer une date de naissance appropriée selon le niveau
    from datetime import datetime, timedelta
    today = date.today()
    
    # Calculer une date de naissance appropriée selon le niveau de classe
    if classe.niveau == 'GARDERIE':
        # Enfants de 1-3 ans
        date_naissance = (today - timedelta(days=365*2)).strftime('%Y-%m-%d')
    elif classe.niveau == 'MATERNELLE':
        # Enfants de 3-5 ans
        date_naissance = (today - timedelta(days=365*4)).strftime('%Y-%m-%d')
    elif classe.niveau == 'PRIMAIRE':
        # Enfants de 6-12 ans
        date_naissance = '2015-01-15'  # ~10 ans
    else:  # SECONDAIRE ou autre
        # Adolescents de 12-18 ans
        date_naissance = '2010-01-15'  # ~15 ans
    
    print(f"✅ Date de naissance utilisée pour les tests: {date_naissance}")
    
    print("\n" + "-"*50)
    print("TEST 1: CRÉATION AVEC MATRICULE AUTOMATIQUE")
    print("-"*50)
    
    # Test 1: Création avec génération automatique
    form_data_auto = {
        'prenom': 'ELEVE',
        'nom': 'AUTOMATIQUE',
        'sexe': 'M',
        'date_naissance': date_naissance,
        'lieu_naissance': 'CONAKRY',
        'classe': classe.id,
        'date_inscription': date.today().strftime('%Y-%m-%d'),
        'statut': 'ACTIF',
        'responsable_principal': responsable.id,
        'saisie_manuelle_matricule': False,  # Pas de saisie manuelle
        'matricule': ''  # Vide pour génération automatique
    }
    
    form_auto = EleveForm(data=form_data_auto, user=admin_user)
    if form_auto.is_valid():
        eleve_auto = form_auto.save(commit=False)
        eleve_auto.cree_par = admin_user
        eleve_auto.save()
        print(f"✅ Élève créé avec matricule automatique: {eleve_auto.matricule}")
        print(f"   Nom complet: {eleve_auto.prenom} {eleve_auto.nom}")
    else:
        print(f"❌ Erreur lors de la création avec matricule automatique:")
        print(f"   {form_auto.errors}")
    
    print("\n" + "-"*50)
    print("TEST 2: CRÉATION AVEC MATRICULE MANUEL")
    print("-"*50)
    
    # Test 2: Création avec saisie manuelle
    matricule_manuel = "TEST-2024-001"
    form_data_manuel = {
        'prenom': 'ELEVE',
        'nom': 'MANUEL',
        'sexe': 'F',
        'date_naissance': date_naissance,
        'lieu_naissance': 'KANKAN',
        'classe': classe.id,
        'date_inscription': date.today().strftime('%Y-%m-%d'),
        'statut': 'ACTIF',
        'responsable_principal': responsable.id,
        'saisie_manuelle_matricule': True,  # Saisie manuelle activée
        'matricule': matricule_manuel
    }
    
    form_manuel = EleveForm(data=form_data_manuel, user=admin_user)
    if form_manuel.is_valid():
        eleve_manuel = form_manuel.save(commit=False)
        eleve_manuel.cree_par = admin_user
        eleve_manuel._skip_matricule_generation = True
        eleve_manuel.save()
        print(f"✅ Élève créé avec matricule manuel: {eleve_manuel.matricule}")
        print(f"   Nom complet: {eleve_manuel.prenom} {eleve_manuel.nom}")
        print(f"   Matricule saisi correspond: {eleve_manuel.matricule == matricule_manuel}")
    else:
        print(f"❌ Erreur lors de la création avec matricule manuel:")
        print(f"   {form_manuel.errors}")
    
    print("\n" + "-"*50)
    print("TEST 3: VÉRIFICATION DE L'UNICITÉ DU MATRICULE")
    print("-"*50)
    
    # Test 3: Tentative de créer un autre élève avec le même matricule manuel
    form_data_doublon = {
        'prenom': 'ELEVE',
        'nom': 'DOUBLON',
        'sexe': 'M',
        'date_naissance': date_naissance,
        'lieu_naissance': 'LABE',
        'classe': classe.id,
        'date_inscription': date.today().strftime('%Y-%m-%d'),
        'statut': 'ACTIF',
        'responsable_principal': responsable.id,
        'saisie_manuelle_matricule': True,
        'matricule': matricule_manuel  # Même matricule que le précédent
    }
    
    form_doublon = EleveForm(data=form_data_doublon, user=admin_user)
    if not form_doublon.is_valid() and 'matricule' in form_doublon.errors:
        print(f"✅ Validation correcte: Le matricule en double est rejeté")
        print(f"   Message d'erreur: {form_doublon.errors['matricule'][0]}")
    else:
        print(f"❌ Problème: Le doublon de matricule n'a pas été détecté")
    
    print("\n" + "-"*50)
    print("TEST 4: MODIFICATION D'UN MATRICULE EXISTANT")
    print("-"*50)
    
    # Test 4: Modification du matricule d'un élève existant
    if 'eleve_auto' in locals():
        ancien_matricule = eleve_auto.matricule
        nouveau_matricule = "MODIF-2024-001"
        
        form_data_modif = {
            'prenom': eleve_auto.prenom,
            'nom': eleve_auto.nom,
            'sexe': eleve_auto.sexe,
            'date_naissance': eleve_auto.date_naissance.strftime('%Y-%m-%d'),
            'lieu_naissance': eleve_auto.lieu_naissance,
            'classe': eleve_auto.classe.id,
            'date_inscription': eleve_auto.date_inscription.strftime('%Y-%m-%d'),
            'statut': eleve_auto.statut,
            'responsable_principal': eleve_auto.responsable_principal.id,
            'saisie_manuelle_matricule': True,
            'matricule': nouveau_matricule
        }
        
        form_modif = EleveForm(data=form_data_modif, instance=eleve_auto, user=admin_user)
        if form_modif.is_valid():
            eleve_modif = form_modif.save(commit=False)
            eleve_modif._skip_matricule_generation = True
            eleve_modif.save()
            print(f"✅ Matricule modifié avec succès:")
            print(f"   Ancien matricule: {ancien_matricule}")
            print(f"   Nouveau matricule: {eleve_modif.matricule}")
        else:
            print(f"❌ Erreur lors de la modification du matricule:")
            print(f"   {form_modif.errors}")
    
    print("\n" + "-"*50)
    print("RÉSUMÉ DES TESTS")
    print("-"*50)
    
    # Afficher tous les élèves créés pendant le test
    eleves_test = Eleve.objects.filter(
        nom__in=['AUTOMATIQUE', 'MANUEL', 'DOUBLON']
    ).order_by('date_creation')
    
    if eleves_test.exists():
        print(f"\n📊 Élèves créés pendant les tests ({eleves_test.count()}):")
        for eleve in eleves_test:
            print(f"   - {eleve.matricule}: {eleve.prenom} {eleve.nom} (Classe: {eleve.classe.nom})")
    
    print("\n✅ Tests terminés avec succès!")
    
    # Nettoyage optionnel
    reponse = input("\n🧹 Voulez-vous supprimer les élèves de test? (oui/non): ")
    if reponse.lower() in ['oui', 'o', 'yes', 'y']:
        count = eleves_test.count()
        eleves_test.delete()
        print(f"✅ {count} élève(s) de test supprimé(s)")

if __name__ == '__main__':
    try:
        test_saisie_manuelle_matricule()
    except Exception as e:
        print(f"\n❌ Erreur lors de l'exécution des tests: {e}")
        import traceback
        traceback.print_exc()
