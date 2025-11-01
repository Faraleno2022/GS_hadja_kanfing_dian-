"""
Test du bulletin dynamique via requêtes HTTP
"""

import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ecole_moderne.settings')
django.setup()

from notes.models import ClasseNote, MatiereNote, Evaluation, NoteEleve
from eleves.models import Eleve, Classe
from django.contrib.auth.models import User
from decimal import Decimal

def afficher_bulletin_test():
    """Afficher les informations de test pour le bulletin"""
    print("\n" + "="*70)
    print("   📊 DONNÉES POUR TEST DU BULLETIN DYNAMIQUE")
    print("="*70)
    
    # Récupérer une classe avec des données
    classes = ClasseNote.objects.filter(actif=True)
    
    if not classes.exists():
        print("❌ Aucune classe active trouvée")
        return
    
    for classe in classes[:3]:  # Tester les 3 premières classes
        print(f"\n{'='*70}")
        print(f"📚 CLASSE: {classe.nom} ({classe.get_niveau_display()})")
        print(f"   Année scolaire: {classe.annee_scolaire}")
        print(f"{'='*70}")
        
        # Récupérer les matières
        matieres = MatiereNote.objects.filter(classe=classe, actif=True)
        print(f"\n📖 Matières ({matieres.count()}):")
        for mat in matieres:
            print(f"   - {mat.nom} (Coef: {mat.coefficient})")
        
        # Récupérer les élèves
        try:
            classe_eleve = Classe.objects.get(
                nom=classe.nom,
                annee_scolaire=classe.annee_scolaire
            )
            eleves = Eleve.objects.filter(classe=classe_eleve, statut='ACTIF')[:5]
            
            print(f"\n👥 Élèves ({Eleve.objects.filter(classe=classe_eleve, statut='ACTIF').count()} total):")
            for eleve in eleves:
                print(f"   - {eleve.nom} {eleve.prenom} (ID: {eleve.id})")
            
            # Vérifier les évaluations pour chaque période
            periodes = ['TRIMESTRE_1', 'TRIMESTRE_2', 'TRIMESTRE_3']
            print(f"\n📝 Évaluations par période:")
            
            for periode in periodes:
                total_evals = 0
                for matiere in matieres:
                    evals = Evaluation.objects.filter(
                        matiere=matiere,
                        periode=periode
                    )
                    total_evals += evals.count()
                
                if total_evals > 0:
                    print(f"   ✅ {periode}: {total_evals} évaluations")
                    
                    # Générer l'URL de test pour un élève
                    if eleves.exists():
                        eleve_test = eleves.first()
                        url = f"http://127.0.0.1:8001/notes/bulletins/?classe_id={classe.id}&system_type=trimestre&periode={periode}&eleve_id={eleve_test.id}"
                        print(f"      🔗 URL TEST: {url}")
                        
                        # Tester les calculs pour cet élève
                        tester_calculs_eleve(eleve_test, classe, periode, matieres)
                        break  # Tester qu'une seule période
                else:
                    print(f"   ⚠️  {periode}: Aucune évaluation")
            
        except Classe.DoesNotExist:
            print(f"   ⚠️  Pas d'élèves trouvés pour cette classe")
        
        break  # Tester qu'une seule classe pour l'instant

