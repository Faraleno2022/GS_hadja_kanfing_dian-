"""
Script de test pour vérifier la cohérence entre bulletins et classement
après l'implémentation du système centralisé
"""

import os
import django

# Configuration Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ecole_moderne.settings')
django.setup()

from notes.models import ClasseNote, MatiereNote, Evaluation, NoteEleve
from eleves.models import Eleve
from notes.calculs_moyennes import (
    calculer_moyenne_generale_eleve,
    calculer_classement_classe,
    formater_rang_intelligent
)

def test_coherence_classe(classe_id, periode='OCTOBRE', system_type='mensuel'):
    """
    Teste la cohérence des calculs pour une classe donnée
    """
    print(f"\n{'='*80}")
    print(f"TEST DE COHÉRENCE - Classe ID: {classe_id}, Période: {periode}")
    print(f"{'='*80}\n")
    
    # Récupérer la classe
    try:
        classe = ClasseNote.objects.get(id=classe_id)
    except ClasseNote.DoesNotExist:
        print(f"❌ Classe {classe_id} introuvable")
        return False
    
    print(f"📚 Classe: {classe.nom}")
    print(f"📅 Année: {classe.annee_scolaire}")
    
    # Récupérer les élèves et matières
    from eleves.models import Classe as ClasseEleve
    try:
        classe_eleve = ClasseEleve.objects.filter(
            nom__icontains=classe.nom.split()[0],
            annee_scolaire=classe.annee_scolaire
        ).first()
        
        if not classe_eleve:
            print("❌ Classe élève correspondante introuvable")
            return False
            
        eleves = Eleve.objects.filter(classe=classe_eleve, statut='ACTIF')
        print(f"👥 Nombre d'élèves: {eleves.count()}")
        
    except Exception as e:
        print(f"❌ Erreur: {e}")
        return False
    
    matieres = MatiereNote.objects.filter(classe=classe, actif=True)
    print(f"📖 Nombre de matières: {matieres.count()}\n")
    
    if not eleves.exists():
        print("❌ Aucun élève trouvé")
        return False
    
    if not matieres.exists():
        print("❌ Aucune matière trouvée")
        return False
    
    # Calculer le classement (source unique)
    print("🔄 Calcul du classement centralisé...")
    classement_complet = calculer_classement_classe(eleves, matieres, periode, system_type)
    
    print(f"✅ Classement calculé: {classement_complet['total_eleves']} élèves avec notes\n")
    
    # Vérifier la cohérence pour chaque élève
    print(f"{'Élève':<30} {'Moyenne':<10} {'Rang':<10} {'Status'}")
    print(f"{'-'*80}")
    
    coherence_ok = True
    eleves_testes = 0
    
    for eleve in eleves[:10]:  # Tester les 10 premiers
        details = classement_complet['details_par_eleve'].get(eleve.id)
        
        if details:
            moyenne = details['moyenne_generale']
            rang = classement_complet['rang_map'].get(eleve.id)
            rang_formate = formater_rang_intelligent(rang, eleve.sexe, classement_complet['total_eleves'])
            
            # Recalculer individuellement pour comparer
            result_individuel = calculer_moyenne_generale_eleve(eleve, matieres, periode, system_type)
            moyenne_individuelle = result_individuel['moyenne_generale']
            
            # Vérifier cohérence
            if moyenne == moyenne_individuelle:
                status = "✅ OK"
            else:
                status = f"❌ DIFF ({moyenne} vs {moyenne_individuelle})"
                coherence_ok = False
            
            nom_complet = f"{eleve.prenom} {eleve.nom}"[:28]
            print(f"{nom_complet:<30} {moyenne:<10.2f} {rang_formate:<10} {status}")
            eleves_testes += 1
        else:
            nom_complet = f"{eleve.prenom} {eleve.nom}"[:28]
            print(f"{nom_complet:<30} {'N/A':<10} {'N/A':<10} ⚠️  Pas de notes")
    
    print(f"\n{'='*80}")
    if coherence_ok and eleves_testes > 0:
        print(f"✅ COHÉRENCE VALIDÉE: {eleves_testes} élèves testés, aucune incohérence détectée")
    elif eleves_testes == 0:
        print(f"⚠️  AUCUN ÉLÈVE TESTÉ: Vérifiez les données")
    else:
        print(f"❌ INCOHÉRENCE DÉTECTÉE: Vérifiez les calculs")
    print(f"{'='*80}\n")
    
    return coherence_ok


def test_toutes_classes():
    """
    Teste toutes les classes disponibles
    """
    classes = ClasseNote.objects.all()[:5]  # Tester les 5 premières
    
    print("\n" + "="*80)
    print("TEST DE COHÉRENCE GLOBAL")
    print("="*80)
    
    resultats = []
    for classe in classes:
        resultat = test_coherence_classe(classe.id)
        resultats.append((classe.nom, resultat))
    
    print("\n" + "="*80)
    print("RÉSUMÉ DES TESTS")
    print("="*80)
    for nom, resultat in resultats:
        status = "✅ OK" if resultat else "❌ ÉCHEC"
        print(f"{nom:<40} {status}")
    print("="*80 + "\n")


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        # Test d'une classe spécifique
        classe_id = int(sys.argv[1])
        periode = sys.argv[2] if len(sys.argv) > 2 else 'OCTOBRE'
        system_type = sys.argv[3] if len(sys.argv) > 3 else 'mensuel'
        test_coherence_classe(classe_id, periode, system_type)
    else:
        # Test de toutes les classes
        test_toutes_classes()
