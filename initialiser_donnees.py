"""
Script d'initialisation des données de base
Crée les types de paiement, modes de paiement, classes et élèves
"""

import os
import django

# Configuration Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ecole_moderne.settings')
django.setup()

from django.contrib.auth import get_user_model
from paiements.models import TypePaiement, ModePaiement
from eleves.models import Ecole, Classe, Eleve, Responsable
from notes.models import ClasseNote
from datetime import date

User = get_user_model()

def creer_types_paiement():
    """Créer les types de paiement de base"""
    print("\n" + "=" * 70)
    print("CRÉATION DES TYPES DE PAIEMENT")
    print("=" * 70)
    
    types = [
        {'nom': 'Scolarité', 'description': 'Frais de scolarité annuels'},
        {'nom': 'Inscription', 'description': 'Frais d\'inscription'},
        {'nom': 'Réinscription', 'description': 'Frais de réinscription'},
        {'nom': 'Cantine', 'description': 'Frais de cantine'},
        {'nom': 'Transport', 'description': 'Frais de transport scolaire'},
        {'nom': 'Uniforme', 'description': 'Achat d\'uniforme scolaire'},
        {'nom': 'Fournitures', 'description': 'Fournitures scolaires'},
        {'nom': 'Activités', 'description': 'Activités parascolaires'},
    ]
    
    created_count = 0
    for type_data in types:
        type_paiement, created = TypePaiement.objects.get_or_create(
            nom=type_data['nom'],
            defaults={
                'description': type_data['description'],
                'actif': True
            }
        )
        if created:
            print(f"   ✅ Type créé: {type_paiement.nom}")
            created_count += 1
        else:
            print(f"   ℹ️  Type existant: {type_paiement.nom}")
    
    print(f"\n✅ {created_count} type(s) de paiement créé(s)")
    print(f"✅ Total types disponibles: {TypePaiement.objects.count()}")

def creer_modes_paiement():
    """Créer les modes de paiement de base"""
    print("\n" + "=" * 70)
    print("CRÉATION DES MODES DE PAIEMENT")
    print("=" * 70)
    
    modes = [
        {'nom': 'Espèces', 'description': 'Paiement en espèces'},
        {'nom': 'Chèque', 'description': 'Paiement par chèque'},
        {'nom': 'Virement Bancaire', 'description': 'Virement bancaire'},
        {'nom': 'Mobile Money', 'description': 'Paiement mobile (Orange Money, MTN, etc.)'},
        {'nom': 'Carte Bancaire', 'description': 'Paiement par carte bancaire'},
    ]
    
    created_count = 0
    for mode_data in modes:
        mode_paiement, created = ModePaiement.objects.get_or_create(
            nom=mode_data['nom'],
            defaults={
                'description': mode_data['description'],
                'actif': True
            }
        )
        if created:
            print(f"   ✅ Mode créé: {mode_paiement.nom}")
            created_count += 1
        else:
            print(f"   ℹ️  Mode existant: {mode_paiement.nom}")
    
    print(f"\n✅ {created_count} mode(s) de paiement créé(s)")
    print(f"✅ Total modes disponibles: {ModePaiement.objects.count()}")

def creer_ecole():
    """Créer ou récupérer l'école"""
    print("\n" + "=" * 70)
    print("CRÉATION/VÉRIFICATION DE L'ÉCOLE")
    print("=" * 70)
    
    ecole, created = Ecole.objects.get_or_create(
        nom="Groupe Scolaire Hadja Kanfing Dian",
        defaults={
            'adresse': 'Conakry, Guinée',
            'telephone': '+224 622 000 000',
            'email': 'contact@gshadjakanfingdian.gn',
            'etat': 'VALIDE'
        }
    )
    
    if created:
        print(f"   ✅ École créée: {ecole.nom}")
    else:
        print(f"   ℹ️  École existante: {ecole.nom}")
    
    return ecole

