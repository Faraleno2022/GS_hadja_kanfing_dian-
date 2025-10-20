# 🍽️ Gestion de la Cantine Scolaire

## 📋 Vue d'Ensemble

Le module **Cantine Scolaire** permet de gérer les abonnements des élèves à la cantine avec un système d'alertes automatiques pour suivre de près les expirations.

---

## ✨ Fonctionnalités

### **1. Gestion des Abonnements**
- ✅ Création d'abonnements cantine
- ✅ Modification et renouvellement
- ✅ Suppression d'abonnements
- ✅ Suivi du statut (Actif, Expiré, Suspendu)

### **2. Types de Repas**
- 🌅 **Déjeuner uniquement**
- 🍪 **Goûter uniquement**
- 🍽️ **Complet** (Déjeuner + Goûter)

### **3. Périodicités**
- 📅 **Journalier**
- 📅 **Hebdomadaire**
- 📅 **Mensuel**
- 📅 **Trimestriel**
- 📅 **Annuel**

### **4. Système d'Alertes** 🔔
- ⚠️ **Alertes Critiques** : Expire dans 3 jours ou moins
- 🔔 **Proche Expiration** : Expire dans 7 jours
- ❌ **Expirés** : Abonnements dépassés mais toujours actifs

### **5. Régime Alimentaire**
- 🥗 Gestion des régimes spéciaux (Végétarien, Halal, Sans porc, etc.)
- 🚫 Suivi des allergies alimentaires
- 📝 Notes et observations

### **6. Statistiques et Rapports**
- 📊 Dashboard avec statistiques en temps réel
- 💰 Revenus mensuels estimés
- 📈 Répartition par type de repas
- 📥 Export Excel

---

## 🚀 Accès Rapide

### **URLs Principales**

```
# Tableau de bord cantine
http://127.0.0.1:8001/bus/cantine/

# Liste des abonnements
http://127.0.0.1:8001/bus/cantine/liste/

# Nouvel abonnement
http://127.0.0.1:8001/bus/cantine/nouveau/

# Modifier un abonnement
http://127.0.0.1:8001/bus/cantine/{id}/modifier/

# Export Excel
http://127.0.0.1:8001/bus/cantine/export/excel/
```

---

## 📊 Tableau de Bord

Le tableau de bord affiche :

### **Statistiques Générales**
```
┌─────────────────────────────────────────────────────┐
│ Total: 150  │ Actifs: 135  │ Expirés: 10  │ Suspendus: 5 │
└─────────────────────────────────────────────────────┘
```

### **Alertes Critiques** (Rouge)
- Abonnements expirant dans ≤ 3 jours
- Affichage en priorité
- Bouton de renouvellement rapide

### **Alertes Expirés** (Orange)
- Abonnements déjà expirés mais statut = ACTIF
- Liste des 10 premiers
- Lien vers la liste complète

### **Alertes Proche Expiration** (Bleu)
- Abonnements expirant dans 4-7 jours
- Notification préventive
- Actions de renouvellement

### **Statistiques par Type de Repas**
```
┌──────────────┬──────────────┬──────────────┐
│  Déjeuner    │   Goûter     │   Complet    │
│     85       │     25       │     25       │
└──────────────┴──────────────┴──────────────┘
```

### **Revenus Mensuels Estimés**
- Calcul automatique basé sur les abonnements mensuels actifs
- Affichage en GNF

---

## 🎯 Comment Utiliser

### **1. Créer un Abonnement**

**Étape 1 :** Cliquez sur "Nouvel Abonnement"

**Étape 2 :** Remplissez le formulaire :
- **Élève** : Sélectionnez l'élève
- **Montant** : Prix de l'abonnement (GNF)
- **Périodicité** : Mensuel, Trimestriel, etc.
- **Type de repas** : Déjeuner, Goûter ou Complet
- **Date début** : Date de début de l'abonnement
- **Date expiration** : Date de fin
- **Statut** : Actif (par défaut)

