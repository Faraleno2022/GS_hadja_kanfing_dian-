# Guide du Système de Paiement Partiel Intelligent

## 🎯 Fonctionnalité Implémentée

Le système détecte automatiquement quand un utilisateur saisit un montant supérieur à ce qui est dû pour une tranche spécifique et propose intelligemment d'utiliser l'excédent comme acompte sur les tranches suivantes.

## 📋 Cas d'Usage

### Situation Exemple
- **Élève**: Fara Leno (PN2-001)
- **Type de paiement**: "1ère tranche"
- **Montant dû T1**: 250 000 GNF
- **Montant saisi**: 280 000 GNF
- **Excédent**: 30 000 GNF

### Comportement du Système

#### 1. **Détection Automatique**
Le système détecte que 280 000 GNF > 250 000 GNF (montant dû T1).

#### 2. **Analyse Intelligente**
- Calcule l'excédent: 280 000 - 250 000 = 30 000 GNF
- Vérifie les tranches suivantes disponibles (T2, T3)
- Propose une répartition optimale

#### 3. **Interface de Confirmation**
Affiche une interface claire avec :
- **Montant T1 maximum**: 250 000 GNF
- **Excédent**: 30 000 GNF
- **Suggestion**: "250 000 GNF pour T1 + 30 000 GNF comme acompte T2"

#### 4. **Validation Utilisateur**
L'utilisateur doit cocher : 
> ☑️ "Je confirme vouloir utiliser l'excédent comme acompte sur la tranche suivante"

#### 5. **Allocation Automatique**
Si confirmé, le système alloue automatiquement :
- 250 000 GNF → Tranche 1 (soldée)
- 30 000 GNF → Tranche 2 (acompte)

## 🔧 Implémentation Technique

### Backend (`paiements/views.py`)

Le contrôle est **unique** et vaut pour tous les types, y compris les types
combinés (« Inscription + Tranche 1 », « Tranche 1 + Tranche 2 », …). Il est
placé après les plafonds d'affectation et de solde annuel, afin de ne demander
confirmation que d'un paiement réellement enregistrable.

```python
# Un montant supérieur au type sélectionné est légitime — l'excédent glisse
# sur les postes suivants — mais il ne doit jamais partir en silence.
if montant_attendu > 0 and montant_saisi > montant_attendu:
    if not request.POST.get('confirmation_paiement_superieur'):
        allocation, _payes, _reliquat = allocate_amount(
            montant_saisi, dues, couverts, type_nom
        )
        repartition = [
            {'label': libelles[bucket], 'montant': int(allocation[bucket])}
            for bucket in (INSCRIPTION, TRANCHE_1, TRANCHE_2, TRANCHE_3)
            if allocation[bucket] > 0
        ]
        return render(request, 'paiements/form_paiement.html', {
            'show_superior_confirmation': True,
            'repartition': repartition,
            # ...
        })
```

La répartition affichée n'est pas une suggestion : elle est calculée par
`allocate_amount`, la fonction qui ventilera réellement le paiement.

### Frontend (`templates/paiements/form_paiement.html`)

Interface de confirmation avec :
- Cartes visuelles pour montants
- Proposition intelligente colorée
- Checkbox de confirmation obligatoire
- Boutons d'action intuitifs

### Allocation (`_allocate_payment_to_echeancier`)

La fonction d'allocation existante gère automatiquement la répartition séquentielle :
1. Inscription (si due)
2. Tranche 1 → Tranche 2 → Tranche 3

## 🎨 Interface Utilisateur

### Écran de Confirmation

```
⚠️ CONFIRMATION REQUISE - MONTANT SUPÉRIEUR

Le montant saisi (280 000 GNF) dépasse le montant standard
pour 1ère tranche (250 000 GNF).

Répartition qui sera enregistrée :
• 1ère tranche : 250 000 GNF
• 2ème tranche : 30 000 GNF

☑️ Je confirme cette répartition et souhaite enregistrer le paiement.

[Confirmer la répartition] [Modifier le montant]
```

## 🔄 Flux Utilisateur

1. **Saisie du paiement**
   - Sélectionner "1ère tranche"
   - Saisir 280 000 GNF

2. **Détection automatique**
   - Système détecte le sur-paiement
   - Calcule la répartition optimale

3. **Confirmation**
   - Interface explicative s'affiche
   - Utilisateur lit la proposition
   - Coche la confirmation

4. **Validation**
   - Paiement enregistré
   - Allocation automatique effectuée
   - Échéancier mis à jour

## ✅ Avantages

### Pour l'Utilisateur
- **Flexibilité** : Peut payer plus que prévu sans blocage
- **Transparence** : Voit exactement comment sera réparti le montant
- **Simplicité** : Une seule transaction au lieu de deux

### Pour le Système
- **Sécurité** : Confirmation obligatoire avant sur-paiement
- **Précision** : Allocation automatique sans erreur manuelle
- **Traçabilité** : Logs détaillés de toutes les opérations

## 🛡️ Sécurité

- **Validation backend** : Vérification côté serveur obligatoire
- **Confirmation explicite** : Utilisateur doit cocher la case
- **Limites respectées** : Jamais de dépassement des montants dus
- **Logs complets** : Traçabilité de toutes les actions

## 📊 Cas de Test

### Test 1 : Paiement Normal
- **Montant** : 250 000 GNF (exact)
- **Résultat** : Passe directement, aucune confirmation

### Test 2 : Sur-paiement Sans Confirmation
- **Montant** : 280 000 GNF
- **Résultat** : Interface de confirmation affichée

### Test 3 : Sur-paiement Avec Confirmation
- **Montant** : 280 000 GNF + confirmation
- **Résultat** : Allocation T1=250k, T2=30k

### Test 4 : Aucune Tranche Suivante Disponible
- **Contexte** : T2 et T3 déjà soldées
- **Résultat** : Erreur de sur-paiement classique

### Test 5 : Type combiné

- **Type** : « Inscription + Tranche 1 » (30 000 + 400 000 = 430 000 dus)
- **Montant** : 500 000 GNF
- **Résultat** : confirmation affichée, répartition 30 000 / 400 000 / 70 000

## ⚠️ Régression corrigée

Pendant un temps, la vue posait `confirmation_partiel_suivant = True` en dur au
lieu de lire le champ POST. Tout le bloc de confirmation devenait inatteignable :
un montant supérieur au type partait sans un mot, alors qu'un montant inférieur,
lui, exigeait toujours une confirmation. Cette asymétrie est corrigée et
couverte par `paiements/tests/test_remise_deduction_et_montant_superieur.py`.

## 🚀 Évolutions Futures

1. **Suggestions multiples** : Proposer plusieurs répartitions
2. **Historique** : Afficher les paiements partiels précédents
3. **Notifications** : Alerter quand acompte suffisant pour solder

---

Cette fonctionnalité transforme l'expérience utilisateur en rendant le système de paiement plus intelligent et flexible, tout en maintenant la sécurité et la précision comptable.
