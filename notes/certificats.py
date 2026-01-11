"""
Module pour la génération des certificats d'appréciation
"""
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404
from django.http import HttpResponse
from django.template.loader import render_to_string
from weasyprint import HTML, CSS
from datetime import datetime
import base64
import os
import logging

from .models import ClasseNote, MatiereNote
from eleves.models import Eleve, Classe as ClasseEleve

logger = logging.getLogger(__name__)


@login_required
def certificats_appreciation_pdf(request):
    """
    Génère les certificats d'appréciation pour les 5 premiers élèves d'une classe
    """
    # Récupérer les paramètres
    classe_id = request.GET.get('classe_id')
    periode = request.GET.get('periode', '')
    
    if not classe_id:
        return HttpResponse("Classe non spécifiée", status=400)
    
    if not periode:
        return HttpResponse("Période non spécifiée", status=400)
    
    try:
        # Récupérer la classe
        classe_note = get_object_or_404(ClasseNote, pk=classe_id)
        
        # Récupérer l'école
        ecole = classe_note.ecole
        
        # Récupérer la classe élève correspondante
        classe_eleve = ClasseEleve.objects.filter(
            nom__iexact=classe_note.nom,
            annee_scolaire=classe_note.annee_scolaire,
            ecole=ecole
        ).first()
        
        if not classe_eleve:
            return HttpResponse(f"Classe élèves non trouvée pour {classe_note.nom}", status=404)
        
        # Récupérer les élèves actifs de la classe
        eleves = Eleve.objects.filter(classe=classe_eleve, statut='ACTIF')
        
        # Récupérer les matières de la classe
        matieres = MatiereNote.objects.filter(classe=classe_note, actif=True)
        
        # Déterminer le type de système selon la période
        if periode in ['TRIMESTRE_1', 'TRIMESTRE_2', 'TRIMESTRE_3']:
            system_type = 'trimestriel'
        elif periode in ['SEMESTRE_1', 'SEMESTRE_2']:
            system_type = 'semestriel'
        elif periode in ['ANNUEL_TRIM']:
            system_type = 'annuel_trimestriel'
        elif periode in ['ANNUEL_SEM']:
            system_type = 'annuel_semestriel'
        else:
            system_type = 'mensuel'
        
        # Calculer le classement
        from .calculs_moyennes import calculer_classement_classe
        classement_resultat = calculer_classement_classe(eleves, matieres, periode, system_type)
        
        if not classement_resultat or 'rang_map' not in classement_resultat:
            return HttpResponse("Impossible de calculer le classement", status=400)
        
        # Récupérer les 5 premiers
        rang_map = classement_resultat['rang_map']
        moyennes = classement_resultat.get('moyennes_par_eleve', {})
        
        # Filtrer les élèves avec un rang valide et trier par rang
        eleves_avec_rang = []
        for eleve_id, rang in rang_map.items():
            if rang and rang <= 5:
                try:
                    eleve = Eleve.objects.get(pk=eleve_id)
                    moyenne = moyennes.get(eleve_id, 0)
                    if moyenne and moyenne > 0:
                        eleves_avec_rang.append({
                            'eleve': eleve,
                            'rang': rang,
                            'moyenne': moyenne
                        })
                except Eleve.DoesNotExist:
                    continue
        
        # Trier par rang
        eleves_avec_rang.sort(key=lambda x: x['rang'])
        
        # Limiter aux 5 premiers
        eleves_top5 = eleves_avec_rang[:5]
        
        if not eleves_top5:
            return HttpResponse("Aucun élève classé trouvé pour cette période", status=400)
        
        # Formater les rangs
        from .export_classement import formater_rang
        for eleve_data in eleves_top5:
            sexe = getattr(eleve_data['eleve'], 'sexe', 'M') or 'M'
            eleve_data['rang_formate'] = formater_rang(eleve_data['rang'], sexe)
        
        # Total élèves dans la classe
        total_eleves = Eleve.objects.filter(classe=classe_eleve, statut='ACTIF').count()
        
        # Encoder le logo en base64 si disponible
        logo_base64 = None
        if ecole and ecole.logo:
            try:
                logo_path = ecole.logo.path
                if os.path.exists(logo_path):
                    with open(logo_path, 'rb') as f:
                        logo_base64 = base64.b64encode(f.read()).decode('utf-8')
            except Exception:
                pass
        
        # Libellé de la période
        periodes_labels = {
            'OCTOBRE': 'Mois d\'Octobre',
            'NOVEMBRE': 'Mois de Novembre',
            'DECEMBRE': 'Mois de Décembre',
            'JANVIER': 'Mois de Janvier',
            'FEVRIER': 'Mois de Février',
            'MARS': 'Mois de Mars',
            'AVRIL': 'Mois d\'Avril',
            'MAI': 'Mois de Mai',
            'JUIN': 'Mois de Juin',
            'TRIMESTRE_1': '1er Trimestre',
            'TRIMESTRE_2': '2ème Trimestre',
            'TRIMESTRE_3': '3ème Trimestre',
            'SEMESTRE_1': '1er Semestre',
            'SEMESTRE_2': '2ème Semestre',
            'ANNUEL_TRIM': 'Année Scolaire (Trimestres)',
            'ANNUEL_SEM': 'Année Scolaire (Semestres)',
        }
        periode_label = periodes_labels.get(periode, periode)
        
        # Contexte pour le template
        context = {
            'eleves_top5': eleves_top5,
            'classe': classe_note,
            'ecole': ecole,
            'logo_base64': logo_base64,
            'total_eleves': total_eleves,
            'periode': periode,
            'periode_label': periode_label,
            'annee_scolaire': classe_note.annee_scolaire,
            'date_emission': datetime.now().strftime('%d/%m/%Y'),
            'ville': getattr(ecole, 'adresse', 'Conakry').split(',')[0] if ecole else 'Conakry',
        }
        
        # Générer le HTML
        html_content = render_to_string('notes/certificat_appreciation.html', context, request=request)
        
        # Créer le PDF avec WeasyPrint
        html = HTML(string=html_content)
        css = CSS(string='''
            @page {
                size: A4 landscape;
                margin: 10mm;
            }
        ''')
        
        pdf = html.write_pdf(stylesheets=[css])
        
        # Retourner le PDF
        response = HttpResponse(pdf, content_type='application/pdf')
        response['Content-Disposition'] = f'inline; filename="certificats_appreciation_{classe_note.nom}_{periode}.pdf"'
        return response
        
    except Exception as e:
        logger.error(f"Erreur lors de la génération des certificats: {str(e)}")
        import traceback
        traceback.print_exc()
        return HttpResponse(f"Erreur: {str(e)}", status=500)
