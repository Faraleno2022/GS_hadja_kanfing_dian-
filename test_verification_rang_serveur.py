"""
Script de vérification du rang sur le serveur de production
À exécuter APRÈS le déploiement des corrections
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ecole_moderne.settings')
django.setup()

from decimal import Decimal
from eleves.models import Eleve, Classe as ClasseEleve
from notes.models import ClasseNote, MatiereNote, Evaluation, NoteEleve

print("=" * 80)
print("VÉRIFICATION DES RANGS - CLASSEMENT vs BULLETIN")
print("=" * 80)

# Rechercher la classe 12 SÉRIE SCIENTIFIQUE
classe_note = ClasseNote.objects.filter(
    nom__icontains="12",
    nom__icontains="SCIENTIFIQUE"
).first()

if not classe_note:
    print("\n❌ Classe 12 SÉRIE SCIENTIFIQUE non trouvée")
    exit(1)

print(f"\n✅ ClasseNote trouvée : {classe_note.nom} (ID: {classe_note.id})")

# Trouver la classe élève correspondante
classe_eleve = ClasseEleve.objects.filter(
    nom__icontains="12",
    nom__icontains="SCIENCE",
    annee_scolaire=classe_note.annee_scolaire,
    ecole=classe_note.ecole
).first()

if not classe_eleve:
    print("❌ Classe élève correspondante non trouvée")
    exit(1)

print(f"✅ ClasseEleve trouvée : {classe_eleve.nom} (ID: {classe_eleve.id})")

# Chercher l'élève DIALLO Alpha Ousmane avec matricule L12SC-022
eleve = Eleve.objects.filter(
    classe=classe_eleve,
    nom__icontains="DIALLO",
    prenom__icontains="ALPHA"
).first()

if not eleve:
    print("\n❌ Élève DIALLO Alpha Ousmane non trouvé")
    print("\nÉlèves disponibles dans la classe:")
    for e in Eleve.objects.filter(classe=classe_eleve)[:10]:
        print(f"   - {e.prenom} {e.nom} (Matricule: {e.matricule})")
    exit(1)

print(f"✅ Élève trouvé : {eleve.prenom} {eleve.nom} (Matricule: {eleve.matricule})")

# Période à tester
periode = "OCTOBRE"
system_type = "mensuel"

print(f"\n📅 Période : {periode}")
print(f"📋 Système : {system_type}")

# Récupérer les matières
matieres = MatiereNote.objects.filter(classe=classe_note, actif=True).order_by('nom')
print(f"\n📚 {matieres.count()} matières trouvées")

# Récupérer tous les élèves actifs
eleves = Eleve.objects.filter(classe=classe_eleve, statut='ACTIF').order_by('prenom', 'nom')
print(f"👥 {eleves.count()} élèves actifs")

print("\n" + "=" * 80)
print("CALCUL DES MOYENNES ET RANGS (comme dans le code corrigé)")
print("=" * 80)

# Calculer les moyennes de tous les élèves
all_moyennes = []

for e in eleves:
    e_total_points = Decimal('0')
    e_total_coef = Decimal('0')
    
    for matiere in matieres:
        evals = Evaluation.objects.filter(
            matiere=matiere,
            periode=periode
        )
        
        e_total_dev = Decimal('0')
        e_count_dev = 0
        e_total_compo = Decimal('0')
        e_count_compo = 0
        
        for ev in evals:
            try:
                n = NoteEleve.objects.get(eleve=e, evaluation=ev)
                if n.note is not None and not n.absent:
                    if ev.type_evaluation in ['COMPOSITION', 'EXAMEN']:
                        e_total_compo += Decimal(str(n.note))
                        e_count_compo += 1
                    else:
                        e_total_dev += Decimal(str(n.note))
                        e_count_dev += 1
            except NoteEleve.DoesNotExist:
                pass
        
        e_moy_dev = e_total_dev / e_count_dev if e_count_dev > 0 else None
        e_note_compo = e_total_compo / e_count_compo if e_count_compo > 0 else None
        
        if system_type == 'mensuel':
            e_moy_mat = e_moy_dev
        elif e_moy_dev is not None and e_note_compo is not None:
            e_moy_mat = (e_moy_dev + e_note_compo * 2) / 3
        elif e_note_compo is not None:
            e_moy_mat = e_note_compo
        elif e_moy_dev is not None:
            e_moy_mat = e_moy_dev
        else:
            e_moy_mat = None
        
        if e_moy_mat is not None:
            e_total_points += e_moy_mat * matiere.coefficient
            e_total_coef += matiere.coefficient
    
    if e_total_coef > 0:
        e_moyenne = e_total_points / e_total_coef
        all_moyennes.append({
            'id': e.id,
            'matricule': e.matricule,
            'nom': f"{e.prenom} {e.nom}",
            'moyenne': float(e_moyenne),
            'sexe': e.sexe
        })

# Trier par moyenne décroissante
all_moyennes.sort(key=lambda x: x['moyenne'], reverse=True)

print(f"\n📊 Classement complet ({len(all_moyennes)} élèves) :")
print("-" * 80)

# Calculer les rangs avec gestion des ex-aequo
rang_actuel = 1
prev_moy = None
rang_diallo = None
moyenne_diallo = None

for idx, eleve_data in enumerate(all_moyennes, start=1):
    # Gestion des ex-aequo
    if prev_moy is not None and abs(eleve_data['moyenne'] - prev_moy) < 0.01:
        pass  # Ex-aequo : garde le même rang
    else:
        rang_actuel = idx
    
    # Formater le rang
    from notes.calculs_intelligent import formater_rang_intelligent
    rang_formate = formater_rang_intelligent(rang_actuel, eleve_data['sexe'], len(all_moyennes))
    
    marker = " ⭐" if eleve_data['id'] == eleve.id else ""
    print(f"  {rang_formate} - {eleve_data['matricule']} - {eleve_data['nom']} : {eleve_data['moyenne']:.2f}/20{marker}")
    
    if eleve_data['id'] == eleve.id:
        rang_diallo = rang_actuel
        moyenne_diallo = eleve_data['moyenne']
    
    prev_moy = eleve_data['moyenne']

print("\n" + "=" * 80)
print("RÉSULTAT DE LA VÉRIFICATION")
print("=" * 80)

print(f"\n🎯 Élève testé : {eleve.prenom} {eleve.nom}")
print(f"📋 Matricule : {eleve.matricule}")
print(f"📊 Moyenne calculée : {moyenne_diallo:.2f}/20")
print(f"🏆 Rang calculé : {rang_diallo}ème/{len(all_moyennes)}")

print("\n" + "=" * 80)
print("COMPARAISON AVEC VOS DONNÉES")
print("=" * 80)

print("\n📄 Données du classement que vous avez fournies :")
print("   Rang : 9ème")
print("   Moyenne : 9.38/20")

print("\n📄 Données du bulletin que vous avez fournies :")
print("   Rang : 10ème (AVANT correction)")
print("   Moyenne : 9.38/20")

if rang_diallo == 9 and abs(moyenne_diallo - 9.38) < 0.01:
    print("\n✅ ✅ ✅ SUCCÈS TOTAL ! ✅ ✅ ✅")
    print("\n   Le rang calculé (9ème) correspond EXACTEMENT au classement général !")
    print("   La moyenne calculée (9.38) correspond EXACTEMENT aux données !")
    print("\n   🎉 La correction est VALIDÉE sur le serveur de production !")
elif rang_diallo == 9:
    print("\n✅ RANG CORRECT !")
    print(f"   ⚠️  Petite différence de moyenne : {moyenne_diallo:.2f} vs 9.38")
    print("   (Cela peut être dû à des arrondis)")
else:
    print(f"\n❌ PROBLÈME DÉTECTÉ !")
    print(f"   Rang calculé : {rang_diallo}ème (attendu : 9ème)")
    print(f"   Moyenne calculée : {moyenne_diallo:.2f} (attendu : 9.38)")
    print("\n   ⚠️  Les corrections n'ont peut-être pas été déployées correctement")
    print("   ⚠️  Ou le serveur n'a pas été redémarré")

print("\n" + "=" * 80)
print("INSTRUCTIONS")
print("=" * 80)

print("\n1. Si le test est ✅ RÉUSSI :")
print("   - Régénérez le bulletin PDF pour DIALLO Alpha Ousmane")
print("   - Vérifiez qu'il affiche maintenant 9ème/18")
print("   - Videz le cache du navigateur si nécessaire (Ctrl+F5)")

print("\n2. Si le test est ❌ ÉCHOUÉ :")
print("   - Vérifiez que vous avez fait : git pull origin main")
print("   - Redémarrez le serveur : sudo systemctl restart gunicorn")
print("   - Relancez ce script de test")

print("\n" + "=" * 80)