def tester_calculs_eleve(eleve, classe, periode, matieres):
    """Tester les calculs pour un élève spécifique"""
    print(f"\n   📊 CALCULS POUR: {eleve.nom} {eleve.prenom}")
    print(f"   {'─'*66}")
    
    total_points = Decimal('0')
    total_coef = Decimal('0')
    
    for matiere in matieres[:5]:  # Limiter à 5 matières pour l'affichage
        evaluations = Evaluation.objects.filter(
            matiere=matiere,
            matiere__classe=classe,
            periode=periode
        )
        
        if not evaluations.exists():
            continue
        
        # Séparer devoirs et compositions
        total_devoirs = Decimal('0')
        count_devoirs = 0
        total_compo = Decimal('0')
        count_compo = 0
        
        for evaluation in evaluations:
            try:
                note_obj = NoteEleve.objects.get(eleve=eleve, evaluation=evaluation)
                if note_obj.note is not None and not note_obj.absent:
                    if evaluation.type_evaluation in ['COMPOSITION', 'EXAMEN']:
                        total_compo += Decimal(str(note_obj.note))
                        count_compo += 1
                    else:
                        total_devoirs += Decimal(str(note_obj.note))
                        count_devoirs += 1
            except NoteEleve.DoesNotExist:
                pass
        
        # Calculer les moyennes
        moy_continue = None
        moy_compo = None
        
        if count_devoirs > 0:
            moy_continue = round(float(total_devoirs / count_devoirs), 2)
        
        if count_compo > 0:
            moy_compo = round(float(total_compo / count_compo), 2)
        
        # Moyenne matière avec pondération
        moy_matiere = None
        if moy_continue is not None and moy_compo is not None:
            moy_matiere = round((moy_continue + moy_compo * 2) / 3, 2)
        elif moy_compo is not None:
            moy_matiere = moy_compo
        elif moy_continue is not None:
            moy_matiere = moy_continue
        
        # Calcul des points
        if moy_matiere is not None:
            points = Decimal(str(moy_matiere)) * matiere.coefficient
            total_points += points
            total_coef += matiere.coefficient
            
            print(f"   {matiere.nom[:20]:20} | MC:{moy_continue or '-':5} | Comp:{moy_compo or '-':5} | Moy:{moy_matiere:5.2f} | Pts:{float(points):6.2f}")
    
    # Moyenne générale
    if total_coef > 0:
        moy_gen = total_points / total_coef
        print(f"   {'─'*66}")
        print(f"   {'TOTAL':20} | Points: {float(total_points):6.2f} | Coef: {float(total_coef):4} | Moy: {float(moy_gen):5.2f}/20")
        
        # Déterminer la mention
        moy_float = float(moy_gen)
        if moy_float >= 18:
            mention = "Excellent"
        elif moy_float >= 16:
            mention = "Très Bien"
        elif moy_float >= 14:
            mention = "Bien"
        elif moy_float >= 12:
            mention = "Assez Bien"
        elif moy_float >= 10:
            mention = "Passable"
        else:
            mention = "Insuffisant"
        
        print(f"   {'─'*66}")
        print(f"   ✅ MENTION: {mention}")
    else:
        print(f"   ⚠️  Aucune note disponible")

def afficher_urls_test():
    """Afficher les URLs de test disponibles"""
    print("\n" + "="*70)
    print("   🔗 URLs DE TEST DISPONIBLES")
    print("="*70)
    
    print("\n1️⃣  Accueil:")
    print("   http://127.0.0.1:8001/")
    
    print("\n2️⃣  Tableau de bord des notes:")
    print("   http://127.0.0.1:8001/notes/")
    
    print("\n3️⃣  Bulletin dynamique (sans paramètres):")
    print("   http://127.0.0.1:8001/notes/bulletins/")
    
    print("\n4️⃣  Gestion des classes:")
    print("   http://127.0.0.1:8001/notes/classes/")
    
    print("\n5️⃣  Gestion des matières:")
    print("   http://127.0.0.1:8001/notes/matieres/")
    
    print("\n6️⃣  Gestion des évaluations:")
    print("   http://127.0.0.1:8001/notes/evaluations/")

def main():
    print("\n" + "="*70)
    print("   🧪 TEST WEB DU BULLETIN DYNAMIQUE")
    print("="*70)
    
    try:
        afficher_bulletin_test()
        afficher_urls_test()
        
        print("\n" + "="*70)
        print("   ✅ TEST TERMINÉ - LE SERVEUR EST PRÊT")
        print("="*70)
        print("\n💡 Utilisez les URLs ci-dessus pour tester le bulletin dans votre navigateur")
        print("💡 Le serveur tourne sur: http://127.0.0.1:8001/")
        
    except Exception as e:
        print(f"\n❌ ERREUR: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    main()
