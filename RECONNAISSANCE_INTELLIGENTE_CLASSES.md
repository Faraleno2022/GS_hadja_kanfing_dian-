# 🧠 Système de Reconnaissance Intelligente des Classes

## 🎯 Vue d'Ensemble

Le système détecte automatiquement le **niveau** (PRIMAIRE/SECONDAIRE), la **série** (Littéraire/Scientifique) et la **section** (A/B/C) à partir du nom de la classe, sans dépendre du champ `niveau_enseignement` de la base de données.

---

## ✨ Fonctionnalités

### 1. **Détection du Niveau**

Le système reconnaît automatiquement :

#### 🔵 PRIMAIRE
- **CP1**, **CP 1**, **CP2**, **CP 2**
- **CE1**, **CE 1**, **CE2**, **CE 2**
- **CM1**, **CM 1**, **CM2**, **CM 2**

#### 🔴 SECONDAIRE - Collège
- **7ème Année**, **7ème Année A**, **7ème Année B**
- **8ème Année**, **8ème Année A**, **8ème Année B**
- **9ème Année**, **9ème Année A**, **9ème Année B**
- **10ème Année**, **10ème Année A**, **10ème Année B**

#### 🔴 SECONDAIRE - Lycée
- **11ème Année**, **11ème Série littéraire**, **11ème Série scientifique**
- **12ème Année**, **12ème Série littéraire**, **12ème Série scientifique**
- **Terminale**, **Terminale SE**, **Terminale SM**, **Terminale SS**

---

### 2. **Détection de la Série**

Le système reconnaît les séries suivantes :

| Nom dans la classe | Série détectée |
|-------------------|----------------|
| "Série littéraire" | Littéraire |
| "Série scientifique" | Scientifique |
| "SL" ou "L" | Littéraire |
| "SS", "SM", "S" | Scientifique |
| "SE" | Sciences Économiques |
| "Terminale SM" | Scientifique (SM) |
| "Terminale SS" | Scientifique (SS) |
| "Terminale SE" | Sciences Économiques (SE) |

---

### 3. **Détection de la Section**

Le système détecte automatiquement les sections A, B, C, etc. :

| Nom de la classe | Section détectée |
|-----------------|------------------|
| "7ème Année A" | A |
| "9ème Année B" | B |
| "12ème Année C" | C |

---

## 🔧 Utilisation

### Dans le Code Python

```python
from notes.classifier import classify

# Exemple 1: Collège avec section
niveau, serie, section = classify("7ème Année A")
# Résultat: ('SECONDAIRE', None, 'A')

# Exemple 2: Lycée avec série
niveau, serie, section = classify("12ème Série scientifique")
# Résultat: ('SECONDAIRE', 'Scientifique', None)

# Exemple 3: Terminale avec sous-série
niveau, serie, section = classify("Terminale SM")
# Résultat: ('SECONDAIRE', 'Scientifique (SM)', None)

# Exemple 4: Primaire
niveau, serie, section = classify("CE1")
# Résultat: ('PRIMAIRE', None, None)
```

### Dans le Bulletin Intelligent

Le système est automatiquement intégré dans `CalculateurBulletinIntelligent` :

```python
from notes.bulletin_intelligent import CalculateurBulletinIntelligent

calculateur = CalculateurBulletinIntelligent(eleve, classe_note, 'TRIMESTRE_1')
bulletin = calculateur.generer_bulletin()

# Le bulletin contient maintenant:
print(bulletin['niveau'])    # 'PRIMAIRE' ou 'SECONDAIRE'
print(bulletin['serie'])     # 'Littéraire', 'Scientifique', etc. ou None
print(bulletin['section'])   # 'A', 'B', 'C', etc. ou None
```

---

## 📊 Exemples de Reconnaissance

### Collège

```python
classify("7ème Année")        → ('SECONDAIRE', None, None)
classify("7ème Année A")      → ('SECONDAIRE', None, 'A')
classify("8ème Année B")      → ('SECONDAIRE', None, 'B')
classify("9ème Année")        → ('SECONDAIRE', None, None)
classify("10ème Année A")     → ('SECONDAIRE', None, 'A')
```

### Lycée - Années

```python
classify("11ème Année")       → ('SECONDAIRE', None, None)
classify("12ème Année")       → ('SECONDAIRE', None, None)
```

### Lycée - Séries

```python
classify("11ème Série littéraire")      → ('SECONDAIRE', 'Littéraire', None)
classify("11ème Série scientifique")    → ('SECONDAIRE', 'Scientifique', None)
classify("12ème Série littéraire")      → ('SECONDAIRE', 'Littéraire', None)
classify("12ème Série scientifique")    → ('SECONDAIRE', 'Scientifique', None)
```

### Terminale

```python
classify("Terminale")         → ('SECONDAIRE', None, None)
classify("Terminale SE")      → ('SECONDAIRE', 'Sciences Économiques (SE)', None)
classify("Terminale SM")      → ('SECONDAIRE', 'Scientifique (SM)', None)
classify("Terminale SS")      → ('SECONDAIRE', 'Scientifique (SS)', None)
```

### Primaire

```python
classify("CP1")               → ('PRIMAIRE', None, None)
classify("CE1")               → ('PRIMAIRE', None, None)
classify("CM2")               → ('PRIMAIRE', None, None)
```

---

## 🧪 Tests

### Test du Classificateur

```bash
python test_classifier.py
```

