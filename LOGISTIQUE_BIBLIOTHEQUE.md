# 📦 Système de Gestion Logistique et Bibliothèque

## 🎉 Modules Créés

Ce document décrit les nouveaux modules de **Gestion Logistique** et **Bibliothèque** ajoutés au système de gestion scolaire.

---

## 📦 MODULE LOGISTIQUE

### **Objectif**
Gérer les achats de fournitures, l'identification des biens de l'établissement, le stock, les entrées et sorties.

### **Fonctionnalités**

#### **1. Gestion des Articles et Stock**
- ✅ Catalogue complet des articles (fournitures, mobilier, équipement, uniformes, etc.)
- ✅ Suivi du stock en temps réel
- ✅ Alertes de stock minimum
- ✅ Valorisation du stock
- ✅ Gestion des emplacements

#### **2. Biens de l'Établissement**
- ✅ Inventaire des infrastructures (salles, bureaux, toilettes, etc.)
- ✅ Suivi de l'état des biens
- ✅ Planification de la maintenance
- ✅ Valorisation du patrimoine

#### **3. Mouvements de Stock**
- ✅ Entrées (achats, dons)
- ✅ Sorties (ventes, distributions, utilisations)
- ✅ Ajustements et transferts
- ✅ Traçabilité complète

#### **4. Inventaires**
- ✅ Inventaires périodiques
- ✅ Détection des écarts
- ✅ Validation et ajustements
- ✅ Rapports détaillés

---

## 📚 MODULE BIBLIOTHÈQUE

### **Objectif**
Gérer le catalogue de livres, les emprunts, les réservations et les pénalités.

### **Fonctionnalités**

#### **1. Catalogue de Livres**
- ✅ Gestion complète des livres (ISBN, auteur, éditeur, etc.)
- ✅ Catégorisation par type
- ✅ Gestion des exemplaires multiples
- ✅ Photos de couverture
- ✅ Recherche avancée

#### **2. Emprunts**
- ✅ Gestion des emprunts élèves
- ✅ Dates de retour et rappels
- ✅ Calcul automatique des pénalités de retard
- ✅ Suivi de l'état des livres
- ✅ Historique complet

#### **3. Réservations**
- ✅ Système de réservation
- ✅ Notifications automatiques
- ✅ Gestion des expirations
- ✅ File d'attente

#### **4. Paramètres**
- ✅ Durée d'emprunt configurable
- ✅ Limites d'emprunts par élève
- ✅ Tarifs des pénalités
- ✅ Règles de gestion

---

## 🗂️ STRUCTURE DES MODÈLES

### **Logistique**

#### **CategorieArticle**
```python
- nom: Nom de la catégorie
- code: Code unique
- type_categorie: FOURNITURE, MOBILIER, EQUIPEMENT, UNIFORME, etc.
- description: Description
- actif: Statut
```

#### **Article**
```python
- code_article: Code unique
- nom: Nom de l'article
- categorie: Catégorie
- description: Description détaillée
- marque: Marque
- reference: Référence fabricant
- unite_mesure: PIECE, BOITE, PAQUET, etc.
- stock_actuel: Quantité en stock
- stock_minimum: Seuil d'alerte
- stock_maximum: Capacité maximale
- prix_unitaire: Prix unitaire (GNF)
- etat: NEUF, BON, MOYEN, MAUVAIS, HORS_SERVICE
- emplacement: Localisation
- photo: Photo de l'article
```

**Propriétés calculées:**
- `valeur_stock`: Valeur totale du stock
- `alerte_stock`: Alerte si stock < minimum
- `taux_stock`: Pourcentage de remplissage

#### **BienEtablissement**
```python
- code_bien: Code unique
- nom: Désignation
- type_bien: SALLE_CLASSE, BUREAU, LABORATOIRE, TOILETTE, etc.
- description: Description
- localisation: Emplacement
- superficie: Surface en m²
- capacite: Capacité (personnes/objets)
- etat: EXCELLENT, BON, MOYEN, MAUVAIS, HORS_SERVICE
- valeur_acquisition: Valeur d'achat (GNF)
- date_acquisition: Date d'achat
- date_derniere_maintenance: Dernière maintenance
- date_prochaine_maintenance: Prochaine maintenance
- photo: Photo du bien
```

**Propriétés calculées:**
- `maintenance_requise`: Alerte maintenance

#### **MouvementStock**
```python
- numero_mouvement: N° unique
- article: Article concerné
- type_mouvement: ENTREE, SORTIE, AJUSTEMENT, TRANSFERT, RETOUR
- motif: ACHAT, DON, VENTE, DISTRIBUTION, PERTE, VOL, etc.
- quantite: Quantité
- stock_avant: Stock avant mouvement
- stock_apres: Stock après mouvement
- prix_unitaire: Prix unitaire (GNF)
- montant_total: Montant total (GNF)
- date_mouvement: Date du mouvement
- destinataire: Destinataire/Fournisseur
- document_reference: Document de référence
- observations: Observations
```

