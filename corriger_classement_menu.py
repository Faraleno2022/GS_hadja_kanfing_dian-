#!/usr/bin/env python
"""
Script principal pour corriger les classements - Interface simplifiée
"""

import os
import sys
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ecole_moderne.settings')
django.setup()

def afficher_menu():
    """Afficher le menu principal"""
    print("🔧 CORRECTION CLASSEMENT - MENU PRINCIPAL")
    print("=" * 50)
    print("1. 11 SÉRIE LITTÉRAIRE (ID: 4)")
    print("2. 10ÈME ANNÉE (A) (ID: 14)")
    print("3. 10ÈME ANNÉE (B) (ID: 15)")
    print("4. Toutes les classes")
    print("5. Classe personnalisée (par ID)")
    print("6. Classe personnalisée (par nom)")
    print("0. Quitter")
    print("=" * 50)

def corriger_classe_id(classe_id, nom_classe):
    """Corriger une classe spécifique"""
    try:
        from corriger_classement_classe_specifique import corriger_classement_classe_specifique
        print(f"\n🔧 Correction de : {nom_classe}")
        corriger_classement_classe_specifique(classe_id=classe_id)
        print(f"\n✅ {nom_classe} terminée !")
    except Exception as e:
        print(f"❌ Erreur : {str(e)}")

def main():
    """Fonction principale"""
    
    # Si arguments passés en ligne de commande
    if len(sys.argv) > 1:
        arg = sys.argv[1].lower()
        
        if arg == "4" or arg == "litteraire":
            corriger_classe_id(4, "11 SÉRIE LITTÉRAIRE")
        elif arg == "14" or arg == "10a":
            corriger_classe_id(14, "10ÈME ANNÉE (A)")
        elif arg == "15" or arg == "10b":
            corriger_classe_id(15, "10ÈME ANNÉE (B)")
        elif arg == "tout" or arg == "toutes":
            from corriger_classement_classe_specifique import corriger_classement_classe_specifique
            print("\n🔧 Correction de TOUTES les classes...")
            corriger_classement_classe_specifique(classe_nom="TOUTES")
        else:
            print("Argument non reconnu. Options : 4, 14, 15, tout, litteraire, 10a, 10b, toutes")
        return
    
    # Mode interactif
    while True:
        afficher_menu()
        
        try:
            choix = input("\nChoisissez une option (0-6): ").strip()
            
            if choix == "0":
                print("👋 Au revoir !")
                break
            elif choix == "1":
                corriger_classe_id(4, "11 SÉRIE LITTÉRAIRE")
            elif choix == "2":
                corriger_classe_id(14, "10ÈME ANNÉE (A)")
            elif choix == "3":
                corriger_classe_id(15, "10ÈME ANNÉE (B)")
            elif choix == "4":
                from corriger_classement_classe_specifique import corriger_classement_classe_specifique
                print("\n🔧 Correction de TOUTES les classes...")
                corriger_classement_classe_specifique(classe_nom="TOUTES")
            elif choix == "5":
                try:
                    classe_id = int(input("Entrez l'ID de la classe: "))
                    corriger_classe_id(classe_id, f"Classe {classe_id}")
                except ValueError:
                    print("❌ ID invalide")
            elif choix == "6":
                nom_classe = input("Entrez le nom de la classe: ")
                from corriger_classement_classe_specifique import corriger_classement_classe_specifique
                corriger_classement_classe_specifique(classe_nom=nom_classe)
            else:
                print("❌ Option invalide")
            
            input("\nAppuyez sur Entrée pour continuer...")
            
        except KeyboardInterrupt:
            print("\n👋 Interruption. Au revoir !")
            break
        except Exception as e:
            print(f"❌ Erreur : {str(e)}")
            input("\nAppuyez sur Entrée pour continuer...")

if __name__ == "__main__":
    main()
