# Synchronisation offline / online

## Synchronisation automatique (poste desktop)

Sur l'application desktop packagee (MySchoolGN.exe), la synchronisation tourne
en tache de fond des le demarrage, sans commande manuelle :

- **Envoi (push)** : des qu'une donnee est enregistree localement (eleve,
  paiement, note, depense, ...), le changement est mis en file puis envoye
  vers le serveur en quelques instants (declenchement immediat, pas d'attente
  d'un intervalle).
- **Reception (pull)** : le poste interroge le serveur toutes les
  `MYSCHOOL_SYNC_INTERVAL` secondes (10s par defaut) pour recuperer les
  changements faits sur les autres postes/le serveur.
- **Transport rapide** : connexion HTTP persistante (keep-alive), compression
  gzip des lots, et vidage complet de la file a chaque cycle (pas de plafond
  a 200 changements comme avant).

Pour l'activer : copiez `sync_config.example.json` en `sync_config.json` a
cote de `MySchoolGN.exe`, renseignez les valeurs (voir enregistrement
ci-dessous), puis redemarrez l'application. Tant que ce fichier n'existe pas
(ou que les variables d'environnement equivalentes ne sont pas definies), la
synchronisation automatique reste silencieuse et n'a aucun effet.

`python manage.py sync_offline` (ci-dessous) reste disponible pour forcer un
cycle manuellement ou pour un environnement serveur sans interface graphique.


## 1. Configurer le serveur Render

Dans Render, ajoute une variable d'environnement secrete :

```text
MYSCHOOL_SYNC_ADMIN_TOKEN=une-longue-cle-secrete
```

Garde aussi :

```text
MYSCHOOL_SYNC_SERVER_URL=https://gs-hadja-kanfing-dian.onrender.com
```

## 2. Enregistrer un poste offline

Sur chaque poste local/offline, mets d'abord dans `.env` :

```text
MYSCHOOL_SYNC_SERVER_URL=https://gs-hadja-kanfing-dian.onrender.com
MYSCHOOL_SYNC_ADMIN_TOKEN=la-meme-cle-que-sur-render
MYSCHOOL_SYNC_ECOLE_ID=1
```

Puis lance :

```bash
python manage.py register_sync_device --nom "Direction"
```

La commande affiche :

```text
MYSCHOOL_SYNC_DEVICE_ID=...
MYSCHOOL_SYNC_TOKEN=...
MYSCHOOL_SYNC_ECOLE_ID=...
```

Copie ces valeurs dans le `.env` du poste offline. Le token n'est affiche qu'une seule fois.

## 3. Synchroniser

Sur le poste offline :

```bash
python manage.py sync_offline
```

Pour la premiere synchronisation d'un poste nouvellement installe :

```bash
python manage.py sync_offline --initial
```

Pour recevoir seulement les changements :

```bash
python manage.py sync_offline --pull-only
```

Pour envoyer seulement les changements locaux :

```bash
python manage.py sync_offline --push-only
```

Pour reprendre apres un changement serveur connu :

```bash
python manage.py sync_offline --since-id 123
```

## Notes importantes

- Chaque poste offline doit avoir son propre `MYSCHOOL_SYNC_DEVICE_ID` et `MYSCHOOL_SYNC_TOKEN`.
- Les changements sont echanges via `/api/v1/sync/push/` et `/api/v1/sync/pull/`.
- Cette base configure le transport entre versions offline. L'application progressive des payloads aux modeles metier peut etre ajoutee modele par modele.
