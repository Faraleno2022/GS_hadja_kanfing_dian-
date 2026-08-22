# Sauvegarde des données — règle 3-2-1 (MySchoolGN Desktop)

But : **qu'une panne de machine, un vol, un formatage ou une réinstallation ne
fasse jamais perdre les données de l'école.**

---

## 1. Le principe en une phrase

| Chiffre | Ce que ça veut dire | Où c'est appliqué dans MySchoolGN |
|---|---|---|
| **3** copies | Les données existent en trois exemplaires | L'installation elle-même + le dossier `backups\archives` du poste + chaque destination externe |
| **2** supports | Deux types de support différents | Un **dossier cloud synchronisé** (OneDrive / Google Drive / Dropbox) **et** une **clé USB ou un disque externe** laissé sur place |
| **1** hors-site | Une copie ailleurs que dans l'école | Le dossier cloud, qui part chez le fournisseur dès que la connexion revient |

Une seule des trois copies qui survit suffit à tout récupérer.

---

## 2. Où ça se règle

Dans l'application : menu utilisateur (en haut à droite) → **Sauvegarde des données**.
Réservé aux administrateurs, visible uniquement dans l'application installée.

La page montre :

* l'état des trois copies (vert = protégé, rouge = à configurer) ;
* les destinations configurées, avec la date de la dernière réussite ;
* les supports détectés sur le poste (cloud installé, clés USB branchées) ;
* la liste des sauvegardes disponibles, pour restaurer ;
* l'historique des passages.

### Première configuration (5 minutes, une seule fois par poste)

1. Ouvrir **Sauvegarde des données**.
2. Dans « Supports détectés », cliquer sur **Utiliser** en face du dossier cloud
   (OneDrive / Google Drive / Dropbox).
3. Brancher la clé USB, recharger la page, cliquer sur **Utiliser** en face de la clé.
4. Cliquer sur **Sauvegarder maintenant** pour vérifier que tout passe.

Si un support n'apparaît pas (partage réseau, chemin inhabituel), utiliser
« Ajouter un dossier manuellement » et coller le chemin copié depuis la barre
d'adresse de l'explorateur Windows.

---

## 3. Ce qui se passe ensuite, tout seul

* Une sauvegarde automatique part **toutes les 6 heures** par défaut
  (réglable de 1 h à 7 jours), pendant que l'application tourne.
* Si l'échéance a été manquée (poste éteint), la sauvegarde se fait au démarrage
  suivant, 90 secondes après le lancement.
* Un support absent (clé débranchée, cloud non monté) **n'est pas une erreur** :
  la destination est simplement réessayée au passage suivant.
* Si Windows donne une **autre lettre** à la clé USB (E: → F:), le support est
  retrouvé automatiquement par son nom de volume.
* Une destination sans succès depuis **7 jours** s'affiche en rouge sur la page.

### Contenu d'une sauvegarde, sur chaque destination

```
<destination>\MySchoolGN_Sauvegardes\<école>\
    archives\    MySchoolGN_<école>_20260812_1430.zip   ← base de données + manifeste
    medias\                                             ← photos élèves, logos (miroir)
    DERNIERE_SAUVEGARDE.txt                             ← état lisible sans ouvrir l'app
    COMMENT_RESTAURER.txt                               ← marche à suivre en cas de panne
```

La base (quelques Mo) est archivée entièrement à chaque passage. Les photos, plus
volumineuses, sont copiées **en miroir** : seuls les fichiers nouveaux ou modifiés
transitent — indispensable pour une clé USB ou un dossier cloud.

Chaque archive contient un `manifest.json` avec la date, le nom de l'école,
l'empreinte SHA-256 de la base et le nombre d'élèves/paiements : de quoi vérifier
d'un coup d'œil qu'on restaure la bonne sauvegarde.

### Rotation (ce qui est conservé)

