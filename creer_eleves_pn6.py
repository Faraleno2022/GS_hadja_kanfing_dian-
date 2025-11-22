#!/usr/bin/env python
"""
Script pour créer les élèves manquants avec matricules PN6-xxx
"""

import os
import sys
import django

# Configuration Django
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ecole_moderne.settings')
django.setup()

from eleves.models import Eleve, Classe as ClasseEleve, Ecole, Responsable
from notes.models import ClasseNote, MatiereNote
from django.contrib.auth.models import User
from datetime import date

def creer_eleves_pn6():
    """Crée les élèves manquants avec matricules PN6-xxx"""
    
    print("🏫 CRÉATION DES ÉLÈVES PN6")
    print("=" * 50)
    
    # Liste des élèves à créer (extraite du message d'erreur)
    eleves_a_creer = [
        ("PN6-032", "ABOUBACAR", "CAMARA"),
        ("PN6-055", "ABOUBACAR SIDIKI", "DIARRA"),
        ("PN6-035", "ALEXANDRE", "TRAORE"),
        ("PN6-048", "ALHASSANE", "BANGOURA"),
        ("PN6-063", "ALI BADRA", "SANGARE"),
        ("PN6-040", "AMADOU", "KOUYATE"),
        ("PN6-049", "AMINATA", "FOFANA"),
        ("PN6-054", "BEATRICE JUNIOR", "SANDOUNO"),
        ("PN6-007", "BOUNTOURABY", "DIALLO"),
        ("PN6-051", "BOUNTOURABY", "SYLLA"),
        ("PN6-036", "CHEICK DJIBRIL HADY", "DIANE"),
        ("PN6-031", "DOUSOUBA", "CONDE"),
        ("PN6-041", "ELHADJ AMADOU FOULAH", "BALDE"),
        ("PN6-050", "FATOUMATA", "CAMARA"),
        ("PN6-043", "FATOUMATA", "CONTE"),
        ("PN6-005", "FATOUMATA DJARAYE", "TOURE"),
        ("PN6-061", "FATOUMATA BINTA", "SYLLA"),
        ("PN6-045", "HASSANATOU", "BAH"),
        ("PN6-038", "KALAGBAN KAZADI", "DIALLO"),
        ("PN6-033", "KANY", "DIARRA"),
        ("PN6-046", "LEONIE NEMA", "KOUROUMA"),
        ("PN6-062", "MAMADOU", "MAGASSOUBA"),
        ("PN6-057", "MAMADOU SALIOU", "BALDE"),
        ("P6-002", "MARIAME", "DOUMBOUYA"),  # Note: P6 au lieu de PN6
        ("PN6-053", "MARIAME", "DOUMBOUYA"),
        ("PN6-060", "MOHAMED", "KANTE"),
        ("PN6-065", "MOHAMED", "KANTÉ"),
        ("PN6-047", "MOHAMED LAMINE", "BANGOURA"),
        ("PN6-039", "MOHAMED LAMINE", "SOUMAH"),
        ("PN6-006", "MORIBA GUILAVO", "GUILAVOGUI"),
        ("PN6-037", "MOUSSA", "DIARRA"),
        ("PN6-030", "NANA", "TRAORE"),
        ("PN6-056", "NENE ADAMA", "CAMARA"),
        ("PN6-058", "OUMAR YAYA", "CAMARA"),
        ("PN6-059", "OUMERKIL", "DIABY"),
        ("PN6-042", "ROUGOUIATA", "DIALLO"),
        ("PN6-064", "SANSSSO", "CAMARA"),
        ("PN6-052", "SONNAH", "KEITA"),
        ("PN6-034", "TIGUIDANTKE", "DIALLO"),
    ]
    
    print(f"📋 {len(eleves_a_creer)} élèves à créer")
    
    # 1. Trouver ou créer l'école
    ecole = Ecole.objects.filter(nom__icontains="HADJA KANFING DIAN").first()
    if not ecole:
        print("❌ École HADJA KANFING DIAN non trouvée")
        return
    
    print(f"🏫 École: {ecole.nom}")
    
    # 2. Trouver ou créer la classe PN6 (Primaire 6ème)
    classe_eleve = ClasseEleve.objects.filter(
        nom="PN6",
        ecole=ecole,
        annee_scolaire="2024-2025"
    ).first()
    
    if not classe_eleve:
        print("📚 Création de la classe PN6...")
        classe_eleve = ClasseEleve.objects.create(
            nom="PN6",
            niveau="PRIMAIRE_6",
            ecole=ecole,
            annee_scolaire="2024-2025",
            code_matricule="PN6",
            capacite_max=50
        )
        print(f"✅ Classe créée: {classe_eleve.nom} (ID: {classe_eleve.id})")
    else:
        print(f"✅ Classe existante: {classe_eleve.nom} (ID: {classe_eleve.id})")
    
    # 3. Trouver ou créer la ClasseNote correspondante
    classe_note = ClasseNote.objects.filter(
        nom="PN6",
        ecole=ecole,
        annee_scolaire="2024-2025"
    ).first()
    
    if not classe_note:
        print("📝 Création de la ClasseNote PN6...")
        classe_note = ClasseNote.objects.create(
            nom="PN6",
            niveau="PRIMAIRE",
            ecole=ecole,
            annee_scolaire="2024-2025",
            actif=True
        )
        print(f"✅ ClasseNote créée: {classe_note.nom} (ID: {classe_note.id})")
        
        # Créer les matières de base pour le primaire
        matieres_primaire = [
            ("Anglais", "ANG", 1.0),
            ("Calcul-problème", "CALC", 1.0),
            ("Dictée et Questions", "DICT", 1.0),
            ("Education Civique et Morale", "ECM", 1.0),
            ("Education Physique et Sportive", "EPS", 1.0),
            ("Géographie", "GEO", 1.0),
            ("Histoire", "HIST", 1.0),
            ("Lecture", "LECT", 1.0),
            ("Rédaction", "REDA", 1.0),
            ("Sciences d'observation", "SCIO", 1.0),
        ]
        
        print("📚 Création des matières...")
        for nom_matiere, code_matiere, coef in matieres_primaire:
            # Vérifier si la matière existe déjà
            matiere_existante = MatiereNote.objects.filter(
                classe=classe_note,
                code=code_matiere
            ).first()
            
            if matiere_existante:
                print(f"  ⚠️  {nom_matiere} - Déjà existante")
                continue
            
            matiere = MatiereNote.objects.create(
                nom=nom_matiere,
                code=code_matiere,
                classe=classe_note,
                coefficient=coef,
                actif=True
            )
            print(f"  ✅ {nom_matiere} ({code_matiere}) - Coef: {coef}")
    else:
        print(f"✅ ClasseNote existante: {classe_note.nom} (ID: {classe_note.id})")
    
    # 4. Créer un responsable par défaut
    responsable_defaut = Responsable.objects.filter(
        nom="PARENT",
        prenom="DEFAUT"
    ).first()
    
    if not responsable_defaut:
        print("👨‍👩‍👧‍👦 Création du responsable par défaut...")
        responsable_defaut = Responsable.objects.create(
            prenom="DEFAUT",
            nom="PARENT",
            relation="TUTEUR",
            telephone="+224000000000",
            adresse="Adresse à compléter",
            profession="À renseigner"
        )
        print(f"✅ Responsable créé: {responsable_defaut.nom_complet}")
    
    # 5. Créer les élèves
    print(f"\n👥 CRÉATION DES ÉLÈVES")
    print("-" * 30)
    
    eleves_crees = 0
    eleves_existants = 0
    
    for matricule, prenom, nom in eleves_a_creer:
        # Vérifier si l'élève existe déjà
        eleve_existant = Eleve.objects.filter(matricule=matricule).first()
        
        if eleve_existant:
            print(f"⚠️  {matricule}: {prenom} {nom} - Déjà existant")
            eleves_existants += 1
            continue
        
        # Déterminer le sexe basé sur le prénom (approximatif)
        prenoms_feminins = [
            "AMINATA", "FATOUMATA", "HASSANATOU", "KANY", "LEONIE", 
            "MARIAME", "ROUGOUIATA", "BEATRICE"
        ]
        
        sexe = "F" if any(p in prenom.upper() for p in prenoms_feminins) else "M"
        
        # Créer l'élève
        try:
            eleve = Eleve.objects.create(
                matricule=matricule,
                prenom=prenom,
                nom=nom,
                sexe=sexe,
                date_naissance=date(2012, 1, 1),  # Date approximative pour PN6
                lieu_naissance="Conakry",  # Lieu par défaut
                classe=classe_eleve,
                date_inscription=date(2024, 9, 1),  # Date d'inscription
                responsable_principal=responsable_defaut,
                statut="ACTIF"
            )
            
            print(f"✅ {matricule}: {prenom} {nom} ({sexe})")
            eleves_crees += 1
            
        except Exception as e:
            print(f"❌ {matricule}: {prenom} {nom} - Erreur: {e}")
    
    # 6. Résumé
    print(f"\n📊 RÉSUMÉ")
    print("=" * 30)
    print(f"✅ Élèves créés: {eleves_crees}")
    print(f"⚠️  Élèves déjà existants: {eleves_existants}")
    print(f"📚 Classe: {classe_eleve.nom} (ID: {classe_eleve.id})")
    print(f"📝 ClasseNote: {classe_note.nom} (ID: {classe_note.id})")
    print(f"📋 Matières créées: {MatiereNote.objects.filter(classe=classe_note).count()}")
    
    # 7. Vérification finale
    print(f"\n🔍 VÉRIFICATION")
    print("-" * 20)
    
    eleves_pn6 = Eleve.objects.filter(matricule__startswith="PN6", classe=classe_eleve)
    print(f"Total élèves PN6 dans la classe: {eleves_pn6.count()}")
    
    if eleves_pn6.exists():
        print("Quelques exemples:")
        for eleve in eleves_pn6[:5]:
            print(f"  - {eleve.matricule}: {eleve.prenom} {eleve.nom}")
    
    print(f"\n🎯 PROCHAINES ÉTAPES")
    print("=" * 30)
    print("1. Importer les notes avec les matricules PN6-xxx")
    print("2. Consulter les notes via:")
    print(f"   /notes/consulter/?classe_id={classe_note.id}&periode=OCTOBRE")
    print("3. Compléter les informations des responsables si nécessaire")

if __name__ == "__main__":
    try:
        creer_eleves_pn6()
    except Exception as e:
        print(f"❌ Erreur lors de la création: {e}")
        import traceback
        traceback.print_exc()
