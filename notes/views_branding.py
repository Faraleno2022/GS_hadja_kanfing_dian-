import io

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import HttpResponse, HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from eleves.models import Ecole
from utilisateurs.utils import user_school
from ecole_moderne.branding import DEFAULT_BRANDING, THEME_FIELDS, get_active_theme, get_reportlab_palette

from .forms import ThemeBulletinForm
from .models import ThemeBulletin


def _school_for_request(request):
    school = user_school(request.user)
    if request.user.is_superuser:
        school_id = request.POST.get('ecole_id') or request.GET.get('ecole_id')
        if school_id:
            return get_object_or_404(Ecole, pk=school_id)
        return school or Ecole.objects.order_by('nom').first()
    return school


def _can_edit_branding(user, school):
    if not school or not user.is_authenticated:
        return False
    if user.is_superuser:
        return True
    profil = getattr(user, 'profil', None)
    return bool(
        profil
        and profil.ecole_id == school.id
        and not profil.lecture_seule
        and (profil.est_compte_principal or profil.role == 'ADMIN')
    )


def _redirect_to_branding(request, school):
    target = reverse('notes:charte_graphique')
    if request.user.is_superuser and school:
        return redirect(f"{target}?ecole_id={school.pk}")
    return redirect(target)


@login_required
def charte_graphique(request):
    school = _school_for_request(request)
    if school is None:
        return HttpResponseForbidden("Aucune école n'est associée à ce compte.")

    can_edit = _can_edit_branding(request.user, school)
    theme = get_active_theme(school)
    if theme is not None and theme.ecole_id != school.id:
        theme = None

    if request.method == 'POST':
        if not can_edit:
            return HttpResponseForbidden("Vous n'êtes pas autorisé à modifier la charte graphique.")

        action = request.POST.get('action', 'save')
        if action == 'reset':
            with transaction.atomic():
                theme = theme or ThemeBulletin(ecole=school)
                theme.nom = f"Charte de {school.nom}"
                for key, attribute in THEME_FIELDS.items():
                    setattr(theme, attribute, DEFAULT_BRANDING[key])
                theme.actif = True
                theme.par_defaut = True
                theme.cree_par = theme.cree_par or request.user
                theme.save()
            messages.success(request, "Les couleurs par défaut ont été restaurées.")
            return _redirect_to_branding(request, school)

        form = ThemeBulletinForm(request.POST, instance=theme)
        if form.is_valid():
            with transaction.atomic():
                saved_theme = form.save(commit=False)
                saved_theme.ecole = school
                saved_theme.actif = True
                saved_theme.par_defaut = True
                saved_theme.cree_par = saved_theme.cree_par or request.user
                saved_theme.save()
            messages.success(
                request,
                "Charte graphique enregistrée. Les cartes et les documents utiliseront désormais ces couleurs.",
            )
            return _redirect_to_branding(request, school)
    else:
        form = ThemeBulletinForm(
            instance=theme,
            initial={
                'nom': f"Charte de {school.nom}",
                'actif': True,
                'par_defaut': True,
            },
        )

    schools = Ecole.objects.order_by('nom') if request.user.is_superuser else Ecole.objects.none()
    return render(request, 'notes/charte_graphique.html', {
        'form': form,
        'ecole': school,
        'schools': schools,
        'can_edit': can_edit,
        'theme': theme,
        'titre_page': 'Charte graphique de l’école',
    })


