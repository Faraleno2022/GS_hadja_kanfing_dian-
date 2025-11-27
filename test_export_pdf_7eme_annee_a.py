#!/usr/bin/env python
"""
Test direct de l'export PDF pour 7ÈME ANNÉE (A)
"""

import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ecole_moderne.settings')
django.setup()

def test_export_pdf_7eme_annee_a():
    """Test direct pour 7ÈME ANNÉE (A)"""
    
    try:
        from django.test import RequestFactory
        from notes.export_classement_pdf_fix import exporter_classement_pdf_fix
        from notes.models import ClasseNote, MatiereNote, Evaluation, NoteEleve
        from eleves.models import Eleve, Classe as ClasseEleve
        
        print("🔧 TEST DIRECT EXPORT PDF - 7ÈME ANNÉE (A)")
        print("=" * 60)
        
        # Configuration
        classe_id = 11  # 7ÈME ANNÉE (A)
        periode = 'OCTOBRE'
        
        print(f"📚 Configuration :")
        print(f"  • Classe ID : {classe_id}")
        print(f"  • Période : {periode}")
        
        # 1. Trouver la classe
        classe = ClasseNote.objects.get(id=classe_id)
        print(f"  ✅ Classe : {classe.nom}")
        
        # 2. Trouver la classe élève
        classe_eleve = ClasseEleve.objects.filter(
            nom=classe.nom,
            annee_scolaire=classe.annee_scolaire,
            ecole=classe.ecole
        ).first()
        
        print(f"  ✅ ClasseEleve ID : {classe_eleve.id if classe_eleve else 'None'}")
        
        if not classe_eleve:
            print(f"  ❌ Classe élève non trouvée")
            return
        
        eleves = Eleve.objects.filter(classe=classe_eleve, statut='ACTIF')
        print(f"  ✅ Élèves trouvés : {eleves.count()}")
        
        # 3. Trouver les matières avec des notes
        print(f"\n📊 MATIÈRES DISPONIBLES :")
        
        matieres = MatiereNote.objects.filter(classe=classe, actif=True)
        matiere_avec_notes = None
        
        for matiere in matieres:
            evaluations = Evaluation.objects.filter(matiere=matiere, periode=periode)
            notes = NoteEleve.objects.filter(evaluation__in=evaluations)
            
            print(f"  📖 {matiere.nom} (ID: {matiere.id}) : {notes.count()} notes")
            
            if notes.count() > 0 and not matiere_avec_notes:
                matiere_avec_notes = matiere
        
        if not matiere_avec_notes:
            print(f"  ❌ Aucune matière avec des notes trouvées")
            return
        
        print(f"\n✅ UTILISATION DE LA MATIÈRE : {matiere_avec_notes.nom} (ID: {matiere_avec_notes.id})")
        
        # 4. Vérifier les notes par élève
        evaluations = Evaluation.objects.filter(matiere=matiere_avec_notes, periode=periode)
        notes = NoteEleve.objects.filter(evaluation__in=evaluations)
        
        print(f"\n👥 NOTES PAR ÉLÈVE :")
        
        for eleve in eleves[:5]:  # Montrer les 5 premiers
            notes_eleve = notes.filter(eleve=eleve)
            
            if notes_eleve.exists():
                total = sum(note.note for note in notes_eleve)
                moyenne = round(total / notes_eleve.count(), 2)
                print(f"  ✅ {eleve.nom_complet} : {notes_eleve.count()} notes, moyenne {moyenne}")
            else:
                print(f"  ❌ {eleve.nom_complet} : 0 notes")
        
        if eleves.count() > 5:
            print(f"  ... et {eleves.count() - 5} autres élèves")
        
        # 5. Test de l'export PDF
        print(f"\n🌐 TEST EXPORT PDF :")
        
        factory = RequestFactory()
        request = factory.get(f'/exporter-classement-pdf-fix/?classe_id={classe_id}&matiere_id={matiere_avec_notes.id}&periode={periode}')
        
        try:
            response = exporter_classement_pdf_fix(request)
            
            print(f"  ✅ Status : {response.status_code}")
            print(f"  ✅ Content-Type : {response.get('Content-Type')}")
            print(f"  ✅ Taille : {len(response.content)} octets")
            
            if response.status_code == 200:
                # Sauvegarder pour inspection
                with open('/tmp/test_pdf_7ea.pdf', 'wb') as f:
                    f.write(response.content)
                print(f"  ✅ PDF sauvegardé : /tmp/test_pdf_7ea.pdf")
                
                # Vérifier si le PDF contient "Non saisi"
                content_str = response.content.decode('utf-8', errors='ignore')
                if 'Non saisi' in content_str:
                    non_saisi_count = content_str.count('Non saisi')
                    print(f"  ❌ Le PDF contient encore 'Non saisi' ({non_saisi_count} occurrences)")
                else:
                    print(f"  ✅ Le PDF ne contient pas 'Non saisi' - SUCCÈS !")
            else:
                print(f"  ❌ Erreur HTTP : {response.status_code}")
                
        except Exception as e:
            print(f"  ❌ Erreur lors de l'appel : {str(e)}")
            import traceback
            traceback.print_exc()
        
        # 6. URL finale à utiliser
        print(f"\n🌟 URL FINALE À UTILISER :")
        print(f"  https://www.myschoolgn.space/notes/exporter-classement-pdf-fix/?classe_id={classe_id}&matiere_id={matiere_avec_notes.id}&periode={periode}")
        
        return True
        
    except Exception as e:
        print(f"❌ Erreur générale : {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    test_export_pdf_7eme_annee_a()
