# Accès temporaires enseignants — Notes

## Déploiement

Après mise à jour du code, exécuter `python manage.py migrate`, puis redémarrer
l’application Django. La migration `notes.0014_acces_enseignants_temporaire`
ajoute les comptes et leurs autorisations sans modifier les notes existantes.

## Compte principal

1. Dans **Salaires → Enseignants**, enregistrer l’enseignant et son affectation de
   classe (dates en cours, active). Les administrateurs et la garderie ne sont
   pas concernés par ces accès.
2. Dans **Notes**, vérifier que la classe existe avec exactement le même nom,
   la même école, la même année scolaire et le bon niveau d’enseignement.
   Ajouter ses matières si nécessaire.
3. Ouvrir **Notes → Accès temporaires enseignants**, choisir l’enseignant,
   les classes et la date d’expiration (7 jours par défaut, 90 jours maximum).
   Au secondaire, sélectionner les matières de chaque classe. Au primaire et
   en maternelle, toutes les matières actives de la classe sont proposées.
4. Créer le compte puis copier le lien, affiché une seule fois. Le transmettre
   en privé à l’enseignant. Aucun message n’est envoyé automatiquement.
5. Révoquer l’accès à tout moment. « Générer un nouveau lien » remplace le lien
   précédent et invalide ses sessions. Pour changer les autorisations, révoquer
   et créer un nouvel accès.

Seuls les comptes principaux et le superadministrateur peuvent gérer les accès.
Les comptes temporaires n’ont pas de mot de passe utilisable ni d’accès aux
autres modules/API, même en saisissant leur URL directement. Les liens sont
des secrets : toute personne qui les reçoit peut utiliser l’accès jusqu’à son
expiration/révocation. Utiliser HTTPS et éviter de journaliser leurs URL dans
les outils de suivi externes.

## Enseignant

Ouvrir le lien, puis cliquer sur « Ouvrir mon espace enseignant ». Sur un
ordinateur partagé, utiliser une fenêtre privée et se déconnecter après usage.

- **Saisir les notes** : une matière à la fois, par mois ou composition.
- **Saisie intelligente** : tableau des matières autorisées, navigation avec
  Entrée et collage d’un bloc Excel à partir de la cellule sélectionnée.
- **Importer** : CSV UTF-8 ou XLSX pour une matière.
- **Importation intelligente** : reconnaissance des colonnes par code/nom des
  matières autorisées. Télécharger le modèle de la classe, le remplir,
  vérifier l’aperçu puis confirmer sous 15 minutes.

Au primaire les notes sont sur 10, au secondaire sur 20. En maternelle, les
appréciations trimestrielles sont A+, A, B+, B, B-, C ou D. `ABS` indique une
absence. Une cellule vide conserve la note déjà enregistrée : elle ne l’efface
pas. Une valeur non vide remplace la note de la même période/matière/élève.
Les notes utilisent les modèles existants et alimentent les bulletins habituels.

Les fichiers sont limités à 2 Mo, 2 000 élèves, 100 colonnes et 10 000 notes.
Les formules Excel et les matricules hors classe sont refusés. Si une ligne
est invalide, aucune note du fichier n’est enregistrée. Seule la feuille active
du classeur est lue. Conserver les matricules en texte, notamment leurs zéros
initiaux. Aucune nouvelle classe, matière ou fiche élève n’est créée par import.

Les affectations, l’école, le statut actif, l’expiration et les autorisations
sont revérifiés à chaque requête et avant l’enregistrement. Une affectation
terminée retire immédiatement l’accès à sa classe. Les comptes et empreintes
de liens ne font pas partie des modèles de synchronisation hors ligne.
