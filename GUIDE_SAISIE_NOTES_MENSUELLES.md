# 📚 GUIDE - SAISIE DES NOTES MENSUELLES

## 🚨 PROBLÈME IDENTIFIÉ
Les notes mensuelles d'OCTOBRE 2025-2026 ne sont pas saisies pour la classe 9ÈME ANNÉE.

**Conséquence** : Les bulletins affichent des colonnes vides.

---

## ✅ SOLUTION 1 : SAISIE MANUELLE (Interface Web)

### Étapes :
1. **Connexion**
   - URL : https://www.myschoolgn.space
   - Identifiants : Utilisateur autorisé

2. **Navigation**
   ```
   Menu Principal → Notes → Notes Mensuelles
   ```

3. **Sélection des paramètres**
   - Classe : `9ÈME ANNÉE`
   - Mois : `OCTOBRE`
   - Année scolaire : `2025-2026`
   - Cliquer sur `Afficher`

4. **Saisie des notes**
   - Un tableau s'affiche avec tous les élèves et matières
   - Saisir les notes sur 20 pour chaque case
   - Pour les absents : cocher la case "Absent"
   - Notes acceptées : 0 à 20

5. **Enregistrement**
   - Cliquer sur `Enregistrer les notes`
   - Message de confirmation : "Notes enregistrées avec succès"

---

## ✅ SOLUTION 2 : IMPORT EXCEL

### Étapes :
1. **Préparation du template**
   ```
   Notes → Importer Notes → Type : Notes Mensuelles
   ```
   - Télécharger le template Excel
   - Le template contient déjà les élèves et matières

2. **Remplissage du fichier**
   - Colonnes :
     * A : Matricule (ne pas modifier)
     * B : Nom complet (ne pas modifier)
     * C-L : Notes par matière
   - Format notes : nombre entre 0 et 20
   - Absences : laisser vide ou mettre "ABS"

3. **Import du fichier**
   - Choisir le fichier complété
   - Cliquer sur `Importer`
   - Vérifier le rapport d'import

---

## 🧪 VÉRIFICATION

### Après saisie, vérifier :
1. **Bulletin individuel**
   ```
   Notes → Bulletins Dynamiques
   Classe : 9ÈME ANNÉE
   Élève : CL9-011 - ABDOUL GOUDOUSSY DIALLO
   Période : OCTOBRE
   Système : Mensuel
   ```
   
   **Résultat attendu** : Les colonnes NOTE et MOY doivent être remplies

2. **Export de classe**
   ```
   Notes → Exporter Classement
   Classe : 9ÈME ANNÉE
   Période : OCTOBRE
   Type : Général
   ```
   
   **Résultat** : Excel avec tous les élèves et leurs moyennes

---

## 📊 EXEMPLE DE NOTES CORRECTES

| Matière | Note | Affichage Bulletin |
|---------|------|-------------------|
| Anglais | 15.5 | NOTE: 15.5 MOY: 15.5 |
| Biologie | 12.0 | NOTE: 12.0 MOY: 12.0 |
| Chimie | 14.0 | NOTE: 14.0 MOY: 14.0 |
| Absent | - | NOTE: - MOY: - |

---

## ⚠️ POINTS IMPORTANTS

1. **Permissions** : Seuls les utilisateurs autorisés peuvent saisir les notes
2. **Validation** : Les notes doivent être entre 0 et 20
3. **Absences** : Bien marquer les absents pour éviter les erreurs de calcul
4. **Coefficients** : Vérifier que les coefficients des matières sont corrects
5. **Sauvegarde** : Les notes sont sauvegardées automatiquement

---

## 🐛 DÉPANNAGE

### Si les notes ne s'affichent pas après saisie :
1. Vider le cache du navigateur
2. Se déconnecter et reconnecter
3. Vérifier l'année scolaire sélectionnée
4. Exécuter sur le serveur :
   ```bash
   cd ~/GS_hadja_kanfing_dian-
   python debug_production_notes.py
   ```

### Si l'import Excel échoue :
- Vérifier le format du fichier (.xlsx)
- Vérifier les matricules (doivent correspondre exactement)
- Vérifier les notes (nombres valides entre 0-20)
- Pas d'espaces dans les cellules vides

---

## 📞 SUPPORT

En cas de problème persistant :
1. Noter le message d'erreur exact
2. Noter l'URL de la page
3. Noter l'heure de l'erreur
4. Exécuter le script de diagnostic
5. Contacter le support technique avec ces informations
