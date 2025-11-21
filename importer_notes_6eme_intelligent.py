#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Import intelligent des notes pour la 6ème Année
Détection automatique des élèves par similarité de noms
"""
import os
import sys
import django

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ecole_moderne.settings')
django.setup()

from django.db import transaction
from notes.models import ClasseNote, MatiereNote, NoteMensuelle
from eleves.models import Eleve
from decimal import Decimal
from data_notes_6eme import NOTES_DATA, MATIERES


def normaliser_nom(nom):
    """Normalise un nom pour comparaison"""
    return nom.lower().strip().replace("  ", " ").replace(".", "").replace("-", " ")


def similarite_noms(nom1, nom2):
    """Calcule la similarité entre deux noms"""
    n1 = set(normaliser_nom(nom1).split())
    n2 = set(normaliser_nom(nom2).split())
    
    if not n1 or not n2:
        return 0.0
    
    intersection = n1 & n2
    union = n1 | n2
    
    return len(intersection) / len(union)


def trouver_eleve(nom_tableau, eleves):
    """Trouve l'élève correspondant par similarité"""
    meilleur = None
    meilleur_score = 0.0
    
    for eleve in eleves:
        nom_complet = f"{eleve.prenom} {eleve.nom}"
        score = similarite_noms(nom_tableau, nom_complet)
        
        if score > meilleur_score:
            meilleur = eleve
            meilleur_score = score
    
    # Seuil de confiance: 50%
    return (meilleur, meilleur_score) if meilleur_score >= 0.5 else (None, 0.0)


@transaction.atomic
def importer_notes(periode="NOVEMBRE", annee_scolaire="2024-2025", dry_run=False):
    """
    Importe les notes avec détection intelligente
    
    Args:
        periode: Période (NOVEMBRE, DECEMBRE, etc.)
        annee_scolaire: Année scolaire (2024-2025)
        dry_run: Si True, n'enregistre pas (test uniquement)
    """
    print("=" * 80)
    print("  🎯 IMPORT INTELLIGENT DES NOTES - 6ÈME ANNÉE")
    print("=" * 80)
    
    # 1. Identifier la classe
    print("\n🔍 Étape 1: Recherche de la classe...")
    
    # Chercher d'abord "6ÈME ANNÉE"
    classe = ClasseNote.objects.filter(nom__icontains="6ÈME ANNÉE").first()
    
    # Si pas trouvé, chercher "CM2" (équivalent 6ème année primaire)
    if not classe:
        classe = ClasseNote.objects.filter(nom__icontains="CM2").first()
    
    # Si toujours pas trouvé, chercher "6"
    if not classe:
        classe = ClasseNote.objects.filter(nom__icontains="6").first()
    
    if not classe:
        print("❌ Classe introuvable")
        print("Classes disponibles:")
        for c in ClasseNote.objects.all()[:20]:
            print(f"   - {c.nom}")
        return
    
    print(f"✅ Classe trouvée: {classe.nom} (ID: {classe.id})")
    
    # 2. Créer les matières
    print("\n📚 Étape 2: Création des matières...")
    matieres_obj = []
    
    for i, nom_matiere in enumerate(MATIERES, 1):
        try:
            # Essayer de récupérer la matière existante
            matiere = MatiereNote.objects.filter(
                nom=nom_matiere,
                classe=classe
            ).first()
            
            if matiere:
                matieres_obj.append(matiere)
                print(f"   ✅ Existante: {nom_matiere}")
            else:
                # Créer avec un code unique
                code = f"MAT{i:02d}"
                matiere = MatiereNote.objects.create(
                    nom=nom_matiere,
                    code=code,
                    classe=classe,
                    coefficient=1,
                    actif=True
                )
                matieres_obj.append(matiere)
                print(f"   ✨ Créée: {nom_matiere} (code: {code})")
        except Exception as e:
            print(f"   ⚠️  Erreur {nom_matiere}: {e}")
            continue
    
    print(f"\n✅ {len(matieres_obj)} matières prêtes")
    
    # 3. Récupérer les élèves de la classe
    print("\n👥 Étape 3: Récupération des élèves...")
    
    # Chercher les élèves de cette classe via ClasseNote
    eleves = list(Eleve.objects.filter(
        classe__nom=classe.nom,
        statut='ACTIF'
    ))
    
    if not eleves:
        print(f"❌ Aucun élève trouvé dans la classe '{classe.nom}'")
        print("💡 Astuce: Vérifiez que les élèves sont bien affectés à cette classe")
        return
    
    print(f"✅ {len(eleves)} élèves actifs trouvés")
    
    # 4. Import des notes avec détection intelligente
    print("\n📝 Étape 4: Import des notes...")
    print("-" * 80)
    
    stats = {
        'eleves_ok': 0,
        'eleves_skip': 0,
        'notes_creees': 0,
        'notes_modifiees': 0
    }
    
    for nom_tableau, notes_list in NOTES_DATA:
        # Trouver l'élève correspondant
        eleve, score = trouver_eleve(nom_tableau, eleves)
        
        if not eleve:
            print(f"⚠️  '{nom_tableau}' → Aucun élève correspondant (score < 50%)")
            stats['eleves_skip'] += 1
            continue
        
        print(f"\n✅ '{nom_tableau}' → {eleve.prenom} {eleve.nom} ({score*100:.0f}% match)")
        stats['eleves_ok'] += 1
        
        # Importer les notes pour chaque matière
        for i, (matiere, note_value) in enumerate(zip(matieres_obj, notes_list)):
            if dry_run:
                print(f"   [TEST] {matiere.nom}: {note_value}/20")
                continue
            
            # Créer ou mettre à jour la note
            note_obj, created = NoteMensuelle.objects.update_or_create(
                eleve=eleve,
                matiere=matiere,
                periode=periode,
                annee_scolaire=annee_scolaire,
                defaults={
                    'note': Decimal(str(note_value))
                }
            )
            
            if created:
                stats['notes_creees'] += 1
                statut = "✨"
            else:
                stats['notes_modifiees'] += 1
                statut = "🔄"
            
            print(f"   {statut} {matiere.nom}: {note_value}/20")
    
    # 5. Résumé
    print("\n" + "=" * 80)
    print("  📊 RÉSUMÉ DE L'IMPORT")
    print("=" * 80)
    print(f"✅ Élèves matchés:        {stats['eleves_ok']}/{len(NOTES_DATA)}")
    print(f"⚠️  Élèves non trouvés:    {stats['eleves_skip']}/{len(NOTES_DATA)}")
    
    if not dry_run:
        print(f"✨ Notes créées:          {stats['notes_creees']}")
        print(f"🔄 Notes modifiées:       {stats['notes_modifiees']}")
        print(f"📝 Total notes traitées:  {stats['notes_creees'] + stats['notes_modifiees']}")
    else:
        print("\n⚠️  MODE TEST - Aucune donnée n'a été enregistrée")
    
    print("\n✅ Import terminé avec succès!")
    print("=" * 80)


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='Import intelligent des notes 6ème Année')
    parser.add_argument('--periode', default='NOVEMBRE', help='Période (NOVEMBRE, DECEMBRE, etc.)')
    parser.add_argument('--annee', default='2024-2025', help='Année scolaire')
    parser.add_argument('--test', action='store_true', help='Mode test (pas d\'enregistrement)')
    
    args = parser.parse_args()
    
    importer_notes(
        periode=args.periode,
        annee_scolaire=args.annee,
        dry_run=args.test
    )
