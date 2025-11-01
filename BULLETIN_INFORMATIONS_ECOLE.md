# 📄 Bulletin de Notes - Informations de l'École Automatiques

## ✅ Fonctionnalité Déjà Implémentée

Le bulletin de notes **récupère automatiquement** toutes les informations de l'école depuis la base de données !

---

## 🎯 Ce Qui S'Affiche Automatiquement

### **1. En-tête National (Automatique)**
```
République de Guinée
Travail - Justice - Solidarité (avec couleurs du drapeau)
Ministère de l'Enseignement Pré-Universitaire et de l'Alphabétisation
```

### **2. Informations Administratives**
Ces champs sont récupérés depuis le modèle `Ecole` :
- **IRE** : `ecole.ire`
- **DPE** : `ecole.dpe`
- **DESEE** : `ecole.desee`

### **3. Informations de l'École (Dans un cadre)**
- **Logo** : Affiché à gauche (54x54 pixels)
- **Nom de l'école** : En MAJUSCULES, centré
- **Adresse** : Avec retour à la ligne automatique
- **Téléphone** : Format +224XXXXXXXXX
- **Email** : Adresse email de l'école
- **Directeur** : Nom du directeur

### **4. Filigrane**
- Logo en filigrane sur toute la page (opacité 4%, rotation 30°)

---

## 📝 Comment Remplir les Informations de l'École

### **Méthode 1 : Interface Admin Django**

1. Allez sur : `http://127.0.0.1:8001/admin/`
2. Connectez-vous avec un compte **superuser**
3. Cliquez sur **"Écoles"**
4. Sélectionnez votre école
5. Remplissez tous les champs :

#### **Champs Obligatoires**
- **Nom** : Ex. "GS myschool"
- **Adresse** : Ex. "Quartier Hamdallaye, Commune de Ratoma, Conakry"
- **Téléphone** : Ex. "+224622123456" (format strict)
- **Directeur** : Ex. "M. Mamadou DIALLO"

#### **Champs Optionnels mais Recommandés**
- **Email** : Ex. "contact@gshadjakanfing.edu.gn"
- **Logo** : Téléchargez une image (PNG/JPG, 500x500px recommandé)
- **IRE** : Ex. "IRE de Conakry"
- **DPE** : Ex. "DPE de Ratoma"
- **DESEE** : Ex. "DESEE de Ratoma"
- **Code préfixe** : Ex. "GSHKD/" (pour les matricules)

6. Cliquez sur **"Enregistrer"**

---

### **Méthode 2 : Interface de Gestion (Si Disponible)**

1. Allez dans **"Administration"** → **"Gestion des Écoles"**
2. Cliquez sur **"Modifier"** pour votre école
3. Remplissez les informations
4. Enregistrez

---

## 🖼️ Format du Logo

### **Recommandations**
- **Format** : PNG avec fond transparent (recommandé) ou JPG
- **Dimensions** : 500x500 pixels (carré)
- **Taille** : Maximum 2 MB
- **Qualité** : Haute résolution pour impression

### **Où le Logo Apparaît**
1. **En-tête du bulletin** : 54x54 pixels à gauche
2. **Filigrane** : Grande taille, opacité 4%, rotation 30°
3. **Cartes scolaires** : En haut de la carte
4. **Tous les documents PDF** : Automatiquement

---

## 📋 Exemple de Données Complètes

```python
# Exemple pour GS myschool
nom = "GS myschool"
adresse = "Quartier Hamdallaye, Commune de Ratoma, BP 1234, Conakry, Guinée"
telephone = "+224622123456"
email = "contact@gshadjakanfing.edu.gn"
directeur = "M. Mamadou DIALLO"
logo = "ecoles/logos/logo_gshkd.png"
ire = "IRE de Conakry"
dpe = "DPE de Ratoma"
desee = "DESEE de Ratoma"
code_prefixe = "GSHKD/"
```

---

## 🔧 Code Technique (Déjà Implémenté)

### **Fichier : `notes/views.py`**

