# Implémentation des Cartes Scolaires - Guide Complet

## 🎯 Objectif
Implémenter la génération de cartes scolaires au format PDF (format carte bancaire 86mm x 54mm).

---

## 📝 Étape 1: Ajouter les Vues

### Fichier: `eleves/views.py`

Ajouter à la fin du fichier (après la ligne 3458):

```python
@login_required
def generer_carte_scolaire_pdf(request, eleve_id):
    """Génère une carte scolaire pour un élève"""
    eleve = get_object_or_404(
        Eleve.objects.select_related('classe', 'classe__ecole', 'responsable_principal'),
        id=eleve_id
    )
    
    # Vérifier permissions
    if not user_is_admin(request.user):
        user_school_obj = user_school(request.user)
        if not user_school_obj or eleve.classe.ecole != user_school_obj:
            messages.error(request, "Vous n'avez pas accès à cet élève.")
            return redirect('eleves:liste_eleves')
    
    # Créer le PDF
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="carte_scolaire_{eleve.matricule}.pdf"'
    
    from reportlab.lib.units import mm
    width, height = 86*mm, 54*mm
    c = canvas.Canvas(response, pagesize=(width, height))
    
    # Polices
    try:
        pdfmetrics.registerFont(TTFont('Arial', 'C:/Windows/Fonts/arial.ttf'))
        pdfmetrics.registerFont(TTFont('Arial-Bold', 'C:/Windows/Fonts/arialbd.ttf'))
        main_font = 'Arial'
        main_font_bold = 'Arial-Bold'
    except:
        main_font = 'Helvetica'
        main_font_bold = 'Helvetica-Bold'
    
    primary_color = '#2563eb'
    light_color = '#dbeafe'
    
    # Fond et bordure
    c.setFillColor(colors.white)
    c.rect(0, 0, width, height, stroke=0, fill=1)
    c.setStrokeColor(colors.HexColor(primary_color))
    c.setLineWidth(2)
    c.roundRect(2, 2, width-4, height-4, 8, stroke=1, fill=0)
    
    # Bande supérieure
    c.setFillColor(colors.HexColor(primary_color))
    c.roundRect(4, height-35, width-8, 31, 6, stroke=0, fill=1)
    
    # Logo école
    try:
        if eleve.classe.ecole.logo and hasattr(eleve.classe.ecole.logo, 'path'):
            if os.path.exists(eleve.classe.ecole.logo.path):
                logo_size = 22
                c.setFillColor(colors.white)
                c.circle(8 + logo_size/2, height - 30 + logo_size/2, logo_size/2 + 1, stroke=0, fill=1)
                c.drawImage(eleve.classe.ecole.logo.path, 8, height - 30, 
                          width=logo_size, height=logo_size, preserveAspectRatio=True, mask='auto')
    except:
        pass
    
    # Nom école
    c.setFillColor(colors.white)
    c.setFont(main_font_bold, 9)
    c.drawString(35, height-12, eleve.classe.ecole.nom[:35])
    c.setFont(main_font, 7)
    c.drawString(35, height-24, f"Année: {eleve.classe.annee_scolaire}")
    
    # Photo élève
    photo_x = width - 38
    photo_y = height/2 - 5
    photo_size = 32
    
    c.setFillColor(colors.white)
    c.roundRect(photo_x, photo_y, photo_size, photo_size, 5, stroke=0, fill=1)
    c.setStrokeColor(colors.HexColor(primary_color))
    c.setLineWidth(2)
    c.roundRect(photo_x, photo_y, photo_size, photo_size, 5, stroke=1, fill=0)
    
    if eleve.photo:
        try:
            from PIL import Image
            if hasattr(eleve.photo, 'path') and os.path.exists(eleve.photo.path):
                img = Image.open(eleve.photo.path)
                if img.mode != 'RGB':
                    img = img.convert('RGB')
                img.thumbnail((photo_size - 4, photo_size - 4), Image.Resampling.LANCZOS)
                temp_buffer = io.BytesIO()
                img.save(temp_buffer, format='JPEG')
                temp_buffer.seek(0)
                c.drawImage(temp_buffer, photo_x + 2, photo_y + 2, 
                          width=photo_size - 4, height=photo_size - 4, preserveAspectRatio=True)
        except:
            c.setFillColor(colors.HexColor(primary_color))
            c.setFont(main_font_bold, 14)
            c.drawCentredString(photo_x + photo_size/2, photo_y + photo_size/2 - 4, 
                              f"{eleve.prenom[0]}{eleve.nom[0]}")
    else:
        c.setFillColor(colors.HexColor(primary_color))
        c.setFont(main_font_bold, 14)
        c.drawCentredString(photo_x + photo_size/2, photo_y + photo_size/2 - 4, 
                          f"{eleve.prenom[0]}{eleve.nom[0]}")
    
    # Informations élève
    y_pos = height - 50
    c.setFillColor(colors.HexColor('#1f2937'))
    c.setFont(main_font_bold, 11)
    nom = f"{eleve.prenom} {eleve.nom}".upper()[:20]
    c.drawString(8, y_pos, nom)
    
    c.setFont(main_font, 8)
    c.setFillColor(colors.HexColor('#4b5563'))
    c.drawString(8, y_pos-10, f"Matricule: {eleve.matricule}")
    c.drawString(8, y_pos-19, f"Classe: {eleve.classe.nom}")
    c.drawString(8, y_pos-28, f"Né(e) le: {eleve.date_naissance.strftime('%d/%m/%Y')}")
    
    # Pied de page
    c.setFont(main_font, 5)
    c.setFillColor(colors.HexColor('#9ca3af'))
    c.drawRightString(width - 5, 5, f"Généré le {timezone.now().strftime('%d/%m/%Y')}")
    
    c.showPage()
    c.save()
    return response


@login_required
def generer_cartes_classe_pdf(request, classe_id):
    """Génère toutes les cartes d'une classe (2 par page)"""
    classe = get_object_or_404(Classe, id=classe_id)
    
    if not user_is_admin(request.user):
        user_school_obj = user_school(request.user)
        if not user_school_obj or classe.ecole != user_school_obj:
            messages.error(request, "Vous n'avez pas accès à cette classe.")
            return redirect('eleves:liste_eleves')
    
    eleves = Eleve.objects.filter(classe=classe, statut='ACTIF').select_related(
        'classe', 'classe__ecole').order_by('nom', 'prenom')
    
    if not eleves.exists():
        messages.warning(request, "Aucun élève actif dans cette classe.")
        return redirect('eleves:liste_eleves')
    
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="cartes_scolaires_{classe.nom}.pdf"'
    
    from reportlab.lib.units import mm
    from reportlab.lib.pagesizes import A4
    
    card_width, card_height = 86*mm, 54*mm
    margin = 10*mm
    spacing = 5*mm
    
    c = canvas.Canvas(response, pagesize=A4)
    page_width, page_height = A4
    
    try:
        pdfmetrics.registerFont(TTFont('Arial', 'C:/Windows/Fonts/arial.ttf'))
        pdfmetrics.registerFont(TTFont('Arial-Bold', 'C:/Windows/Fonts/arialbd.ttf'))
        main_font = 'Arial'
        main_font_bold = 'Arial-Bold'
    except:
        main_font = 'Helvetica'
        main_font_bold = 'Helvetica-Bold'
    
    primary_color = '#2563eb'
    positions = [
        (margin, page_height - margin - card_height),
        (margin, page_height - margin - (2 * card_height) - spacing),
    ]
    
    card_count = 0
    
    for eleve in eleves:
        pos_index = card_count % 2
        x, y = positions[pos_index]
        
        # Bordure
        c.setStrokeColor(colors.HexColor(primary_color))
        c.setLineWidth(1.5)
        c.roundRect(x, y, card_width, card_height, 8, stroke=1, fill=0)
        
        # Bande supérieure
        c.setFillColor(colors.HexColor(primary_color))
        c.roundRect(x+2, y+card_height-30, card_width-4, 28, 6, stroke=0, fill=1)
        
        # Nom école
        c.setFillColor(colors.white)
        c.setFont(main_font_bold, 8)
        c.drawString(x+5, y+card_height-12, classe.ecole.nom[:40])
        c.setFont(main_font, 6)
        c.drawString(x+5, y+card_height-22, f"Année: {classe.annee_scolaire}")
        
        # Nom élève
        c.setFillColor(colors.HexColor('#1f2937'))
        c.setFont(main_font_bold, 10)
        c.drawString(x+5, y+card_height-42, f"{eleve.prenom} {eleve.nom}".upper()[:25])
        
        # Infos
        c.setFont(main_font, 7)
        c.setFillColor(colors.HexColor('#4b5563'))
        c.drawString(x+5, y+card_height-52, f"Mat: {eleve.matricule}")
        c.drawString(x+5, y+card_height-60, f"Classe: {classe.nom}")
        
        # Photo
        photo_size = 28
        photo_x = x + card_width - photo_size - 5
        photo_y = y + card_height/2 - photo_size/2
        
        c.setFillColor(colors.white)
        c.roundRect(photo_x, photo_y, photo_size, photo_size, 4, stroke=0, fill=1)
        c.setStrokeColor(colors.HexColor(primary_color))
        c.setLineWidth(1)
        c.roundRect(photo_x, photo_y, photo_size, photo_size, 4, stroke=1, fill=0)
        
        if eleve.photo:
            try:
                from PIL import Image
                if hasattr(eleve.photo, 'path') and os.path.exists(eleve.photo.path):
                    img = Image.open(eleve.photo.path)
                    if img.mode != 'RGB':
                        img = img.convert('RGB')
                    img.thumbnail((photo_size-2, photo_size-2), Image.Resampling.LANCZOS)
                    temp_buffer = io.BytesIO()
                    img.save(temp_buffer, format='JPEG')
                    temp_buffer.seek(0)
                    c.drawImage(temp_buffer, photo_x+1, photo_y+1, 
                              width=photo_size-2, height=photo_size-2, preserveAspectRatio=True)
            except:
                c.setFillColor(colors.HexColor(primary_color))
                c.setFont(main_font_bold, 12)
                c.drawCentredString(photo_x+photo_size/2, photo_y+photo_size/2-3, 
                                  f"{eleve.prenom[0]}{eleve.nom[0]}")
        else:
            c.setFillColor(colors.HexColor(primary_color))
            c.setFont(main_font_bold, 12)
            c.drawCentredString(photo_x+photo_size/2, photo_y+photo_size/2-3, 
                              f"{eleve.prenom[0]}{eleve.nom[0]}")
        
        card_count += 1
        if card_count % 2 == 0 and card_count < eleves.count():
            c.showPage()
    
    c.showPage()
    c.save()
    return response
```

