"""Cartes professionnelles, individuelles ou par planche de huit."""
from io import BytesIO
from types import SimpleNamespace

from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.http import HttpResponse, HttpResponseBadRequest
from django.shortcuts import get_object_or_404
from reportlab.pdfgen import canvas

from eleves.cartes_layout import (
    A4, CARTE_HAUTEUR, CARTE_LARGEUR, dessiner_carte_eleve,
    dessiner_planche_cartes, enregistrer_polices,
)
from eleves.utils_annee import get_annee_active
from utilisateurs.utils import filter_by_user_school
from .models import Enseignant


def enseignants_autorises(user):
    return filter_by_user_school(
        Enseignant.objects.select_related('ecole', 'classe_principale').prefetch_related('affectations__classe'),
        user, 'ecole',
    ).order_by('ecole__nom', 'nom', 'prenoms')


def construire_cartes_pdf(enseignants, annees, individuelle=False):
    buffer = BytesIO()
    document = canvas.Canvas(buffer, pagesize=(CARTE_LARGEUR, CARTE_HAUTEUR) if individuelle else A4)
    document.setTitle('Cartes des enseignants')
    font, bold = enregistrer_polices()

    def dessiner(c, enseignant, x, y, width, height):
        # Le dessin commun conserve la charte graphique et le format PVC.
        identite = SimpleNamespace(
            id=enseignant.pk, prenom=enseignant.prenoms, nom=enseignant.nom,
            photo=enseignant.photo,
            classe=SimpleNamespace(ecole=enseignant.ecole, annee_scolaire=annees.get(enseignant.ecole_id, '')),
        )
        rows = [
            ('Type', enseignant.get_type_enseignant_display()),
            ('Affectation', enseignant.classe_ou_fonction),
            ('Téléphone', enseignant.telephone),
            ('Embauche', enseignant.date_embauche.strftime('%d/%m/%Y')),
            ('Statut', enseignant.get_statut_display()),
        ]
        dessiner_carte_eleve(c, identite, x, y, width, height, font, bold,
                            'CARTE ENSEIGNANT', '#167d8d', '#e8f6f8', rows, 'ENS')

    enseignants = list(enseignants)
    if individuelle:
        dessiner(document, enseignants[0], 0, 0, CARTE_LARGEUR, CARTE_HAUTEUR)
    else:
        dessiner_planche_cartes(document, enseignants, dessiner)
    document.save()
    return buffer.getvalue()


@login_required
def carte_enseignant_pdf(request, enseignant_id):
    enseignant = get_object_or_404(enseignants_autorises(request.user), pk=enseignant_id)
    annees = {enseignant.ecole_id: get_annee_active(request, enseignant.ecole)}
    response = HttpResponse(construire_cartes_pdf([enseignant], annees, individuelle=True), content_type='application/pdf')
    response['Content-Disposition'] = f'inline; filename="carte_enseignant_{enseignant.pk}.pdf"'
    return response


@login_required
def cartes_enseignants_pdf(request):
    enseignants = enseignants_autorises(request.user)
    search = request.GET.get('search', '').strip()
    if search:
        enseignants = enseignants.filter(Q(nom__icontains=search) | Q(prenoms__icontains=search) | Q(email__icontains=search))
    ecole_id = request.GET.get('ecole', '').strip()
    if ecole_id:
        if not ecole_id.isascii() or not ecole_id.isdecimal():
            return HttpResponseBadRequest('École invalide.')
        enseignants = enseignants.filter(ecole_id=int(ecole_id))
    for field in ('type_enseignant', 'statut'):
        if request.GET.get(field):
            enseignants = enseignants.filter(**{field: request.GET[field]})
    enseignants = list(enseignants)
    if not enseignants:
        return HttpResponseBadRequest('Aucun enseignant à imprimer pour ces filtres.')
    annees = {}
    for enseignant in enseignants:
        if enseignant.ecole_id not in annees:
            annees[enseignant.ecole_id] = get_annee_active(request, enseignant.ecole)
    response = HttpResponse(construire_cartes_pdf(enseignants, annees), content_type='application/pdf')
    response['Content-Disposition'] = 'inline; filename="cartes_enseignants.pdf"'
    return response
