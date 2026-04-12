"""
URL configuration for ecole_moderne project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include, re_path
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import TemplateView, RedirectView
from .static_views import serve_static_no_cache
from notes.rapport_scolaire import rapport_scolaire_recherche, rapport_scolaire_detail, rapport_scolaire_pdf, rapport_scolaire_recu_pdf, rapport_scolaire_classes_ajax

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', TemplateView.as_view(template_name='home.html'), name='home'),
    path('index/', TemplateView.as_view(template_name='home.html'), name='index'),
    # Rapport scolaire public (espace parent, pas de login)
    path('rapport-scolaire/', rapport_scolaire_recherche, name='rapport_scolaire'),
    path('rapport-scolaire/detail/', rapport_scolaire_detail, name='rapport_scolaire_detail'),
    path('rapport-scolaire/pdf/', rapport_scolaire_pdf, name='rapport_scolaire_pdf'),
    path('rapport-scolaire/recu/<int:paiement_id>/pdf/', rapport_scolaire_recu_pdf, name='rapport_scolaire_recu_pdf'),
    path('rapport-scolaire/ajax/classes/', rapport_scolaire_classes_ajax, name='rapport_scolaire_classes_ajax'),
    # Friendly redirects for legacy/mistyped routes under /ecole/
    path('ecole/inscription/', RedirectView.as_view(pattern_name='home', permanent=False)),
    path('ecole/inscription-complete/', RedirectView.as_view(pattern_name='home', permanent=False)),
    path('ecole/verifier-statut/', RedirectView.as_view(pattern_name='home', permanent=False)),
    path('eleves/', include('eleves.urls')),
    path('paiements/', include('paiements.urls')),
    path('depenses/', include('depenses.urls')),
    path('salaires/', include('salaires.urls')),
    path('administration/', include('administration.urls')),
    path('utilisateurs/', include('utilisateurs.urls')),
    path('rapports/', include('rapports.urls')),
    path('bus/', include('bus.urls')),
    path('notes/', include('notes.urls')),
    path('abonnements/', include('abonnements.urls')),
    path('chatbot/', include('chatbot.urls')),
]

# Servir les fichiers STATIC et MEDIA en développement
if settings.DEBUG:
    # Route spéciale pour les images sans cache (rechargement automatique)
    urlpatterns += [
        re_path(r'^static/images/(?P<path>.*)$', serve_static_no_cache, name='static_images_no_cache'),
    ]
    # Routes normales pour les autres fichiers statiques
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