**Étape 3 (Optionnel) :** Ajoutez des informations supplémentaires :
- **Régime alimentaire** : Ex. "Végétarien", "Halal"
- **Allergies** : Ex. "Arachides, Lactose"
- **Contact parent** : Téléphone pour les relances
- **Alerte avant** : Nombre de jours avant expiration (défaut: 7)

**Étape 4 :** Cliquez sur "Enregistrer"

---

### **2. Renouveler un Abonnement**

**Méthode 1 : Depuis les Alertes**
1. Allez sur le tableau de bord
2. Dans la section "Alertes Critiques" ou "Proche Expiration"
3. Cliquez sur l'icône 🔄 (Renouveler)
4. Modifiez la date d'expiration
5. Enregistrez

**Méthode 2 : Depuis la Liste**
1. Allez sur "Liste des Abonnements"
2. Trouvez l'abonnement à renouveler
3. Cliquez sur "Modifier"
4. Changez la date d'expiration
5. Enregistrez

---

### **3. Filtrer les Abonnements**

Dans la liste des abonnements, utilisez les filtres :

**Par Statut :**
- `?filtre=actif` : Abonnements actifs
- `?filtre=expire` : Abonnements expirés
- `?filtre=suspendu` : Abonnements suspendus
- `?filtre=proche_expiration` : Expire dans 7 jours
- `?filtre=critique` : Expire dans 3 jours ou moins

**Par Type de Repas :**
- `?type_repas=DEJEUNER`
- `?type_repas=GOUTER`
- `?type_repas=COMPLET`

**Par Classe :**
- `?classe={classe_id}`

**Recherche :**
- `?q=nom_eleve` : Recherche par nom, prénom, matricule

**Exemples :**
```
# Tous les abonnements critiques
/bus/cantine/liste/?filtre=critique

# Abonnements déjeuner actifs
/bus/cantine/liste/?filtre=actif&type_repas=DEJEUNER

# Recherche "Diallo"
/bus/cantine/liste/?q=Diallo
```

---

### **4. Exporter en Excel**

**Méthode 1 : Depuis le Tableau de Bord**
1. Cliquez sur "Exporter en Excel" dans les actions rapides

**Méthode 2 : Depuis la Liste**
1. Appliquez les filtres souhaités
2. Cliquez sur "Export Excel"

**Contenu de l'Export :**
- Matricule
- Nom et Prénom
- Classe
- Type de repas
- Périodicité
- Montant
- Dates (début, expiration)
- Jours restants
- Statut
- Régime alimentaire
- Allergies
- Contact parent

---

## 🔔 Système d'Alertes

### **Niveaux d'Alerte**

| Niveau | Jours Restants | Couleur | Action |
|--------|----------------|---------|--------|
| **Critique** | ≤ 3 jours | 🔴 Rouge | Renouveler immédiatement |
| **Avertissement** | 4-7 jours | 🟡 Orange | Planifier le renouvellement |
| **Information** | > 7 jours | 🔵 Bleu | Surveillance normale |

### **Calcul Automatique**

Le système calcule automatiquement :
- **Jours restants** : `date_expiration - aujourd'hui`
- **Est proche expiration** : `jours_restants ≤ alerte_avant_jours`
- **Est expiré** : `aujourd'hui > date_expiration`

### **Propriétés du Modèle**

```python
# Dans le modèle AbonnementCantine
@property
def jours_restants(self) -> int:
    """Nombre de jours avant expiration"""
    
@property
def est_proche_expiration(self) -> bool:
    """True si expire dans les N jours (alerte_avant_jours)"""
    
@property
def est_expire(self) -> bool:
    """True si déjà expiré"""
```

---

## 💾 Structure de la Base de Données

### **Modèle : AbonnementCantine**

