# Corrections de l’audit du 8 septembre 2026

Les 22 anomalies reproduites dans l’audit de la révision `a3d5506` sont traitées sur la branche `codex/corrections-audit-projet`.

| Constats | Correction |
|---|---|
| B01 | Rejet limité au superadministrateur et aux demandes encore en attente ; suppression transactionnelle. Liste et validation des demandes également réservées au superadministrateur. |
| B02–B03 | Contrôle de l’objet existant et de ses relations avant synchronisation. Filtrage des responsables, dépenses et rapports par école. Rattachement conservé dans SyncOwnership pour les objets sans lien direct d’école. |
| B04 | Recalcul métier des échéanciers et remises après écriture ou suppression synchronisée ; recalcul des anciens et nouveaux élèves/années concernés. |
| B05 | Snapshot paginé avec curseur signé lié à l’école, avancement local persistant et reprise sans sauter un lot en échec. Compatibilité des anciens clients conservée sans le plafond de 5 000 lignes. |
| B06–B07 | Les administrateurs d’école restent limités à leur établissement dans les cartes, tickets et abonnements. Pointage cantine étranger refusé. |
| B08 | Recherche documentaire limitée à l’école ; suggestions populaires rattachées à leur école. Les anciennes suggestions sans rattachement ne sont plus diffusées aux écoles. |
| B09, B20 | Aperçus, génération, statistiques et modifications des rappels filtrés ; utilisation des permissions réellement disponibles pour les comptables. |
| B10 | Suppression des identifiants de classes codés en dur ; correspondance par école et invalidation de l’ancien cache des rangs. |
| B11–B14 | Rapports journaliers et de période limités aux dates demandées, aux paiements validés et aux dépenses de l’école. Ventilation des encaissements selon les échéanciers de l’année des reçus. |
| B15 | Zéro refusé par le formulaire de dépense ; TVA et TTC recalculés même lorsque le modèle reçoit zéro directement. |
| B16–B18 | Imports manquants réparés ; saisie des notes limitée aux élèves sélectionnables ; liens PDF/Excel du bulletin réparés et classe du bulletin limitée à l’école de l’élève. |
| B19 | Sept pages restaurées : tableau de bord abonnements, liste/création/présences cantine, élèves en retard, statistiques de rappels, rejet de compte. |
| B21 | Objets JSON, opérations, relations et limites de lots validés ; erreurs de saisie renvoyées sans erreur 500. |
| B22 | Configuration de production basée sur le module settings existant et chemins dérivés du projet. |

Les changements web en attente de diffusion sont désormais inclus dans le téléchargement incrémental des postes. Les données historiques du journal ne sont pas utilisées pour contourner le périmètre courant de l’objet.

Maintenance : Django passe de 5.2.6 à 5.2.17 ([annonce officielle de sécurité](https://www.djangoproject.com/weblog/2026/aug/04/security-releases/)). Axes reste à la version déclarée 8.2.0. Le test de couleurs obsolète cible les champs concernés, les deux anciens modèles HTML invalides compilent, et les workflows GitHub exécutent les tests avant une future compilation Desktop.

## Vérification

Les régressions de l’audit sont dans `ecole_moderne/test_audit_regressions.py`. Elles couvrent les refus entre écoles et les accès autorisés, les calculs, les pages et exports, ainsi que la pagination et la reprise après échec.

Commandes depuis la racine :

```bash
python scripts/run_project_tests.py --schema
python scripts/run_project_tests.py
```

Ces commandes utilisent SQLite en mémoire, des fichiers temporaires, une boîte mail en mémoire et des connexions réseau bloquées. Elles ne modifient pas la base métier. La commande `--schema` applique les migrations sur une base neuve ; la suite métier crée ses tables sans rejouer les migrations à chaque lancement.

Résultat final : **451 tests réussis** (413 tests existants et 38 régressions complémentaires), aucune erreur ni aucun échec. Vérification de 508 fichiers Python sans erreur de syntaxe, compilation de 239 modèles HTML, dépendances cohérentes (`pip check`) et migrations appliquées à une base neuve. La suite finale a utilisé Django 5.2.17 et Axes 8.2.0.

Les workflows ont été ajoutés au dépôt mais n'ont pas encore été exécutés sur GitHub.

## Mise en service

Après fusion et publication des corrections, mettre à jour le serveur avec son environnement Python :

```bash
cd /home/myschoolgn/GS_hadja_kanfing_dian-
source venv311/bin/activate
git pull --ff-only origin main
python -m pip install -r requirements.txt
python manage.py migrate --noinput
python manage.py collectstatic --noinput
```

Recharger ensuite l’application depuis l’onglet Web de PythonAnywhere. Les migrations `chatbot.0002_recherchepopulaire_ecole` et `synchronisation.0002_synccheckpoint_syncownership` sont nécessaires avant de servir les nouvelles vues.

Les postes doivent recevoir un installateur construit avec ces corrections pour bénéficier de la reprise persistante. Le workflow Desktop exécute maintenant les contrôles de schéma et les tests avant de construire et publier un installateur. Aucun nouvel installateur ni déploiement serveur n’est réalisé par la seule modification du code.

Aucune donnée de production n’a été lue ou modifiée pendant ces corrections. La configuration effective du serveur, son moteur MySQL et les échanges réels entre plusieurs postes restent à vérifier lors de la mise en service.
