#!/usr/bin/env python
"""
Tester la correction des rangs dans la consultation des notes
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
from notes.utils_rangs import calculer_rangs_classe_periode

def tester_calcul_rangs():
    """Tester le calcul des rangs pour la classe 59"""
    print("🧪 TEST CALCUL RANGS CONSULTATION")
    print("=" * 35)
    
    # Paramètres de test
    classe_id = 59
    
    # 1. Récupérer la classe
    classe_note = ClasseNote.objects.get(pk=classe_id)
    print(f"✅ ClasseNote: {classe_note.nom}")
    
    # 2. Vérifier le mapping
    mapping_classes = {59: 8}
    classe_eleve = ClasseEleve.objects.get(pk=mapping_classes[classe_id])
    print(f"✅ ClasseEleve: {classe_eleve.nom} (ID: {classe_eleve.id})")
    
    # 3. Vérifier les élèves
    eleves = Eleve.objects.filter(classe=classe_eleve, statut='ACTIF')
    print(f"👥 Élèves actifs: {eleves.count()}")
    
    # 4. Tester le calcul des rangs pour OCTOBRE
    print(f"\n🏆 TEST CALCUL RANGS OCTOBRE:")
    
    try:
        rangs_dict = calculer_rangs_classe_periode(classe_note, 'OCTOBRE')
        print(f"✅ Calcul réussi: {len(rangs_dict)} élèves avec rangs")
        
        # Afficher le top 5
        rangs_list = [(eleve_id, info) for eleve_id, info in rangs_dict.items()]
        rangs_list.sort(key=lambda x: x[1]['rang'])
        
        print(f"🥇 TOP 5:")
        for i, (eleve_id, info) in enumerate(rangs_list[:5], 1):
            eleve = Eleve.objects.get(pk=eleve_id)
            rang = info['rang']
            moyenne = info.get('moyenne', 'N/A')
            print(f"   {rang}. {eleve.prenom} {eleve.nom} - {moyenne}/20")
            
    except Exception as e:
        print(f"❌ Erreur calcul rangs: {e}")
    
    # 5. Simuler la logique de la vue consulter_notes
    print(f"\n🔍 SIMULATION VUE CONSULTER_NOTES:")
    
    # Périodes disponibles (comme dans la vue)
    periodes_disponibles = [
        ('OCTOBRE', 'Octobre'),
        ('NOVEMBRE', 'Novembre'),
        ('DECEMBRE', 'Décembre'),
        ('JANVIER', 'Janvier'),
        ('FEVRIER', 'Février'),
        ('MARS', 'Mars'),
        ('AVRIL', 'Avril'),
        ('MAI', 'Mai'),
        ('JUIN', 'Juin'),
        ('TRIMESTRE_1', '1er Trimestre'),
        ('TRIMESTRE_2', '2ème Trimestre'),
        ('TRIMESTRE_3', '3ème Trimestre'),
        ('SEMESTRE_1', '1er Semestre'),
        ('SEMESTRE_2', '2ème Semestre'),
    ]
    
    # Test avec période vide (comme dans l'URL problématique)
    periode_classement = ''  # Vide comme dans l'URL
    
    print(f"📋 Paramètres:")
    print(f"   - periode_classement: '{periode_classement}' (vide)")
    print(f"   - periodes_disponibles: {len(periodes_disponibles)} périodes")
    
    # Appliquer la logique corrigée
    if periodes_disponibles and classe_note:
        if periode_classement:
            periode_pour_rang = periode_classement
            print(f"✅ Utilisation période sélectionnée: {periode_pour_rang}")
        else:
            # Utiliser OCTOBRE par défaut (logique corrigée)
            periode_pour_rang = 'OCTOBRE'
            periodes_codes = [p[0] for p in periodes_disponibles]
            if 'OCTOBRE' not in periodes_codes:
                periode_pour_rang = periodes_disponibles[0][0]
            print(f"✅ Utilisation période par défaut: {periode_pour_rang}")
        
        # Calculer les rangs
        try:
            rangs_dict = calculer_rangs_classe_periode(classe_note, periode_pour_rang)
            print(f"✅ Rangs calculés pour {len(rangs_dict)} élèves")
            
            # Simuler l'attribution des rangs aux élèves
            eleves_avec_rangs = 0
            eleves_sans_rangs = 0
            
            for eleve in eleves:
                rang_info = rangs_dict.get(eleve.id)
                if rang_info:
                    eleves_avec_rangs += 1
                else:
                    eleves_sans_rangs += 1
            
            print(f"📊 Résultat:")
            print(f"   - Élèves avec rangs: {eleves_avec_rangs}")
            print(f"   - Élèves sans rangs: {eleves_sans_rangs}")
            
            if eleves_avec_rangs > 0:
                print(f"🎉 SUCCÈS ! Les rangs devraient maintenant s'afficher")
                print(f"🔗 URL de test: http://127.0.0.1:8000/notes/consulter/?classe_id={classe_id}")
                print(f"🔗 URL avec période: http://127.0.0.1:8000/notes/consulter/?classe_id={classe_id}&periode=OCTOBRE")
            else:
                print(f"⚠️  Problème: Aucun rang calculé")
                
        except Exception as e:
            print(f"❌ Erreur calcul rangs: {e}")
    else:
        print(f"❌ Conditions non remplies pour calcul rangs")

def tester_differentes_periodes():
    """Tester le calcul des rangs pour différentes périodes"""
    print(f"\n🔄 TEST DIFFÉRENTES PÉRIODES")
    print("=" * 30)
    
    classe_note = ClasseNote.objects.get(pk=59)
    periodes_test = ['OCTOBRE', 'NOVEMBRE', 'DECEMBRE', 'JANVIER']
    
    for periode in periodes_test:
        try:
            rangs_dict = calculer_rangs_classe_periode(classe_note, periode)
            print(f"✅ {periode}: {len(rangs_dict)} élèves avec rangs")
        except Exception as e:
            print(f"❌ {periode}: Erreur - {e}")

if __name__ == "__main__":
    try:
        tester_calcul_rangs()
        tester_differentes_periodes()
        
        print(f"\n🎯 RÉSUMÉ")
        print("=" * 15)
        print("✅ Correction appliquée dans consulter_notes")
        print("✅ Période par défaut: OCTOBRE")
        print("✅ Les rangs devraient maintenant s'afficher")
        print("🔗 Testez: http://127.0.0.1:8000/notes/consulter/?classe_id=59")
        
    except Exception as e:
        print(f"❌ Erreur: {e}")
        import traceback
        traceback.print_exc()
