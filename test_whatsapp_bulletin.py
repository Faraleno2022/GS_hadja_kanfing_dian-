#!/usr/bin/env python
"""
Script de test pour la fonctionnalité WhatsApp Bulletin
"""

import os
import sys
import django

# Configuration Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'myschool.settings')
django.setup()

from django.contrib.auth.models import User
from eleves.models import Eleve, Classe, Responsable
from notes.whatsapp_bulletin import whatsapp_sender

def test_whatsapp_bulletin():
    """Test de la fonctionnalité d'envoi de bulletin par WhatsApp"""
    
    print("🧪 Test de la fonctionnalité WhatsApp Bulletin")
    print("=" * 50)
    
    # 1. Trouver un élève avec un responsable ayant un téléphone
    eleves_avec_telephone = Eleve.objects.filter(
        responsable_principal__telephone__isnull=False,
        actif=True
    ).select_related('responsable_principal', 'classe')
    
    if not eleves_avec_telephone.exists():
        print("❌ Aucun élève trouvé avec un numéro de téléphone de responsable")
        return
    
    eleve = eleves_avec_telephone.first()
    print(f"✅ Élève sélectionné: {eleve.prenom} {eleve.nom}")
    print(f"📞 Téléphone parent: {eleve.responsable_principal.telephone}")
    print(f"🏫 Classe: {eleve.classe.nom}")
    
    # 2. Test de récupération du téléphone
    telephone = whatsapp_sender._get_telephone_parent(eleve)
    print(f"\n📱 Test récupération téléphone:")
    print(f"   Résultat: {telephone}")
    
    if not telephone:
        print("❌ Aucun téléphone récupéré")
        return
    
    # 3. Test de génération du message
    print(f"\n📝 Test génération message:")
    message = whatsapp_sender._generer_message_whatsapp(eleve, 'TRIMESTRE_1', 'trimestre')
    print("   Message généré:")
    print("   " + "─" * 40)
    for ligne in message.split('\n'):
        print(f"   {ligne}")
    print("   " + "─" * 40)
    
    # 4. Test de génération PDF (simulation)
    print(f"\n📄 Test génération PDF:")
    try:
        pdf_path, filename = whatsapp_sender.generer_bulletin_pdf(
            eleve.id, eleve.classe.id, 'TRIMESTRE_1', 'trimestre'
        )
        
        if pdf_path:
            print(f"   ✅ PDF généré: {filename}")
            print(f"   📁 Chemin: {pdf_path}")
            
            # Vérifier la taille du fichier
            if os.path.exists(pdf_path):
                taille = os.path.getsize(pdf_path)
                print(f"   📊 Taille: {taille} octets")
            else:
                print(f"   ❌ Fichier PDF non trouvé")
        else:
            print(f"   ❌ Échec de génération PDF")
            
    except Exception as e:
        print(f"   ❌ Erreur génération PDF: {e}")
    
    # 5. Test d'envoi complet (simulation)
    print(f"\n📤 Test envoi complet (simulation):")
    
    try:
        # Créer un utilisateur de test
        user_test, created = User.objects.get_or_create(
            username='test_whatsapp',
            defaults={'first_name': 'Test', 'last_name': 'WhatsApp'}
        )
        
        result = whatsapp_sender.envoyer_whatsapp_bulletin(
            eleve.id, eleve.classe.id, 'TRIMESTRE_1', 'trimestre', user_test
        )
        
        print(f"   Résultat: {result}")
        
        if result['success']:
            print(f"   ✅ Envoi simulé avec succès")
            print(f"   📞 Numéro: {result.get('telephone', 'N/A')}")
        else:
            print(f"   ❌ Échec: {result.get('error', 'Erreur inconnue')}")
            
    except Exception as e:
        print(f"   ❌ Erreur envoi: {e}")
    
    # 6. Statistiques
    print(f"\n📊 Statistiques:")
    total_eleves = Eleve.objects.filter(actif=True).count()
    eleves_avec_tel = Eleve.objects.filter(
        responsable_principal__telephone__isnull=False,
        actif=True
    ).count()
    
    pourcentage = (eleves_avec_tel / total_eleves * 100) if total_eleves > 0 else 0
    
    print(f"   Total élèves actifs: {total_eleves}")
    print(f"   Élèves avec téléphone parent: {eleves_avec_tel}")
    print(f"   Couverture: {pourcentage:.1f}%")
    
    print(f"\n🎉 Test terminé!")

def lister_eleves_sans_telephone():
    """Liste les élèves sans numéro de téléphone de responsable"""
    
    print("\n📋 Élèves sans numéro de téléphone:")
    print("=" * 40)
    
    eleves_sans_tel = Eleve.objects.filter(
        responsable_principal__telephone__isnull=True,
        actif=True
    ).select_related('responsable_principal', 'classe')
    
    if not eleves_sans_tel.exists():
        print("✅ Tous les élèves ont un numéro de téléphone")
        return
    
    for eleve in eleves_sans_tel[:10]:  # Limiter à 10
        print(f"   - {eleve.prenom} {eleve.nom} ({eleve.classe.nom})")
        if eleve.responsable_principal:
            print(f"     Responsable: {eleve.responsable_principal.nom_complet}")
        else:
            print(f"     ❌ Aucun responsable principal")
    
    if eleves_sans_tel.count() > 10:
        print(f"   ... et {eleves_sans_tel.count() - 10} autres")

if __name__ == "__main__":
    try:
        test_whatsapp_bulletin()
        lister_eleves_sans_telephone()
    except Exception as e:
        print(f"❌ Erreur lors du test: {e}")
        import traceback
        traceback.print_exc()
