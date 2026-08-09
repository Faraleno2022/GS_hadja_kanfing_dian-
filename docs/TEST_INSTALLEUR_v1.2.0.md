# Procédure de test — MySchoolGN_Setup_v1.2.0.exe

Objectif : valider sur un **poste vierge** (sans Python, sans MSYS2, sans le dossier de
développement) que l'installeur fonctionne et que les nouveautés de cette version sont
opérationnelles.

Durée : environ 20 minutes.

---

## 0. Préparer le poste de test

| Point | À vérifier |
|---|---|
| Windows | 64 bits |
| MSYS2 | **Ne doit pas** être installé (`C:\msys64` absent) — c'est tout l'intérêt du test |
| Python | Aucune installation requise |
| Antivirus | Autoriser l'exécutable si une alerte apparaît |

Copier `Output\MySchoolGN_Setup_v1.2.0.exe` (78 Mo) sur le poste.

---

## 1. Installation

1. Double-cliquer sur `MySchoolGN_Setup_v1.2.0.exe`.
2. Accepter l'installation par défaut (`C:\Users\<vous>\AppData\Local\Programs\MySchoolGN`
   ou `Program Files` selon les droits — l'installeur ne demande pas les droits admin).
3. Cocher le raccourci bureau si proposé.

✅ **Attendu** : installation sans erreur, raccourci « MySchoolGN » sur le bureau et dans le
menu Démarrer.

---

## 2. Premier lancement

1. Lancer **MySchoolGN** (bureau ou menu Démarrer).
2. Patienter : le premier démarrage applique les migrations et collecte les fichiers
   statiques, c'est le plus long (1 à 3 minutes).
3. Le navigateur s'ouvre sur `http://127.0.0.1:8000`.

✅ **Attendu** : page de connexion affichée, aucune fenêtre d'erreur.

**Connexion** : `admin` / `admin1234` (compte créé automatiquement si la base est vide —
à changer immédiatement en production).

**Licence** : sans fichier de licence, l'application démarre en **essai 30 jours**.

⚠️ Si l'application ne démarre pas, ouvrir `myschool.log` dans le dossier d'installation :
la trace complète de l'erreur y est écrite.

---

## 3. Test décisif — PDF via WeasyPrint

C'est le point à valider en priorité : ces écrans utilisent WeasyPrint, qui a besoin des
DLL GTK embarquées dans `_internal/`. Sur ce poste sans MSYS2, un échec se verrait
immédiatement (erreur `cannot load library libgobject-2.0-0.dll` ou page 500).

Prérequis : au moins une classe avec des élèves et quelques notes. Si la base est vide,
créer une classe, deux élèves et saisir quelques notes (5 minutes) — sinon les écrans
répondent « aucune donnée » sans solliciter WeasyPrint, et le test ne prouve rien.

| # | Écran | Chemin |
|---|---|---|
| 3.1 | **Bulletins** | Notes → Générer Bulletins → choisir une classe → générer le PDF |
| 3.2 | **Tableau d'honneur** | Notes → Tableau d'Honneur → télécharger le PDF |
| 3.3 | **Certificats d'appréciation** | Notes → Maternelle → certificats (si classe maternelle) |
| 3.4 | **Livret scolaire** | Notes → Livrets Scolaires → un élève → PDF |

✅ **Attendu** : chaque PDF s'ouvre, avec la mise en page, les polices et le logo de l'école.

❌ **En cas d'échec** : noter le message exact et le contenu de `myschool.log` — cela
signifierait qu'une DLL manque dans `_internal/`.

---

## 4. Nouveautés de cette version

### 4.1 Motif obligatoire sur les remises

1. Paiements → un paiement **en attente** → « Appliquer remises ».
2. Cocher une tranche, choisir un pourcentage, **ne pas** choisir de motif → le bouton
   « Appliquer les remises » reste **désactivé** et un avertissement s'affiche.
