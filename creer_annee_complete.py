"""
Script pour créer une année scolaire complète de notes mensuelles
"""

import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ecole_moderne.settings')
django.setup()

from gerer_notes_mensuelles import creer_evaluations_mensuelles, saisir_notes_mensuelles

MOIS_ANNEE = [
    'OCTOBRE', 'NOVEMBRE', 'DECEMBRE',  # 1er Trimestre
    'JANVIER', 'FEVRIER', 'MARS',        # 2ème Trimestre
    'AVRIL', 'MAI', 'JUIN'               # 3ème Trimestre
]

def creer_annee_complete(classe_id, nombre_eleves=10):
    """Créer les notes mensuelles pour toute l'année scolaire"""
    print("\n" + "="*80)
    print(" "*15 + "📅 CRÉATION D'UNE ANNÉE SCOLAIRE COMPLÈTE")
    print("="*80)
    
    print(f"\n📋 Configuration:")
    print(f"   - Classe ID: {classe_id}")
    print(f"   - Nombre d'élèves: {nombre_eleves}")
    print(f"   - Mois à créer: {len(MOIS_ANNEE)}")
    
    total_evals = 0
    total_notes = 0
    
    for i, mois in enumerate(MOIS_ANNEE, 1):
        print(f"\n{'─'*80}")
        print(f"   {i}/9 - Traitement de {mois}")
        print(f"{'─'*80}")
        
        # Créer les évaluations
        nb_evals = creer_evaluations_mensuelles(classe_id, mois)
        if nb_evals:
            total_evals += nb_evals
        
        # Saisir les notes
        saisir_notes_mensuelles(classe_id, mois, nombre_eleves)
        # Estimation: nb_evals × nombre_eleves
        if nb_evals:
            total_notes += nb_evals * nombre_eleves
    
    print(f"\n{'='*80}")
    print(f"   ✅ ANNÉE SCOLAIRE COMPLÈTE CRÉÉE")
    print(f"{'='*80}")
    
    print(f"\n📊 Statistiques:")
    print(f"   - Mois créés: {len(MOIS_ANNEE)}")
    print(f"   - Évaluations totales: ~{total_evals}")
    print(f"   - Notes saisies: ~{total_notes}")
    
    print(f"\n🔗 URLs des Bulletins Mensuels:")
    print(f"{'─'*80}")
    base_url = "http://127.0.0.1:8001/notes/bulletins/?"
    
    # Prendre le premier élève comme exemple
    from eleves.models import Eleve, Classe
    from notes.models import ClasseNote
    
    try:
        classe = ClasseNote.objects.get(pk=classe_id)
        classe_eleve = Classe.objects.get(
            nom=classe.nom,
            annee_scolaire=classe.annee_scolaire
        )
        eleve = Eleve.objects.filter(classe=classe_eleve, statut='ACTIF').first()
        
        if eleve:
            print(f"\n   Élève exemple: {eleve.nom} {eleve.prenom} (ID: {eleve.id})")
            print()
            for mois in MOIS_ANNEE:
                url = f"{base_url}classe_id={classe_id}&system_type=mensuel&periode={mois}&eleve_id={eleve.id}"
                print(f"   • {mois:10} : {url}")
    except Exception as e:
        print(f"   ⚠️  Impossible de générer les URLs: {e}")
    
    print(f"\n💡 Prochaines Étapes:")
    print(f"{'─'*80}")
    print(f"   1. Vérifiez les bulletins en cliquant sur les URLs ci-dessus")
    print(f"   2. Testez l'impression de chaque bulletin")
    print(f"   3. Partagez les URLs avec les professeurs/parents")

def creer_trimestre(classe_id, trimestre, nombre_eleves=10):
    """Créer les notes pour un trimestre spécifique"""
    trimestres = {
        1: ['OCTOBRE', 'NOVEMBRE', 'DECEMBRE'],
        2: ['JANVIER', 'FEVRIER', 'MARS'],
        3: ['AVRIL', 'MAI', 'JUIN']
    }
    
    if trimestre not in trimestres:
        print("❌ Trimestre invalide (1, 2 ou 3)")
        return
    
    mois_trimestre = trimestres[trimestre]
    
    print(f"\n{'='*80}")
    print(f"   📅 CRÉATION DU TRIMESTRE {trimestre}")
    print(f"{'='*80}")
    
    print(f"\n📋 Mois du trimestre {trimestre}:")
    for m in mois_trimestre:
        print(f"   - {m}")
    
    for mois in mois_trimestre:
        print(f"\n🔄 Traitement de {mois}...")
        creer_evaluations_mensuelles(classe_id, mois)
        saisir_notes_mensuelles(classe_id, mois, nombre_eleves)
    
    print(f"\n✅ Trimestre {trimestre} créé avec succès!")

def menu():
    """Menu interactif"""
    print("\n" + "="*80)
    print(" "*20 + "📅 CRÉATION RAPIDE - NOTES MENSUELLES")
    print("="*80)
    
    print("\n1️⃣  Créer toute l'année (9 mois)")
    print("2️⃣  Créer le 1er trimestre (Oct, Nov, Dec)")
    print("3️⃣  Créer le 2ème trimestre (Jan, Fév, Mar)")
    print("4️⃣  Créer le 3ème trimestre (Avr, Mai, Jun)")
    print("0️⃣  Quitter")
    
    choix = input("\n👉 Votre choix: ").strip()
    
    if choix == '0':
        return
    
    classe_id = input("ID de la classe (ex: 6): ").strip()
    nb_eleves = input("Nombre d'élèves (ex: 10): ").strip()
    
    try:
        classe_id = int(classe_id)
        nb_eleves = int(nb_eleves)
    except:
        print("❌ Valeurs invalides!")
        return
    
    if choix == '1':
        creer_annee_complete(classe_id, nb_eleves)
    elif choix in ['2', '3', '4']:
        creer_trimestre(classe_id, int(choix), nb_eleves)
    else:
        print("❌ Choix invalide!")

if __name__ == '__main__':
    import sys
    
    if len(sys.argv) > 1:
        if sys.argv[1] == '--annee':
            # python creer_annee_complete.py --annee 6 10
            classe = int(sys.argv[2]) if len(sys.argv) > 2 else 6
            eleves = int(sys.argv[3]) if len(sys.argv) > 3 else 10
            creer_annee_complete(classe, eleves)
        elif sys.argv[1] == '--trimestre':
            # python creer_annee_complete.py --trimestre 1 6 10
            trim = int(sys.argv[2]) if len(sys.argv) > 2 else 1
            classe = int(sys.argv[3]) if len(sys.argv) > 3 else 6
            eleves = int(sys.argv[4]) if len(sys.argv) > 4 else 10
            creer_trimestre(classe, trim, eleves)
    else:
        menu()
