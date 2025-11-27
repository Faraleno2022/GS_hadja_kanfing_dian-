#!/usr/bin/env python
"""
Test direct de l'export PDF pour 11 SÉRIE LITTÉRAIRE
"""

import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ecole_moderne.settings')
django.setup()

def test_export_pdf_direct():
    """Test direct de l'export PDF pour diagnostiquer le problème"""
    
    try:
        from django.test import RequestFactory
        from notes.export_classement_pdf_fix import exporter_classement_pdf_fix
        from notes.models import ClasseNote, MatiereNote, Evaluation, NoteEleve
        from eleves.models import Eleve, Classe as ClasseEleve
        
        print("🔧 TEST DIRECT EXPORT PDF - 11 SÉRIE LITTÉRAIRE")
        print("=" * 60)
        
        # Configuration
        classe_id = 4  # 11 SÉRIE LITTÉRAIRE
        matiere_id = 41  # Anglais
        periode = 'OCTOBRE'
        
        print(f"📚 Configuration :")
        print(f"  • Classe ID : {classe_id}")
        print(f"  • Matière ID : {matiere_id}")
        print(f"  • Période : {periode}")
        
        # 1. Vérifier les données brutes
        print(f"\n📋 VÉRIFICATION DONNÉES BRUTES :")
        
        classe = ClasseNote.objects.get(id=classe_id)
        matiere = MatiereNote.objects.get(id=matiere_id)
        
        print(f"  ✅ Classe : {classe.nom}")
        print(f"  ✅ Matière : {matiere.nom}")
        
        # Trouver la classe élève (comme dans notre code)
        mapping_classes = {
            59: 8,   # ClasseNote '11ème Série littéraire' -> ClasseEleve '11ème série littéraire'
        }
        
        classe_eleve = None
        if classe.id in mapping_classes:
            classe_eleve = ClasseEleve.objects.filter(id=mapping_classes[classe.id]).first()
            print(f"  🔍 Mapping explicite -> ClasseEleve ID: {classe_eleve.id if classe_eleve else 'None'}")
        
        if not classe_eleve:
            classe_eleve = ClasseEleve.objects.filter(
                nom=classe.nom,
                annee_scolaire=classe.annee_scolaire,
                ecole=classe.ecole
            ).first()
            print(f"  🔍 Mapping par nom -> ClasseEleve ID: {classe_eleve.id if classe_eleve else 'None'}")
        
        if not classe_eleve:
            print(f"  ❌ Classe élève non trouvée")
            return
        
        eleves = Eleve.objects.filter(classe=classe_eleve, statut='ACTIF')
        print(f"  ✅ Élèves trouvés : {eleves.count()}")
        
        # 2. Vérifier les évaluations et notes
        print(f"\n📊 VÉRIFICATION ÉVALUATIONS ET NOTES :")
        
        evaluations = Evaluation.objects.filter(matiere=matiere, periode=periode)
        print(f"  • Évaluations trouvées : {evaluations.count()}")
        
        notes = NoteEleve.objects.filter(evaluation__in=evaluations)
        print(f"  • Notes trouvées : {notes.count()}")
        
        # 3. Vérifier les notes par élève
        print(f"\n👥 NOTES PAR ÉLÈVE :")
        
        notes_par_eleve = {}
        for eleve in eleves:
            notes_eleve = notes.filter(eleve=eleve)
            notes_par_eleve[eleve.id] = notes_eleve.count()
            
            if notes_eleve.exists():
                total = sum(note.note for note in notes_eleve)
                moyenne = round(total / notes_eleve.count(), 2)
                print(f"  ✅ {eleve.nom_complet} : {notes_eleve.count()} notes, moyenne {moyenne}")
            else:
                print(f"  ❌ {eleve.nom_complet} : 0 notes")
        
        # 4. Créer une requête HTTP factice
        print(f"\n🌐 TEST REQUÊTE HTTP :")
        
        factory = RequestFactory()
        request = factory.get(f'/exporter-classement-pdf-fix/?classe_id={classe_id}&matiere_id={matiere_id}&periode={periode}')
        
        try:
            response = exporter_classement_pdf_fix(request)
            
            print(f"  ✅ Status : {response.status_code}")
            print(f"  ✅ Content-Type : {response.get('Content-Type')}")
            print(f"  ✅ Taille : {len(response.content)} octets")
            
            if response.status_code == 200:
                # Sauvegarder pour inspection
                with open('/tmp/test_pdf_11sl.pdf', 'wb') as f:
                    f.write(response.content)
                print(f"  ✅ PDF sauvegardé : /tmp/test_pdf_11sl.pdf")
                
                # Vérifier si le PDF contient "Non saisi"
                content_str = response.content.decode('utf-8', errors='ignore')
                if 'Non saisi' in content_str:
                    print(f"  ❌ Le PDF contient encore 'Non saisi'")
                    
                    # Compter les occurrences
                    non_saisi_count = content_str.count('Non saisi')
                    print(f"  📊 Nombre de 'Non saisi' : {non_saisi_count}")
                    
                    if non_saisi_count == eleves.count():
                        print(f"  🔍 TOUS les élèves sont 'Non saisi' - problème de récupération des notes")
                else:
                    print(f"  ✅ Le PDF ne contient pas 'Non saisi'")
            else:
                print(f"  ❌ Erreur HTTP : {response.status_code}")
                
        except Exception as e:
            print(f"  ❌ Erreur lors de l'appel : {str(e)}")
            import traceback
            traceback.print_exc()
        
        # 5. Diagnostic du mapping
        print(f"\n🔍 DIAGNOSTIC MAPPING :")
        print(f"  • ClasseNote ID : {classe.id}")
        print(f"  • ClasseEleve ID trouvée : {classe_eleve.id}")
        print(f"  • Mapping utilisé : {'explicite' if classe.id in mapping_classes else 'par nom'}")
        
        # Vérifier si le mapping est correct
        eleves_attendus = Eleve.objects.filter(classe=classe_eleve, statut='ACTIF')
        print(f"  • Élèves attendus : {eleves_attendus.count()}")
        
        # Comparer avec le diagnostic précédent
        print(f"\n📊 COMPARAISON AVEC DIAGNOSTIC PRÉCÉDENT :")
        print(f"  • Diagnostic précédent : 229 notes OCTOBRE")
        print(f"  • Test actuel : {notes.count()} notes pour Anglais")
        print(f"  • Élèves : {eleves.count()}")
        
        if notes.count() == 0:
            print(f"  ❌ PROBLÈME : Les notes existent mais ne sont pas trouvées pour cette matière")
            print(f"  🔍 Essayer avec une autre matière...")
            
            # Tester avec d'autres matières
            autres_matieres = MatiereNote.objects.filter(classe=classe, actif=True).exclude(id=matiere_id)
            
            for autre_matiere in autres_matieres[:3]:  # Tester 3 premières
                autres_evaluations = Evaluation.objects.filter(matiere=autre_matiere, periode=periode)
                autres_notes = NoteEleve.objects.filter(evaluation__in=autres_evaluations)
                
                print(f"    📖 {autre_matiere.nom} (ID: {autre_matiere.id}) : {autres_notes.count()} notes")
                
                if autres_notes.count() > 0:
                    print(f"      ✅ Utiliser cette matière : {autre_matiere.id}")
                    break
        
        return True
        
    except Exception as e:
        print(f"❌ Erreur générale : {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    test_export_pdf_direct()