**Résultat attendu:**
```
================================================================================
   TEST DU CLASSIFICATEUR INTELLIGENT DE CLASSES
================================================================================
📚 CP1                            → Niveau: PRIMAIRE      Série: —                         Section: —
📚 7ème Année                     → Niveau: SECONDAIRE    Série: —                         Section: —
📚 7ème Année A                   → Niveau: SECONDAIRE    Série: —                         Section: A
📚 12ème Série scientifique       → Niveau: SECONDAIRE    Série: Scientifique              Section: —
📚 Terminale SM                   → Niveau: SECONDAIRE    Série: Scientifique (SM)         Section: —
================================================================================
   ✅ TEST TERMINÉ
================================================================================
```

### Créer les Classes Secondaires

```bash
python creer_classes_secondaires.py
```

**Résultat attendu:**
```
================================================================================
   🏫 CRÉATION DES CLASSES SECONDAIRES
================================================================================
   ✅ CRÉÉE       7ème Année                          → COLLEGE     
   ✅ CRÉÉE       7ème Année A                        → COLLEGE      Section: A
   ✅ CRÉÉE       12ème Série scientifique            → LYCEE        Série: Scientifique
   ✅ CRÉÉE       Terminale SM                        → LYCEE        Série: Scientifique (SM)
================================================================================
   📊 RÉSUMÉ
================================================================================
   ✅ Classes créées: 24
   🔄 Classes mises à jour: 0
   📚 Total classes secondaires: 24
================================================================================
```

---

## 🔍 Algorithme de Détection

### Niveau (PRIMAIRE vs SECONDAIRE)

```python
1. Recherche de mots-clés PRIMAIRE:
   - CP1, CP2, CE1, CE2, CM1, CM2
   
2. Recherche de mots-clés COLLÈGE:
   - 7ème, 8ème, 9ème, 10ème
   
3. Recherche de mots-clés LYCÉE:
   - 11ème, 12ème, Terminale
   
4. Si aucun match → PRIMAIRE par défaut
```

### Série

```python
1. Recherche de patterns:
   - "Série littéraire" → Littéraire
   - "Série scientifique" → Scientifique
   - "SL" ou "L" → Littéraire
   - "SS", "SM", "S" → Scientifique
   - "SE" → Sciences Économiques
   
2. Cas spéciaux Terminale:
   - "Terminale SM" → Scientifique (SM)
   - "Terminale SS" → Scientifique (SS)
   - "Terminale SE" → Sciences Économiques (SE)
```

### Section

```python
1. Recherche d'une lettre majuscule isolée en fin de nom:
   - "7ème Année A" → A
   - "9ème Année B" → B
   
2. Pattern regex: \b([A-Z])\b$
```

---

## 🎨 Intégration dans les Templates

### Afficher la Série et la Section

```django
{% if bulletin.serie %}
    <p>Série: {{ bulletin.serie }}</p>
{% endif %}

{% if bulletin.section %}
    <p>Section: {{ bulletin.section }}</p>
{% endif %}
```

### Exemple Complet

```django
<div class="classe-info">
    <h3>{{ bulletin.classe }}</h3>
    
    {% if bulletin.niveau == 'SECONDAIRE' %}
        <span class="badge badge-secondary">Secondaire</span>
        
        {% if bulletin.serie %}
            <span class="badge badge-info">{{ bulletin.serie }}</span>
        {% endif %}
        
        {% if bulletin.section %}
            <span class="badge badge-warning">Section {{ bulletin.section }}</span>
        {% endif %}
    {% else %}
        <span class="badge badge-primary">Primaire</span>
    {% endif %}
</div>
```

---

## 🔧 Personnalisation

### Ajouter de Nouveaux Patterns

Modifiez `notes/classifier.py` :

```python
# Ajouter une nouvelle série
SERIE_PATTERNS = [
    # ... patterns existants ...
    (r"\bnouvelle_serie\b", "Nouvelle Série"),
]

# Ajouter un nouveau niveau
PRIMAIRE_KEYWORDS = [
    # ... keywords existants ...
    r"\bnouveau_niveau\b",
]
```

### Modifier la Logique de Détection

```python
def classify_level(class_name: str) -> str:
    name = class_name.lower()
    
    # Votre logique personnalisée ici
    if "votre_pattern" in name:
        return 'VOTRE_NIVEAU'
    
    # ... reste du code ...
```

---

## 📦 Fichiers Créés

| Fichier | Description |
|---------|-------------|
| `notes/classifier.py` | Module de classification intelligent |
| `test_classifier.py` | Script de test du classificateur |
| `creer_classes_secondaires.py` | Script de création des classes |
| `RECONNAISSANCE_INTELLIGENTE_CLASSES.md` | Documentation complète |

---

## ✅ Avantages

1. **Robustesse** : Fonctionne même si `niveau_enseignement` est absent ou incorrect
2. **Flexibilité** : Reconnaît de nombreuses variantes de noms
3. **Extensibilité** : Facile d'ajouter de nouveaux patterns
4. **Automatique** : Pas besoin de configuration manuelle
5. **Intelligent** : Combine DB et détection automatique

---

## 🚀 Prochaines Étapes

1. **Tester le classificateur** :
   ```bash
   python test_classifier.py
   ```

2. **Créer les classes secondaires** :
   ```bash
   python creer_classes_secondaires.py
   ```

3. **Relancer les tests du bulletin** :
   ```bash
   python test_bulletin_intelligent.py
   ```

4. **Vérifier dans l'interface web** :
   - Accéder à un bulletin
   - Vérifier que la série et la section s'affichent

---

## 📝 Notes Importantes

- Le système privilégie le champ `niveau_enseignement` de la DB s'il est cohérent
- En cas d'incohérence, la détection automatique prend le relais
- Les regex sont insensibles à la casse (majuscules/minuscules)
- Les accents sont gérés (ème, eme)

---

**🎉 Le système de reconnaissance intelligente est maintenant intégré et opérationnel !**