3. Choisir un motif (ex. « Client fidèle ») → le bouton s'active ; valider.
4. Vérifier la fenêtre de confirmation : elle annonce le motif, la portée, la base, la
   remise et rappelle que **le montant encaissé ne change pas**.
5. Sur le détail du paiement, le motif apparaît sous la remise.

Cas particuliers à essayer :
- Motif **« Ne paie rien »** sans pourcentage → applique **100 %** sur les tranches cochées.
- Motif **« La moitié »** sans pourcentage → applique **50 %**.
- Un pourcentage explicitement choisi reste prioritaire sur celui du motif.

### 4.2 Menu Recouvrement

1. Le menu s'appelle désormais **« Recouvrement »** (plus « Dépenses ») et ouvre
   directement le hub.
2. Vérifier le tableau de bord général en haut (sorties du mois, versements, recettes,
   abonnements à surveiller) puis le récapitulatif par module.
3. Vérifier les **9 cards** : dépenses générales, cuisine, documents, versements,
   informatique, fournitures, logistique, bibliothèque, catégories.

### 4.3 Cuisine / Documents / Versements

Pour **chacun** des trois modules :

1. Ouvrir la card → tableau de bord.
2. « Nouvelle dépense » (ou « Nouveau versement ») : la date est **déjà remplie au jour du
   jour**. Saisir une désignation (ou un lieu de versement), un montant, une observation.
3. Vérifier que la ligne apparaît et que les totaux du mois se mettent à jour.
4. Tester les filtres (période du/au, recherche) puis les exports **Excel** et **PDF** :
   ils doivent reprendre exactement les lignes filtrées, avec une ligne TOTAL.
5. Modifier puis supprimer la ligne de test.

Contrôles négatifs attendus :
- Montant à 0 → refusé (« Le montant doit être supérieur à zéro »).
- Date dans le futur → refusée.

### 4.4 Informatique (abonnements)

1. Recouvrement → card **Informatique** → « Nouvel abonnement ».
2. Taper un **matricule** dans le champ de recherche : la liste d'élèves se réduit en
   direct ; sélectionner l'élève → sa fiche s'affiche (matricule, classe, dernier
   abonnement).
3. Saisir le montant, utiliser un bouton de durée rapide (1 mois / 3 mois / 1 an) pour
   remplir la date de fin, enregistrer.
4. Sur le tableau de bord : vérifier les compteurs (actifs / expirés / sous 7 jours) et la
   recherche par matricule.
5. Cliquer sur l'icône **carte** : un PDF au format carte bancaire s'ouvre, avec le nom,
   le matricule, la classe, la période, le montant et le statut.
6. Tester les exports **Excel** et **PDF** de la liste.
7. Pour vérifier les alertes : modifier un abonnement en mettant une date de fin passée →
   il doit basculer en **Expiré** (badge rouge) et apparaître dans l'encadré d'alerte, et
   le bandeau d'avertissement doit apparaître sur le hub Recouvrement.

---

## 5. Contrôle de non-régression rapide

| Écran | Attendu |
|---|---|
| Élèves → liste | s'affiche, photos visibles |
| Paiements → reçu PDF | se génère (ReportLab, indépendant de WeasyPrint) |
| Fiche inscription PDF | se génère |
| Dépenses générales | accessible via la card, bouton « Recouvrement » pour revenir |
| Bibliothèque | menu toujours présent et fonctionnel |

---

## 6. Désinstallation

1. Menu Démarrer → « Désinstaller MySchoolGN » (ou Panneau de configuration).
2. ✅ **Attendu** : la base de données, les médias et la licence sont **conservés** (voir
   `desinstaller.bat`) ; seule l'application est retirée.

---

## Récapitulatif à me remonter en cas de problème

- L'étape exacte qui échoue (numéro ci-dessus).
- Le message d'erreur affiché à l'écran.
- Les 50 dernières lignes de `myschool.log` (dans le dossier d'installation).
