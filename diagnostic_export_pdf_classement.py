#!/usr/bin/env python
"""
Diagnostic de l'export PDF du classement
"""

import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ecole_moderne.settings')
django.setup()

def diagnostic_export_pdf_classement():
    """Diagnostic complet de l'export PDF du classement"""
    
    try:
        from django.test import Client
        from django.contrib.auth.models import User
        from notes.models import ClasseNote, MatiereNote, Evaluation, NoteEleve
        from eleves.models import Eleve, Classe as ClasseEleve
        
        print("🔧 DIAGNOSTIC EXPORT PDF CLASSEMENT")
        
        # 1. Configuration de test
        classe_id = 4  # 11 SÉRIE LITTÉRAIRE
        matiere_id = 41  # Anglais
        periode = 'OCTOBRE'
        
        print(f"📚 Configuration :")
        print(f"  • Classe ID : {classe_id}")
        print(f"  • Matière ID : {matiere_id}")
        print(f"  • Période : {periode}")
        
        # 2. Vérifier que les données existent
        print(f"\n📋 VÉRIFICATION DES DONNÉES :")
        
        try:
            classe = ClasseNote.objects.get(id=classe_id)
            print(f"  ✅ Classe : {classe.nom}")
        except ClasseNote.DoesNotExist:
            print(f"  ❌ Classe {classe_id} non trouvée")
            return
        
        try:
            matiere = MatiereNote.objects.get(id=matiere_id)
            print(f"  ✅ Matière : {matiere.nom}")
        except MatiereNote.DoesNotExist:
            print(f"  ❌ Matière {matiere_id} non trouvée")
            return
        
        # Vérifier les évaluations
        evaluations = Evaluation.objects.filter(matiere=matiere, periode=periode)
        print(f"  ✅ Évaluations : {evaluations.count()}")
        
        # Vérifier les notes
        notes = NoteEleve.objects.filter(evaluation__in=evaluations)
        print(f"  ✅ Notes : {notes.count()}")
        
        if notes.count() == 0:
            print(f"  ❌ Aucune note trouvée - L'export sera vide")
            return
        
        # 3. Test de l'URL d'export
        print(f"\n🌐 TEST DE L'URL D'EXPORT :")
        
        client = Client()
        user = User.objects.first()
        client.force_login(user)
        
        # URL sans PDF
        url_html = f'/notes/exporter-classement/?classe_id={classe_id}&matiere_id={matiere_id}&periode={periode}'
        print(f"  URL HTML : {url_html}")
        
        try:
            response_html = client.get(url_html)
            print(f"  Status HTML : {response_html.status_code}")
            
            if response_html.status_code == 200:
                content = response_html.content.decode('utf-8')
                if 'Non saisi' in content:
                    print(f"  ❌ Contient 'Non saisi' - Problème de données")
                elif 'table' in content:
                    print(f"  ✅ Contient un tableau - OK")
                else:
                    print(f"  ⚠️  Contenu HTML inhabituel")
            else:
                print(f"  ❌ Erreur HTTP : {response_html.status_code}")
                print(f"  Contenu : {response_html.content.decode('utf-8')[:500]}")
                
        except Exception as e:
            print(f"  ❌ Erreur lors de l'appel HTML : {str(e)}")
        
        # URL avec PDF
        url_pdf = f'/notes/exporter-classement/?classe_id={classe_id}&matiere_id={matiere_id}&periode={periode}&format=pdf'
        print(f"  URL PDF : {url_pdf}")
        
        try:
            response_pdf = client.get(url_pdf)
            print(f"  Status PDF : {response_pdf.status_code}")
            
            if response_pdf.status_code == 200:
                content_type = response_pdf.get('Content-Type', '')
                if 'pdf' in content_type.lower():
                    print(f"  ✅ Content-Type PDF : {content_type}")
                    print(f"  ✅ Taille PDF : {len(response_pdf.content)} octets")
                else:
                    print(f"  ❌ Content-Type incorrect : {content_type}")
                    print(f"  Contenu : {response_pdf.content.decode('utf-8')[:500]}")
            else:
                print(f"  ❌ Erreur HTTP PDF : {response_pdf.status_code}")
                print(f"  Contenu : {response_pdf.content.decode('utf-8')[:500]}")
                
        except Exception as e:
            print(f"  ❌ Erreur lors de l'appel PDF : {str(e)}")
            import traceback
            traceback.print_exc()
        
        # 4. Vérifier le code d'export
        print(f"\n🔍 VÉRIFICATION DU CODE D'EXPORT :")
        
        try:
            from notes.views import exporter_classement_classe
            print(f"  ✅ Vue exporter_classement_classe trouvée")
        except ImportError as e:
            print(f"  ❌ Vue non trouvée : {str(e)}")
        
        try:
            from notes.export_classement import generer_pdf_classement
            print(f"  ✅ Fonction generer_pdf_classement trouvée")
        except ImportError as e:
            print(f"  ❌ Fonction PDF non trouvée : {str(e)}")
        
        # 5. Diagnostic des dépendances PDF
        print(f"\n📦 VÉRIFICATION DES DÉPENDANCES PDF :")
        
        try:
            import weasyprint
            print(f"  ✅ WeasyPrint installé : {weasyprint.__version__}")
        except ImportError:
            print(f"  ❌ WeasyPrint non installé")
        
        try:
            import reportlab
            print(f"  ✅ ReportLab installé : {reportlab.__version__}")
        except ImportError:
            print(f"  ❌ ReportLab non installé")
        
        # 6. Recommandations
        print(f"\n💡 RECOMMANDATIONS :")
        
        if notes.count() == 0:
            print(f"  • Créer les notes manquantes : corriger {classe_id}")
        
        if not os.path.exists('/usr/local/bin/corriger'):
            print(f"  • Installer le script de correction")
        
        print(f"  • URL de test : {url_pdf}")
        print(f"  • Vérifier les logs Apache/Django en cas d'erreur")
        
    except Exception as e:
        print(f"❌ Erreur générale : {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    diagnostic_export_pdf_classement()
