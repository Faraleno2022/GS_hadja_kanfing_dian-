"""
Script pour réparer le lien entre les classes Eleve et ClasseNote
Résout le problème de décalage d'IDs
"""

import os
import sys
import django

# Configuration Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ecole_moderne.settings')
django.setup()

from notes.models import NoteMensuelle, ClasseNote, MatiereNote
from eleves.models import Eleve, Classe
from django.db import transaction

def analyser_probleme():
    """Analyse le problème de décalage entre les modèles"""
    print("\n" + "="*80)
    print("🔍 ANALYSE DU PROBLÈME DE DÉCALAGE")
    print("="*80)
    
    # 1. Chercher l'élève CL9-011
    print("\n1️⃣ ÉLÈVE CL9-011:")
    try:
        eleve = Eleve.objects.get(matricule='CL9-011')
        print(f"✅ Trouvé : {eleve.nom} {eleve.prenom}")
        print(f"   • Classe (Eleve) : {eleve.classe.nom}")
        print(f"   • Classe ID : {eleve.classe.id}")
        print(f"   • École : {eleve.classe.ecole.nom}")
        print(f"   • Année : {eleve.classe.annee_scolaire}")
        
        # 2. Chercher les ClasseNote correspondantes
        print(f"\n2️⃣ RECHERCHE ClasseNote pour '{eleve.classe.nom}':")
        
        # Recherche exacte
        classe_notes_exact = ClasseNote.objects.filter(
            nom__exact=eleve.classe.nom,
            annee_scolaire=eleve.classe.annee_scolaire
        )
        
        if classe_notes_exact.exists():
            print("   Correspondances EXACTES trouvées :")
            for cn in classe_notes_exact:
                print(f"   • ID {cn.id}: {cn.nom} ({cn.ecole.nom})")
        else:
            print("   ❌ Aucune correspondance exacte")
        
        # Recherche approximative
        classe_notes_approx = ClasseNote.objects.filter(
            nom__icontains='9',
            annee_scolaire=eleve.classe.annee_scolaire,
            ecole=eleve.classe.ecole
        )
        
        if classe_notes_approx.exists():
            print("\n   Correspondances APPROXIMATIVES (même école) :")
            for cn in classe_notes_approx:
                nb_matieres = MatiereNote.objects.filter(classe=cn).count()
                print(f"   • ID {cn.id}: {cn.nom} ({nb_matieres} matières)")
        
        return eleve, classe_notes_approx
        
    except Eleve.DoesNotExist:
        print("❌ Élève CL9-011 non trouvé")
        return None, None

def proposer_solution(eleve, classe_notes):
    """Propose une solution pour lier les classes"""
    print("\n" + "="*80)
    print("💡 SOLUTION PROPOSÉE")
    print("="*80)
    
    if not eleve or not classe_notes.exists():
        print("\n❌ Impossible de proposer une solution automatique")
        return None
    
    # Trouver la meilleure correspondance
    meilleure = None
    for cn in classe_notes:
        # Priorité à la correspondance exacte du nom
        if cn.nom.upper().replace('È', 'E') == eleve.classe.nom.upper().replace('È', 'E'):
            meilleure = cn
            break
    
    # Si pas de correspondance exacte, prendre la première
    if not meilleure:
        meilleure = classe_notes.first()
    
    print(f"\n✅ ClasseNote recommandée : {meilleure.nom} (ID: {meilleure.id})")
    print(f"   • École : {meilleure.ecole.nom}")
    print(f"   • Année : {meilleure.annee_scolaire}")
    
    # Vérifier les matières
    matieres = MatiereNote.objects.filter(classe=meilleure)
    print(f"\n📚 Matières disponibles : {matieres.count()}")
    
    if matieres.exists():
        for m in matieres[:5]:
            print(f"   • {m.nom} (Coef: {m.coefficient})")
        if matieres.count() > 5:
            print(f"   ... et {matieres.count() - 5} autres")
    
    return meilleure

