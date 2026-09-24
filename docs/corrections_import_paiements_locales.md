# Import d’élèves et recalculs des paiements

Adaptation locale du 6 septembre 2026, à partir des correctifs GitHub
`3a44080` / `c5e6607`, `42e9c2b` / `ba33106`, `6db1093` / `e2f80d4`
et des scénarios de récapitulatif `2117d35` / `ea9bef7`.

## Fonctionnement

- L’import Excel/CSV propose le verrouillage jusqu’au premier paiement validé.
  Les dossiers existants gardent leur statut lors d’un réimport.
- La page **Élèves → Répartir les élèves importés** propose pour chaque élève
  les classes du même niveau, de la même école et de la même année.
  L’affectation conserve le matricule et permet d’ouvrir le premier paiement.
- La fiche et la saisie de paiement restent accessibles. Les notes, bulletins,
  imports de notes, classements et présences excluent les dossiers verrouillés.
- Un paiement positif validé pour l’année de la classe déverrouille l’élève.
  La validation, le recalcul et le déverrouillage forment une transaction.
- Une correction, suppression ou restauration recalcule les remises de tous
  les versements concernés, dans l’ordre de leur date de paiement. Les paiements
  en attente ne consomment pas le solde. L’administration et les deux corbeilles
  utilisent le même service de recalcul.
- Le taux accordé est mémorisé avec la base et les tranches. Les anciennes
  remises sans règle enregistrée gardent leur montant. L’export affiche le taux
  mémorisé. La gestion locale des remises déduites du reçu est conservée.
- Les transferts de classe appliquent le tarif cible et recalculent les remises
  en conservant les encaissements. Les échéanciers des différentes années restent
  séparés. Une simple modification de commentaire ne change pas le montant reçu.
- Le récapitulatif par classe et ses exports sont vérifiés avec plusieurs
  versements et plusieurs élèves ayant un montant dû identique.

## Migrations

Deux migrations adaptées à l’historique de ce dossier sont ajoutées :

- `eleves/0021_import_verrouille_premier_paiement`
- `paiements/0020_regle_calcul_remises`

Elles ajoutent le verrou d’import, son statut et la règle de remise. Elles ne
recalculent pas les anciens paiements. Les migrations doivent être appliquées
à la base utilisée par l’application avant de démarrer cette version.

Les modifications locales déjà présentes sont conservées. Aucun commit, aucune
fusion de branche, aucun envoi GitHub ni déploiement n’est effectué par ce portage.

## Vérification

Les tests utilisent une base SQLite temporaire, avec les migrations réelles.
Les paiements de l’école et la base locale ne sont pas utilisés.

Les nouveaux scénarios sont dans `eleves/test_import_verrouille.py` et
`paiements/tests/test_recalcul_remises_historique.py`. Ils couvrent les contrôles
d’école, d’année et de permission, le déverrouillage, les erreurs transactionnelles,
les changements de montant et de date, les deux corbeilles, les remises figées,
les transferts, les reçus et les récapitulatifs.

La suite générale comportait déjà des échecs sur des tests d’une autre version
(fonctions ou routes absentes, attentes de rapports différentes et dates fixes).
Ces écarts sont distingués des tests ciblés du portage.


Résultat final : **166 tests réussis sur 168** dans la sélection élargie.
Les deux échecs de `eleves.test_export_transfert` attendent une casse mixte
alors que les signaux existants enregistrent les noms en majuscules. Ces deux
échecs ont été reproduits séparément avec les fichiers locaux sauvegardés
avant cette intervention.

Les 168 scénarios ont été exécutés avec les migrations réelles, puis relancés
sur le schéma des modèles après les derniers ajustements. Le contrôle Django
est sans erreur et `makemigrations eleves paiements --check --dry-run` ne
signale aucun écart.
