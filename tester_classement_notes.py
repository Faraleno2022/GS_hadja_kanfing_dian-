#!/usr/bin/env python
"""
Tester si les notes et le classement sont maintenant accessibles
"""
import os
import sys
import django

# Configuration Django
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ecole_moderne.settings')
django.setup()

from django.test import Client
from django.contrib.auth.models import User
from notes.models import ClasseNote, MatiereNote, Evaluation, NoteEleve
from eleves.models import Eleve, Classe as ClasseEleve

def tester_recuperation_notes():
    """Tester la récupération des notes avec les nouveaux modèles"""
    print("🔍 TEST RÉCUPÉRATION DES NOTES")
    print("=" * 40)
    
    # Trouver une ClasseEleve
    try:
        classe_eleve = ClasseEleve.objects.get(pk=8)
        print(f"✅ ClasseEleve trouvée: {classe_eleve.nom}")
        print(f"   - ID: {classe_eleve.id}")
        print(f"   - École: {classe_eleve.ecole}")
    except Exception as e:
        print(f"❌ Erreur ClasseEleve: {e}")
        return False
    
    # Trouver la ClasseNote correspondante
    try:
        classe_note = ClasseNote.objects.filter(
            nom=classe_eleve.nom,
            annee_scolaire=classe_eleve.annee_scolaire,
            ecole=classe_eleve.ecole
        ).first()
        
        if classe_note:
            print(f"✅ ClasseNote trouvée: {classe_note.nom}")
            print(f"   - ID: {classe_note.id}")
        else:
            print(f"❌ Aucune ClasseNote correspondante")
            return False
    except Exception as e:
        print(f"❌ Erreur ClasseNote: {e}")
        return False
    
    # Récupérer les matières
    try:
        matieres = MatiereNote.objects.filter(classe=classe_note, actif=True)
        print(f"✅ Matières trouvées: {matieres.count()}")
        for mat in matieres[:3]:
            print(f"   - {mat.nom} (coef {mat.coefficient})")
    except Exception as e:
        print(f"❌ Erreur matières: {e}")
        return False
    
    # Récupérer les évaluations
    try:
        evaluations = Evaluation.objects.filter(matiere__in=matieres, periode='TRIMESTRE_1')
        print(f"✅ Évaluations TRIMESTRE_1: {evaluations.count()}")
        for eval in evaluations[:3]:
            print(f"   - {eval.titre} ({eval.matiere.nom})")
    except Exception as e:
        print(f"❌ Erreur évaluations: {e}")
        return False
    
    # Récupérer les élèves
    try:
        eleves = Eleve.objects.filter(classe=classe_eleve, statut='ACTIF')
        print(f"✅ Élèves actifs: {eleves.count()}")
        
        if eleves.exists():
            eleve = eleves.first()
            print(f"   - Test avec: {eleve.prenom} {eleve.nom}")
            
            # Récupérer les notes de cet élève
            notes = NoteEleve.objects.filter(
                eleve=eleve,
                evaluation__matiere__in=[m.id for m in matieres],
                evaluation__periode='TRIMESTRE_1'
            )
            print(f"   - Notes trouvées: {notes.count()}")
            
            for note in notes[:5]:
                print(f"      • {note.evaluation.matiere.nom}: {note.note if note.note else 'ABS'}")
        
    except Exception as e:
        print(f"❌ Erreur élèves/notes: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True

def tester_url_classement():
    """Tester l'URL de consultation/classement"""
    print(f"\n🌐 TEST URL CLASSEMENT")
    print("=" * 25)
    
    client = Client()
    user = User.objects.filter(is_superuser=True).first()
    client.force_login(user)
    
    try:
        # Tester l'URL de consultation (similaire au classement)
        response = client.get('/notes/consulter/', {
            'classe_id': '59',
            'periode': 'TRIMESTRE_1'
        })
        
        print(f"✅ URL consultation testée")
        print(f"   - Status: {response.status_code}")
        
        if response.status_code == 200:
            print(f"   - ✅ Page accessible !")
            # Vérifier si le contenu contient des notes
            content = response.content.decode('utf-8')
            if 'Non saisi' in content:
                print(f"   - ⚠️  Contient 'Non saisi' - Vérifier les données")
            elif 'Moyenne' in content:
                print(f"   - ✅ Contient des moyennes !")
        else:
            print(f"   - ❌ Erreur HTTP {response.status_code}")
            
    except Exception as e:
        print(f"❌ Erreur requête: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True

if __name__ == "__main__":
    try:
        print("🚀 TEST COMPLET NOTES ET CLASSEMENT")
        print("=" * 50)
        
        test1 = tester_recuperation_notes()
        test2 = tester_url_classement()
        
        print(f"\n🎯 RÉSUMÉ")
        print("=" * 15)
        print(f"{'✅' if test1 else '❌'} Récupération des notes")
        print(f"{'✅' if test2 else '❌'} URL de consultation")
        
        if test1 and test2:
            print(f"\n✅ TOUS LES TESTS RÉUSSIS !")
            print(f"\n🔗 URLs à tester:")
            print("   - Consultation: http://127.0.0.1:8000/notes/consulter/?classe_id=59&periode=TRIMESTRE_1")
            print("   - Bulletins PDF: http://127.0.0.1:8000/notes/bulletins/classe/pdf/?classe_id=59&periode=TRIMESTRE_1&system_type=trimestre")
        else:
            print(f"\n❌ Certains tests ont échoué - Vérifier les erreurs ci-dessus")
        
    except Exception as e:
        print(f"❌ Erreur globale: {e}")
        import traceback
        traceback.print_exc()