def creer_classes(ecole):
    """Créer les classes de base"""
    print("\n" + "=" * 70)
    print("CRÉATION DES CLASSES")
    print("=" * 70)
    
    annee_scolaire = "2024-2025"
    
    classes_data = [
        # Maternelle
        {'nom': 'Petite Section', 'niveau': 'MATERNELLE', 'effectif': 20},
        {'nom': 'Moyenne Section', 'niveau': 'MATERNELLE', 'effectif': 22},
        {'nom': 'Grande Section', 'niveau': 'MATERNELLE', 'effectif': 25},
        
        # Primaire
        {'nom': 'CP1', 'niveau': 'PRIMAIRE', 'effectif': 30},
        {'nom': 'CP2', 'niveau': 'PRIMAIRE', 'effectif': 28},
        {'nom': 'CE1', 'niveau': 'PRIMAIRE', 'effectif': 32},
        {'nom': 'CE2', 'niveau': 'PRIMAIRE', 'effectif': 30},
        {'nom': 'CM1', 'niveau': 'PRIMAIRE', 'effectif': 35},
        {'nom': 'CM2', 'niveau': 'PRIMAIRE', 'effectif': 33},
        
        # Collège
        {'nom': '7ème Année', 'niveau': 'COLLEGE', 'effectif': 40},
        {'nom': '8ème Année', 'niveau': 'COLLEGE', 'effectif': 38},
        {'nom': '9ème Année', 'niveau': 'COLLEGE', 'effectif': 36},
        {'nom': '10ème Année', 'niveau': 'COLLEGE', 'effectif': 35},
        
        # Lycée
        {'nom': '11ème Sciences', 'niveau': 'LYCEE', 'effectif': 30},
        {'nom': '11ème Lettres', 'niveau': 'LYCEE', 'effectif': 25},
        {'nom': '12ème Sciences', 'niveau': 'LYCEE', 'effectif': 28},
        {'nom': '12ème Lettres', 'niveau': 'LYCEE', 'effectif': 22},
    ]
    
    created_count = 0
    classes_creees = []
    
    for classe_data in classes_data:
        # Classe pour module eleves
        classe, created = Classe.objects.get_or_create(
            nom=classe_data['nom'],
            annee_scolaire=annee_scolaire,
            ecole=ecole,
            defaults={
                'niveau': classe_data['niveau']
            }
        )
        
        if created:
            print(f"   ✅ Classe créée: {classe.nom} ({classe.niveau})")
            created_count += 1
        else:
            print(f"   ℹ️  Classe existante: {classe.nom}")
        
        classes_creees.append(classe)
    
    print(f"\n✅ {created_count} classe(s) créée(s)")
    print(f"✅ Total classes disponibles: {Classe.objects.count()}")
    
    return classes_creees

def creer_classes_notes(ecole):
    """Créer les classes pour le module notes"""
    print("\n" + "=" * 70)
    print("CRÉATION DES CLASSES (MODULE NOTES)")
    print("=" * 70)
    
    annee_scolaire = "2024-2025"
    user = User.objects.filter(is_superuser=True).first()
    
    classes_data = [
        # Maternelle
        {'nom': 'Petite Section', 'niveau': 'MATERNELLE'},
        {'nom': 'Moyenne Section', 'niveau': 'MATERNELLE'},
        {'nom': 'Grande Section', 'niveau': 'MATERNELLE'},
        
        # Primaire
        {'nom': 'CP1', 'niveau': 'PRIMAIRE'},
        {'nom': 'CP2', 'niveau': 'PRIMAIRE'},
        {'nom': 'CE1', 'niveau': 'PRIMAIRE'},
        {'nom': 'CE2', 'niveau': 'PRIMAIRE'},
        {'nom': 'CM1', 'niveau': 'PRIMAIRE'},
        {'nom': 'CM2', 'niveau': 'PRIMAIRE'},
        
        # Secondaire
        {'nom': '7ème Année', 'niveau': 'SECONDAIRE'},
        {'nom': '8ème Année', 'niveau': 'SECONDAIRE'},
        {'nom': '9ème Année', 'niveau': 'SECONDAIRE'},
        {'nom': '10ème Année', 'niveau': 'SECONDAIRE'},
        {'nom': '11ème Sciences', 'niveau': 'SECONDAIRE'},
        {'nom': '11ème Lettres', 'niveau': 'SECONDAIRE'},
        {'nom': '12ème Sciences', 'niveau': 'SECONDAIRE'},
        {'nom': '12ème Lettres', 'niveau': 'SECONDAIRE'},
    ]
    
    created_count = 0
    
    for classe_data in classes_data:
        classe_note, created = ClasseNote.objects.get_or_create(
            nom=classe_data['nom'],
            annee_scolaire=annee_scolaire,
            ecole=ecole,
            defaults={
                'niveau': classe_data['niveau'],
                'niveau_enseignement': classe_data['niveau'],
                'actif': True,
                'cree_par': user
            }
        )
        
        if created:
            print(f"   ✅ ClasseNote créée: {classe_note.nom} ({classe_note.niveau})")
            created_count += 1
        else:
            print(f"   ℹ️  ClasseNote existante: {classe_note.nom}")
    
    print(f"\n✅ {created_count} ClasseNote(s) créée(s)")
    print(f"✅ Total ClasseNotes disponibles: {ClasseNote.objects.count()}")

