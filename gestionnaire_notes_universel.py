"""
Gestionnaire universel de notes mensuelles
Fonctionne pour toutes les classes et tous les mois
"""

import os
import sys
import django
import random
from decimal import Decimal
from datetime import datetime

# Configuration Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ecole_moderne.settings')
django.setup()

from notes.models import NoteMensuelle, ClasseNote, MatiereNote
from eleves.models import Eleve, Classe
from django.db import transaction
from django.db.models import Count, Avg, Q

def lister_toutes_classes():
    """Liste toutes les classes disponibles"""
    print("\n" + "="*80)
    print("📚 TOUTES LES CLASSES DISPONIBLES")
    print("="*80)
    
    # Classes dans ClasseNote (pour les notes)
    print("\n🎯 Classes configurées pour les notes (ClasseNote):")
    classes_notes = ClasseNote.objects.all().order_by('nom', 'annee_scolaire')
    
    if classes_notes.exists():
        for cn in classes_notes:
            nb_matieres = MatiereNote.objects.filter(classe=cn).count()
            
            # Compter les élèves correspondants
            classe_eleve = Classe.objects.filter(
                nom__icontains=cn.nom.replace('È', 'E').replace('è', 'e'),
                annee_scolaire=cn.annee_scolaire
            ).first()
            
            nb_eleves = 0
            if classe_eleve:
                nb_eleves = Eleve.objects.filter(
                    classe=classe_eleve, 
                    statut__in=['ACTIF', 'INSCRIT']
                ).count()
            
            print(f"\n   ID {cn.id:3}: {cn.nom:30} ({cn.annee_scolaire})")
            print(f"           École: {cn.ecole.nom if cn.ecole else 'Non définie'}")
            print(f"           Matières: {nb_matieres:2} | Élèves: {nb_eleves:3}")
    else:
        print("   ❌ Aucune classe configurée")
    
    # Classes dans le modèle Eleve
    print("\n" + "-"*80)
    print("👥 Classes avec élèves (Classe):")
    classes_eleves = Classe.objects.annotate(
        nb_eleves=Count('eleves', filter=Q(eleves__statut__in=['ACTIF', 'INSCRIT']))
    ).filter(nb_eleves__gt=0).order_by('nom')
    
    if classes_eleves.exists():
        for ce in classes_eleves[:10]:  # Limiter à 10 pour éviter trop d'affichage
            print(f"   • {ce.nom:30} ({ce.annee_scolaire}) - {ce.nb_eleves} élèves")
        
        if classes_eleves.count() > 10:
            print(f"   ... et {classes_eleves.count() - 10} autres classes")
    else:
        print("   ❌ Aucune classe avec élèves")
    
    return classes_notes, classes_eleves

def analyser_classe(nom_classe=None):
    """Analyse une classe spécifique"""
    print("\n" + "="*80)
    print(f"🔍 ANALYSE DE CLASSE : {nom_classe if nom_classe else 'Sélection interactive'}")
    print("="*80)
    
    if not nom_classe:
        # Afficher les classes disponibles
        classes_notes, _ = lister_toutes_classes()
        
        print("\n👉 Entrez l'ID de la ClasseNote à analyser")
        print("   (ou le nom/partie du nom) : ", end='')
        choix = input().strip()
        
        if choix.isdigit():
            # Recherche par ID
            classe_note = ClasseNote.objects.filter(id=int(choix)).first()
        else:
            # Recherche par nom
            classe_note = ClasseNote.objects.filter(
                nom__icontains=choix
            ).order_by('-annee_scolaire').first()
    else:
        # Recherche directe
        classe_note = ClasseNote.objects.filter(
            nom__icontains=nom_classe
        ).order_by('-annee_scolaire').first()
    
    if not classe_note:
        print("❌ Classe non trouvée")
        return None
    
    print(f"\n✅ Classe sélectionnée : {classe_note.nom}")
    print(f"   • ID : {classe_note.id}")
    print(f"   • Année : {classe_note.annee_scolaire}")
    print(f"   • École : {classe_note.ecole.nom if classe_note.ecole else 'Non définie'}")
    
    # Matières
    matieres = MatiereNote.objects.filter(classe=classe_note)
    print(f"\n📚 Matières configurées : {matieres.count()}")
    if matieres.exists():
        for m in matieres[:5]:
            print(f"   • {m.nom} (Coef: {m.coefficient})")
        if matieres.count() > 5:
            print(f"   ... et {matieres.count() - 5} autres")
    
    # Élèves correspondants
    nom_recherche = classe_note.nom.replace('È', 'E').replace('è', 'e')
    eleves = Eleve.objects.filter(
        Q(classe__nom__icontains=nom_recherche) |
        Q(classe__nom__icontains=nom_recherche.split()[0]),  # Premier mot
        classe__annee_scolaire=classe_note.annee_scolaire,
        statut__in=['ACTIF', 'INSCRIT']
    )
    
    print(f"\n👥 Élèves trouvés : {eleves.count()}")
    if eleves.exists():
        for e in eleves[:5]:
            print(f"   • {e.matricule} - {e.nom} {e.prenom}")
        if eleves.count() > 5:
            print(f"   ... et {eleves.count() - 5} autres")
    
    # Statistiques des notes
    for mois in ['OCTOBRE', 'NOVEMBRE', 'DÉCEMBRE']:
        notes = NoteMensuelle.objects.filter(
            matiere__classe=classe_note,
            mois=mois,
            annee_scolaire=classe_note.annee_scolaire
        ).values('eleve').distinct().count()
        
        if notes > 0:
            print(f"\n📊 Notes {mois} : {notes}/{eleves.count()} élèves")
    
    return classe_note