#### **Fonction : `_draw_school_header()`**
```python
def _draw_school_header(c, ecole, *, y_start, margin, page_width):
    """Dessine un en-tête officiel avec logo, nom, coordonnées."""
    
    # 1. En-tête national
    c.drawCentredString(center_x, y, "République de Guinée")
    # Devise avec couleurs
    
    # 2. Informations administratives
    ire = getattr(ecole, 'ire', None) or ''
    dpe = getattr(ecole, 'dpe', None) or ''
    desee = getattr(ecole, 'desee', None) or ''
    c.drawCentredString(center_x, y, f"IRE: {ire}")
    c.drawCentredString(center_x, y, f"DPE: {dpe}")
    c.drawCentredString(center_x, y, f"DESEE: {desee}")
    
    # 3. Logo (gauche)
    if hasattr(ecole, 'logo') and ecole.logo.path:
        c.drawImage(ecole.logo.path, margin + 8, y - 62, 
                    width=54, height=54, preserveAspectRatio=True)
    
    # 4. Informations de l'école (centrées)
    school_name = (getattr(ecole, 'nom', '') or 'ÉCOLE').upper()
    c.drawCentredString(center_x, top_line_y, school_name)
    
    adresse = getattr(ecole, 'adresse', None) or ''
    telephone = getattr(ecole, 'telephone', None) or ''
    email = getattr(ecole, 'email', None) or ''
    directeur = getattr(ecole, 'directeur', None) or ''
    
    # Affichage avec retour à la ligne automatique
    if adresse:
        draw_wrapped_centered(f"Adresse: {adresse}", line_y, avail_w)
    if telephone or email:
        draw_wrapped_centered(f"Tél: {telephone}  |  Email: {email}", line_y, avail_w)
    if directeur:
        c.drawCentredString(center_x, line_y, f"Directeur: {directeur}")
    
    # 5. Cadre autour des informations
    c.roundRect(margin, frame_start_y - box_height, 
                page_width - 2*margin, box_height, 6, stroke=1, fill=0)
    
    return y
```

#### **Utilisation dans `bulletin_pdf()`**
```python
def bulletin_pdf(request, classe_id: int, eleve_id: int, trimestre: str = "T1"):
    # ... récupération des données ...
    
    # En-tête avec informations de l'école
    if getattr(classe, 'ecole', None):
        y = _draw_school_header(c, classe.ecole, y_start=y, 
                                 margin=margin, page_width=width)
    
    # Filigrane avec logo
    from ecole_moderne.pdf_utils import draw_logo_watermark
    draw_logo_watermark(c, width, height, opacity=0.04, 
                        rotate=30, scale=1.5, ecole=classe.ecole)
    
    # ... reste du bulletin ...
```

---

## 🎨 Aperçu du Bulletin

```
┌─────────────────────────────────────────────────────────────┐
│                   République de Guinée                       │
│              Travail - Justice - Solidarité                  │
│  Ministère de l'Enseignement Pré-Universitaire et de       │
│                  l'Alphabétisation                           │
│                                                              │
│                    IRE: IRE de Conakry                       │
│                    DPE: DPE de Ratoma                        │
│                    DESEE: DESEE de Ratoma                    │
│                                                              │
│  ┌────────────────────────────────────────────────────┐    │
│  │ [LOGO]    GS myschool                   │    │
│  │                                                     │    │
│  │  Adresse: Quartier Hamdallaye, Commune de Ratoma  │    │
│  │  Tél: +224622123456  |  Email: contact@gshkd.gn   │    │
│  │  Directeur: M. Mamadou DIALLO                      │    │
│  └────────────────────────────────────────────────────┘    │
│                                                              │
│              Bulletin de notes — T1                          │
│                                                              │
│  Élève: DIALLO Mamadou  (Matricule: PN3-042)               │
│  Classe: 3ème Année — Année: 2025-2026                      │
│  ─────────────────────────────────────────────────────      │
│                                                              │
│  Matière          Coef.  Moyenne /20  Moy. classe          │
│  ──────────────────────────────────────────────────────     │
│  Mathématiques      4      15.50         13.20             │
│  Français           4      14.00         12.50             │
│  Sciences           3      16.00         14.00             │
│  Histoire-Géo       2      13.50         11.80             │
│  ──────────────────────────────────────────────────────     │
│                                                              │
│  Moyenne générale: 14.85 / 20                               │
│  Rang: 3 / 25                                               │
│  Mention: Bien                                              │
│                                                              │
│  Prof. principal: _______________  Chef d'établ.: ________  │
│  Parent/Tuteur: _____________________                       │
│                                                              │
│  Généré le 14/10/2025 05:47                                 │
└─────────────────────────────────────────────────────────────┘
```