def build_brand_preview_pdf(school, theme=None):
    """Construit un document témoin utilisant exactement la palette sauvegardée."""
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import cm
    from reportlab.pdfgen import canvas

    palette = get_reportlab_palette(school, theme=theme)
    buffer = io.BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    margin = 1.6 * cm

    pdf.setTitle(f"Aperçu charte graphique - {school.nom}")
    pdf.setFillColor(palette['header'])
    pdf.roundRect(margin, height - 5.2 * cm, width - 2 * margin, 3.6 * cm, 14, fill=1, stroke=0)

    logo_path = None
    try:
        if school.logo and school.logo.path:
            logo_path = school.logo.path
    except Exception:
        logo_path = None
    if logo_path:
        try:
            pdf.setFillColor(palette['card'])
            pdf.circle(margin + 1.15 * cm, height - 3.4 * cm, 0.75 * cm, fill=1, stroke=0)
            pdf.drawImage(logo_path, margin + 0.42 * cm, height - 4.12 * cm, 1.45 * cm, 1.45 * cm,
                          preserveAspectRatio=True, mask='auto')
        except Exception:
            pass

    pdf.setFillColor(palette['header_text'])
    pdf.setFont('Helvetica-Bold', 18)
    pdf.drawString(margin + 2.2 * cm, height - 3.05 * cm, school.nom.upper()[:48])
    pdf.setFont('Helvetica', 10)
    pdf.drawString(margin + 2.2 * cm, height - 3.65 * cm, "APERÇU DE LA CHARTE GRAPHIQUE")

    y = height - 6.25 * cm
    pdf.setFillColor(palette['text'])
    pdf.setFont('Helvetica-Bold', 15)
    pdf.drawString(margin, y, "BULLETIN DE NOTES - DOCUMENT TÉMOIN")
    y -= 0.8 * cm
    pdf.setFillColor(palette['muted'])
    pdf.setFont('Helvetica', 9)
    pdf.drawString(margin, y, "Élève : Exemple A.  |  Classe : 6ème A  |  Année scolaire : 2026-2027")
    y -= 0.75 * cm

    columns = [6.8 * cm, 2.2 * cm, 2.4 * cm, 4.1 * cm]
    row_height = 0.78 * cm
    headers = ['Matière', 'Coef.', 'Moyenne', 'Appréciation']
    rows = [
        ['Français', '2', '15,50', 'Bien'],
        ['Mathématiques', '3', '17,00', 'Très bien'],
        ['Sciences', '2', '13,50', 'Assez bien'],
    ]
    x = margin
    pdf.setFillColor(palette['primary'])
    pdf.rect(x, y - row_height, sum(columns), row_height, fill=1, stroke=0)
    pdf.setFillColor(palette['primary_text'])
    pdf.setFont('Helvetica-Bold', 9)
    cursor = x
    for label, col_width in zip(headers, columns):
        pdf.drawString(cursor + 0.18 * cm, y - 0.51 * cm, label)
        cursor += col_width
    y -= row_height

    for index, row in enumerate(rows):
        pdf.setFillColor(palette['table'] if index % 2 == 0 else palette['table_alt'])
        pdf.rect(x, y - row_height, sum(columns), row_height, fill=1, stroke=0)
        pdf.setFillColor(palette['text'])
        pdf.setFont('Helvetica', 9)
        cursor = x
        for value, col_width in zip(row, columns):
            pdf.drawString(cursor + 0.18 * cm, y - 0.51 * cm, value)
            cursor += col_width
        y -= row_height

    pdf.setStrokeColor(palette['border'])
    pdf.rect(x, y, sum(columns), row_height * 4, fill=0, stroke=1)
    y -= 1.2 * cm

    card_gap = 0.35 * cm
    card_width = (width - 2 * margin - 3 * card_gap) / 4
    card_colors = [palette['card_primary'], palette['card_success'], palette['card_warning'], palette['card_danger']]
    card_texts = [palette['card_primary_text'], palette['card_success_text'], palette['card_warning_text'], palette['card_danger_text']]
    card_labels = ['Moyenne', 'Admis', 'À suivre', 'Alerte']
    for index, (background, foreground, label) in enumerate(zip(card_colors, card_texts, card_labels)):
        card_x = margin + index * (card_width + card_gap)
        pdf.setFillColor(background)
        pdf.roundRect(card_x, y - 1.6 * cm, card_width, 1.45 * cm, 8, fill=1, stroke=0)
        pdf.setFillColor(foreground)
        pdf.setFont('Helvetica-Bold', 9)
        pdf.drawCentredString(card_x + card_width / 2, y - 0.62 * cm, label)
        pdf.setFont('Helvetica-Bold', 13)
        pdf.drawCentredString(card_x + card_width / 2, y - 1.18 * cm, ['15,33', '28', '4', '1'][index])

    y -= 2.65 * cm
    pdf.setFillColor(palette['primary_soft'])
    pdf.roundRect(margin, y - 2.2 * cm, width - 2 * margin, 2.1 * cm, 10, fill=1, stroke=0)
    pdf.setFillColor(palette['primary'])
    pdf.setFont('Helvetica-Bold', 11)
    pdf.drawString(margin + 0.45 * cm, y - 0.7 * cm, "APPRÉCIATION GÉNÉRALE")
    pdf.setFillColor(palette['text'])
    pdf.setFont('Helvetica', 10)
    pdf.drawString(margin + 0.45 * cm, y - 1.35 * cm, "Très bon ensemble. Poursuivez vos efforts avec régularité.")

    pdf.setFillColor(palette['muted'])
    pdf.setFont('Helvetica', 8)
    pdf.drawCentredString(width / 2, 1.05 * cm, "Aperçu automatique - les données affichées sont fictives")
    pdf.showPage()
    pdf.save()
    buffer.seek(0)
    return buffer.getvalue()


@login_required
def charte_graphique_apercu_pdf(request):
    school = _school_for_request(request)
    if school is None:
        return HttpResponseForbidden("Aucune école n'est associée à ce compte.")
    theme = get_active_theme(school)
    response = HttpResponse(build_brand_preview_pdf(school, theme=theme), content_type='application/pdf')
    response['Content-Disposition'] = f'inline; filename="apercu_charte_{school.pk}.pdf"'
    return response
