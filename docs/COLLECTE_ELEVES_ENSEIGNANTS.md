# Collecte d’élèves par lien enseignant

## Utilisation

1. Dans **Élèves**, ouvrir **Collecte enseignants**.
2. Choisir la classe et l’enseignant destinataire, puis la date et l’heure de fin. Créer le lien.
3. Utiliser **Copier le lien** ou **Partager** pour le transmettre à l’enseignant.
4. L’enseignant ouvre le formulaire sans compte, renseigne son nom et ajoute les élèves. Prénom, nom et sexe sont obligatoires ; naissance et coordonnées du responsable sont facultatives.
5. Les envois apparaissent dans la collecte, avec un compteur **à vérifier**. Aucune fiche élève n’est créée à ce stade.
6. L’utilisateur de l’école peut corriger une proposition, l’accepter ou la refuser. La sélection de plusieurs propositions permet un traitement par lot.
7. Par défaut, les élèves acceptés restent verrouillés jusqu’au premier paiement validé. Leur fiche et leur paiement sont accessibles ; leur présence dans les listes pédagogiques attend ce paiement. L’utilisateur peut décocher cette option avant la validation.

La détection des homonymes compare le prénom et le nom dans la classe, sans tenir compte de la casse, des accents ou des espaces répétés. Une confirmation explicite est nécessaire pour créer un second dossier portant les mêmes noms.

## Durée et révocation

La durée proposée est de sept jours. L’échéance est modifiable, jusqu’à un an dans le futur. L’heure suit le fuseau horaire configuré dans l’application.

**Révoquer le lien** bloque immédiatement les prochains envois. Les propositions reçues restent disponibles et peuvent être traitées. Un lien révoqué ne se réactive pas : créer un nouveau lien. Un lien simplement expiré peut être prolongé.

Un changement d’école ou d’année de la classe, ou la perte des droits de son créateur, désactive aussi l’accès public.

## Droits et confidentialité

La gestion est réservée aux comptes actifs et validés de l’école autorisés à importer les élèves, aux comptes principaux et aux rôles administrateur, directeur ou comptable. Un sous-compte doit également disposer du menu Élèves. La lecture seule ne permet pas cette gestion.

Toute personne possédant le lien peut proposer des élèves pour sa classe. Le nom du destinataire et celui saisi lors de l’envoi ne constituent pas une preuve d’identité. La validation par l’école reste obligatoire. Le formulaire ne montre ni les élèves existants, ni les autres propositions, ni les paiements.

Les envois sont limités à 50 élèves chacun, 30 envois par heure et 1 000 propositions par lien. Un renvoi du même formulaire ne crée pas de deuxième lot. Les formulaires conservent la protection CSRF.

## Mise en service

Appliquer la migration `eleves.0021_collecte_eleves_enseignants` puis redémarrer l’application web avec la nouvelle version. Aucun paiement existant n’est modifié.

Créer les liens sur le site web accessible aux enseignants. Une adresse locale du poste ne sera pas accessible depuis leur téléphone. Les liens et propositions appartiennent au serveur sur lequel ils sont créés ; ils ne sont pas synchronisés entre installations. Une fois acceptés, les élèves utilisent le mécanisme habituel de synchronisation du projet.

Les propositions se consultent dans **Collecte enseignants** ; cette fonctionnalité n’envoie pas automatiquement d’e-mail ou de SMS.
