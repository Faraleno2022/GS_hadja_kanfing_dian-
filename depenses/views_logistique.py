from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q, Sum, Count, F
from django.db import models
from django.http import JsonResponse, HttpResponse
from datetime import datetime, date
from decimal import Decimal
import openpyxl
from openpyxl.styles import Font, Alignment, PatternFill

from .models_logistique import (
    CategorieArticle, Article, BienEtablissement, 
    MouvementStock, Inventaire, LigneInventaire
)
from .forms import (
    ArticleForm, BienEtablissementForm, MouvementStockForm,
    InventaireForm, LigneInventaireForm
)


@login_required
def dashboard_logistique(request):
    """Dashboard principal de la logistique"""
    from utilisateurs.utils import user_school

    ecole = user_school(request.user)

    # Filtres de base par école
    articles_qs = Article.objects.filter(actif=True)
    biens_qs = BienEtablissement.objects.filter(actif=True)
    mouvements_qs = MouvementStock.objects.all()
    if ecole:
        articles_qs = articles_qs.filter(cree_par__profil__ecole=ecole)
        biens_qs = biens_qs.filter(cree_par__profil__ecole=ecole)
        mouvements_qs = mouvements_qs.filter(cree_par__profil__ecole=ecole)

    # Statistiques générales
    total_articles = articles_qs.count()
    total_biens = biens_qs.count()

    # Valeur totale du stock
    valeur_stock = articles_qs.aggregate(
        total=Sum('stock_actuel') * Sum('prix_unitaire')
    )

    # Articles en alerte (stock minimum)
    articles_alerte = articles_qs.filter(
        stock_actuel__lte=models.F('stock_minimum')
    ).count()

    # Derniers mouvements
    derniers_mouvements = mouvements_qs.select_related(
        'article', 'cree_par'
    ).order_by('-date_mouvement')[:10]

    # Répartition par catégorie
    repartition_categories = CategorieArticle.objects.annotate(
        nb_articles=Count('articles'),
        valeur_totale=Sum('articles__stock_actuel') * Sum('articles__prix_unitaire')
    ).filter(actif=True)

    # Biens nécessitant une maintenance
    biens_maintenance = biens_qs.filter(
        date_prochaine_maintenance__lte=date.today()
    ).count()
    
    context = {
        'titre_page': 'Dashboard Logistique',
        'total_articles': total_articles,
        'total_biens': total_biens,
        'valeur_stock': valeur_stock.get('total', 0) or 0,
        'articles_alerte': articles_alerte,
        'derniers_mouvements': derniers_mouvements,
        'repartition_categories': repartition_categories,
        'biens_maintenance': biens_maintenance,
    }
    
    return render(request, 'depenses/logistique/dashboard.html', context)


@login_required
def liste_articles(request):
    """Liste des articles en stock"""
    from utilisateurs.utils import user_school

    # Filtres
    q = request.GET.get('q', '')
    categorie_id = request.GET.get('categorie', '')
    etat = request.GET.get('etat', '')
    alerte = request.GET.get('alerte', '')

    articles = Article.objects.select_related('categorie').filter(actif=True)
    # Sécurité : filtrer par école
    ecole = user_school(request.user)
    if ecole:
        articles = articles.filter(cree_par__profil__ecole=ecole)
    
    if q:
        articles = articles.filter(
            Q(code_article__icontains=q) |
            Q(nom__icontains=q) |
            Q(marque__icontains=q) |
            Q(reference__icontains=q)
        )
    
    if categorie_id:
        articles = articles.filter(categorie_id=categorie_id)
    
    if etat:
        articles = articles.filter(etat=etat)
    
    if alerte == 'oui':
        articles = articles.filter(stock_actuel__lte=models.F('stock_minimum'))
    
    categories = CategorieArticle.objects.filter(actif=True)
    
    context = {
        'titre_page': 'Stock & Articles',
        'articles': articles,
        'categories': categories,
        'q': q,
        'categorie_id': categorie_id,
        'etat': etat,
        'alerte': alerte,
    }
    
    return render(request, 'depenses/logistique/liste_articles.html', context)