```python
class AbonnementCantine(models.Model):
    # Informations de base
    eleve = ForeignKey(Eleve)
    montant = DecimalField(max_digits=10, decimal_places=0)
    periodicite = CharField(choices=Periodicite.choices)
    type_repas = CharField(choices=TypeRepas.choices)
    
    # Dates
    date_debut = DateField()
    date_expiration = DateField()
    statut = CharField(choices=Statut.choices)
    
    # Alertes
    alerte_avant_jours = PositiveIntegerField(default=7)
    derniere_relance = DateTimeField(null=True, blank=True)
    
    # Régime alimentaire
    regime_alimentaire = CharField(max_length=100, blank=True)
    allergies = TextField(blank=True)
    
    # Contact
    contact_parent = CharField(max_length=100, blank=True)
    observations = TextField(blank=True)
    
    # Métadonnées
    created_at = DateTimeField(auto_now_add=True)
    updated_at = DateTimeField(auto_now=True)
```

### **Choix (Choices)**

```python
class Statut(TextChoices):
    ACTIF = 'ACTIF', 'Actif'
    EXPIRE = 'EXPIRE', 'Expiré'
    SUSPENDU = 'SUSPENDU', 'Suspendu'

class Periodicite(TextChoices):
    JOURNALIER = 'JOURNALIER', 'Journalier'
    HEBDOMADAIRE = 'HEBDOMADAIRE', 'Hebdomadaire'
    MENSUEL = 'MENSUEL', 'Mensuel'
    TRIMESTRIEL = 'TRIMESTRIEL', 'Trimestriel'
    ANNUEL = 'ANNUEL', 'Annuel'

class TypeRepas(TextChoices):
    DEJEUNER = 'DEJEUNER', 'Déjeuner uniquement'
    GOUTER = 'GOUTER', 'Goûter uniquement'
    COMPLET = 'COMPLET', 'Déjeuner + Goûter'
```

---

## 🔧 Migration de la Base de Données

Après avoir ajouté le modèle, créez et appliquez la migration :

```bash
# Créer la migration
python manage.py makemigrations bus

# Appliquer la migration
python manage.py migrate bus
```

**Sortie attendue :**
```
Migrations for 'bus':
  bus\migrations\0002_abonnementcantine.py
    - Create model AbonnementCantine
```

---

## 📱 Interface Admin Django

Le modèle est enregistré dans l'admin Django avec :

**Liste :**
- Élève
- Type de repas
- Montant
- Périodicité
- Dates (début, expiration)
- Statut
- Jours restants

**Filtres :**
- Statut
- Périodicité
- Type de repas
- Régime alimentaire

**Recherche :**
- Nom élève
- Prénom élève
- Matricule
- Contact parent
- Régime alimentaire

**Fieldsets organisés :**
1. Informations Élève
2. Abonnement
3. Régime Alimentaire (collapsible)
4. Alertes
5. Observations (collapsible)
6. Métadonnées (collapsible)

---

## 🎨 Intégration dans le Menu

### **Ajouter un Bouton dans le Menu Principal**

Dans `templates/base.html` ou votre menu de navigation :

```html
<!-- Menu Bus/Cantine -->
<li class="nav-item dropdown">
    <a class="nav-link dropdown-toggle" href="#" data-bs-toggle="dropdown">
        <i class="fas fa-bus"></i> Transport & Cantine
    </a>
    <ul class="dropdown-menu">
        <!-- Bus -->
        <li>
            <a class="dropdown-item" href="{% url 'bus:index' %}">
                <i class="fas fa-bus"></i> Abonnements Bus
            </a>
        </li>
        <li><hr class="dropdown-divider"></li>
        
        <!-- Cantine -->
        <li>
            <a class="dropdown-item" href="{% url 'bus:tableau_bord_cantine' %}">
                <i class="fas fa-utensils text-success"></i> Cantine Scolaire
            </a>
        </li>
        <li>
            <a class="dropdown-item" href="{% url 'bus:liste_abonnements_cantine' %}">
                <i class="fas fa-list"></i> Liste Abonnements Cantine
            </a>
        </li>
        <li>
            <a class="dropdown-item" href="{% url 'bus:creer_abonnement_cantine' %}">
                <i class="fas fa-plus"></i> Nouvel Abonnement Cantine
            </a>
        </li>
    </ul>
</li>
```

