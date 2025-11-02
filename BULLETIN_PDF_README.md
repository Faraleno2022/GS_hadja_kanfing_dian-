# Bouton d'Enregistrement PDF pour les Bulletins

## 📋 Résumé des Modifications

J'ai ajouté un bouton pour télécharger les bulletins dynamiques en PDF sur la page `notes/bulletins/`.

## 🎯 Fonctionnalités Ajoutées

### 1. Bouton d'Ouverture PDF
- **Emplacement** : Au-dessus du bulletin, à côté du bouton "Imprimer"
- **Icône** : 📄 avec texte "Ouvrir PDF"
- **Style** : Bouton vert (Bootstrap success)
- **Action** : Génère et ouvre automatiquement le bulletin au format PDF dans un nouvel onglet
- **Fonctionnalité** : Le PDF s'affiche directement dans le navigateur, permettant de le consulter, télécharger ou imprimer

### 2. Bouton d'Impression
- **Emplacement** : Au-dessus du bulletin
- **Icône** : 🖨️ avec texte "Imprimer"
- **Style** : Bouton bleu (Bootstrap primary)
- **Action** : Ouvre la boîte de dialogue d'impression du navigateur

## 📁 Fichiers Modifiés

### 1. `notes/views.py`
- **Nouvelle vue** : `bulletin_dynamique_pdf(request)`
  - Génère le bulletin en PDF avec WeasyPrint
  - Récupère les mêmes données que `bulletin_dynamique`
  - Calcule les moyennes et mentions
  - Retourne un fichier PDF téléchargeable
  - Gestion d'erreur si WeasyPrint n'est pas installé

### 2. `notes/urls.py`
- **Nouvelle URL** : `path('bulletins/pdf/', views.bulletin_dynamique_pdf, name='bulletin_dynamique_pdf')`
- Accessible via : `/notes/bulletins/pdf/?classe_id=X&eleve_id=Y&periode=Z&system_type=W`

### 3. `templates/notes/bulletin_dynamique.html`
- **Ajout** : Section de boutons d'action (ligne 518-530)
- Les boutons apparaissent uniquement quand un bulletin est affiché
- Les boutons sont masqués lors de l'impression (classe `no-print`)

## 🔧 Installation Requise

Pour que la génération PDF fonctionne, WeasyPrint doit être installé :

```bash
pip install weasyprint
```

### Dépendances de WeasyPrint
WeasyPrint nécessite également :
- **Windows** : GTK+ (généralement installé automatiquement)
- **Linux** : `libpango-1.0-0 libpangocairo-1.0-0`
- **macOS** : `brew install cairo pango gdk-pixbuf libffi`

## 📖 Utilisation

### Pour l'Utilisateur

1. **Accéder à la page des bulletins** : `/notes/bulletins/`
2. **Sélectionner** :
   - Une classe
   - Un système (mensuel/trimestre/semestre/annuel)
   - Une période
   - Un élève
3. **Le bulletin s'affiche** avec deux boutons :
   - **Imprimer** : Pour imprimer directement ou enregistrer en PDF via le navigateur
   - **Ouvrir PDF** : Pour ouvrir automatiquement le bulletin en PDF dans un nouvel onglet
     - Le PDF s'affiche dans le navigateur
     - Vous pouvez ensuite le télécharger, l'imprimer ou simplement le consulter

### Exemple d'URL

```
/notes/bulletins/?classe_id=5&system_type=trimestre&periode=TRIMESTRE_1&eleve_id=801
```

Le bouton PDF génère l'URL :
```
/notes/bulletins/pdf/?classe_id=5&system_type=trimestre&periode=TRIMESTRE_1&eleve_id=801
```

## 🎨 Caractéristiques du PDF

- **Format** : A4
- **Contenu** :
  - En-tête avec logo de l'école et photo de l'élève
  - Informations de l'élève (nom, prénom, matricule, classe)
  - Tableau des notes par matière
  - Moyenne générale
  - Rang dans la classe
  - Mention obtenue
  - Appréciation du conseil de classe
  - Signatures (Professeur, Chef d'établissement, Parent)
- **Nom du fichier** : `bulletin_NOM_PRENOM_PERIODE.pdf`

## ⚠️ Gestion d'Erreurs

### Si WeasyPrint n'est pas installé
- Un message informatif s'affiche
- L'utilisateur est invité à utiliser le bouton "Imprimer" à la place
- Instructions d'installation fournies

### Si une erreur survient
- Message d'erreur détaillé affiché
- Lien de retour vers le bulletin

## 🔄 Alternative Sans WeasyPrint

Si WeasyPrint ne peut pas être installé, les utilisateurs peuvent :

1. Cliquer sur le bouton **"Imprimer"**
2. Dans la boîte de dialogue d'impression :
   - Sélectionner **"Enregistrer au format PDF"** comme imprimante
   - Cliquer sur **"Enregistrer"**
3. Le bulletin sera enregistré en PDF via le navigateur

## ✅ Tests

Les fonctionnalités ont été testées et validées :
- ✅ Boutons affichés correctement
- ✅ Boutons masqués lors de l'impression
- ✅ URL correctement générée avec tous les paramètres
- ✅ Gestion d'erreur fonctionnelle
- ✅ PDF s'ouvre automatiquement dans un nouvel onglet
- ✅ Possibilité de télécharger le PDF depuis le navigateur

## 📝 Notes Techniques

### Calcul des Moyennes
La vue PDF utilise la même logique que la vue HTML :
- **Système mensuel** : Moyenne des devoirs uniquement
- **Système trimestre/semestre** : `(Moyenne Continue + Composition × 2) / 3`
- **Pondération** : Par coefficient de chaque matière

### Mentions
- **Très Bien** : ≥ 16/20
- **Bien** : ≥ 14/20
- **Assez Bien** : ≥ 12/20
- **Passable** : ≥ 10/20
- **Insuffisant** : < 10/20

## 🚀 Améliorations Futures Possibles

1. **Téléchargement groupé** : Générer tous les bulletins d'une classe en un seul PDF
2. **Personnalisation** : Permettre de choisir le format (A4, Letter, etc.)
3. **Envoi par email** : Envoyer automatiquement les bulletins aux parents
4. **Historique** : Conserver les bulletins générés pour consultation ultérieure
5. **Signature numérique** : Ajouter des signatures numériques au PDF

## 📞 Support

En cas de problème :
1. Vérifier que WeasyPrint est installé : `pip show weasyprint`
2. Vérifier les logs Django pour les erreurs
3. Utiliser le bouton "Imprimer" comme alternative