def creer_notes_classe(classe_note=None, mois=None, mode='test'):
    """Créer des notes pour une classe"""
    print("\n" + "="*80)
    print("🎲 CRÉATION DE NOTES")
    print("="*80)
    
    # Sélection de la classe
    if not classe_note:
        classe_note = analyser_classe()
        if not classe_note:
            return False
    
    # Sélection du mois
    if not mois:
        print("\n📅 Sélectionnez le mois :")
        mois_disponibles = [
            'JANVIER', 'FÉVRIER', 'MARS', 'AVRIL', 'MAI', 'JUIN',
            'JUILLET', 'AOÛT', 'SEPTEMBRE', 'OCTOBRE', 'NOVEMBRE', 'DÉCEMBRE'
        ]
        
        mois_actuel = datetime.now().month
        
        for i, m in enumerate(mois_disponibles, 1):
            marqueur = " ← Mois actuel" if i == mois_actuel else ""
            print(f"   {i:2}. {m}{marqueur}")
        
        choix = input("\nVotre choix (1-12) : ").strip()
        
        try:
            mois = mois_disponibles[int(choix) - 1]
        except (ValueError, IndexError):
            print("❌ Choix invalide, utilisation d'OCTOBRE")
            mois = 'OCTOBRE'
    
    print(f"\n📋 Paramètres sélectionnés :")
    print(f"   • Classe : {classe_note.nom}")
    print(f"   • Mois : {mois}")
    print(f"   • Mode : {mode}")
    
    # Trouver les élèves
    nom_recherche = classe_note.nom.replace('È', 'E').replace('è', 'e')
    
    # Recherche flexible pour trouver les élèves
    eleves = Eleve.objects.filter(
        statut__in=['ACTIF', 'INSCRIT']
    ).filter(
        Q(classe__nom__icontains=nom_recherche) |
        Q(classe__nom__icontains=nom_recherche.split()[0]) |  # Premier mot
        Q(classe__nom__icontains='11') if '11' in nom_recherche else Q()  # Si c'est 11ème
    ).filter(
        classe__annee_scolaire=classe_note.annee_scolaire
    )
    
    if not eleves.exists():
        print(f"\n❌ Aucun élève trouvé pour {classe_note.nom}")
        print("   Essayons une recherche plus large...")
        
        # Recherche encore plus flexible
        if '11' in classe_note.nom:
            eleves = Eleve.objects.filter(
                classe__nom__icontains='11',
                statut__in=['ACTIF', 'INSCRIT']
            )
        
        if eleves.exists():
            print(f"   ✅ {eleves.count()} élèves trouvés avec recherche élargie")
        else:
            return False
    
    print(f"\n👥 {eleves.count()} élèves trouvés")
    
    # Matières
    matieres = MatiereNote.objects.filter(classe=classe_note)
    
    if not matieres.exists():
        print("❌ Aucune matière configurée pour cette classe")
        return False
    
    print(f"📚 {matieres.count()} matières configurées")
    
    # Confirmation
    print(f"\n⚠️ Cette action va créer {eleves.count() * matieres.count()} notes")
    reponse = input("👉 Continuer ? (oui/non) : ")
    
    if reponse.lower() not in ['oui', 'o', 'yes', 'y']:
        print("❌ Opération annulée")
        return False
    
    # Création des notes
    print("\n⏳ Création des notes en cours...")
    
    notes_creees = 0
    notes_existantes = 0
    
    with transaction.atomic():
        for eleve in eleves:
            for matiere in matieres:
                # Vérifier si la note existe déjà
                exists = NoteMensuelle.objects.filter(
                    eleve=eleve,
                    matiere=matiere,
                    mois=mois,
                    annee_scolaire=classe_note.annee_scolaire
                ).exists()
                
                if exists:
                    notes_existantes += 1
                else:
                    # Générer la note selon le mode
                    if mode == 'test':
                        # Notes aléatoires entre 8 et 18
                        note = Decimal(str(random.uniform(8, 18))).quantize(Decimal('0.1'))
                        absent = random.random() < 0.05  # 5% d'absences
                    elif mode == 'vide':
                        # Notes vides (à saisir plus tard)
                        note = None
                        absent = False
                    else:
                        # Mode réel - demander la note
                        print(f"{eleve.matricule} - {matiere.nom} : ", end='')
                        saisie = input().strip()
                        
                        if saisie.upper() in ['ABS', 'ABSENT']:
                            note = None
                            absent = True
                        elif saisie == '':
                            note = None
                            absent = False
                        else:
                            try:
                                note = Decimal(saisie).quantize(Decimal('0.1'))
                                absent = False
                            except:
                                note = None
                                absent = False
                    
                    # Créer la note
                    NoteMensuelle.objects.create(
                        eleve=eleve,
                        matiere=matiere,
                        mois=mois,
                        annee_scolaire=classe_note.annee_scolaire,
                        note=note if not absent else None,
                        absent=absent,
                        observations="Note de test" if mode == 'test' else ""
                    )
                    notes_creees += 1
    
    print(f"\n✅ Terminé !")
    print(f"   • Notes créées : {notes_creees}")
    print(f"   • Notes existantes : {notes_existantes}")
    
    # Afficher un échantillon
    if notes_creees > 0:
        print("\n📊 Échantillon des notes créées :")
        sample = NoteMensuelle.objects.filter(
            matiere__classe=classe_note,
            mois=mois,
            annee_scolaire=classe_note.annee_scolaire
        ).order_by('-date_creation')[:5]
        
        for n in sample:
            status = "ABSENT" if n.absent else f"{n.note}/20" if n.note else "Non saisi"
            print(f"   • {n.eleve.matricule} - {n.matiere.nom}: {status}")
    
    return True