def creer_notes_pour_eleve(eleve, classe_note, mois='OCTOBRE'):
    """Créer des notes de test pour un élève spécifique"""
    print("\n" + "="*80)
    print("🎲 CRÉATION DE NOTES DE TEST")
    print("="*80)
    
    if not eleve or not classe_note:
        print("❌ Paramètres manquants")
        return False
    
    # Confirmation
    print(f"\n⚠️ Cette action va créer des notes de test pour :")
    print(f"   • Élève : {eleve.matricule} - {eleve.nom} {eleve.prenom}")
    print(f"   • ClasseNote : {classe_note.nom} (ID: {classe_note.id})")
    print(f"   • Mois : {mois}")
    
    reponse = input("\n👉 Continuer ? (oui/non) : ")
    if reponse.lower() not in ['oui', 'o', 'yes', 'y']:
        print("❌ Opération annulée")
        return False
    
    try:
        with transaction.atomic():
            # Récupérer les matières
            matieres = MatiereNote.objects.filter(classe=classe_note)
            
            if not matieres.exists():
                print("❌ Aucune matière configurée pour cette classe")
                return False
            
            notes_creees = 0
            import random
            from decimal import Decimal
            
            for matiere in matieres:
                # Vérifier si la note existe déjà
                exists = NoteMensuelle.objects.filter(
                    eleve=eleve,
                    matiere=matiere,
                    mois=mois,
                    annee_scolaire=classe_note.annee_scolaire
                ).exists()
                
                if not exists:
                    # Générer une note aléatoire entre 10 et 17
                    note_value = Decimal(str(random.uniform(10, 17))).quantize(Decimal('0.1'))
                    
                    NoteMensuelle.objects.create(
                        eleve=eleve,
                        matiere=matiere,
                        mois=mois,
                        annee_scolaire=classe_note.annee_scolaire,
                        note=note_value,
                        absent=False,
                        observations="Note de test"
                    )
                    notes_creees += 1
                    print(f"   ✅ {matiere.nom}: {note_value}/20")
            
            print(f"\n✅ {notes_creees} notes créées avec succès !")
            return True
            
    except Exception as e:
        print(f"❌ Erreur : {e}")
        return False

def creer_notes_pour_tous(classe_note, mois='OCTOBRE'):
    """Créer des notes pour tous les élèves de la classe"""
    print("\n" + "="*80)
    print("🎲 CRÉATION DE NOTES POUR TOUTE LA CLASSE")
    print("="*80)
    
    if not classe_note:
        print("❌ ClasseNote manquante")
        return False
    
    # Trouver tous les élèves de cette classe
    # Recherche flexible du nom
    nom_recherche = classe_note.nom.replace('È', 'E').replace('é', 'e')
    
    eleves = Eleve.objects.filter(
        classe__nom__icontains=nom_recherche.split()[0],  # Prendre le premier mot (ex: "9ÈME")
        classe__annee_scolaire=classe_note.annee_scolaire,
        statut__in=['ACTIF', 'INSCRIT']
    )
    
    print(f"\n👥 Élèves trouvés : {eleves.count()}")
    
    if not eleves.exists():
        print("❌ Aucun élève trouvé pour cette classe")
        return False
    
    # Afficher quelques élèves
    print("\nÉlèves concernés :")
    for e in eleves[:5]:
        print(f"   • {e.matricule} - {e.nom} {e.prenom}")
    if eleves.count() > 5:
        print(f"   ... et {eleves.count() - 5} autres")
    
    # Confirmation
    print(f"\n⚠️ Créer des notes pour {eleves.count()} élèves ?")
    reponse = input("👉 Continuer ? (oui/non) : ")
    if reponse.lower() not in ['oui', 'o', 'yes', 'y']:
        print("❌ Opération annulée")
        return False
    
    # Créer les notes
    matieres = MatiereNote.objects.filter(classe=classe_note)
    
    if not matieres.exists():
        print("❌ Aucune matière configurée")
        return False
    
    print(f"\n📚 Création de notes pour {matieres.count()} matières...")
    
    import random
    from decimal import Decimal
    
    total_notes = 0
    
    with transaction.atomic():
        for eleve in eleves:
            for matiere in matieres:
                # Vérifier si existe déjà
                exists = NoteMensuelle.objects.filter(
                    eleve=eleve,
                    matiere=matiere,
                    mois=mois,
                    annee_scolaire=classe_note.annee_scolaire
                ).exists()
                
                if not exists:
                    # Note aléatoire entre 8 et 18
                    note = Decimal(str(random.uniform(8, 18))).quantize(Decimal('0.1'))
                    
                    # 5% d'absences
                    absent = random.random() < 0.05
                    
                    NoteMensuelle.objects.create(
                        eleve=eleve,
                        matiere=matiere,
                        mois=mois,
                        annee_scolaire=classe_note.annee_scolaire,
                        note=None if absent else note,
                        absent=absent,
                        observations="Note de test" if not absent else "Absent"
                    )
                    total_notes += 1
    
    print(f"\n✅ {total_notes} notes créées avec succès !")
    
    # Afficher un échantillon
    print("\n📊 Échantillon :")
    sample = NoteMensuelle.objects.filter(
        eleve__in=eleves[:2],
        mois=mois,
        annee_scolaire=classe_note.annee_scolaire
    )[:5]
    
    for n in sample:
        status = "ABSENT" if n.absent else f"{n.note}/20"
        print(f"   • {n.eleve.matricule} - {n.matiere.nom}: {status}")
    
    return True