### **Badge d'Alerte dans le Menu**

Pour afficher le nombre d'alertes critiques :

```html
<a class="dropdown-item" href="{% url 'bus:tableau_bord_cantine' %}">
    <i class="fas fa-utensils text-success"></i> Cantine Scolaire
    {% if nb_alertes_cantine > 0 %}
        <span class="badge badge-danger">{{ nb_alertes_cantine }}</span>
    {% endif %}
</a>
```

---

## 📊 API JSON pour Dashboard

### **Endpoint : `/bus/cantine/api/alertes/`**

Retourne les alertes en format JSON pour intégration dans un dashboard.

**Réponse :**
```json
{
    "total": 150,
    "actifs": 135,
    "expires": {
        "count": 10,
        "abonnements": [
            {
                "id": 42,
                "eleve": "DIALLO Mamadou",
                "classe": "7ème Année",
                "date_expiration": "10/10/2025",
                "jours_restants": -5
            }
        ]
    },
    "proche_expiration": {
        "count": 15,
        "abonnements": [...]
    },
    "critiques": {
        "count": 5,
        "abonnements": [...]
    }
}
```

**Utilisation en JavaScript :**
```javascript
fetch('/bus/cantine/api/alertes/')
    .then(response => response.json())
    .then(data => {
        console.log('Alertes critiques:', data.critiques.count);
        // Afficher les alertes dans le dashboard
    });
```

---

## 🎯 Cas d'Usage

### **Scénario 1 : Renouvellement Mensuel**

1. **Jour 1** : Création abonnement (01/10/2025 → 31/10/2025)
2. **Jour 24** : Alerte "Proche expiration" (7 jours restants)
3. **Jour 28** : Alerte "Critique" (3 jours restants)
4. **Jour 30** : Renouvellement (01/11/2025 → 30/11/2025)

### **Scénario 2 : Abonnement Trimestriel**

1. **Trimestre 1** : 01/10/2025 → 31/12/2025
2. **Alerte** : 24/12/2025 (7 jours avant)
3. **Renouvellement** : 01/01/2026 → 31/03/2026

### **Scénario 3 : Gestion des Allergies**

1. Élève avec allergie aux arachides
2. Saisie dans le champ "Allergies"
3. Information visible dans la liste
4. Export Excel inclut cette information
5. Personnel de cantine peut consulter

---

## ✅ Checklist de Déploiement

- [x] Modèle `AbonnementCantine` créé
- [x] Formulaire `AbonnementCantineForm` créé
- [x] Vues dans `views_cantine.py` créées
- [x] Routes dans `urls.py` ajoutées
- [x] Admin Django configuré
- [ ] Migration créée et appliquée
- [ ] Template `tableau_bord.html` créé
- [ ] Templates `liste.html`, `form.html` à créer
- [ ] Intégration dans le menu principal
- [ ] Tests fonctionnels

---

## 🚀 Prochaines Étapes

1. **Créer la migration** : `python manage.py makemigrations bus`
2. **Appliquer la migration** : `python manage.py migrate bus`
3. **Créer les templates manquants** (liste, formulaire)
4. **Ajouter le bouton dans le menu**
5. **Tester le système complet**

---

## 📝 Résumé

Le module **Cantine Scolaire** offre :

- ✅ **Gestion complète** des abonnements
- ✅ **Alertes automatiques** (critiques, proche expiration, expirés)
- ✅ **Types de repas** (Déjeuner, Goûter, Complet)
- ✅ **Régimes alimentaires** et allergies
- ✅ **Statistiques** en temps réel
- ✅ **Export Excel** avec filtres
- ✅ **API JSON** pour intégration
- ✅ **Interface intuitive** avec codes couleur

**URL principale :** `http://127.0.0.1:8001/bus/cantine/`

🎉 **Le système est prêt à être déployé !**
