#!/usr/bin/env python
"""
Correction simple et efficace pour l'export PDF du classement
"""

import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ecole_moderne.settings')
django.setup()

def corriger_export_pdf_simple():
    """Correction simple et efficace pour l'export PDF"""
    
    try:
        from django.test import RequestFactory
        from django.contrib.auth.models import User
        from django.http import HttpResponse
        from django.template.loader import get_template
        from django.template import Context
        from notes.models import ClasseNote, MatiereNote, Evaluation, NoteEleve
        from eleves.models import Eleve, Classe as ClasseEleve
        
        print("🔧 CORRECTION EXPORT PDF - VERSION SIMPLE")
        
        # 1. Configuration
        classe_id = 4  # 11 SÉRIE LITTÉRAIRE
        matiere_id = 41  # Anglais
        periode = 'OCTOBRE'
        
        print(f"📚 Configuration :")
        print(f"  • Classe ID : {classe_id}")
        print(f"  • Matière ID : {matiere_id}")
        print(f"  • Période : {periode}")
        
        # 2. Récupérer les données
        classe = ClasseNote.objects.get(id=classe_id)
        matiere = MatiereNote.objects.get(id=matiere_id)
        evaluations = Evaluation.objects.filter(matiere=matiere, periode=periode)
        notes = NoteEleve.objects.filter(evaluation__in=evaluations)
        
        print(f"\n📋 DONNÉES :")
        print(f"  ✅ Classe : {classe.nom}")
        print(f"  ✅ Matière : {matiere.nom}")
        print(f"  ✅ Évaluations : {evaluations.count()}")
        print(f"  ✅ Notes : {notes.count()}")
        
        # 3. Trouver la classe élève correspondante
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
        print(f"  ✅ Élèves : {len(eleves)}")
        
        # 4. Calculer les moyennes manuellement
        print(f"\n🔍 CALCUL DES MOYENNES :")
        
        classement_data = []
        
        for eleve in eleves:
            # Calculer la moyenne pour cet élève
            notes_eleve = notes.filter(eleve=eleve)
            
            if notes_eleve.exists():
                total = sum(note.note for note in notes_eleve)
                moyenne = round(total / notes_eleve.count(), 2)
            else:
                moyenne = None
            
            classement_data.append({
                'eleve': eleve,
                'moyenne': moyenne,
                'notes_count': notes_eleve.count()
            })
            
            if moyenne:
                print(f"    📝 {eleve.nom_complet} : {moyenne}")
        
        # 5. Calculer les rangs
        print(f"\n🏆 CALCUL DES RANGS :")
        
        # Filtrer les élèves avec des notes
        avec_notes = [item for item in classement_data if item['moyenne'] is not None]
        sans_notes = [item for item in classement_data if item['moyenne'] is None]
        
        # Trier par moyenne décroissante
        avec_notes.sort(key=lambda x: x['moyenne'], reverse=True)
        
        # Ajouter les rangs
        for i, item in enumerate(avec_notes):
            item['rang'] = i + 1
            item['rang_affiche'] = f"{i+1}ème"
            print(f"    🥇 {i+1}. {item['eleve'].nom_complet} : {item['moyenne']}")
        
        # Mettre les sans notes à la fin
        for item in sans_notes:
            item['rang'] = None
            item['rang_affiche'] = "-"
        
        # Recombiner
        rangs = avec_notes + sans_notes
        
        print(f"\n📊 STATISTIQUES :")
        print(f"  • Total élèves : {len(rangs)}")
        print(f"  • Avec notes : {len(avec_notes)}")
        print(f"  • Sans notes : {len(sans_notes)}")
        
        # 6. Créer le template HTML
        print(f"\n📄 CRÉATION TEMPLATE HTML :")
        
        html_content = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>Classement {classe.nom} - {matiere.nom}</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        h1, h2, h3 {{ color: #333; text-align: center; }}
        .header {{ text-align: center; margin-bottom: 30px; }}
        table {{ width: 100%; border-collapse: collapse; margin: 20px 0; }}
        th, td {{ border: 1px solid #ddd; padding: 8px; text-align: center; }}
        th {{ background-color: #f2f2f2; font-weight: bold; }}
        .rank {{ font-weight: bold; }}
        .moyenne {{ background-color: #e8f5e8; }}
        .non-saisi {{ color: red; font-style: italic; }}
        .stats {{ margin: 20px 0; padding: 10px; background-color: #f9f9f9; border-radius: 5px; }}
        .footer {{ text-align: center; margin-top: 30px; font-size: 12px; color: #666; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>République de Guinée</h1>
        <h2>Travail - Justice - Solidarité</h2>
        <h3>Ministère de l'Enseignement Pré-Universitaire et de l'Alphabétisation</h3>
        <h3>GROUPE SCOLAIRE HADJA KANFING DIANE (SONFONIA)</h3>
    </div>
    
    <h1>CLASSEMENT GÉNÉRAL</h1>
    <h2>{classe.nom}</h2>
    <h3>{matiere.nom} - Notes Mensuelles</h3>
    <h3>Période : {periode}</h3>
    
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
"""
        
        for rang_info in rangs:
            rang_affiche = rang_info['rang_affiche'] if rang_info['rang_affiche'] else '-'
            moyenne_affiche = f"{rang_info['moyenne']}" if rang_info['moyenne'] else "Non saisi"
            classe_css = "moyenne" if rang_info['moyenne'] else "non-saisi"
            
            html_content += f"""            <tr>
                <td class="rank">{rang_affiche}</td>
                <td>{rang_info['eleve'].matricule}</td>
                <td>{rang_info['eleve'].nom_complet}</td>
                <td class="{classe_css}">{moyenne_affiche}</td>
            </tr>
"""
        
        html_content += f"""        </tbody>
    </table>
    
    <div class="stats">
        <h3>STATISTIQUES</h3>
        <p>• Nombre total d'élèves: {len(rangs)}</p>
        <p>• Élèves avec notes: {len(avec_notes)}</p>
        <p>• Élèves sans notes: {len(sans_notes)}</p>
        {f'<p>■ ATTENTION: {len(sans_notes)} élève(s) n\'ont pas de notes pour cette période</p>' if len(sans_notes) > 0 else ''}
    </div>
    
    <div class="footer">
        <p>Exporté le 26/11/2025 à 20:44</p>
        <p>Tél: +224620643009 | Email: gshkd2025@gmail.com</p>
    </div>
</body>
</html>"""
        
        # 7. Générer le PDF
        print(f"\n🔧 GÉNÉRATION PDF :")
        
        try:
            # Essayer avec WeasyPrint
            import weasyprint
            
            # Créer le PDF
            pdf_html = weasyprint.HTML(string=html_content)
            pdf_content = pdf_html.write_pdf()
            
            print(f"  ✅ PDF généré avec WeasyPrint")
            print(f"  📊 Taille PDF : {len(pdf_content)} octets")
            
            # Sauvegarder pour test
            with open('/tmp/classement_test.pdf', 'wb') as f:
                f.write(pdf_content)
            print(f"  ✅ PDF sauvegardé : /tmp/classement_test.pdf")
            
            # Créer la réponse HTTP
            response = HttpResponse(pdf_content, content_type='application/pdf')
            response['Content-Disposition'] = f'attachment; filename="classement_{classe.nom}_{matiere.nom}_{periode}.pdf"'
            
            print(f"\n🎉 SUCCÈS !")
            print(f"  ✅ PDF généré avec {len(rangs)} élèves")
            print(f"  ✅ {len(avec_notes)} élèves avec notes")
            print(f"  ✅ {len(sans_notes)} élèves sans notes")
            
            return response
            
        except ImportError:
            print(f"  ❌ WeasyPrint non installé")
            print(f"  💡 Solution : pip install weasyprint")
            
            # Alternative : retourner HTML
            response = HttpResponse(html_content, content_type='text/html')
            return response
            
        except Exception as e:
            print(f"  ❌ Erreur génération PDF : {str(e)}")
            import traceback
            traceback.print_exc()
            return None
        
    except Exception as e:
        print(f"❌ Erreur générale : {str(e)}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    corriger_export_pdf_simple()
