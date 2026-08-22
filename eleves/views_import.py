"""
Vues pour l'importation d'élèves depuis Excel/CSV
"""
import os
import tempfile
from datetime import datetime
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, JsonResponse
from django.views.decorators.http import require_http_methods
from django.db import transaction

from eleves.models import Classe, Eleve


@login_required
@require_http_methods(["GET", "POST"])
def importer_eleves(request):
    """
    Vue principale pour importer des élèves
    """
    # Vérifier les permissions
    peut_importer = (
        request.user.is_staff or 
        request.user.is_superuser or
        request.user.groups.filter(name__in=['Administrateurs', 'Directeurs', 'Comptables']).exists() or
        (hasattr(request.user, 'profil') and request.user.profil.peut_importer_eleves) or
        (hasattr(request.user, 'profil') and request.user.profil.role == 'COMPTABLE')
    )
    
    if not peut_importer:
        messages.error(request, "Vous n'avez pas la permission d'importer des élèves.")
        return redirect('eleves:liste_eleves')
    
    # Déterminer l'année scolaire à utiliser : on prend la plus récente existante
    annee_courante = Classe.objects.order_by('-annee_scolaire').values_list('annee_scolaire', flat=True).first()

    # Récupérer les classes pour cette année scolaire
    classes = Classe.objects.all()
    if annee_courante:
        classes = classes.filter(annee_scolaire=annee_courante)
    classes = classes.order_by('nom')
    
    # Filtrage par école. Un utilisateur sans école rattachée ne se voit
    # proposer aucune classe : sans cela il aurait accès à toutes les écoles.
    from utilisateurs.utils import filter_by_user_school
    classes = filter_by_user_school(classes, request.user)

    context = {
        'classes': classes,
        'annee_courante': annee_courante,
    }
    
    if request.method == 'POST':
        return _traiter_import_eleves(request)
    
    return render(request, 'eleves/importer_eleves.html', context)


def _traiter_import_eleves(request):
    """
    Traite l'importation d'élèves
    """
    from eleves.import_eleves import (
        ImportElevesError,
        ImportElevesValidator,
        ImportElevesProcessor,
        lire_fichier_eleves,
    )

    try:
        # Récupérer les paramètres
        classe_id = request.POST.get('classe_id')
        generer_matricules = request.POST.get('generer_matricules') == 'on'
        fichier = request.FILES.get('fichier')
        
        if not classe_id:
            messages.error(request, "Veuillez sélectionner une classe.")
            return redirect('eleves:importer_eleves')

        # La classe de destination doit appartenir à l'école de l'utilisateur.
        # Le formulaire ne propose que ses classes, mais l'identifiant arrive du
        # POST : sans ce contrôle, importer dans une autre école reste possible.
        from utilisateurs.utils import filter_by_user_school

        classe_cible = filter_by_user_school(
            Classe.objects.filter(id=classe_id), request.user
        ).first()
        if classe_cible is None:
            messages.error(
                request,
                "Cette classe n'appartient pas à votre école : importation refusée."
            )
            return redirect('eleves:importer_eleves')

        if not fichier:
            messages.error(request, "Veuillez sélectionner un fichier.")
            return redirect('eleves:importer_eleves')

        # Sauvegarder temporairement le fichier
        with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(fichier.name)[1]) as tmp_file:
            for chunk in fichier.chunks():
                tmp_file.write(chunk)
            tmp_path = tmp_file.name
        
        try:
            # Lire le fichier
            df = lire_fichier_eleves(tmp_path)
            
            # Valider les données
            validator = ImportElevesValidator(df, classe_id)
            
            if not validator.valider():
                # Afficher les erreurs
                for erreur in validator.erreurs[:5]:  # Limiter à 5 erreurs
                    messages.error(request, erreur)
                if len(validator.erreurs) > 5:
                    messages.error(request, f"... et {len(validator.erreurs) - 5} autres erreurs")
                return redirect('eleves:importer_eleves')
            
            # Afficher les avertissements
            for avertissement in validator.avertissements[:3]:
                messages.warning(request, avertissement)
            
            # Importer les données
            processor = ImportElevesProcessor(
                df=df,
                classe_id=classe_id,
                user=request.user,
                generer_matricules=generer_matricules
            )
            
            stats = processor.importer()
            
            # Afficher les résultats
            classe = classe_cible

            if stats.get('classes_ciblees', 0) > 1:
                resultat_import = f"{stats['classes_ciblees']} classes"
            else:
                resultat_import = f"la classe {classe.nom}"
            messages.success(request, f"✅ Importation terminée pour {resultat_import} !")
            
            if stats['crees'] > 0:
                messages.success(
                    request,
                    f"📝 {stats['crees']} élève(s) créé(s)"
                )
            
            if stats['modifies'] > 0:
                messages.info(
                    request,
                    f"✏️ {stats['modifies']} élève(s) mis à jour"
                )
            
            if stats['matricules_generes'] > 0:
                messages.info(
                    request,
                    f"🔢 {stats['matricules_generes']} matricule(s) généré(s) automatiquement"
                )
            
            if stats.get('doublons_ignores', 0) > 0:
                details = stats.get('doublons_details') or []
                messages.warning(
                    request,
                    f"🚫 {stats['doublons_ignores']} ligne(s) rejetée(s) : matricule déjà "
                    f"utilisé. Aucun élève en double n'a été créé."
                )
                if details:
                    messages.warning(
                        request,
                        "Matricules en doublon — " + " ; ".join(details[:10])
                        + (" ; …" if stats['doublons_ignores'] > len(details[:10]) else "")
                    )

            if stats.get('classes_ciblees', 0) > 1:
                messages.info(
                    request,
                    f"🏫 Élèves répartis dans {stats['classes_ciblees']} classes "
                    f"d'après la colonne « Classe » du fichier"
                )

            introuvables = stats.get('classes_introuvables') or []
            if introuvables:
                messages.warning(
                    request,
                    f"⚠️ {stats.get('lignes_classes_rejetees', 0)} ligne(s) rejetée(s) : "
                    f"classe absente ou ambiguë : {', '.join(introuvables[:5])}"
                    + (f" (+{len(introuvables) - 5})" if len(introuvables) > 5 else "")
                )

            if stats['erreurs'] > 0:
                messages.warning(
                    request,
                    f"⚠️ {stats['erreurs']} erreur(s) rencontrée(s)"
                )
            
            messages.info(
                request,
                f"📊 Total traité: {stats['total']} élève(s)"
            )
            
            # Rediriger vers la liste des élèves de la classe
            return redirect('eleves:gestion_classes')
            
        finally:
            # Nettoyer le fichier temporaire
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)
    
    except ImportElevesError as e:
        messages.error(request, f"Erreur d'importation: {e}")
    except Exception as e:
        messages.error(request, f"Erreur inattendue: {e}")
        import traceback
        print(traceback.format_exc())
    
    return redirect('eleves:importer_eleves')