---

## 📝 Étape 2: Ajouter les Routes URL

### Fichier: `eleves/urls.py`

Ajouter après la ligne 32 (après ticket-bus-pdf):

```python
path('<int:eleve_id>/carte-scolaire-pdf/', views.generer_carte_scolaire_pdf, name='carte_scolaire_pdf'),

# Après la ligne 36 (après tickets-bus-pdf):
path('classe/<int:classe_id>/cartes-scolaires-pdf/', views.generer_cartes_classe_pdf, name='cartes_scolaires_classe_pdf'),
```

---

## 📝 Étape 3: Mettre à Jour les Templates

### Fichier: `templates/eleves/liste_eleves.html`

**Ligne 145-146**, remplacer:
```javascript
alert('Fonctionnalité de cartes scolaires en cours de développement');
// TODO: Implémenter la génération de cartes scolaires
```

Par:
```javascript
window.location.href = `/eleves/classe/${classeId}/cartes-scolaires-pdf/`;
```

**Ligne 270-271**, remplacer:
```javascript
alert('Fonctionnalité de carte scolaire en cours de développement');
return;
```

Par:
```javascript
window.location.href = `/eleves/${matricule}/carte-scolaire-pdf/`;
return;
```

### Fichier: `templates/eleves/partials/_liste_eleves_results.html`