@login_required
def liste_biens(request):
    """Liste des biens de l'établissement"""
    from utilisateurs.utils import user_school

    # Filtres
    q = request.GET.get('q', '')
    type_bien = request.GET.get('type_bien', '')
    etat = request.GET.get('etat', '')

    biens = BienEtablissement.objects.filter(actif=True)
    # Sécurité : filtrer par école
    ecole = user_school(request.user)
    if ecole:
        biens = biens.filter(cree_par__profil__ecole=ecole)
    
    if q:
        biens = biens.filter(
            Q(code_bien__icontains=q) |
            Q(nom__icontains=q) |
            Q(localisation__icontains=q)
        )
    
    if type_bien:
        biens = biens.filter(type_bien=type_bien)
    
    if etat:
        biens = biens.filter(etat=etat)
    
    context = {
        'titre_page': 'Biens de l\'Établissement',
        'biens': biens,
        'q': q,
        'type_bien': type_bien,
        'etat': etat,
    }
    
    return render(request, 'depenses/logistique/liste_biens.html', context)


@login_required
def creer_bien(request):
    """Créer un bien de l'établissement"""
    
    if request.method == 'POST':
        form = BienEtablissementForm(request.POST, request.FILES)
        if form.is_valid():
            bien = form.save(commit=False)
            bien.cree_par = request.user
            
            # Générer le code du bien si non fourni
            if not bien.code_bien:
                today = date.today()
                prefix = f"BIEN-{today.strftime('%Y%m%d')}"
                last_bien = BienEtablissement.objects.filter(
                    code_bien__startswith=prefix
                ).order_by('-code_bien').first()
                
                if last_bien:
                    last_num = int(last_bien.code_bien.split('-')[-1])
                    bien.code_bien = f"{prefix}-{last_num + 1:04d}"
                else:
                    bien.code_bien = f"{prefix}-0001"
            
            bien.save()
            messages.success(request, f'Bien "{bien.nom}" créé avec succès.')
            return redirect('depenses:liste_biens')
    else:
        form = BienEtablissementForm()
    
    context = {
        'titre_page': 'Nouveau Bien',
        'form': form,
    }
    
    return render(request, 'depenses/logistique/form_bien.html', context)


@login_required
def modifier_bien(request, bien_id):
    """Modifier un bien de l'établissement"""
    
    bien = get_object_or_404(BienEtablissement, pk=bien_id)
    
    if request.method == 'POST':
        form = BienEtablissementForm(request.POST, request.FILES, instance=bien)
        if form.is_valid():
            form.save()
            messages.success(request, f'Bien "{bien.nom}" modifié avec succès.')
            return redirect('depenses:liste_biens')
    else:
        form = BienEtablissementForm(instance=bien)
    
    context = {
        'titre_page': 'Modifier Bien',
        'form': form,
        'bien': bien,
    }
    
    return render(request, 'depenses/logistique/form_bien.html', context)


@login_required
def liste_mouvements(request):
    """Liste des mouvements de stock"""
    from utilisateurs.utils import user_school

    # Filtres
    article_id = request.GET.get('article', '')
    type_mouvement = request.GET.get('type', '')
    date_debut = request.GET.get('date_debut', '')
    date_fin = request.GET.get('date_fin', '')

    mouvements = MouvementStock.objects.select_related(
        'article', 'cree_par'
    ).all()
    # Sécurité : filtrer par école
    ecole = user_school(request.user)
    if ecole:
        mouvements = mouvements.filter(cree_par__profil__ecole=ecole)
    
    if article_id:
        mouvements = mouvements.filter(article_id=article_id)
    
    if type_mouvement:
        mouvements = mouvements.filter(type_mouvement=type_mouvement)
    
    if date_debut:
        mouvements = mouvements.filter(date_mouvement__gte=date_debut)
    
    if date_fin:
        mouvements = mouvements.filter(date_mouvement__lte=date_fin)
    
    articles = Article.objects.filter(actif=True)
    
    context = {
        'titre_page': 'Mouvements de Stock',
        'mouvements': mouvements,
        'articles': articles,
        'article_id': article_id,
        'type_mouvement': type_mouvement,
        'date_debut': date_debut,
        'date_fin': date_fin,
    }
    
    return render(request, 'depenses/logistique/liste_mouvements.html', context)


