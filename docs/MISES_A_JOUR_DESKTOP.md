# Mises à jour de MySchoolGN Desktop

La version Desktop vérifie automatiquement la dernière Release GitHub au
démarrage, au maximum une fois toutes les six heures. Une vérification manuelle
est également disponible dans le menu Démarrer sous **MySchoolGN > Vérifier les
mises à jour**.

## Publier une version

1. Modifier `APP_VERSION` dans `app_version.py` avec une version à trois nombres,
   par exemple `1.3.1`.
2. Commiter et pousser les changements sur `main`.
3. Créer puis pousser le tag correspondant :

   ```powershell
   git tag desktop-v1.3.1
   git push origin desktop-v1.3.1
   ```

Le workflow GitHub Windows compile alors `MySchoolGN.exe`, construit
l'installateur Inno Setup, génère son empreinte SHA-256 et publie les deux
fichiers dans une Release GitHub. Le build échoue si le numéro du tag ne
correspond pas à celui de `app_version.py`.

## Sécurité et données

- L'application refuse un téléchargement qui ne vient pas de GitHub.
- L'installateur n'est lancé que si son SHA-256 correspond à celui publié.
- Avant remplacement des fichiers, l'installateur sauvegarde la base SQLite,
  les médias, les licences, les sauvegardes et les configurations locales.
- Après installation, le démarrage applique automatiquement les migrations
  Django à la base conservée.

La première installation de la version `1.3.0` doit encore être faite avec son
installateur. À partir de cette version, les versions suivantes sont proposées
automatiquement par l'application.
