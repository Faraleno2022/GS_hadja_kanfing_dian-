# Carte des frais de révision — version 1.3.16

La carte « Frais de révision » est affichée dans le tableau de bord des paiements et dans la liste des révisions. Elle présente le montant total, le nombre d'élèves, le tarif fixe de 20 000 GNF par élève et l'année scolaire. Le bouton « Voir les élèves » ouvre la liste avec les mêmes filtres.

Le total ne compte que les paiements validés portant l'option de révision. Les versements suivants d'un même élève ne sont pas comptés une seconde fois. Le tableau de bord actualise la carte toutes les 30 secondes ; validation, modification, suppression et restauration sont prises en compte. Les résultats respectent l'école, l'année, la classe et la recherche.

Cette mise à jour ajoute la présentation du montant de révision. Elle conserve le calcul précédemment confirmé : 300 000 GNF dus − 100 000 GNF versés − 20 000 GNF déduits de la scolarité = 180 000 GNF restants. Le montant de révision n'est pas ajouté aux encaissements. Aucune nouvelle migration n'est nécessaire par rapport à la version 1.3.15.

## Vérification

- 32 tests ciblés réussis : révision, carte et tableau de bord, dont 5 nouveaux tests portant sur les totaux, les changements de statut, les corrections, les filtres et la séparation des écoles.
- 7 contrôles de version réussis.
- Vérification de l'affichage avec des données fictives.
- Journaux : `tmp/tests_carte_revision.log` et `tmp/test_carte_version.log`.
- Les tests utilisent une base temporaire isolée ; aucun paiement réel n'a été modifié.

## Distribution vérifiée

Installateur : Output/MySchoolGN_Setup_v1.3.16.exe (80 444 729 octets).

SHA-256 : a20552d3b6ea08580894de5c9e318561d955d2d611ef9781e295fe29acb832e2.

519 modules et 433 ressources comparés aux sources ; aucun module de production manquant. Le contrôle de démarrage a réussi dans un environnement temporaire.