def afficher_url_bulletin(eleve, classe_note):
    """Affiche l'URL correcte pour accéder au bulletin"""
    print("\n" + "="*80)
    print("🌐 URL DU BULLETIN")
    print("="*80)
    
    if eleve and classe_note:
        url = f"https://www.myschoolgn.space/notes/bulletins/"
        params = f"?classe_id={classe_note.id}&eleve_id={eleve.id}&periode=OCTOBRE&system_type=mensuel"
        
        print(f"\n✅ URL pour tester :")
        print(f"   {url}{params}")
        
        print(f"\n📋 Paramètres :")
        print(f"   • Classe ID : {classe_note.id}")
        print(f"   • Élève ID : {eleve.id}")
        print(f"   • Période : OCTOBRE")
        print(f"   • Système : mensuel")

def menu_principal():
    """Menu principal du script"""
    print("\n" + "="*80)
    print("🔧 RÉPARATEUR DE LIENS CLASSE-NOTES")
    print("="*80)
    
    # Analyse
    eleve, classe_notes = analyser_probleme()
    
    if not eleve:
        print("\n❌ Impossible de continuer sans l'élève CL9-011")
        return
    
    # Solution
    classe_note = proposer_solution(eleve, classe_notes)
    
    if not classe_note:
        print("\n❌ Aucune ClasseNote compatible trouvée")
        return
    
    # Menu d'actions
    print("\n" + "-"*80)
    print("ACTIONS DISPONIBLES :")
    print("1. Créer des notes pour CL9-011 uniquement")
    print("2. Créer des notes pour TOUTE la classe")
    print("3. Afficher l'URL du bulletin")
    print("4. Tout faire (1 + 3)")
    print("5. Quitter")
    
    choix = input("\nVotre choix (1-5) : ")
    
    if choix == "1":
        if creer_notes_pour_eleve(eleve, classe_note):
            afficher_url_bulletin(eleve, classe_note)
    elif choix == "2":
        creer_notes_pour_tous(classe_note)
    elif choix == "3":
        afficher_url_bulletin(eleve, classe_note)
    elif choix == "4":
        if creer_notes_pour_eleve(eleve, classe_note):
            afficher_url_bulletin(eleve, classe_note)
    elif choix == "5":
        print("\n👋 Au revoir !")
    else:
        print("\n❌ Choix invalide")

if __name__ == "__main__":
    menu_principal()
    print("\n" + "="*80)
    print("✅ TERMINÉ")
    print("="*80)