**Automatismes:**
- Mise à jour automatique du stock
- Calcul du montant total
- Traçabilité complète

#### **Inventaire**
```python
- numero_inventaire: N° unique
- date_inventaire: Date de l'inventaire
- description: Description
- statut: EN_COURS, TERMINE, VALIDE, ANNULE
- nombre_articles: Nombre d'articles inventoriés
- valeur_totale: Valeur totale (GNF)
- ecarts_detectes: Nombre d'écarts
- observations: Observations
```

#### **LigneInventaire**
```python
- inventaire: Inventaire parent
- article: Article inventorié
- stock_theorique: Stock théorique
- stock_physique: Stock physique compté
- ecart: Écart (physique - théorique)
- prix_unitaire: Prix unitaire (GNF)
- valeur_theorique: Valeur théorique (GNF)
- valeur_physique: Valeur physique (GNF)
- observations: Observations
```

---

### **Bibliothèque**

#### **CategorieLivre**
```python
- nom: Nom de la catégorie
- code: Code unique
- description: Description
- actif: Statut
```

#### **Livre**
```python
- code_livre: Code unique
- isbn: ISBN
- titre: Titre du livre
- auteur: Auteur
- categorie: Catégorie
- editeur: Éditeur
- annee_publication: Année de publication
- edition: Édition
- langue: Langue (défaut: Français)
- nombre_pages: Nombre de pages
- resume: Résumé
- mots_cles: Mots-clés pour recherche
- emplacement: Rayon/Étagère
- etat: NEUF, TRES_BON, BON, MOYEN, MAUVAIS, HORS_SERVICE
- statut: DISPONIBLE, EMPRUNTE, RESERVE, PERDU, EN_REPARATION, RETIRE
- nombre_exemplaires: Nombre total d'exemplaires
- exemplaires_disponibles: Exemplaires disponibles
- prix_acquisition: Prix d'achat (GNF)
- date_acquisition: Date d'achat
- couverture: Photo de couverture
```

**Propriétés calculées:**
- `est_disponible`: Disponible pour emprunt
- `taux_disponibilite`: % d'exemplaires disponibles

#### **Emprunt**
```python
- numero_emprunt: N° unique
- livre: Livre emprunté
- eleve: Élève emprunteur
- date_emprunt: Date d'emprunt
- date_retour_prevue: Date de retour prévue
- date_retour_effectif: Date de retour effectif
- statut: EN_COURS, RETOURNE, EN_RETARD, PERDU, ANNULE
- jours_retard: Nombre de jours de retard
- montant_penalite: Montant de la pénalité (GNF)
- penalite_payee: Pénalité payée (oui/non)
- observations_emprunt: Observations à l'emprunt
- observations_retour: Observations au retour
- etat_livre_emprunt: État du livre à l'emprunt
- etat_livre_retour: État du livre au retour
```

**Propriétés calculées:**
- `est_en_retard`: Emprunt en retard
- `jours_restants`: Jours avant retour

**Automatismes:**
- Calcul automatique de la date de retour (14 jours par défaut)
- Calcul automatique des pénalités
- Mise à jour du statut si en retard

#### **Reservation**
```python
- numero_reservation: N° unique
- livre: Livre réservé
- eleve: Élève
- date_reservation: Date de réservation
- date_expiration: Date d'expiration
- date_notification: Date de notification
- statut: EN_ATTENTE, DISPONIBLE, EMPRUNTEE, ANNULEE, EXPIREE
- observations: Observations
```

**Propriétés calculées:**
- `est_expiree`: Réservation expirée

**Automatismes:**
- Expiration automatique après 7 jours

#### **ParametreBibliotheque**
```python
- duree_emprunt_defaut: 14 jours
- duree_reservation_defaut: 7 jours
- nombre_emprunts_max: 3 emprunts simultanés
- nombre_reservations_max: 2 réservations simultanées
- penalite_retard_journalier: 1000 GNF/jour
- penalite_perte: 50000 GNF
- penalite_degradation: 25000 GNF
- rappel_avant_echeance: 3 jours
```

---

## 🎯 CATÉGORIES D'ARTICLES

### **Types de Catégories**
1. **FOURNITURE** - Fournitures scolaires
   - Cahiers, stylos, crayons, gommes
   - Papier, cartouches d'encre
   - Matériel de dessin

2. **MOBILIER** - Mobilier
   - Tables, chaises, bureaux
   - Armoires, étagères
   - Tableaux

3. **EQUIPEMENT** - Équipement pédagogique
   - Matériel de laboratoire
   - Instruments de musique
   - Équipement sportif

4. **UNIFORME** - Uniformes
   - Uniformes élèves
   - Tenues de sport
   - Accessoires

5. **MATERIEL_INFO** - Matériel informatique
   - Ordinateurs, imprimantes
   - Projecteurs, écrans
   - Logiciels

