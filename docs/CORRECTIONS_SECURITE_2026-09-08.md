Corrections de sécurité — 8 septembre 2026

Les six problèmes confirmés par la campagne de tests sont corrigés dans la branche `codex/corrections-audit-projet`. Les corrections fonctionnelles préparées avant cette campagne sont conservées.

**Validation finale : 497 tests exécutés et réussis, aucun échec, aucune erreur, aucun test ignoré.** Exécution sur Python 3.13 et SQLite en mémoire, en 79,734 secondes. Les paiements, remises, suppressions, transferts, rapports, exports PDF/Excel, imports et accès enseignants sont inclus. Aucun paiement réel n'a été modifié.

- **Permissions :** l'API accepte uniquement les huit permissions métier du formulaire. Elle ne peut plus modifier l'identité, l'école, la validation ou le statut de compte principal. La sauvegarde est limitée au champ autorisé.
- **Administrateur sans école :** les exports et mises à jour groupées utilisent un périmètre vide. Deux comptes sans école ne sont plus considérés comme appartenant à une même école autorisée.
- **Synchronisation :** le statut d'approbation d'une école est contrôlé par le serveur. Une mise à jour provenant d'un PC ignore ce champ et conserve les autres modifications autorisées, même si le PC possède un ancien statut. Les mises à jour authentiques reçues du serveur peuvent toujours appliquer une validation.
- **CSRF :** l'enregistrement d'un poste par session exige désormais la protection CSRF. L'authentification explicite par jeton d'administration conserve son fonctionnement sans cookie. Un jeton erroné ne désactive pas CSRF.
- **Sessions :** les contrôles sont placés après l'authentification, la vérification des liens enseignants et le contrôle du profil. L'expiration après 30 minutes d'inactivité et la revérification téléphonique s'appliquent. Les liens enseignants conservent leurs propres règles d'accès et d'expiration.
- **Révocation du profil :** les indicateurs actif et validé sont relus à chaque requête authentifiée. Une révocation ferme la session existante ; un profil désactivé ne peut pas se reconnecter. Les comptes Django désactivés restent refusés.

Le parcours téléphonique réactivé refuse aussi les redirections vers des sites non autorisés. Les liens internes légitimes restent utilisables.

45 tests de sécurité permanents sont ajoutés dans `ecole_moderne/test_vulnerabilites.py`, ainsi qu'un test du lien enseignant avec la configuration de production. Les préparations des anciens tests de permissions utilisent désormais des comptes fictifs explicitement validés. Les attentes métier ont été conservées.

**Dépendances corrigées**

| Bibliothèque | Version retenue |
| --- | --- |
| aiohttp | 3.14.3 |
| idna | 3.15 |
| Pillow | 12.3.0 |
| PyJWT | 2.13.0 |
| requests | 2.33.0 |
| sqlparse | 0.6.0 |
| urllib3 | 2.7.0 |
| WeasyPrint | 69.0 |
| pypdf | 6.16.1 |
| python-dotenv | 1.2.2 |

OpenAI et pandas sont épinglés aux versions vérifiées, respectivement 2.54.0 et 3.0.1. pip 26.2.1 et setuptools 83.0.0 ont également été installés dans l'environnement local.

L'audit pip-audit des **72 paquets effectivement installés ne signale aucune vulnérabilité connue**. La résolution complète pour Python 3.11 réussit également, et son inventaire résolu ne présente aucune alerte connue. Cette résolution a été vérifiée depuis Windows ; elle ne remplace pas une exécution sur le serveur MySQL/PythonAnywhere.

WeasyPrint 69.0 couvre les corrections annoncées par l'éditeur concernant les redirections SSRF et l'injection CSS : [avis SSRF](https://github.com/Kozea/WeasyPrint/security/advisories/GHSA-983w-rhvv-gwmv), [avis CSS](https://github.com/Kozea/WeasyPrint/security/advisories/GHSA-jhhc-3hcp-qhm5).

`pip check` réussit. Le contrôle de cohérence et l'application de toutes les migrations sur une base temporaire réussissent. Un contrôle des dépendances installées est ajouté à GitHub Actions ; il s'exécutera après publication du code.

**Reproduire localement**

```powershell
venv/Scripts/python.exe scripts/run_project_tests.py --schema
venv/Scripts/python.exe scripts/run_project_tests.py
```

Les tests utilisent des données fictives, une base temporaire, des fichiers isolés et des communications applicatives externes bloquées. Les résultats JSON de la campagne sont conservés dans `livrables/Tests_vulnerabilite_2026-09-08/resultats_apres_corrections.json`, avec les rapports de dépendances avant et après correction. Le rapport d'audit initial décrit l'état antérieur ; la suite permanente ci-dessus décrit la version corrigée.

**Mise en service**

La fusion sur GitHub ne déploie pas automatiquement ces corrections sur le serveur. Après récupération du code sur le serveur, utiliser son environnement virtuel, installer les dépendances puis appliquer les migrations :

```bash
source venv311/bin/activate
python -m pip install --upgrade "pip>=26.2.1" "setuptools>=83.0.0"
python -m pip install -r requirements.txt
python manage.py migrate --noinput
python manage.py check
```

Recharger ensuite l'application dans PythonAnywhere. Les sessions non valides ou expirées seront refusées ; certains utilisateurs devront se reconnecter et vérifier leur téléphone. Aucune nouvelle migration n'est créée spécifiquement pour ces six corrections, mais les migrations des travaux précédents restent nécessaires si elles ne sont pas encore appliquées.

L'audit ne constitue pas une garantie d'absence de toute autre faille. Il valide les scénarios reproduits et les avis de dépendances connus au moment de la vérification.
