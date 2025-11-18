#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Script de test pour vérifier le calcul du classement et des moyennes
Teste la fonction consulter_notes pour toutes les classes
"""

import os
import sys
import django
from decimal import Decimal

# Configuration Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ecole_moderne.settings')
django.setup()

from django.contrib.auth.models import User
from django.test import RequestFactory
from notes.models import ClasseNote, MatiereNote, Evaluation, NoteEleve
from eleves.models import Eleve, Classe as ClasseEleve, Ecole
from notes.views import consulter_notes

def test_classement_classe(classe_note_id):
    """Tester le classement pour une classe spécifique"""
    print(f"\n{'='*70}")
    print(f"TEST CLASSE ID: {classe_note_id}")
    print(f"{'='*70}")
    
    try:
        classe_note = ClasseNote.objects.get(pk=classe_note_id)
        print(f"✅ Classe trouvée: {classe_note.nom} ({classe_note.annee_scolaire})")
    except ClasseNote.DoesNotExist:
        print(f"❌ Classe ID {classe_note_id} non trouvée")
        return False
    
    # Créer une requête simulée
    factory = RequestFactory()
    user = User.objects.filter(is_superuser=True).first()
    if not user:
        print("❌ Aucun utilisateur admin trouvé")
        return False
    
    request = factory.get(f'/notes/consulter/?classe_id={classe_note_id}')
    request.user = user
    
    # Appeler la vue
    try:
        response = consulter_notes(request)
        context = response.context_data if hasattr(response, 'context_data') else {}
        
        eleves_toutes_notes = context.get('eleves_toutes_notes', [])
        classe_selectionnee = context.get('classe_selectionnee')
        
        if not classe_selectionnee:
            print("❌ Aucune classe sélectionnée dans le contexte")
            return False
        
        print(f"\n📊 RÉSULTATS POUR {classe_selectionnee.nom}:")
        print(f"   Nombre d'élèves: {len(eleves_toutes_notes)}")
        
        if len(eleves_toutes_notes) == 0:
            print("⚠️  Aucun élève trouvé pour cette classe")
            return True
        
        # Vérifier les données de chaque élève
        eleves_avec_moyenne = 0
        eleves_sans_moyenne = 0
        rangs_attribues = 0
        
        for idx, eleve_data in enumerate(eleves_toutes_notes[:10], 1):  # Limiter à 10 pour l'affichage
            eleve = eleve_data.get('eleve')
            moyenne_generale = eleve_data.get('moyenne_generale')
            rang = eleve_data.get('rang', '-')
            notes_par_matiere = eleve_data.get('notes_par_matiere', {})
            
            if eleve:
                nom_complet = f"{eleve.prenom} {eleve.nom}"
                matricule = eleve.matricule or "N/A"
                
                if moyenne_generale is not None:
                    eleves_avec_moyenne += 1
                    if rang != '-':
                        rangs_attribues += 1
                    print(f"\n   {idx}. {nom_complet} ({matricule})")
                    print(f"      Moyenne générale: {moyenne_generale}/20")
                    print(f"      Rang: {rang}")
                    
                    # Afficher les moyennes par matière
                    for matiere_id, notes_matiere in notes_par_matiere.items():
                        moyenne_matiere = notes_matiere.get('moyenne')
                        if moyenne_matiere is not None:
                            matiere = MatiereNote.objects.filter(pk=matiere_id).first()
                            if matiere:
                                print(f"         - {matiere.nom}: {moyenne_matiere}/20")
                else:
                    eleves_sans_moyenne += 1
                    print(f"\n   {idx}. {nom_complet} ({matricule})")
                    print(f"      ❌ Pas de moyenne générale")
                    print(f"      Rang: {rang}")
        
        if len(eleves_toutes_notes) > 10:
            print(f"\n   ... et {len(eleves_toutes_notes) - 10} autres élèves")
        
        # Résumé
        print(f"\n📈 STATISTIQUES:")
        print(f"   ✅ Élèves avec moyenne: {eleves_avec_moyenne}/{len(eleves_toutes_notes)}")
        print(f"   ⚠️  Élèves sans moyenne: {eleves_sans_moyenne}/{len(eleves_toutes_notes)}")
        print(f"   🏆 Rangs attribués: {rangs_attribues}/{eleves_avec_moyenne}")
        
        # Vérifier que le classement est correct (décroissant)
        moyennes = [e.get('moyenne_generale') for e in eleves_toutes_notes if e.get('moyenne_generale') is not None]
        if len(moyennes) > 1:
            est_trie = all(moyennes[i] >= moyennes[i+1] for i in range(len(moyennes)-1))
            if est_trie:
                print(f"   ✅ Classement correct (décroissant)")
            else:
                print(f"   ❌ Classement incorrect (pas décroissant)")
                return False
        
        return True
        
    except Exception as e:
        print(f"❌ Erreur lors du test: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def test_toutes_les_classes():
    """Tester le classement pour toutes les classes actives"""
    print("\n" + "="*70)
    print("TEST DU CLASSEMENT POUR TOUTES LES CLASSES")
    print("="*70)
    
    classes = ClasseNote.objects.filter(actif=True).order_by('nom')
    print(f"\n📚 Nombre de classes actives: {classes.count()}")
    
    if classes.count() == 0:
        print("⚠️  Aucune classe active trouvée")
        return
    
    resultats = []
    for classe in classes:
        resultat = test_classement_classe(classe.id)
        resultats.append((classe.nom, resultat))
    
    # Résumé final
    print("\n" + "="*70)
    print("RÉSUMÉ DES TESTS")
    print("="*70)
    
    reussis = sum(1 for _, r in resultats if r)
    echecs = len(resultats) - reussis
    
    for nom, resultat in resultats:
        status = "✅" if resultat else "❌"
        print(f"{status} {nom}")
    
    print(f"\n📊 Total: {reussis} réussis, {echecs} échecs sur {len(resultats)} classes")

def test_classe_specifique(classe_id):
    """Tester une classe spécifique (par exemple classe_id=6)"""
    return test_classement_classe(classe_id)

if __name__ == "__main__":
    print("🧪 TEST DU SYSTÈME DE CLASSEMENT")
    print("="*70)
    
    # Test de la classe spécifique mentionnée (classe_id=6)
    print("\n1. Test de la classe ID 6 (mentionnée dans le problème)")
    test_classe_specifique(6)
    
    # Test de toutes les classes
    print("\n\n2. Test de toutes les classes actives")
    test_toutes_les_classes()
    
    print("\n" + "="*70)
    print("TESTS TERMINÉS")
    print("="*70)

