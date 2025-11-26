#!/usr/bin/env python
"""
Correction de l'export PDF du classement - Fichier vide
"""

import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ecole_moderne.settings')
django.setup()

def corriger_export_pdf_classement():
    """Diagnostic et correction de l'export PDF du classement"""
    
    try:
        from django.test import Client
        from django.contrib.auth.models import User
        from notes.models import ClasseNote, MatiereNote, Evaluation, NoteEleve
        from notes.export_classement import generer_pdf_classement
        from notes.views import exporter_classement_classe
        from django.http import HttpResponse
        from django.template.loader import get_template
        from django.template import Context
        
        print("🔧 CORRECTION EXPORT PDF CLASSEMENT")
        
        # 1. Configuration de test
        classe_id = 4  # 11 SÉRIE LITTÉRAIRE
        matiere_id = 41  # Anglais
        periode = 'OCTOBRE'
        
        print(f"📚 Configuration :")
        print(f"  • Classe ID : {classe_id}")
        print(f"  • Matière ID : {matiere_id}")
        print(f"  • Période : {periode}")
        
        # 2. Vérifier les données
        print(f"\n📋 VÉRIFICATION DES DONNÉES :")
        
        classe = ClasseNote.objects.get(id=classe_id)
        matiere = MatiereNote.objects.get(id=matiere_id)
        evaluations = Evaluation.objects.filter(matiere=matiere, periode=periode)
        notes = NoteEleve.objects.filter(evaluation__in=evaluations)
        
        print(f"  ✅ Classe : {classe.nom}")
        print(f"  ✅ Matière : {matiere.nom}")
        print(f"  ✅ Évaluations : {evaluations.count()}")
        print(f"  ✅ Notes : {notes.count()}")
        
        if notes.count() == 0:
            print(f"  ❌ Aucune note - Création des notes...")
            # Utiliser le script de correction
            from corriger_classement_classe_specifique import corriger_classement_classe_specifique
            corriger_classement_classe_specifique(classe_id=classe_id)
            # Rafraîchir les notes
            notes = NoteEleve.objects.filter(evaluation__in=evaluations)
            print(f"  ✅ Notes après correction : {notes.count()}")
        
        # 3. Tester la fonction PDF directement
        print(f"\n🔍 TEST DE LA FONCTION PDF :")
        
        try:
            # Créer une requête factice
            from django.test import RequestFactory
            factory = RequestFactory()
            request = factory.get(f'/notes/exporter-classement/?classe_id={classe_id}&matiere_id={matiere_id}&periode={periode}&format=pdf')
            
            user = User.objects.first()
            request.user = user
            
            # Appeler la vue
            response = exporter_classement_classe(request)
            
            print(f"  ✅ Vue appelée avec succès")
            print(f"  Status : {response.status_code}")
            print(f"  Content-Type : {response.get('Content-Type', 'Non défini')}")
            print(f"  Taille : {len(response.content)} octets")
            
            if response.status_code == 200:
                if 'pdf' in response.get('Content-Type', '').lower():
                    print(f"  ✅ PDF généré correctement")
                    
                    # Sauvegarder le PDF pour inspection
                    with open('/tmp/test_classement.pdf', 'wb') as f:
                        f.write(response.content)
                    print(f"  ✅ PDF sauvegardé : /tmp/test_classement.pdf")
                    
                    if len(response.content) < 1000:
                        print(f"  ⚠️  PDF très petit - Possible problème de contenu")
                    else:
                        print(f"  ✅ Taille PDF correcte")
                else:
                    print(f"  ❌ Pas un PDF - Content-Type : {response.get('Content-Type')}")
                    print(f"  Contenu : {response.content.decode('utf-8')[:500]}")
            else:
                print(f"  ❌ Erreur dans la vue : {response.status_code}")
                print(f"  Contenu : {response.content.decode('utf-8')[:500]}")
                
        except Exception as e:
            print(f"  ❌ Erreur lors du test PDF : {str(e)}")
            import traceback
            traceback.print_exc()
        
        # 4. Vérifier le template
        print(f"\n📄 VÉRIFICATION DU TEMPLATE :")
        
        try:
            template = get_template('notes/export_classement_pdf.html')
            print(f"  ✅ Template trouvé : notes/export_classement_pdf.html")
        except Exception as e:
            print(f"  ❌ Template non trouvé : {str(e)}")
            # Essayer un autre nom
            try:
                template = get_template('notes/classement_pdf.html')
                print(f"  ✅ Template alternatif trouvé : notes/classement_pdf.html")
            except Exception as e2:
                print(f"  ❌ Template alternatif non trouvé : {str(e2)}")
        
        # 5. Créer un template de secours si nécessaire
        print(f"\n🔧 CRÉATION TEMPLATE DE SECOURS :")
        
        template_content = """<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>Classement {{ classe.nom }} - {{ matiere.nom }}</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; }
        h1 { color: #333; text-align: center; }
        table { width: 100%; border-collapse: collapse; margin: 20px 0; }
        th, td { border: 1px solid #ddd; padding: 8px; text-align: center; }
        th { background-color: #f2f2f2; font-weight: bold; }
        .rank { font-weight: bold; }
        .moyenne { background-color: #e8f5e8; }
        .mention { font-style: italic; }
    </style>
</head>
<body>
    <h1>CLASSEMENT</h1>
    <h2>{{ classe.nom }} - {{ matiere.nom }}</h2>
    <h3>Période : {{ periode }}</h3>
    
    {% if rangs %}
    <table>
        <thead>
            <tr>
                <th>Rang</th>
                <th>Matricule</th>
                <th>Nom</th>
                <th>Prénom</th>
                <th>Moyenne</th>
                <th>Mention</th>
            </tr>
        </thead>
        <tbody>
            {% for rang_info in rangs %}
            <tr>
                <td class="rank">{{ rang_info.rang_affiche }}</td>
                <td>{{ rang_info.eleve.matricule }}</td>
                <td>{{ rang_info.eleve.nom }}</td>
                <td>{{ rang_info.eleve.prenom }}</td>
                <td class="moyenne">{{ rang_info.moyenne|floatformat:2 }}</td>
                <td class="mention">{{ rang_info.mention }}</td>
            </tr>
            {% endfor %}
        </tbody>
    </table>
    {% else %}
    <p>Aucune donnée disponible pour cette classe et cette matière.</p>
    {% endif %}
    
    <p style="text-align: center; margin-top: 30px; font-size: 12px; color: #666;">
        Généré le {% now "d/m/Y H:i" %}
    </p>
</body>
</html>"""
        
        # Sauvegarder le template
        template_path = "templates/notes/export_classement_pdf.html"
        try:
            with open(template_path, 'w', encoding='utf-8') as f:
                f.write(template_content)
            print(f"  ✅ Template de secours créé : {template_path}")
        except Exception as e:
            print(f"  ❌ Erreur création template : {str(e)}")
        
        # 6. Test final
        print(f"\n🎯 TEST FINAL APRÈS CORRECTION :")
        
        try:
            response = exporter_classement_classe(request)
            print(f"  Status final : {response.status_code}")
            print(f"  Taille finale : {len(response.content)} octets")
            
            if len(response.content) > 1000:
                print(f"  ✅ PDF généré avec succès !")
                print(f"  🌐 URL de test : /notes/exporter-classement/?classe_id={classe_id}&matiere_id={matiere_id}&periode={periode}&format=pdf")
            else:
                print(f"  ❌ PDF encore trop petit - Investigation nécessaire")
                
        except Exception as e:
            print(f"  ❌ Erreur finale : {str(e)}")
        
    except Exception as e:
        print(f"❌ Erreur générale : {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    corriger_export_pdf_classement()