**Ligne 309-310**, remplacer:
```javascript
alert('Fonctionnalité de carte scolaire en cours de développement');
return;
```

Par:
```javascript
window.location.href = `/eleves/${matricule}/carte-scolaire-pdf/`;
return;
```

---

## 🧪 Étape 4: Tester

### Test 1: Carte Individuelle
```
URL: http://127.0.0.1:8000/eleves/8/carte-scolaire-pdf/

Vérifications:
✅ PDF généré
✅ Format carte bancaire (86x54mm)
✅ Logo école visible
✅ Photo élève visible
✅ Informations complètes
```

### Test 2: Cartes en Masse
```
URL: http://127.0.0.1:8000/eleves/classe/1/cartes-scolaires-pdf/

Vérifications:
✅ PDF généré
✅ 2 cartes par page
✅ Toutes les cartes de la classe
✅ Photos et logos visibles
```

### Test 3: Depuis l'Interface
```
1. Aller sur /eleves/liste/
2. Sélectionner une classe
3. Cliquer sur "Cartes Scolaires"
4. PDF téléchargé automatiquement
```

---

## ✅ Checklist d'Implémentation

- [ ] Copier le code des vues dans `eleves/views.py`
- [ ] Ajouter les routes dans `eleves/urls.py`
- [ ] Mettre à jour `liste_eleves.html`
- [ ] Mettre à jour `_liste_eleves_results.html`
- [ ] Tester carte individuelle
- [ ] Tester cartes en masse
- [ ] Tester depuis l'interface

---

## 📊 Résultat Attendu

### Carte Individuelle
```
┌─────────────────────────────────────┐
│ [Logo] ÉCOLE NAME          [Photo]  │
│ Année: 2024-2025                    │
├─────────────────────────────────────┤
│ PRENOM NOM                          │
│ Matricule: 2025/XXXXX               │
│ Classe: CP1                         │
│ Né(e) le: 01/01/2015                │
└─────────────────────────────────────┘
```

### Cartes en Masse
```
Page A4:
┌─────────────────┐
│ Carte Élève 1   │
└─────────────────┘

┌─────────────────┐
│ Carte Élève 2   │
└─────────────────┘

[Nouvelle page pour élèves 3-4, etc.]
```

---

**🎉 IMPLÉMENTATION COMPLÈTE DES CARTES SCOLAIRES !**

**Statut**: ✅ Prêt à implémenter  
**Temps estimé**: 15-20 minutes  
**Dépendances**: ReportLab, Pillow (déjà installés)