def creer_eleves(classes):
    """Créer des élèves de test"""
    print("\n" + "=" * 70)
    print("CRÉATION DES ÉLÈVES")
    print("=" * 70)
    
    # Noms guinéens courants
    noms = ['DIALLO', 'BARRY', 'BAH', 'SOW', 'CAMARA', 'SYLLA', 'CONDE', 'TOURE', 
            'KEITA', 'BANGOURA', 'CISSE', 'SOUMAH', 'KABA', 'FOFANA', 'KOUROUMA']
    
    prenoms_garcons = ['Mamadou', 'Ibrahima', 'Abdoulaye', 'Mohamed', 'Ousmane', 
                       'Thierno', 'Alpha', 'Boubacar', 'Saliou', 'Amadou']
    
    prenoms_filles = ['Fatoumata', 'Aissatou', 'Mariama', 'Kadiatou', 'Hawa', 
                      'Aminata', 'Safiatou', 'Hadja', 'Ramata', 'Oumou']
    
    created_count = 0
    
    # Créer un responsable par défaut
    responsable, _ = Responsable.objects.get_or_create(
        nom='DIALLO',
        prenom='Mamadou',
        defaults={
            'telephone': '+224 622 000 000',
            'email': 'parent@example.gn',
            'adresse': 'Conakry, Guinée',
            'profession': 'Commerçant'
        }
    )
    
    print(f"   ℹ️  Responsable: {responsable.nom_complet}")
    
    # Créer 5 élèves par classe
    for classe in classes[:5]:  # Limiter aux 5 premières classes pour le test
        print(f"\n   Classe: {classe.nom}")
        
        for i in range(5):
            sexe = 'M' if i % 2 == 0 else 'F'
            nom = noms[i % len(noms)]
            prenom = prenoms_garcons[i % len(prenoms_garcons)] if sexe == 'M' else prenoms_filles[i % len(prenoms_filles)]
            
            # Générer un matricule unique
            annee = date.today().year
            numero = f"{classe.id:02d}{i+1:03d}"
            matricule = f"{annee}/{numero}"
            
            eleve, created = Eleve.objects.get_or_create(
                matricule=matricule,
                defaults={
                    'nom': nom,
                    'prenom': prenom,
                    'sexe': sexe,
                    'date_naissance': date(2010 + (i % 5), (i % 12) + 1, (i % 28) + 1),
                    'lieu_naissance': 'Conakry',
                    'classe': classe,
                    'responsable_principal': responsable,
                    'date_inscription': date.today(),
                    'statut': 'ACTIF'
                }
            )
            
            if created:
                print(f"      ✅ Élève créé: {eleve.matricule} - {eleve.nom_complet}")
                created_count += 1
            else:
                print(f"      ℹ️  Élève existant: {eleve.matricule}")
    
    print(f"\n✅ {created_count} élève(s) créé(s)")
    print(f"✅ Total élèves disponibles: {Eleve.objects.count()}")

def main():
    """Fonction principale"""
    print("\n" + "=" * 70)
    print("INITIALISATION DES DONNÉES DE BASE")
    print("=" * 70)
    
    try:
        # 1. Types de paiement
        creer_types_paiement()
        
        # 2. Modes de paiement
        creer_modes_paiement()
        
        # 3. École
        ecole = creer_ecole()
        
        # 4. Classes (module eleves)
        classes = creer_classes(ecole)
        
        # 5. Classes (module notes)
        creer_classes_notes(ecole)
        
        # 6. Élèves
        creer_eleves(classes)
        
        # Résumé final
        print("\n" + "=" * 70)
        print("RÉSUMÉ FINAL")
        print("=" * 70)
        print(f"✅ Types de paiement: {TypePaiement.objects.count()}")
        print(f"✅ Modes de paiement: {ModePaiement.objects.count()}")
        print(f"✅ Écoles: {Ecole.objects.count()}")
        print(f"✅ Classes (eleves): {Classe.objects.count()}")
        print(f"✅ Classes (notes): {ClasseNote.objects.count()}")
        print(f"✅ Élèves: {Eleve.objects.count()}")
        print(f"✅ Responsables: {Responsable.objects.count()}")
        
        print("\n" + "=" * 70)
        print("✅ INITIALISATION TERMINÉE AVEC SUCCÈS !")
        print("=" * 70)
        
        print("\n📝 PROCHAINES ÉTAPES:")
        print("   1. Accéder à l'application: http://127.0.0.1:8000")
        print("   2. Se connecter avec un compte admin")
        print("   3. Vérifier les données créées")
        print("   4. Commencer à utiliser l'application")
        
    except Exception as e:
        print(f"\n❌ ERREUR: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    main()