@login_required
def telecharger_template_eleves(request):
    import pandas as pd
    from eleves.import_eleves import generer_template_eleves

    """
    Télécharge un template Excel pour l'importation d'élèves
    """
    try:
        classe_id = request.GET.get('classe_id')
        
        # Générer le template
        df = generer_template_eleves(classe_id)
        
        # Créer la réponse Excel
        response = HttpResponse(
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        
        # Nom du fichier
        if classe_id:
            classe = Classe.objects.get(id=classe_id)
            filename = f"template_eleves_{classe.nom.replace(' ', '_')}.xlsx"
        else:
            filename = f"template_eleves_{datetime.now().strftime('%Y%m%d')}.xlsx"
        
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        
        # Écrire le DataFrame dans la réponse
        with pd.ExcelWriter(response, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='Élèves', index=False)
            
            # Obtenir la feuille pour la formater
            worksheet = writer.sheets['Élèves']
            
            # Ajuster la largeur des colonnes
            for idx, col in enumerate(df.columns, 1):
                column_letter = chr(64 + idx) if idx <= 26 else 'A' + chr(64 + idx - 26)
                if col in ['Prénom', 'Nom', 'Lieu de Naissance', 'Adresse']:
                    worksheet.column_dimensions[column_letter].width = 20
                elif col == 'Matricule':
                    worksheet.column_dimensions[column_letter].width = 15
                elif col in ['Date de Naissance', 'Téléphone Principal', 'Téléphone Secondaire']:
                    worksheet.column_dimensions[column_letter].width = 18
                else:
                    worksheet.column_dimensions[column_letter].width = 15
            
            # Ajouter un style à l'en-tête
            from openpyxl.styles import Font, PatternFill, Alignment
            
            header_font = Font(bold=True, color="FFFFFF")
            header_fill = PatternFill(start_color="366092", end_color="366092", fill_type="solid")
            header_alignment = Alignment(horizontal="center", vertical="center")
            
            for cell in worksheet[1]:
                cell.font = header_font
                cell.fill = header_fill
                cell.alignment = header_alignment
            
            # Ajouter des instructions dans une nouvelle feuille
            instructions_sheet = writer.book.create_sheet('Instructions')
            instructions = [
                ["INSTRUCTIONS POUR L'IMPORTATION DES ÉLÈVES"],
                [""],
                ["1. COLONNES OBLIGATOIRES:"],
                ["   - Prénom: Le prénom de l'élève"],
                ["   - Nom: Le nom de famille de l'élève"],
                ["   - Sexe: M (Masculin) ou F (Féminin)"],
                ["   - Date de Naissance: Format JJ/MM/AAAA (ex: 15/01/2010)"],
                ["   - Lieu de Naissance: Ville ou commune de naissance"],
                ["   - Nom du Père/Tuteur: Nom du responsable principal"],
                ["   - Prénom du Père/Tuteur: Prénom du responsable principal"],
                ["   - Téléphone Principal: Numéro de téléphone (8 chiffres minimum)"],
                ["   - Adresse: Adresse complète de la famille"],
                [""],
                ["2. COLONNES OPTIONNELLES:"],
                ["   - Matricule: Si vide, sera généré automatiquement"],
                ["   - Nom de la Mère: Nom du responsable secondaire"],
                ["   - Prénom de la Mère: Prénom du responsable secondaire"],
                ["   - Téléphone Secondaire: Numéro secondaire"],
                ["   - Email: Adresse email de contact"],
                [""],
                ["3. RÈGLES IMPORTANTES:"],
                ["   - Ne pas modifier les noms des colonnes"],
                ["   - Respecter le format de date JJ/MM/AAAA"],
                ["   - Le sexe doit être uniquement M ou F"],
                ["   - Les téléphones doivent contenir au moins 8 chiffres"],
                ["   - Supprimer les lignes d'exemple avant l'import"],
                [""],
                ["4. GÉNÉRATION AUTOMATIQUE DES MATRICULES:"],
                ["   - Format: [CODE_CLASSE]-[ANNÉE]-[NUMÉRO]"],
                ["   - Exemple: 6A-2024-001"],
                ["   - Cochez l'option lors de l'importation"],
                [""],
                ["5. EN CAS D'ERREUR:"],
                ["   - Vérifier que toutes les colonnes obligatoires sont remplies"],
                ["   - Vérifier le format des dates"],
                ["   - Vérifier que les téléphones sont valides"],
                ["   - S'assurer qu'il n'y a pas de doublons"]
            ]
            
            for row_idx, instruction in enumerate(instructions, 1):
                for col_idx, text in enumerate(instruction, 1):
                    instructions_sheet.cell(row=row_idx, column=col_idx, value=text)
            
            # Formater la feuille d'instructions
            instructions_sheet.column_dimensions['A'].width = 80
            title_cell = instructions_sheet['A1']
            title_cell.font = Font(bold=True, size=14, color="366092")
            
            for row in [3, 14, 21, 27, 32]:
                instructions_sheet.cell(row=row, column=1).font = Font(bold=True, color="366092")
        
        return response
    
    except Exception as e:
        messages.error(request, f"Erreur lors de la génération du template: {e}")
        return redirect('eleves:importer_eleves')


@login_required
def exporter_tous_eleves_import(request):
    """
    Exporte tous les élèves au format exact du template d'importation,
    afin de pouvoir les réimporter sur un autre poste.

    Filtres GET optionnels : classe_id, statut (défaut ACTIF, `tous` pour tout).
    """
    import pandas as pd
    from eleves.import_eleves import COLONNES_TRANSFERT, exporter_eleves_modele_import

    try:
        eleves = Eleve.objects.all()

        # Restriction à l'école de l'utilisateur
        from utilisateurs.utils import user_is_superadmin, user_school

        ecole = None
        if not user_is_superadmin(request.user):
            ecole = user_school(request.user)
            if ecole:
                eleves = eleves.filter(classe__ecole=ecole)

        classe_id = request.GET.get('classe_id')
        if classe_id:
            eleves = eleves.filter(classe_id=classe_id)

        statut = (request.GET.get('statut') or 'ACTIF').upper()
        if statut != 'TOUS':
            eleves = eleves.filter(statut=statut)

        df = exporter_eleves_modele_import(eleves)

        if df.empty:
            messages.warning(request, "Aucun élève à exporter avec ces filtres.")
            return redirect('eleves:liste_eleves')

        response = HttpResponse(
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        filename = f"eleves_import_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        response['Content-Disposition'] = f'attachment; filename="{filename}"'

        from openpyxl.styles import Alignment, Font, PatternFill
        from openpyxl.utils import get_column_letter

        with pd.ExcelWriter(response, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='Élèves', index=False)
            worksheet = writer.sheets['Élèves']

            for idx, col in enumerate(COLONNES_TRANSFERT, 1):
                lettre = get_column_letter(idx)
                if col in ('École', 'Classe', 'Prénom', 'Nom', 'Lieu de Naissance', 'Adresse'):
                    worksheet.column_dimensions[lettre].width = 22
                else:
                    worksheet.column_dimensions[lettre].width = 16

            for cell in worksheet[1]:
                cell.font = Font(bold=True, color="FFFFFF")
                cell.fill = PatternFill(start_color="366092", end_color="366092", fill_type="solid")
                cell.alignment = Alignment(horizontal="center", vertical="center")

            worksheet.freeze_panes = 'A2'

            # Récapitulatif par classe + mode d'emploi du transfert
            recap = writer.book.create_sheet('Instructions')
            lignes = [
                ["TRANSFERT DES ÉLÈVES VERS UN AUTRE POSTE"],
                [""],
                [f"Export du {datetime.now().strftime('%d/%m/%Y à %H:%M')}"],
                [f"École : {ecole.nom if ecole else 'toutes les écoles'}"],
                [f"Nombre d'élèves exportés : {len(df)}"],
                [""],
                ["MODE D'EMPLOI SUR LE POSTE DE DESTINATION :"],
                ["   1. Créer d'abord les classes avec EXACTEMENT les mêmes noms que"],
                ["      dans la colonne 'Classe' de la feuille 'Élèves'."],
                ["   2. Ouvrir Élèves > Importer des élèves."],
                ["   3. Choisir ce fichier et sélectionner une classe par défaut."],
                ["   4. Chaque élève est placé dans la classe indiquée par la colonne"],
                ["      'Classe'. Si le nom n'existe pas, l'élève va dans la classe"],
                ["      par défaut choisie à l'étape 3 et un avertissement s'affiche."],
                [""],
                ["IMPORTANT :"],
                ["   - Ne pas modifier les noms des colonnes."],
                ["   - Les colonnes École / Classe / Année scolaire servent au transfert ;"],
                ["     elles sont ignorées par un import classique."],
                ["   - Les matricules sont conservés tels quels."],
                [""],
                ["RÉPARTITION PAR CLASSE :"],
            ]

            for (classe_nom, annee), sous_df in df.groupby(['Classe', 'Année scolaire'], sort=True):
                lignes.append([f"   - {classe_nom} ({annee}) : {len(sous_df)} élève(s)"])

            for row_idx, ligne in enumerate(lignes, 1):
                for col_idx, texte in enumerate(ligne, 1):
                    recap.cell(row=row_idx, column=col_idx, value=texte)

            recap.column_dimensions['A'].width = 80
            recap['A1'].font = Font(bold=True, size=14, color="366092")
            for row_idx in (7, 16, 22):
                recap.cell(row=row_idx, column=1).font = Font(bold=True, color="366092")

        return response

    except Exception as e:
        messages.error(request, f"Erreur lors de l'export: {e}")
        return redirect('eleves:liste_eleves')


@login_required
def exporter_eleves_classe(request, classe_id):
    import pandas as pd
    from eleves.import_eleves import exporter_liste_eleves

    """
    Exporte la liste des élèves d'une classe
    """
    try:
        classe = get_object_or_404(Classe, id=classe_id)
        
        # Vérifier les permissions
        if not request.user.is_superuser:
            from utilisateurs.utils import user_school
            ecole = user_school(request.user)
            if ecole and classe.ecole != ecole:
                messages.error(request, "Vous n'avez pas accès à cette classe.")
                return redirect('eleves:liste_eleves')
        
        # Exporter les élèves
        df = exporter_liste_eleves(classe_id)
        
        # Créer la réponse Excel
        response = HttpResponse(
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        
        filename = f"eleves_{classe.nom.replace(' ', '_')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        
        # Écrire le DataFrame
        with pd.ExcelWriter(response, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name=f'Élèves {classe.nom}', index=False)
            
            # Formater
            worksheet = writer.sheets[f'Élèves {classe.nom}']
            
            # Largeur des colonnes
            for idx, col in enumerate(df.columns, 1):
                column_letter = chr(64 + idx) if idx <= 26 else 'A' + chr(64 + idx - 26)
                worksheet.column_dimensions[column_letter].width = 18
            
            # Style de l'en-tête
            from openpyxl.styles import Font, PatternFill, Alignment
            
            for cell in worksheet[1]:
                cell.font = Font(bold=True, color="FFFFFF")
                cell.fill = PatternFill(start_color="28a745", end_color="28a745", fill_type="solid")
                cell.alignment = Alignment(horizontal="center")
        
        return response
    
    except Exception as e:
        messages.error(request, f"Erreur lors de l'export: {e}")
        return redirect('eleves:gestion_classes')