| Réglage | Défaut | Rôle |
|---|---|---|
| Dernières gardées | 8 | Les 8 dernières archives, quelle que soit leur date — si une donnée est abîmée à 10 h et sauvegardée à 12 h, la version de 6 h existe encore |
| Quotidiennes | 7 | Une par jour sur la dernière semaine |
| Hebdomadaires | 4 | Une par semaine sur le dernier mois |
| Mensuelles | 12 | Une par mois sur l'année |

Le reste est purgé automatiquement, sur le poste comme sur chaque destination.

---

## 4. Restaurer — machine en panne ou réinstallation

1. Installer MySchoolGN sur la machine (neuve ou réinstallée), avec l'installateur habituel.
2. Lancer l'application, se connecter (`admin` / `admin1234` sur une installation neuve).
3. Brancher la clé USB, **ou** attendre que le dossier cloud soit synchronisé sur ce poste.
4. Menu utilisateur → **Sauvegarde des données** → section « Restaurer des données ».
   Les sauvegardes trouvées sur les supports branchés apparaissent, la plus récente en haut.
5. Cliquer **Restaurer**, confirmer.
6. Fermer MySchoolGN, puis le relancer : les données sont remises en place au démarrage.

Détails importants :

* La restauration ne touche **jamais** la base pendant que l'application tourne :
  elle est appliquée au démarrage suivant, avant l'ouverture de la base.
* La base présente avant la restauration est **conservée** dans
  `backups\db_avant_restauration_<date>.sqlite3` — rien n'est effacé.
* Une archive illisible ou incomplète est refusée : les données en place restent intactes.
* Les photos et logos sont restaurés en même temps que la base, depuis le dossier `medias`.
* La **licence est liée à la machine** : après un changement d'ordinateur, il faut
  demander une nouvelle licence à GS Hadja Kanfing Dian. Les données, elles, sont intactes.
* La configuration de synchronisation (`sync_config.json`) est archivée pour
  référence mais **n'est pas réappliquée** : l'identifiant d'appareil doit rester
  unique par poste.

Le bouton **Télécharger** permet aussi de récupérer une archive pour la mettre à
l'abri autrement (mail, second disque, remise à un technicien).

---

## 5. Fichiers et emplacements (pour le technicien)

| Élément | Chemin | Remarque |
|---|---|---|
| Réglages du poste | `<installation>\backup_config.json` | Propre à chaque machine, jamais dans le build ; préservé lors des mises à jour |
| Archives locales | `<installation>\backups\archives\` | 3ᵉ copie, sur le disque du poste |
| Historique | `<installation>\backups\journal_sauvegarde.json` | Les 100 derniers passages |
| Restauration demandée | `<installation>\.restauration_en_attente.json` | Consommé au démarrage suivant |
| Journal de restauration | `<installation>\logs\restauration.log` | Une ligne par restauration |
| Moteur | `ecole_moderne/sauvegarde.py` | Bibliothèque standard uniquement |
| Interface | `ecole_moderne/sauvegarde_views.py`, `templates/desktop/sauvegarde.html` | Réservée au mode desktop + administrateur |

Points de contrôle rapides sur un poste :

```bash
type "C:\Program Files\MySchoolGN\backup_config.json"
```

```bash
type "C:\Program Files\MySchoolGN\backups\journal_sauvegarde.json"
```

---

## 6. Limites connues

* Les sauvegardes automatiques ne partent que **pendant que l'application tourne**.
  Sur un poste utilisé tous les jours, cela suffit ; sinon, ouvrir MySchoolGN une
  fois par jour, ou cliquer sur « Sauvegarder maintenant » avant de fermer.
* Le dossier cloud dépend du client (OneDrive/Drive/Dropbox) pour envoyer les
  fichiers : si l'utilisateur est déconnecté de son compte cloud, la copie reste
  locale jusqu'à la reconnexion.
* Un antivirus qui verrouille la clé USB peut faire échouer un passage : le
  message exact apparaît dans l'historique de la page.
