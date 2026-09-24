# Refus d'une remise excessive

Correctif local du 8 septembre 2026 pour la page « Appliquer une remise ».

La version Git consultée appelait `_retour_detail()` sans définir cette
fonction dans la vue. La version locale autorisait le dépassement avec un
avertissement. Elle affiche désormais le refus dans le formulaire existant,
avant toute modification financière.

- Les paiements validés et en attente de la même année sont pris en compte,
  ainsi que leurs remises. Les paiements annulés et les autres années sont exclus.
- Le reçu en cours et ses anciennes remises sont remplacés dans la simulation,
  sans double comptage. Une remise déduite utilise le montant net proposé.
- Si le total dépasse le montant dû, les paiements, remises existantes,
  échéanciers et règles du catalogue restent inchangés. Le formulaire affiche
  la remise maximale disponible et conserve la sélection.
- Une déduction qui annulerait le reçu est refusée avant d’atteindre la
  contrainte de montant strictement positif de la base.
- Une remise à la limite exacte est autorisée. L'absence d'échéancier annuel
  produit aussi un refus explicite, sans enregistrement.
- Les nouvelles règles de pourcentage ne sont enregistrées qu'après acceptation,
  dans la même transaction que les liens de remise.

Les scénarios de non-modification sont dans
`paiements/tests/test_refus_remise_excessive.py`. Aucune migration n'est nécessaire.