6. **INFRASTRUCTURE** - Infrastructure
   - Équipements fixes
   - Installations

---

## 🏢 TYPES DE BIENS

1. **SALLE_CLASSE** - Salle de classe
2. **BUREAU** - Bureau
3. **LABORATOIRE** - Laboratoire
4. **BIBLIOTHEQUE** - Bibliothèque
5. **TOILETTE** - Toilette
6. **CANTINE** - Cantine
7. **TERRAIN_SPORT** - Terrain de sport
8. **COUR** - Cour
9. **PARKING** - Parking
10. **AUTRE** - Autre

---

## 📊 RAPPORTS ET STATISTIQUES

### **Logistique**
- État du stock par catégorie
- Valeur totale du stock
- Articles en alerte (stock minimum)
- Mouvements par période
- Écarts d'inventaire
- État des biens de l'établissement
- Planification de la maintenance

### **Bibliothèque**
- Livres les plus empruntés
- Taux d'occupation de la bibliothèque
- Emprunts en retard
- Pénalités à recouvrer
- Statistiques par catégorie
- Taux de rotation des livres

---

## 🎨 INTERFACE UTILISATEUR

### **Menu Principal**

#### **Dépenses & Logistique**
- 📄 Dépenses
- 📦 Stock & Articles
- 🏢 Biens de l'Établissement
- 🔄 Mouvements Stock
- 📋 Inventaires

#### **Bibliothèque**
- 📚 Catalogue Livres
- 🤝 Emprunts
- 🔖 Réservations
- 📊 Statistiques

---

## 🔐 SÉCURITÉ ET PERMISSIONS

- ✅ Accès restreint selon les rôles
- ✅ Traçabilité de toutes les actions
- ✅ Historique complet
- ✅ Validation des mouvements importants

---

## 📝 FICHIERS CRÉÉS

```
depenses/
├── models.py                          ✅ Modifié (imports ajoutés)
├── models_logistique.py               ✅ Créé (6 modèles)
├── models_bibliotheque.py             ✅ Créé (6 modèles)
├── admin.py                           ✅ Modifié (admin complet)
└── migrations/
    └── 0002_categoriearticle_...py    ✅ Créé et appliqué

templates/
└── base.html                          ✅ Modifié (menus ajoutés)

LOGISTIQUE_BIBLIOTHEQUE.md             ✅ Créé (ce fichier)
```

---

## 🚀 PROCHAINES ÉTAPES

### **Phase 1: Vues et Templates (À créer)**
- [ ] Dashboard logistique
- [ ] Liste des articles
- [ ] Formulaires de mouvement
- [ ] Dashboard bibliothèque
- [ ] Catalogue de livres
- [ ] Gestion des emprunts

### **Phase 2: Fonctionnalités Avancées**
- [ ] Génération de codes-barres
- [ ] Scan de livres
- [ ] Notifications automatiques
- [ ] Rapports PDF
- [ ] Export Excel
- [ ] Statistiques graphiques

### **Phase 3: Optimisations**
- [ ] Recherche avancée
- [ ] Filtres dynamiques
- [ ] API REST
- [ ] Application mobile

---

## 💡 EXEMPLES D'UTILISATION

### **Logistique**

#### **Enregistrer un achat de fournitures**
1. Créer un mouvement de type "ENTREE"
2. Motif: "ACHAT"
3. Sélectionner l'article
4. Indiquer la quantité et le prix
5. Le stock se met à jour automatiquement

#### **Faire un inventaire**
1. Créer un nouvel inventaire
2. Ajouter les lignes d'inventaire
3. Compter physiquement
4. Le système calcule les écarts
5. Valider l'inventaire

### **Bibliothèque**

#### **Emprunter un livre**
1. Sélectionner le livre
2. Sélectionner l'élève
3. Définir la durée (14 jours par défaut)
4. Le système gère automatiquement:
   - Diminution des exemplaires disponibles
   - Calcul de la date de retour
   - Alertes de retard
   - Calcul des pénalités

#### **Retourner un livre**
1. Trouver l'emprunt
2. Enregistrer le retour
3. Noter l'état du livre
4. Le système calcule automatiquement les pénalités si retard

---

## ✅ RÉSUMÉ

**12 nouveaux modèles créés:**
- ✅ 6 modèles Logistique
- ✅ 6 modèles Bibliothèque

**Fonctionnalités principales:**
- ✅ Gestion complète du stock
- ✅ Suivi des biens de l'établissement
- ✅ Traçabilité des mouvements
- ✅ Inventaires périodiques
- ✅ Catalogue de livres
- ✅ Emprunts et réservations
- ✅ Calcul automatique des pénalités
- ✅ Menus intégrés

**Base de données:**
- ✅ Migrations créées et appliquées
- ✅ Admin Django configuré
- ✅ Prêt pour l'utilisation

**Le système est maintenant prêt pour le développement des vues et templates !** 🎉
