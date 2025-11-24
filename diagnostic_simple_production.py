"""
Diagnostic simple et rapide pour production
Identifie le problème des classes multiples
"""

import os
import sys
import django

# Configuration Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ecole_moderne.settings')
django.setup()

from notes.models import NoteMensuelle, ClasseNote, MatiereNote
from eleves.models import Eleve, Classe

print("\n" + "="*80)
print("🔍 DIAGNOSTIC RAPIDE - CLASSES 9ÈME ANNÉE")
print("="*80)

# 1. Lister TOUTES les ClasseNote avec "9" dans le nom
print("\n📚 CLASSES CONTENANT '9' :")
classes_9 = ClasseNote.objects.filter(nom__icontains='9').order_by('nom', 'annee_scolaire')

for c in classes_9:
    nb_matieres = MatiereNote.objects.filter(classe=c).count()
    
    # Chercher les élèves via Classe (modèle Eleve)
    classe_eleve = Classe.objects.filter(
        nom__icontains=c.nom.replace('È', 'E'),
        annee_scolaire=c.annee_scolaire
    ).first()
    
    nb_eleves = 0
    if classe_eleve:
        nb_eleves = Eleve.objects.filter(classe=classe_eleve, statut='INSCRIT').count()
    
    print(f"\nID {c.id:3} : {c.nom:30}")
    print(f"         Année : {c.annee_scolaire}")
    print(f"         Matières : {nb_matieres}")
    print(f"         Élèves : {nb_eleves}")
    print(f"         École : {c.ecole.nom if c.ecole else 'Non définie'}")

# 2. Chercher l'élève CL9-011
print("\n" + "-"*80)
print("👤 RECHERCHE ÉLÈVE CL9-011 :")

try:
    eleve = Eleve.objects.get(matricule='CL9-011')
    print(f"✅ TROUVÉ : {eleve.nom} {eleve.prenom}")
    print(f"   • Classe (Eleve) : {eleve.classe.nom} (ID: {eleve.classe.id})")
    print(f"   • Année scolaire : {eleve.classe.annee_scolaire}")
    print(f"   • Statut : {eleve.statut}")
    
    # Trouver la ClasseNote correspondante
    print("\n🔄 Recherche ClasseNote correspondante...")
    classes_correspondantes = ClasseNote.objects.filter(
        nom__icontains=eleve.classe.nom.replace('è', 'e').replace('È', 'E'),
        annee_scolaire=eleve.classe.annee_scolaire
    )
    
    if classes_correspondantes.exists():
        print(f"   Trouvé {classes_correspondantes.count()} ClasseNote(s) :")
        for cn in classes_correspondantes:
            print(f"   • ID {cn.id}: {cn.nom} ({cn.annee_scolaire})")
            
            # Compter les notes de cet élève pour cette ClasseNote
            nb_notes = NoteMensuelle.objects.filter(
                eleve=eleve,
                matiere__classe=cn,
                mois='OCTOBRE',
                annee_scolaire=cn.annee_scolaire
            ).count()
            print(f"     Notes OCTOBRE : {nb_notes}")
    else:
        print("   ❌ Aucune ClasseNote correspondante")
        
except Eleve.DoesNotExist:
    print("❌ Élève CL9-011 NON TROUVÉ")
    
    # Chercher des élèves similaires
    print("\n🔍 Élèves avec matricule commençant par CL9- :")
    eleves_cl9 = Eleve.objects.filter(matricule__startswith='CL9-').order_by('matricule')[:10]
    
    if eleves_cl9.exists():
        for e in eleves_cl9:
            print(f"   • {e.matricule} - {e.nom} {e.prenom} ({e.classe.nom})")
    else:
        print("   Aucun élève avec matricule CL9-xxx")

# 3. Statistiques notes OCTOBRE
print("\n" + "-"*80)
print("📊 STATISTIQUES NOTES OCTOBRE :")

from django.db.models import Count

# Total général
total = NoteMensuelle.objects.filter(mois='OCTOBRE').count()
print(f"\nTotal notes OCTOBRE (toute l'école) : {total}")

# Par année scolaire
print("\nPar année scolaire :")
stats = NoteMensuelle.objects.filter(mois='OCTOBRE').values('annee_scolaire').annotate(nb=Count('id')).order_by('-annee_scolaire')
for s in stats:
    print(f"   • {s['annee_scolaire']} : {s['nb']} notes")

# Classes avec le plus de notes
print("\nTop 5 classes avec notes OCTOBRE :")
from django.db.models import Q

for cn in ClasseNote.objects.all():
    nb = NoteMensuelle.objects.filter(
        matiere__classe=cn,
        mois='OCTOBRE'
    ).values('eleve').distinct().count()
    
    if nb > 0:
        print(f"   • {cn.nom} ({cn.annee_scolaire}) : {nb} élèves avec notes")

print("\n" + "="*80)
print("📋 RECOMMANDATIONS")
print("="*80)

if classes_9.count() > 1:
    print("\n⚠️ ATTENTION : Plusieurs classes 9ème trouvées")
    print("   Solution : Utiliser le script verifier_notes_production_fix.py")
    print("   qui gère automatiquement les classes multiples")
    
if total == 0:
    print("\n❌ AUCUNE NOTE MENSUELLE D'OCTOBRE")
    print("   Solution : Saisir les notes via l'interface web")
    print("   ou utiliser le script pour créer des notes de test")
else:
    print(f"\n✅ {total} notes trouvées pour OCTOBRE")
    print("   Si elles ne s'affichent pas, vérifier :")
    print("   1. La bonne classe est sélectionnée")
    print("   2. L'année scolaire correspond")
    print("   3. Le code a été déployé (git pull)")

print("\n" + "="*80)
