#!/usr/bin/env python
"""
Script pour créer les matières manquantes pour la classe 11ème Série scientifique
"""

import os
import sys
import django

# Configuration Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ecole_moderne.settings')
django.setup()

from notes.models import MatiereNote, ClasseNote
from django.contrib.auth import get_user_model

User = get_user_model()

def creer_matieres_11_scientifique():
    """Créer les matières pour 11ème Série scientifique"""
    
    print("\n" + "="*80)
    print("CRÉATION DES MATIÈRES POUR 11ÈME SÉRIE SCIENTIFIQUE")
    print("="*80)
    
    # Rechercher la classe cible
    try:
        classe = ClasseNote.objects.get(id=60)  # 11ème Série scientifique
        print(f"✅ Classe trouvée: {classe.nom}")
    except ClasseNote.DoesNotExist:
        print("❌ Classe avec ID 60 non trouvée")
        return
    
    # Vérifier si des matières existent déjà
    matieres_existantes = MatiereNote.objects.filter(classe=classe)
    if matieres_existantes.exists():
        print(f"⚠️ {matieres_existantes.count()} matières existent déjà:")
        for mat in matieres_existantes:
            print(f"  - {mat.nom}")
        
        reponse = input("\nVoulez-vous continuer et ajouter les matières manquantes? (o/n): ")
        if reponse.lower() != 'o':
            print("❌ Annulé")
            return
    
    # Liste des matières à créer pour 11ème Série scientifique
    # Coefficients adaptés pour le profil scientifique
    matieres_a_creer = [
        ('ANGLAIS', 1.00),
        ('BIOLOGIE', 2.00),  # Plus important en scientifique
        ('CHIMIE', 3.00),    # Matière principale en scientifique
        ('ECONOMIE', 1.00),  
        ('FRANÇAIS', 2.00),  # Moins important qu'en littéraire
        ('GÉOGRAPHIE', 1.00),
        ('HISTOIRE', 1.00),
        ('MATHÉMATIQUE', 4.00),  # Matière principale en scientifique
        ('PHILOSOPHIE', 1.00),
        ('PHYSIQUE', 3.00),  # Matière principale en scientifique
        ('ECM', 1.00),       # Éducation civique et morale
        ('EPS', 1.00),       # Éducation physique et sportive
    ]
    
    # Récupérer un utilisateur admin pour l'attribution
    try:
        admin_user = User.objects.filter(is_superuser=True).first()
        if not admin_user:
            admin_user = User.objects.first()
    except:
        admin_user = None
    
    print(f"\n📝 Création des matières...")
    print("-" * 40)
    
    matieres_creees = 0
    matieres_ignorees = 0
    
    for nom_matiere, coefficient in matieres_a_creer:
        # Vérifier si la matière existe déjà
        existe = MatiereNote.objects.filter(
            classe=classe,
            nom=nom_matiere
        ).exists()
        
        if existe:
            print(f"  ⏭️ {nom_matiere} existe déjà - ignorée")
            matieres_ignorees += 1
            continue
        
        try:
            # Créer la matière
            matiere = MatiereNote.objects.create(
                nom=nom_matiere,
                classe=classe,
                coefficient=coefficient,
                ecole=classe.ecole,
                actif=True,
                niveau_enseignement=classe.niveau_enseignement,
                cree_par=admin_user
            )
            print(f"  ✅ {nom_matiere} créée (Coef: {coefficient})")
            matieres_creees += 1
            
        except Exception as e:
            print(f"  ❌ Erreur pour {nom_matiere}: {e}")
    
    # Résumé
    print("\n" + "="*80)
    print("RÉSUMÉ:")
    print("-" * 40)
    print(f"✅ {matieres_creees} matières créées")
    print(f"⏭️ {matieres_ignorees} matières ignorées (existaient déjà)")
    
    # Vérifier le résultat final
    total_matieres = MatiereNote.objects.filter(classe=classe).count()
    print(f"\n📊 Total des matières pour {classe.nom}: {total_matieres}")
    
    print("\n" + "="*80)
    print("✅ TERMINÉ!")
    print("Les matières ont été créées. Maintenant vous pouvez:")
    print("1. Créer des évaluations pour ces matières")
    print("2. Saisir les notes des élèves")
    print("3. Le bulletin affichera correctement les notes")
    print("="*80)

if __name__ == '__main__':
    import sys
    
    print("\n⚠️ ATTENTION: Ce script va créer les matières pour la classe 11ème Série scientifique")
    print("Assurez-vous d'avoir fait une sauvegarde de votre base de données.")
    
    reponse = input("\nVoulez-vous continuer? (o/n): ")
    if reponse.lower() == 'o':
        creer_matieres_11_scientifique()
    else:
        print("❌ Annulé")
