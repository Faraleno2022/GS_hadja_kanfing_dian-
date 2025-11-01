#!/usr/bin/env python
"""Script de test pour vérifier le bulletin et sa pagination"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ecole_moderne.settings')
django.setup()

from notes.models import ClasseNote, MatiereNote, NoteMensuelle, CompositionNote, ThemeBulletin
from eleves.models import Eleve

print("=" * 80)
print("TEST DU BULLETIN - IMPRESSION ET PAGINATION")
print("=" * 80)

# 1. Vérifier les thèmes
print("\n1. VÉRIFICATION DES THÈMES")
themes = ThemeBulletin.objects.all()
print(f"   Nombre de thèmes: {themes.count()}")
theme_defaut = ThemeBulletin.objects.filter(par_defaut=True, actif=True).first()
if theme_defaut:
    print(f"   ✅ Thème par défaut: {theme_defaut.nom}")
    print(f"      Couleur primaire: {theme_defaut.couleur_primaire}")
else:
    print("   ⚠️  Aucun thème par défaut")

# 2. Trouver un élève avec des notes
print("\n2. RECHERCHE D'UN ÉLÈVE AVEC NOTES")
eleves_avec_notes = []
for eleve in Eleve.objects.all()[:50]:
    nb_notes_mois = NoteMensuelle.objects.filter(eleve=eleve).count()
    nb_notes_compo = CompositionNote.objects.filter(eleve=eleve).count()
    if nb_notes_mois > 0 and nb_notes_compo > 0:
        eleves_avec_notes.append((eleve, nb_notes_mois, nb_notes_compo))
        if len(eleves_avec_notes) >= 3:
            break

if eleves_avec_notes:
    print(f"   ✅ {len(eleves_avec_notes)} élèves trouvés avec notes")
    for eleve, nb_mois, nb_compo in eleves_avec_notes:
        print(f"      - {eleve.nom} {eleve.prenom}")
        print(f"        Classe: {eleve.classe.nom}")
        print(f"        Notes mensuelles: {nb_mois}")
        print(f"        Notes composition: {nb_compo}")
else:
    print("   ❌ Aucun élève avec notes trouvé")

# 3. Vérifier la structure du bulletin
print("\n3. STRUCTURE DU BULLETIN")
if eleves_avec_notes:
    eleve = eleves_avec_notes[0][0]
    print(f"   Élève test: {eleve.nom} {eleve.prenom}")
    
    # Trouver la ClasseNote
    from notes.models import ClasseNote
    try:
        classe_note = ClasseNote.objects.get(
            nom=eleve.classe.nom,
            annee_scolaire=eleve.classe.annee_scolaire
        )
        print(f"   ✅ ClasseNote trouvée: {classe_note.nom}")
        
        # Matières
        matieres = MatiereNote.objects.filter(classe=classe_note)
        print(f"   ✅ Matières: {matieres.count()}")
        
        # Notes mensuelles
        notes_mois = NoteMensuelle.objects.filter(eleve=eleve)
        print(f"   ✅ Notes mensuelles: {notes_mois.count()}")
        
        # Notes composition
        notes_compo = CompositionNote.objects.filter(eleve=eleve)
        print(f"   ✅ Notes composition: {notes_compo.count()}")
        
        # Périodes disponibles
        periodes = notes_compo.values_list('periode', flat=True).distinct()
        print(f"   ✅ Périodes: {list(periodes)}")
        
    except ClasseNote.DoesNotExist:
        print(f"   ❌ ClasseNote non trouvée pour {eleve.classe.nom}")

# 4. Générer l'URL de test
print("\n4. URL DE TEST")
if eleves_avec_notes:
    eleve = eleves_avec_notes[0][0]
    notes_compo = CompositionNote.objects.filter(eleve=eleve).first()
    
    if notes_compo:
        periode = notes_compo.periode
        system_type = 'trimestre' if 'TRIMESTRE' in periode else 'semestre'
        
        # Trouver l'ID de la classe
        try:
            classe_note = ClasseNote.objects.get(
                nom=eleve.classe.nom,
                annee_scolaire=eleve.classe.annee_scolaire
            )
            classe_id = classe_note.id
        except:
            classe_note = ClasseNote.objects.filter(nom__iexact=eleve.classe.nom).first()
            classe_id = classe_note.id if classe_note else None
        
        if classe_id:
            url = f"http://127.0.0.1:8000/notes/bulletins/?classe_id={classe_id}&system_type={system_type}&periode={periode}&eleve_id={eleve.id}"
            print(f"\n   URL de test:")
            print(f"   {url}")
            print(f"\n   Paramètres:")
            print(f"   - Classe ID: {classe_id}")
            print(f"   - Système: {system_type}")
            print(f"   - Période: {periode}")
            print(f"   - Élève ID: {eleve.id}")
            print(f"   - Élève: {eleve.nom} {eleve.prenom}")

# 5. Instructions de test
print("\n" + "=" * 80)
print("INSTRUCTIONS DE TEST")
print("=" * 80)

print("\n📋 TEST 1: Affichage à l'écran")
print("   1. Copiez l'URL ci-dessus")
print("   2. Collez dans le navigateur")
print("   3. Vérifiez que le bulletin s'affiche")
print("   4. Vérifiez les couleurs bleu clair")

print("\n🖨️  TEST 2: Aperçu d'impression")
print("   1. Sur la page du bulletin")
print("   2. Appuyez sur Ctrl+P (ou Cmd+P)")
print("   3. Vérifiez l'aperçu:")
print("      ✅ Doit montrer 1 seule page")
print("      ✅ Pas de page blanche en bas")
print("      ✅ Tout le contenu visible")

print("\n📄 TEST 3: Génération PDF")
print("   1. Appuyez sur Ctrl+P")
print("   2. Destination: Enregistrer au format PDF")
print("   3. Enregistrez le fichier")
print("   4. Ouvrez le PDF")
print("   5. Vérifiez:")
print("      ✅ 1 seule page")
print("      ✅ Contenu complet")
print("      ✅ Couleurs correctes")

print("\n🖨️  TEST 4: Impression réelle")
print("   1. Appuyez sur Ctrl+P")
print("   2. Sélectionnez votre imprimante")
print("   3. Imprimez")
print("   4. Vérifiez la sortie papier:")
print("      ✅ Tient sur 1 feuille A4")
print("      ✅ Pas de coupure")
print("      ✅ Lisible")

print("\n" + "=" * 80)
print("RÉSUMÉ")
print("=" * 80)
print(f"Thèmes disponibles: {themes.count()}")
print(f"Thème par défaut: {theme_defaut.nom if theme_defaut else 'Aucun'}")
print(f"Élèves avec notes: {len(eleves_avec_notes)}")
if eleves_avec_notes:
    print(f"Élève de test: {eleves_avec_notes[0][0].nom} {eleves_avec_notes[0][0].prenom}")
print("\n✅ Prêt pour les tests !")
print("=" * 80)