def statistiques_globales():
    """Affiche les statistiques globales"""
    print("\n" + "="*80)
    print("📊 STATISTIQUES GLOBALES")
    print("="*80)
    
    # Total des notes
    total = NoteMensuelle.objects.count()
    print(f"\n📈 Total des notes mensuelles : {total}")
    
    # Par mois
    print("\n📅 Par mois :")
    mois_stats = NoteMensuelle.objects.values('mois').annotate(
        nb=Count('id'),
        moy=Avg('note')
    ).order_by('mois')
    
    for ms in mois_stats:
        moyenne = f"{ms['moy']:.2f}" if ms['moy'] else "N/A"
        print(f"   • {ms['mois']:10} : {ms['nb']:5} notes (Moy: {moyenne})")
    
    # Par année scolaire
    print("\n🎓 Par année scolaire :")
    annee_stats = NoteMensuelle.objects.values('annee_scolaire').annotate(
        nb=Count('id')
    ).order_by('-annee_scolaire')
    
    for a in annee_stats:
        print(f"   • {a['annee_scolaire']} : {a['nb']} notes")
    
    # Classes avec le plus de notes
    print("\n🏆 Top 5 classes avec le plus de notes :")
    
    top_classes = []
    for cn in ClasseNote.objects.all():
        nb_notes = NoteMensuelle.objects.filter(
            matiere__classe=cn
        ).count()
        
        if nb_notes > 0:
            top_classes.append((cn, nb_notes))
    
    top_classes.sort(key=lambda x: x[1], reverse=True)
    
    for cn, nb in top_classes[:5]:
        print(f"   • {cn.nom} ({cn.annee_scolaire}) : {nb} notes")
    
    # Classes sans notes
    print("\n⚠️ Classes SANS notes :")
    classes_sans_notes = []
    
    for cn in ClasseNote.objects.all():
        nb_notes = NoteMensuelle.objects.filter(
            matiere__classe=cn
        ).count()
        
        if nb_notes == 0:
            nb_matieres = MatiereNote.objects.filter(classe=cn).count()
            
            # Compter les élèves
            nom_recherche = cn.nom.replace('È', 'E').replace('è', 'e')
            nb_eleves = Eleve.objects.filter(
                classe__nom__icontains=nom_recherche.split()[0],
                classe__annee_scolaire=cn.annee_scolaire,
                statut__in=['ACTIF', 'INSCRIT']
            ).count()
            
            if nb_eleves > 0:  # Seulement si il y a des élèves
                classes_sans_notes.append((cn, nb_eleves, nb_matieres))
    
    if classes_sans_notes:
        for cn, nb_eleves, nb_matieres in classes_sans_notes:
            print(f"   • {cn.nom} : {nb_eleves} élèves, {nb_matieres} matières")
    else:
        print("   ✅ Toutes les classes ont des notes")

