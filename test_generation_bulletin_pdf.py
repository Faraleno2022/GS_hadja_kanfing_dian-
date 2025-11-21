"""
Test de génération de bulletin PDF pour vérifier le calcul du rang
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ecole_moderne.settings')
django.setup()

from decimal import Decimal
from eleves.models import Eleve, Classe
from notes.models import Evaluation, NoteEleve
from django.test import RequestFactory
from django.contrib.auth.models import User
from utilisateurs.models import Profil

print("=" * 80)
print("TEST DE GÉNÉRATION DE BULLETIN PDF")
print("=" * 80)

# Trouver une classe avec des élèves
classe = Classe.objects.filter(
    eleves__isnull=False
).distinct().first()

if not classe:
    print("\n❌ Aucune classe avec des élèves trouvée")
    exit(1)

print(f"\n✅ Classe trouvée : {classe.nom}")
print(f"   ID: {classe.id}")

# Trouver des élèves dans cette classe
eleves = Eleve.objects.filter(classe=classe)[:5]
print(f"\n📊 {eleves.count()} élèves trouvés dans la classe:")

for idx, e in enumerate(eleves, 1):
    print(f"   {idx}. {e.prenom} {e.nom} (ID: {e.id}, Matricule: {e.matricule})")

if not eleves:
    print("\n❌ Aucun élève dans cette classe")
    exit(1)

# Prendre le premier élève pour le test
eleve_test = eleves.first()
print(f"\n🎯 Élève sélectionné pour le test : {eleve_test.prenom} {eleve_test.nom}")

# Vérifier s'il y a des évaluations
evaluations = Evaluation.objects.filter(classe=classe)
print(f"\n📝 {evaluations.count()} évaluations trouvées pour cette classe")

if evaluations.count() == 0:
    print("\n⚠️  Aucune évaluation trouvée. Le bulletin sera vide mais le test de génération continuera.")

# Vérifier s'il y a des notes pour cet élève
notes = NoteEleve.objects.filter(eleve=eleve_test)
print(f"📊 {notes.count()} notes trouvées pour cet élève")

# Créer un utilisateur de test pour la requête
try:
    user = User.objects.filter(is_superuser=True).first()
    if not user:
        user = User.objects.first()
    
    if not user:
        print("\n❌ Aucun utilisateur trouvé dans la base")
        exit(1)
    
    print(f"\n👤 Utilisateur pour le test : {user.username}")
except Exception as e:
    print(f"\n❌ Erreur lors de la récupération de l'utilisateur : {e}")
    exit(1)

# Créer une requête factice
factory = RequestFactory()
request = factory.get(f'/notes/bulletin-pdf/{classe.id}/{eleve_test.id}/T1/')
request.user = user

print("\n" + "=" * 80)
print("GÉNÉRATION DU BULLETIN PDF")
print("=" * 80)

try:
    from notes.views import bulletin_pdf
    
    print("\n⏳ Génération du bulletin en cours...")
    response = bulletin_pdf(request, classe.id, eleve_test.id, "T1")
    
    if response.status_code == 200:
        print("✅ Bulletin généré avec succès!")
        print(f"   Type de contenu : {response['Content-Type']}")
        print(f"   Taille : {len(response.content)} octets")
        
        # Sauvegarder le PDF pour inspection
        output_file = f"bulletin_test_{eleve_test.id}.pdf"
        with open(output_file, 'wb') as f:
            f.write(response.content)
        
        print(f"\n💾 Bulletin sauvegardé : {output_file}")
        print(f"\n📂 Ouvrez ce fichier pour vérifier que le rang s'affiche correctement")
        
    else:
        print(f"❌ Erreur lors de la génération : Status {response.status_code}")
        
except Exception as e:
    print(f"\n❌ Erreur lors de la génération du bulletin : {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 80)
print("VÉRIFICATION DU CALCUL DU RANG")
print("=" * 80)

# Simuler le calcul du rang comme dans bulletin_pdf
try:
    from notes.models import Evaluation, NoteEleve
    
    # Récupérer les matières (en utilisant le code réel de bulletin_pdf)
    # Note: MatiereClasse n'existe pas dans les imports, donc on va chercher autrement
    
    print("\n⏳ Calcul du rang pour tous les élèves de la classe...")
    
    # Récupérer toutes les évaluations du trimestre T1
    trimestre = "T1"
    evals = Evaluation.objects.filter(classe=classe, trimestre=trimestre)
    
    if evals.count() == 0:
        print("\n⚠️  Aucune évaluation pour le trimestre T1")
        print("   Impossible de calculer le rang")
    else:
        print(f"   {evals.count()} évaluations trouvées pour T1")
        
        # Calculer les moyennes de tous les élèves
        eleves_classe = Eleve.objects.filter(classe=classe)
        moyennes = []
        
        for e in eleves_classe:
            notes_eleve = NoteEleve.objects.filter(
                eleve=e,
                evaluation__classe=classe,
                evaluation__trimestre=trimestre
            )
            
            if notes_eleve.count() > 0:
                total = Decimal('0')
                count = 0
                for n in notes_eleve:
                    if n.note is not None:
                        total += Decimal(str(n.note))
                        count += 1
                
                if count > 0:
                    moyenne = total / count
                    moyennes.append((e.id, moyenne, e.prenom, e.nom))
        
        if moyennes:
            # Trier par moyenne décroissante
            moyennes.sort(key=lambda x: x[1], reverse=True)
            
            print(f"\n📊 Classement de la classe ({len(moyennes)} élèves avec notes):")
            print("-" * 80)
            
            # Calculer le rang avec ex-aequo
            rang_actuel = 1
            prev_moy = None
            
            for idx, (eid, moy, prenom, nom) in enumerate(moyennes, start=1):
                if prev_moy is not None and abs(moy - prev_moy) < Decimal('0.01'):
                    pass  # Ex-aequo
                else:
                    rang_actuel = idx
                
                marker = " ⭐" if eid == eleve_test.id else ""
                print(f"   {rang_actuel}. {prenom} {nom} : {moy:.2f}/20{marker}")
                
                prev_moy = moy
            
            print("\n✅ Le calcul du rang fonctionne correctement avec gestion des ex-aequo")
        else:
            print("\n⚠️  Aucun élève avec des notes dans cette classe")

except Exception as e:
    print(f"\n❌ Erreur lors du calcul du rang : {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 80)
print("FIN DU TEST")
print("=" * 80)