---

## ✅ Vérification

### **Pour Tester**
1. Remplissez les informations de votre école dans l'admin
2. Générez un bulletin : `/notes/classes/{classe_id}/eleves/{eleve_id}/bulletin/{trimestre}/`
3. Vérifiez que toutes les informations s'affichent correctement

### **Points de Contrôle**
- ✅ Logo affiché en haut à gauche
- ✅ Nom de l'école en MAJUSCULES
- ✅ Adresse complète avec retour à la ligne
- ✅ Téléphone et email sur la même ligne
- ✅ Nom du directeur
- ✅ IRE, DPE, DESEE affichés
- ✅ Cadre autour des informations
- ✅ Filigrane en arrière-plan

---

## 🔍 Dépannage

### **Le logo ne s'affiche pas**
**Causes possibles :**
1. Le fichier logo n'existe pas dans `media/ecoles/logos/`
2. Le chemin est incorrect
3. Le format n'est pas supporté

**Solution :**
```python
# Vérifier dans l'admin Django
1. Allez dans Écoles
2. Vérifiez que le champ "Logo" contient un fichier
3. Téléchargez à nouveau si nécessaire
```

### **Les informations sont vides**
**Cause :** Les champs ne sont pas remplis dans la base de données

**Solution :**
```python
# Remplir via l'admin ou via shell
python manage.py shell

from eleves.models import Ecole
ecole = Ecole.objects.first()
ecole.nom = "GS myschool"
ecole.adresse = "Quartier Hamdallaye, Ratoma"
ecole.telephone = "+224622123456"
ecole.directeur = "M. Mamadou DIALLO"
ecole.ire = "IRE de Conakry"
ecole.dpe = "DPE de Ratoma"
ecole.desee = "DESEE de Ratoma"
ecole.save()
```

### **Le texte dépasse du cadre**
**Cause :** Adresse trop longue

**Solution :** La fonction `draw_wrapped_centered()` gère automatiquement le retour à la ligne. Si le problème persiste, réduisez la longueur de l'adresse.

---

## 📊 Champs du Modèle Ecole

```python
class Ecole(models.Model):
    # Informations de base
    nom = models.CharField(max_length=200)
    adresse = models.TextField()
    telephone = models.CharField(max_length=20)
    email = models.EmailField(blank=True, null=True)
    directeur = models.CharField(max_length=100)
    logo = models.ImageField(upload_to='ecoles/logos/', blank=True, null=True)
    
    # Informations administratives
    ire = models.CharField(max_length=100, blank=True, null=True)
    dpe = models.CharField(max_length=100, blank=True, null=True)
    desee = models.CharField(max_length=100, blank=True, null=True)
    
    # Autres
    code_prefixe = models.CharField(max_length=20, blank=True, null=True)
    date_creation = models.DateTimeField(auto_now_add=True)
    etat = models.CharField(max_length=20, default="BROUILLON")
```

---

## 🎯 Résumé

### **✅ Ce Qui Fonctionne Automatiquement**
1. Récupération de toutes les informations depuis `classe.ecole`
2. Affichage du logo (si disponible)
3. Formatage automatique avec retour à la ligne
4. En-tête national standardisé
5. Filigrane avec logo

### **📝 Ce Que Vous Devez Faire**
1. Remplir les informations de l'école dans l'admin
2. Télécharger un logo (recommandé)
3. Vérifier que tout s'affiche correctement

### **🚀 Avantages**
- ✅ **Automatique** : Pas besoin de modifier le code
- ✅ **Centralisé** : Une seule source de vérité (base de données)
- ✅ **Cohérent** : Même format sur tous les bulletins
- ✅ **Professionnel** : En-tête officiel avec logo et cadre
- ✅ **Flexible** : Retour à la ligne automatique pour textes longs

---

**Le système est déjà opérationnel ! Il suffit de remplir les informations de votre école dans l'interface d'administration. 🎉**
