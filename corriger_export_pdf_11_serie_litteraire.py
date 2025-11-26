#!/usr/bin/env python
"""
Correction spécifique pour l'export PDF classement 11 SÉRIE LITTÉRAIRE
"""

import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ecole_moderne.settings')
django.setup()

def corriger_export_pdf_11_serie_litteraire():
    """Diagnostic et correction de l'export PDF pour 11 SÉRIE LITTÉRAIRE"""
    
    try:
        from django.test import Client, RequestFactory
        from django.contrib.auth.models import User
        from notes.models import ClasseNote, MatiereNote, Evaluation, NoteEleve
        from notes.views import exporter_classement_classe
        from notes.export_classement import generer_pdf_classement
        from eleves.models import Eleve, Classe as ClasseEleve
        
        print("🔧 CORRECTION EXPORT PDF - 11 SÉRIE LITTÉRAIRE")
        
        # 1. Configuration
        classe_id = 4  # 11 SÉRIE LITTÉRAIRE
        periode = 'OCTOBRE'
        
        print(f"📚 Configuration :")
        print(f"  • Classe ID : {classe_id} (11 SÉRIE LITTÉRAIRE)")
        print(f"  • Période : {periode}")
        
        # 2. Vérifier toutes les matières et leurs notes
        print(f"\n📋 VÉRIFICATION COMPLÈTE DES DONNÉES :")
        
        classe = ClasseNote.objects.get(id=classe_id)
        print(f"  ✅ Classe : {classe.nom}")
        
        # Trouver la classe élève correspondante
        mapping_classes = {
            59: 8,   # ClasseNote '11ème Série littéraire' -> ClasseEleve '11ème série littéraire'
        }
        
        classe_eleve = None
        if classe.id in mapping_classes:
            classe_eleve = ClasseEleve.objects.filter(id=mapping_classes[classe.id]).first()
        
        if not classe_eleve:
            classe_eleve = ClasseEleve.objects.filter(
                nom=classe.nom,
                annee_scolaire=classe.annee_scolaire,
                ecole=classe.ecole
            ).first()
        
        if not classe_eleve:
            print(f"  ❌ Classe élève non trouvée")
            return
        
        eleves = Eleve.objects.filter(classe=classe_eleve, statut='ACTIF')
        matieres = MatiereNote.objects.filter(classe=classe, actif=True)
        
        print(f"  ✅ Élèves : {len(eleves)}")
        print(f"  ✅ Matières : {len(matieres)}")
        
        # 3. Vérifier chaque matière en détail
        total_evaluations = 0
        total_notes = 0
        
        for matiere in matieres:
            evaluations = Evaluation.objects.filter(matiere=matiere, periode=periode)
            notes = NoteEleve.objects.filter(evaluation__in=evaluations)
            
            print(f"    📖 {matiere.nom} : {evaluations.count()} eval, {notes.count()} notes")
            
            total_evaluations += evaluations.count()
            total_notes += notes.count()
        
        print(f"  📊 Total : {total_evaluations} évaluations, {total_notes} notes")
        
        if total_notes == 0:
            print(f"  ❌ Aucune note trouvée - Création des données...")
            from corriger_classement_classe_specifique import corriger_classement_classe_specifique
            corriger_classement_classe_specifique(classe_id=classe_id)
            print(f"  ✅ Données créées - Rafraîchissement...")
            
            # Rafraîchir les comptes
            total_notes = 0
            for matiere in matieres:
                evaluations = Evaluation.objects.filter(matiere=matiere, periode=periode)
                notes = NoteEleve.objects.filter(evaluation__in=evaluations)
                total_notes += notes.count()
            
            print(f"  📊 Total après création : {total_notes} notes")
        
        # 4. Tester l'export PDF pour chaque matière
        print(f"\n🔍 TEST EXPORT PDF PAR MATIÈRE :")
        
        factory = RequestFactory()
        user = User.objects.first()
        
        for matiere in matieres[:3]:  # Tester les 3 premières matières
            print(f"\n  📖 Test {matiere.nom} (ID: {matiere.id}) :")
            
            # Créer la requête
            url = f'/notes/exporter-classement/?classe_id={classe_id}&matiere_id={matiere.id}&periode={periode}&format=pdf'
            request = factory.get(url)
            request.user = user
            
            try:
                response = exporter_classement_classe(request)
                
                print(f"    Status : {response.status_code}")
                print(f"    Content-Type : {response.get('Content-Type', 'Non défini')}")
                print(f"    Taille : {len(response.content)} octets")
                
                if response.status_code == 200:
                    if 'pdf' in response.get('Content-Type', '').lower():
                        if len(response.content) > 1000:
                            print(f"    ✅ PDF généré correctement")
                            
                            # Vérifier le contenu
                            content_str = response.content.decode('utf-8', errors='ignore')
                            if 'Non saisi' in content_str:
                                print(f"    ⚠️  PDF contient 'Non saisi' - Problème de données")
                            elif 'table' in content_str.lower():
                                print(f"    ✅ PDF contient un tableau")
                            else:
                                print(f"    ⚠️  Contenu PDF inhabituel")
                        else:
                            print(f"    ❌ PDF trop petit - Possible problème")
                    else:
                        print(f"    ❌ Pas un PDF - Content-Type : {response.get('Content-Type')}")
                        print(f"    Contenu : {response.content.decode('utf-8', errors='ignore')[:200]}")
                else:
                    print(f"    ❌ Erreur : {response.status_code}")
                    print(f"    Contenu : {response.content.decode('utf-8', errors='ignore')[:200]}")
                    
            except Exception as e:
                print(f"    ❌ Erreur lors du test : {str(e)}")
        
        # 5. Diagnostic du problème de calcul des rangs
        print(f"\n🔍 DIAGNOSTIC CALCUL DES RANGS :")
        
        # Tester la fonction de calcul des rangs directement
        try:
            from notes.calculs import calculer_rangs_classe_periode
            
            # Prendre une matière au hasard
            matiere_test = matieres.first()
            
            rangs = calculer_rangs_classe_periode(classe_eleve, matiere_test, periode)
            
            print(f"  ✅ Fonction calculer_rangs_classe_periode exécutée")
            print(f"  📊 Rangs calculés : {len(rangs)}")
            
            if len(rangs) > 0:
                premier_rang = rangs[0]
                print(f"  🏆 Premier rang : {premier_rang.eleve.nom_complet} - {premier_rang.moyenne}")
            else:
                print(f"  ❌ Aucun rang calculé - Problème de données ou de calcul")
                
        except Exception as e:
            print(f"  ❌ Erreur calcul rangs : {str(e)}")
            import traceback
            traceback.print_exc()
        
        # 6. Vérifier le template PDF
        print(f"\n📄 VÉRIFICATION TEMPLATE PDF :")
        
        try:
            from django.template.loader import get_template
            template = get_template('notes/export_classement_pdf.html')
            print(f"  ✅ Template trouvé : notes/export_classement_pdf.html")
        except Exception as e:
            print(f"  ❌ Template non trouvé : {str(e)}")
            
            # Créer un template de secours
            template_content = """<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>Classement {{ classe.nom }} - {{ matiere.nom }}</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; }
        h1, h2, h3 { color: #333; text-align: center; }
        table { width: 100%; border-collapse: collapse; margin: 20px 0; }
        th, td { border: 1px solid #ddd; padding: 8px; text-align: center; }
        th { background-color: #f2f2f2; font-weight: bold; }
        .rank { font-weight: bold; }
        .moyenne { background-color: #e8f5e8; }
        .non-saisi { color: red; font-style: italic; }
        .stats { margin: 20px 0; padding: 10px; background-color: #f9f9f9; border-radius: 5px; }
    </style>
</head>
<body>
    <h1>CLASSEMENT GÉNÉRAL</h1>
    <h2>{{ classe.nom }}</h2>
    <h3>{{ matiere.nom }} - Notes Mensuelles</h3>
    <h3>Période : {{ periode }}</h3>
    
    {% if rangs %}
    <table>
        <thead>
            <tr>
                <th>Rang</th>
                <th>Matricule</th>
                <th>Nom Complet</th>
                <th>Moyenne /20</th>
            </tr>
        </thead>
        <tbody>
            {% for rang_info in rangs %}
            <tr>
                <td class="rank">{{ rang_info.rang_affiche|default:"-" }}</td>
                <td>{{ rang_info.eleve.matricule }}</td>
                <td>{{ rang_info.eleve.nom_complet }}</td>
                <td class="{% if rang_info.moyenne %}moyenne{% else %}non-saisi{% endif %}">
                    {% if rang_info.moyenne %}{{ rang_info.moyenne|floatformat:2 }}{% else %}Non saisi{% endif %}
                </td>
            </tr>
            {% endfor %}
        </tbody>
    </table>
    
    <div class="stats">
        <h3>STATISTIQUES</h3>
        <p>• Nombre total d'élèves: {{ rangs|length }}</p>
        <p>• Élèves avec notes: {% with notes_count=rangs|selectattr:'moyenne'|list %}{{ notes_count|length }}{% endwith %}</p>
        <p>• Élèves sans notes: {% with non_saisi_count=rangs|selectattr:'moyenne'|rejectattr:'moyenne'|list %}{{ non_saisi_count|length }}{% endwith %}</p>
        {% with non_saisi_count=rangs|selectattr:'moyenne'|rejectattr:'moyenne'|list %}
        {% if non_saisi_count %}<p>■ ATTENTION: {{ non_saisi_count|length }} élève(s) n'ont pas de notes pour cette période</p>{% endif %}
        {% endwith %}
    </div>
    {% else %}
    <p>Aucune donnée disponible pour cette classe et cette matière.</p>
    {% endif %}
    
    <p style="text-align: center; margin-top: 30px; font-size: 12px; color: #666;">
        Exporté le {% now "d/m/Y à H:i" %}
    </p>
</body>
</html>"""
            
            template_path = "templates/notes/export_classement_pdf.html"
            with open(template_path, 'w', encoding='utf-8') as f:
                f.write(template_content)
            print(f"  ✅ Template de secours créé")
        
        # 7. Test final après correction
        print(f"\n🎯 TEST FINAL APRÈS CORRECTION :")
        
        matiere_test = matieres.first()
        url = f'/notes/exporter-classement/?classe_id={classe_id}&matiere_id={matiere_test.id}&periode={periode}&format=pdf'
        request = factory.get(url)
        request.user = user
        
        try:
            response = exporter_classement_classe(request)
            
            print(f"  Status final : {response.status_code}")
            print(f"  Taille finale : {len(response.content)} octets")
            
            if len(response.content) > 1000:
                print(f"  ✅ PDF généré avec succès !")
                print(f"  🌐 URL de test : {url}")
            else:
                print(f"  ❌ PDF encore trop petit")
                
        except Exception as e:
            print(f"  ❌ Erreur finale : {str(e)}")
        
    except Exception as e:
        print(f"❌ Erreur générale : {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    corriger_export_pdf_11_serie_litteraire()
