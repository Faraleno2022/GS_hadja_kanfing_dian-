# 🔧 Solution pour WeasyPrint sur Windows

## ❌ Erreur Rencontrée
```
OSError: cannot load library 'libgobject-2.0-0'
```

WeasyPrint nécessite **GTK+ Runtime** pour fonctionner sur Windows.

## ✅ Solutions Disponibles

### Solution 1 : Utilisation Automatique de ReportLab (DÉJÀ IMPLÉMENTÉE)

Le système **détecte automatiquement** si WeasyPrint fonctionne :
- **Si WeasyPrint fonctionne** → Utilisation de WeasyPrint (meilleur rendu)
- **Si WeasyPrint échoue** → Bascule automatique sur ReportLab

**Aucune action requise !** Le système s'adapte automatiquement.

### Solution 2 : Installer GTK+ pour Windows (OPTIONNEL)

Si vous voulez utiliser WeasyPrint avec toutes ses fonctionnalités :

#### 📥 Installation de GTK+

1. **Télécharger GTK+ Runtime**
   - Aller sur : https://github.com/tschoonj/GTK-for-Windows-Runtime-Environment-Installer/releases
   - Télécharger : `gtk3-runtime-3.24.xx-202x-xx-xx-ts-win64.exe`

2. **Installer GTK+**
   - Exécuter l'installateur
   - Accepter les options par défaut
   - **IMPORTANT** : Cocher "Add GTK to PATH"

3. **Redémarrer votre ordinateur**

4. **Vérifier l'installation**
   ```bash
   python test_weasyprint.py
   ```

## 🎯 État Actuel du Système

### ✅ Ce qui fonctionne MAINTENANT

1. **Export PDF avec ReportLab** (automatique si WeasyPrint échoue)
   - Bulletins générés correctement
   - Toutes les informations présentes
   - Performance rapide

2. **Détection automatique**
   - Le système teste WeasyPrint au démarrage
   - Bascule sur ReportLab si nécessaire
   - Message d'information affiché

### 📊 Comparaison des Rendus

| Fonctionnalité | WeasyPrint (avec GTK+) | ReportLab (actuel) |
|----------------|------------------------|-------------------|
| **Installation** | Complexe sur Windows | ✅ Simple |
| **Filigrane** | ✅ Parfait | ✅ Fonctionnel |
| **Images** | ✅ Base64 natif | ✅ Supporté |
| **Mise en page** | ✅ HTML/CSS complet | ✅ Programmé |
| **Performance** | Moyen | ✅ Rapide |
| **Symboles nationaux** | ✅ Parfait | ✅ Présent |

## 🚀 Test Immédiat

### Sans installer GTK+ (Solution actuelle)

1. **Démarrer le serveur**
   ```bash
   python manage.py runserver
   ```

2. **Tester l'export PDF**
   - Aller sur : http://127.0.0.1:8000/notes/bulletin-dynamique/
   - Sélectionner une classe et période
   - Cliquer sur "Exporter tous les bulletins de la classe"
   - **Le PDF sera généré avec ReportLab automatiquement**

## 📝 Code Modifié

### notes/views.py - Détection automatique

```python
# Détection du système et choix du générateur PDF
use_weasyprint = True
try:
    from weasyprint import HTML, CSS
    from weasyprint.text.fonts import FontConfiguration
except (ImportError, OSError) as e:
    # Sur Windows, WeasyPrint peut nécessiter GTK+
    # Utiliser ReportLab comme alternative
    use_weasyprint = False
```

## ✅ Résumé

- **Problème** : WeasyPrint nécessite GTK+ sur Windows
- **Solution implémentée** : Détection automatique et fallback sur ReportLab
- **Résultat** : L'export PDF fonctionne dans tous les cas
- **Option** : Installer GTK+ pour utiliser WeasyPrint (meilleur rendu CSS)

## 🎉 Conclusion

**L'export PDF fonctionne MAINTENANT** même sans GTK+ grâce au fallback automatique sur ReportLab !

Vous pouvez :
1. **Utiliser le système tel quel** (ReportLab automatique)
2. **Installer GTK+ plus tard** si vous voulez le rendu WeasyPrint

---

*Document créé le 13/11/2024*
