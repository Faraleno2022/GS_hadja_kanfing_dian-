# Audit des calculs — 15 septembre 2026

## Périmètre et méthode

Audit du code local à partir du commit `5e812387`, avec priorité aux paiements scolaires, remises, rapports financiers, transport, paie et notes. Relecture des calculs de dépenses et de grilles bus ; exécution de la suite du projet pour les autres modules : élèves, importation, présence, cantine, logistique, administration, synchronisation, comptes et mise à jour PC.

Les anomalies ci-dessous ont été reproduites sur des données fictives, puis corrigées. Les tests utilisent SQLite en mémoire, des médias et journaux temporaires, un serveur de courrier en mémoire et le réseau désactivé. Aucun paiement, salaire, élève ou bulletin réel n'a été modifié. Ce document décrit les règles du logiciel ; il ne constitue pas une validation réglementaire des barèmes scolaires ou fiscaux.

## Anomalies corrigées

| Zone | Erreur constatée | Correction et contrôle |
| --- | --- | --- |
| Rapport des remises | Un reçu était additionné autant de fois qu'il portait de remises. | Somme des reçus uniques par identifiant. Deux reçus distincts de même montant comptent chacun. Exemple testé : deux reçus de 30 000 donnent 60 000, même avec trois remises. |
| Rapport des remises | Une seconde soustraction des remises au net déjà encaissé produisait une différence trompeuse. | Le montant avant remises est reconstitué par net + remises. Le net n'apparaît qu'une fois par reçu dans les lignes du tableau. |
| Rapports journaliers et périodiques | Le reste dû ignorait les remises, y compris celles des versements précédents. | Même principe que la fiche élève : dû annuel − paiements cumulés − remises validées du même élève et de la même année. |
| Années scolaires des rapports | L'année était déduite du calendrier du versement, avec un pivot en août. Un règlement tardif pouvait perdre sa dette d'origine. | Sélection de l'échéancier correspondant à l'année enregistrée sur le reçu. Pour une nouvelle inscription sans reçu : année de la classe. Les autres années sont exclues. |
| Effectifs par classe | Un élève présent sur deux échéanciers annuels était compté deux fois. | Effectif calculé sur les élèves uniques, montants calculés sur les échéanciers uniques. Un excédent d'une année ne compense pas la dette d'une autre. |
| Reçus historiques | L'affectation d'un ancien reçu pouvait utiliser le tarif de la nouvelle année de la classe. | Recherche de l'échéancier de l'année du reçu. Exemple testé : les 30 000 d'inscription restent affectés à l'inscription malgré un nouveau tarif de 10 000. |
| Dépenses | Une facture sortait des totaux lorsqu'elle passait de « validée » à « payée ». | Les rapports incluent les dépenses VALIDEE et PAYEE, selon la date de facture et dans l'école autorisée. |
| Salaires dans les rapports | Une période sans validation reprenait tous les anciens salaires validés. Les validations du dernier jour après minuit étaient exclues. | Suppression du repli historique ; filtrage inclusif sur les dates locales de validation. |
| Avances de salaire | Déplacer une avance vers une période ouverte permettait de changer le net d'une paie déjà validée dans sa période d'origine. | Validation de la période enregistrée et de la destination. Création, modification, suppression et recalcul associés sont transactionnels. Un échec de recalcul annule l'écriture. |
| Répartition des heures | Les arrondis cumulés pouvaient créer une dernière ligne négative. Exemple : 0,03 heure sur cinq affectations. | Chaque arrondi est borné par le reliquat disponible ; la somme reste exactement égale au total, sans ligne négative. |
| Cache des moyennes et classements | Un résultat calculé pour une sélection d'élèves ou de matières pouvait être réutilisé pour une autre sélection. | Clés de cache incluant les identifiants demandés et la version de la classe. Le schéma de cache est renouvelé. |
| Coefficients | Changer le coefficient d'une matière pouvait laisser l'ancienne moyenne en cache. | Invalidation des rangs et moyennes après sauvegarde ou suppression d'une matière. Exemple : français 12, coefficient 2 ; maths 4, coefficient passant de 2 à 6 : moyenne passant de 8 à 6. |
| Composition absente | Le calcul d'un seul élève ne voyait pas les compositions saisies pour ses camarades et appliquait une formule différente de celle de la classe entière. | La détection d'une composition porte sur toute la matière/classe. Même calcul pour le bulletin individuel et le groupe. |
| Absence semestrielle | Une absence explicitement saisie au semestre pouvait être remplacée par une ancienne note trimestrielle. | Le repli trimestriel s'applique uniquement en l'absence d'un enregistrement semestriel. |
| Dates du rapport des remises | Une date invalide provoquait une erreur serveur ; une période inversée était acceptée. | Réponse 400 explicite pour une date invalide ou une borne de début postérieure à la fin. |
| Rapport du transport | Les versements étaient utilisés comme tarif dû ; le payé était cherché dans les paiements scolaires ; plusieurs versements gonflaient le nombre d'abonnés. | Utilisation des reçus bus et du calcul des grilles. Une grille annuelle est comptée une fois par élève ; les élèves sont dédupliqués. |
| Transport : périmètre et statuts | Les anciennes années pouvaient être mélangées et une suspension retirait l'argent déjà reçu. | Année active, école autorisée, encaissements conservés quel que soit le statut d'utilisation du bus. |
| Transport sans grille | Un ancien versement sans tarif pouvait donner un faux reste à payer. | Encaissement conservé, dû et reste affichés « Indéterminé ». Aucun tarif n'est inventé. |
| Confidentialité du rapport bus | Un compte sans école pouvait voir des montants des autres écoles. | Aucun résultat pour un compte non superadministrateur sans école ; contrôle de la cohérence entre élève, école et grille. |