@login_required
def liste_inventaires(request):
    """Liste des inventaires"""
    
    inventaires = Inventaire.objects.select_related(
        'cree_par', 'valide_par'
    ).order_by('-date_inventaire')
    
    context = {
        'titre_page': 'Inventaires',
        'inventaires': inventaires,
    }
    
    return render(request, 'depenses/logistique/liste_inventaires.html', context)


@login_required
def creer_mouvement(request):
    """Créer un mouvement de stock"""
    
    if request.method == 'POST':
        form = MouvementStockForm(request.POST)
        if form.is_valid():
            mouvement = form.save(commit=False)
            mouvement.cree_par = request.user
            
            # Générer le numéro de mouvement
            today = date.today()
            prefix = f"MVT-{today.strftime('%Y%m%d')}"
            last_mvt = MouvementStock.objects.filter(
                numero_mouvement__startswith=prefix
            ).order_by('-numero_mouvement').first()
            
            if last_mvt:
                last_num = int(last_mvt.numero_mouvement.split('-')[-1])
                mouvement.numero_mouvement = f"{prefix}-{last_num + 1:04d}"
            else:
                mouvement.numero_mouvement = f"{prefix}-0001"
            
            mouvement.save()
            messages.success(request, 'Mouvement de stock créé avec succès.')
            return redirect('depenses:liste_mouvements')
    else:
        form = MouvementStockForm()
    
    context = {
        'titre_page': 'Nouveau Mouvement',
        'form': form,
    }
    
    return render(request, 'depenses/logistique/form_mouvement.html', context)


@login_required
def export_stock_excel(request):
    """Exporter le stock en Excel"""
    
    # Créer le workbook
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Stock Articles"
    
    # En-têtes
    headers = [
        'Code Article', 'Nom', 'Catégorie', 'Stock Actuel', 
        'Stock Minimum', 'Prix Unitaire', 'Valeur Stock', 'État', 'Emplacement'
    ]
    
    # Style des en-têtes
    header_fill = PatternFill(start_color="366092", end_color="366092", fill_type="solid")
    header_font = Font(bold=True, color="FFFFFF")
    
    for col, header in enumerate(headers, 1):
        cell = ws.cell(row=1, column=col, value=header)
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = Alignment(horizontal='center')
    
    # Données
    articles = Article.objects.select_related('categorie').filter(actif=True)
    
    for row, article in enumerate(articles, 2):
        ws.cell(row=row, column=1, value=article.code_article)
        ws.cell(row=row, column=2, value=article.nom)
        ws.cell(row=row, column=3, value=article.categorie.nom)
        ws.cell(row=row, column=4, value=article.stock_actuel)
        ws.cell(row=row, column=5, value=article.stock_minimum)
        ws.cell(row=row, column=6, value=float(article.prix_unitaire))
        ws.cell(row=row, column=7, value=float(article.valeur_stock))
        ws.cell(row=row, column=8, value=article.get_etat_display())
        ws.cell(row=row, column=9, value=article.emplacement)
    
    # Ajuster la largeur des colonnes
    for col in ws.columns:
        max_length = 0
        column = col[0].column_letter
        for cell in col:
            if cell.value:
                max_length = max(max_length, len(str(cell.value)))
        ws.column_dimensions[column].width = max_length + 2
    
    # Réponse HTTP
    response = HttpResponse(
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = f'attachment; filename=stock_articles_{date.today()}.xlsx'
    
    wb.save(response)
    return response
