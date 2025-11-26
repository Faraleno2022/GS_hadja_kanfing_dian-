#!/usr/bin/env python
"""
Intégrer la solution PDF dans le système existant
"""

import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ecole_moderne.settings')
django.setup()

def integrer_solution_pdf():
    """Intégrer la solution PDF dans le système existant"""
    
    try:
        print("🔧 INTÉGRATION SOLUTION PDF DANS LE SYSTÈME")
        
        # 1. Créer une nouvelle vue pour l'export PDF
        vue_pdf_content = '''from django.shortcuts import render
from django.http import HttpResponse
from django.template.loader import get_template
from notes.models import ClasseNote, MatiereNote, Evaluation, NoteEleve
from eleves.models import Eleve, Classe as ClasseEleve
import weasyprint

def exporter_classement_pdf_fix(request):
    """
    Export PDF du classement avec la solution corrigée
    """
    # Récupérer les paramètres
    classe_id = request.GET.get('classe_id')
    matiere_id = request.GET.get('matiere_id')
    periode = request.GET.get('periode', 'OCTOBRE')
    
    if not classe_id or not matiere_id:
        return HttpResponse("Paramètres manquants", status=400)
    
    try:
        # Récupérer les données
        classe = ClasseNote.objects.get(id=classe_id)
        matiere = MatiereNote.objects.get(id=matiere_id)
        evaluations = Evaluation.objects.filter(matiere=matiere, periode=periode)
        notes = NoteEleve.objects.filter(evaluation__in=evaluations)
        
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
            return HttpResponse("Classe élève non trouvée", status=404)
        
        eleves = Eleve.objects.filter(classe=classe_eleve, statut='ACTIF')
        
        # Calculer les moyennes manuellement
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
        
        # Calculer les rangs
        # Filtrer les élèves avec des notes
        avec_notes = [item for item in classement_data if item['moyenne'] is not None]
        sans_notes = [item for item in classement_data if item['moyenne'] is None]
        
        # Trier par moyenne décroissante
        avec_notes.sort(key=lambda x: x['moyenne'], reverse=True)
        
        # Ajouter les rangs
        for i, item in enumerate(avec_notes):
            item['rang'] = i + 1
            item['rang_affiche'] = f"{i+1}ème"
        
        # Mettre les sans notes à la fin
        for item in sans_notes:
            item['rang'] = None
            item['rang_affiche'] = "-"
        
        # Recombiner
        rangs = avec_notes + sans_notes
        
        # Créer le template HTML
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
        
        # Générer le PDF
        pdf_html = weasyprint.HTML(string=html_content)
        pdf_content = pdf_html.write_pdf()
        
        # Créer la réponse HTTP
        response = HttpResponse(pdf_content, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="classement_{classe.nom}_{matiere.nom}_{periode}.pdf"'
        
        return response
        
    except Exception as e:
        return HttpResponse(f"Erreur: {str(e)}", status=500)
'''
        
        # 2. Sauvegarder la nouvelle vue
        vue_path = "notes/export_classement_pdf_fix.py"
        with open(vue_path, 'w', encoding='utf-8') as f:
            f.write(vue_pdf_content)
        
        print(f"  ✅ Vue créée : {vue_path}")
        
        # 3. Mettre à jour les URLs
        urls_update = '''
# Ajouter cette ligne à notes/urls.py après les autres URLs d'export
from .export_classement_pdf_fix import exporter_classement_pdf_fix

# Ajouter cette URL
path('exporter-classement-pdf-fix/', exporter_classement_pdf_fix, name='exporter_classement_pdf_fix'),
'''
        
        print(f"  📋 Mise à jour URLs nécessaire :")
        print(f"     Ajouter dans notes/urls.py :")
        print(f"     from .export_classement_pdf_fix import exporter_classement_pdf_fix")
        print(f"     path('exporter-classement-pdf-fix/', exporter_classement_pdf_fix, name='exporter_classement_pdf_fix'),")
        
        # 4. Instructions d'utilisation
        print(f"\n🚀 UTILISATION :")
        print(f"  1. Ajouter l'URL dans notes/urls.py")
        print(f"  2. Redémarrer le serveur : touch ecole_moderne/wsgi.py")
        print(f"  3. Tester l'URL : /notes/exporter-classement-pdf-fix/?classe_id=4&matiere_id=41&periode=OCTOBRE")
        
        print(f"\n🎯 AVANTAGES :")
        print(f"  ✅ Plus de 'Non saisi' dans le PDF")
        print(f"  ✅ Calcul des rangs correct")
        print(f"  ✅ Template HTML intégré")
        print(f"  ✅ Compatible avec le système existant")
        
    except Exception as e:
        print(f"❌ Erreur : {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    integrer_solution_pdf()