## Principes de calcul vérifiés

### Paiements scolaires et remises

- Dû annuel = frais d'inscription **ou** de réinscription + tranche 1 + tranche 2 + tranche 3.
- Le montant du reçu est le net réellement enregistré comme paiement. Les remises sont conservées séparément.
- Reste courant = max(0, dû annuel − paiements validés cumulés − remises validées cumulées), pour le même élève et la même année.
- La remise de scolarité porte sur les tranches sélectionnées, jamais sur les frais d'inscription ou de réinscription. Le calcul conserve la base choisie dans le formulaire.
- Exemple : tarif 2 010 000, dont 30 000 d'inscription et 1 980 000 de scolarité. Une remise de 5 % sur les trois tranches vaut 99 000 ; le net à encaisser est 1 911 000. La déduction du tarif avant remise exige l'option correspondante lorsque l'argent n'a pas été encaissé.
- Les opérations en attente ne réduisent pas le solde validé affiché dans ces rapports. Elles restent prises en compte par les protections de saisie existantes.
- Les tests existants couvrent aussi les modifications, suppressions, restaurations, inscription/réinscription, changements de classe, cartes et reçus.

### Rapports

Les encaissements et remises de la période sont des **flux limités aux dates demandées**. La répartition par classe montre la **situation actuelle des échéanciers concernés**, avec leurs paiements et remises cumulés, même antérieurs à la période. Les libellés des exports précisent ce solde actuel.

Ces rapports ne reconstruisent pas un historique figé du solde à une date passée. La classe affichée est la classe actuellement associée à l'élève.

Les dépenses sont retenues selon la date de facture et leur statut validé/payé ; les salaires selon la date de validation. Le résumé financier conserve cette convention de gestion et ne doit pas être interprété comme un rapprochement bancaire fondé exclusivement sur les dates effectives de décaissement.

### Bus

- Dû annuel = somme des trois tranches de la grille.
- Les versements annuels complètent successivement T1, T2 et T3 après prise en compte des versements directs de tranche.
- Payé = somme des reçus bus ; reste = max(0, tarif − payé), calculé séparément par élève/grille puis additionné.
- Une suspension ou une expiration du service ne constitue pas un remboursement.
- Exemple testé : grille de 400 000, versements de 50 000 et 100 000 : un élève, payé 150 000, reste 250 000.
- Modification, suppression et transfert vers une autre classe sont couverts par les tests du suivi bus et du rapport.

### Paie

Net = salaire de base + primes − retenues − avances. Les tests existants vérifient le salaire fixe, le prorata d'embauche, les heures pointées ou mensuelles, les primes récurrentes/ponctuelles et les plafonds empêchant un net négatif.

La ventilation des heures est arrondie au centième et conserve exactement le total. Une paie validée, payée ou clôturée ne doit pas être modifiée en déplaçant une avance.

### Notes et bonus

- Bonus de suivi, lorsqu'il est activé : moyenne des notes de suivi ÷ 20 × 2, plafonné à 2.
- Note mensuelle après bonus plafonnée à 20 ; sans suivi, bonus nul.
- Le calcul actuel au secondaire combine 40 % de contrôle continu et 60 % de composition lorsque les deux composantes existent ; la moyenne générale utilise les coefficients des matières.
- Au primaire, la règle existante retient la composition seule lorsqu'elle existe et des coefficients unitaires.
- Une absence à une composition déjà organisée dans la matière compte zéro. Si aucune composition n'existe, le calcul conserve son comportement fondé sur le contrôle continu.
- Les formules pédagogiques existantes sont conservées ; l'audit corrige leur application incohérente entre sélections, caches et périodes.

## Validation

Résultat final : **585 tests réussis en 276,670 secondes**, dont **29 nouveaux tests** dans cet audit.
Contrôle Django : **aucune anomalie signalée**. Aucun changement de modèle nécessitant une migration. Toutes les migrations ont été appliquées avec succès à une base temporaire. Vérification du diff Git : aucune erreur de format.

Commandes reproductibles depuis l'environnement Python du projet :

```powershell
venv/Scripts/python.exe scripts/run_project_tests.py
venv/Scripts/python.exe scripts/run_project_tests.py --schema
```

Les nouveaux tests sont dans `ecole_moderne/test_audit_calculs.py`. Le script global inclut les suites de paiements, notes, bus, paie, synchronisation et sécurité déjà présentes.

## Limites et livraison

Les corrections concernent le code local de la branche `codex/audit-calculs-2026-09-15`. Elles n'ont pas été déployées sur le site pendant cet audit.

Les tests ne certifient pas l'intégrité de chaque donnée historique de production ni les courses concurrentes propres au serveur MySQL. Aucun recalcul massif de données réelles n'a été lancé. Les anciennes écritures bus sans grille nécessitent un tarif connu pour produire un solde fiable. Cet audit ne prétend pas garantir l'absence de tout défaut dans tous les parcours du projet.
