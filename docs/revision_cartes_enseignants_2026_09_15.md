# Révision et cartes enseignants — version 1.3.15

La saisie et la modification d'un paiement proposent l'option « L'élève paie aussi les frais de révision ». Son montant est fixé à **20 000 GNF** pour toutes les classes ; aucun montant supplémentaire n'est à saisir.

La réduction porte sur la scolarité et ne diminue jamais le versement enregistré. Exemple confirmé : **300 000 GNF dus − 100 000 GNF versés − 20 000 GNF de réduction = 180 000 GNF restants**.

L'option est réservée une fois par élève et par année scolaire, y compris sur un paiement en attente. Elle prend effet à la validation. Une contrainte de base de données protège aussi contre les doublons concurrents. Les refus annulent l'opération ; la modification, la suppression, la restauration et les transferts reprennent le calcul annuel. Les frais d'inscription ne sont pas réduits.

La liste « Révisions payées » présente les paiements validés, avec recherche, année et classe, ainsi que des exports Excel et PDF. La précision figure sur le reçu privé et public, le ticket de paiement de 80 mm, le carnet, les exports de paiements, les états par tranche et les rapports comptables. Les tableaux d'encaissement continuent à totaliser l'argent effectivement versé.

Dans Salaires, la photo d'un enseignant peut être importée ou prise avec la caméra. Sa carte professionnelle est disponible individuellement au format 85,6 × 53,98 mm ou en planches A4 de huit cartes. Les cartes respectent l'école du compte et les filtres de la liste. L'ajout d'une photo ne change pas le salaire.

La capture attend une image vidéo valide et arrête la caméra à la fermeture, même lorsqu'une autorisation arrive en retard. Les images invalides et les photos dépassant les limites du formulaire sont refusées.

Migrations incluses : `paiements.0021_paiement_frais_revision_inclus_and_more` et `salaires.0012_enseignant_photo`. La distribution est préparée séparément de l'installation de l'école ; les tests utilisent une base et des médias temporaires.

Les journaux de validation sont conservés dans `tmp/test_revision_global_migrations.log`, `tmp/test_revision_finances.log` et `tmp/test_revision_final.log`. Les aperçus fictifs se trouvent dans `tmp/pdfs/revision`.

## Validation

- 357 tests de paiements et salaires réussis.
- 597 tests généraux exécutés avec les migrations réelles ; le contrôle de version, initialisé avant le passage à 1.3.15, a été relancé après la mise à jour.
- 45 contrôles finaux réussis, incluant la cohérence de version, les nouveaux calculs et les exports.
- Vérification complémentaire des PDF après correction du contraste : réussie.
- 4 scénarios caméra simulés réussis (capture, fermeture, bascule, refus).
- 245 gabarits et 960 routes contrôlés ; aucune migration manquante.
- Cartes, reçu, ticket, carnet et états de paiement inspectés visuellement avec des données fictives.

## Distribution vérifiée

Installateur : Output/MySchoolGN_Setup_v1.3.15.exe (80436225 octets).

SHA-256 : 63c53d7d6c4d3a9bff67ea0d0d34649f58f7d106e3cdd485ac8f40bdce53780d.

518 modules et 432 ressources comparés au projet ; aucun module de production manquant. Contrôle de lancement réussi sur un environnement temporaire.