def menu_principal():
    """Menu principal interactif"""
    while True:
        print("\n" + "="*80)
        print("🎓 GESTIONNAIRE UNIVERSEL DE NOTES MENSUELLES")
        print("="*80)
        print("\n1. Lister toutes les classes")
        print("2. Analyser une classe spécifique")
        print("3. Créer des notes de TEST (aléatoires)")
        print("4. Créer des notes VIDES (à saisir plus tard)")
        print("5. Statistiques globales")
        print("6. Recherche classe 11ème")
        print("7. Quitter")
        
        choix = input("\nVotre choix (1-7) : ").strip()
        
        if choix == "1":
            lister_toutes_classes()
        
        elif choix == "2":
            analyser_classe()
        
        elif choix == "3":
            creer_notes_classe(mode='test')
        
        elif choix == "4":
            creer_notes_classe(mode='vide')
        
        elif choix == "5":
            statistiques_globales()
        
        elif choix == "6":
            # Recherche spécifique pour 11ème
            print("\n🔍 Recherche des classes 11ème...")
            
            # Dans ClasseNote
            classes_11_notes = ClasseNote.objects.filter(
                Q(nom__icontains='11') | Q(nom__icontains='onz')
            )
            
            if classes_11_notes.exists():
                print(f"\n✅ {classes_11_notes.count()} classe(s) 11ème trouvée(s) :")
                for cn in classes_11_notes:
                    print(f"   • ID {cn.id}: {cn.nom} ({cn.annee_scolaire})")
                    
                    # Analyser automatiquement la première
                    analyser_classe(cn.nom)
                    
                    print("\n👉 Créer des notes pour cette classe ?")
                    reponse = input("   (oui/non) : ")
                    if reponse.lower() in ['oui', 'o', 'yes', 'y']:
                        creer_notes_classe(cn)
            else:
                print("❌ Aucune classe 11ème trouvée dans ClasseNote")
                
                # Chercher dans les classes d'élèves
                classes_11_eleves = Classe.objects.filter(
                    Q(nom__icontains='11') | Q(nom__icontains='onz')
                )
                
                if classes_11_eleves.exists():
                    print(f"\n⚠️ {classes_11_eleves.count()} classe(s) 11ème dans le modèle Eleve :")
                    for ce in classes_11_eleves:
                        nb = Eleve.objects.filter(classe=ce, statut__in=['ACTIF', 'INSCRIT']).count()
                        print(f"   • {ce.nom} ({ce.annee_scolaire}) - {nb} élèves")
                    
                    print("\n❌ Mais aucune ClasseNote correspondante configurée")
                    print("   Solution : Créer la ClasseNote dans l'admin Django")
        
        elif choix == "7":
            print("\n👋 Au revoir !")
            break
        
        else:
            print("❌ Choix invalide")

if __name__ == "__main__":
    # Si arguments passés, mode direct
    import sys
    
    if len(sys.argv) > 1:
        if sys.argv[1] == '--stats':
            statistiques_globales()
        elif sys.argv[1] == '--list':
            lister_toutes_classes()
        elif sys.argv[1] == '--11eme':
            # Mode direct 11ème
            classes_11 = ClasseNote.objects.filter(
                Q(nom__icontains='11') | Q(nom__icontains='onz')
            ).first()
            if classes_11:
                creer_notes_classe(classes_11, 'OCTOBRE', 'test')
            else:
                print("❌ Aucune classe 11ème trouvée")
        else:
            print(f"❌ Argument inconnu : {sys.argv[1]}")
            print("   Options : --stats, --list, --11eme")
    else:
        # Mode interactif
        menu_principal()
    
    print("\n" + "="*80)
    print("✅ TERMINÉ")
    print("="*80)
