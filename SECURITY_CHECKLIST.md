# 🔒 CHECKLIST DE SÉCURITÉ - MySchool GN

## ✅ Configuration Initiale

- [ ] Fichier .env créé avec SECRET_KEY aléatoire
- [ ] DEBUG=false en production
- [ ] .env ajouté au .gitignore
- [ ] Permissions fichier .env: 600 (lecture/écriture propriétaire uniquement)

## ✅ Base de Données

- [ ] Backup automatique configuré
- [ ] Permissions db.sqlite3: 600
- [ ] Backup testé et fonctionnel

## ✅ Authentification

- [ ] Mots de passe administrateurs changés (12+ caractères)
- [ ] Limitation tentatives connexion testée
- [ ] Sessions expiration configurée (30 min)
- [ ] Blocage superuser login public activé

## ✅ HTTPS/Certificats

- [ ] Certificat SSL valide et actif
- [ ] HSTS activé (31536000 secondes)
- [ ] Redirection HTTP → HTTPS fonctionnelle
- [ ] Cookies SECURE activés

## ✅ Protection Attaques

- [ ] Middleware sécurité activé en production
- [ ] Rate limiting configuré
- [ ] CSRF protection testée
- [ ] XSS protection testée
- [ ] SQL Injection protection testée

## ✅ Logging/Monitoring

- [ ] Logs sécurité activés
- [ ] Rotation logs configurée
- [ ] Alertes administrateur configurées
- [ ] Monitoring erreurs 500 actif

## ✅ Backups

- [ ] Backup quotidien base de données
- [ ] Backup fichiers media
- [ ] Test restauration backup réussi
- [ ] Backup stocké hors serveur

## ✅ Mises à Jour

- [ ] Django à jour (dernière version stable)
- [ ] Dépendances Python à jour
- [ ] Système d'exploitation à jour
- [ ] Scanner vulnérabilités exécuté

## ✅ Tests de Sécurité

- [ ] Test SQL Injection effectué
- [ ] Test XSS effectué
- [ ] Test CSRF effectué
- [ ] Test Brute Force effectué
- [ ] Scan ports effectué

## ✅ Documentation

- [ ] Procédures incident sécurité documentées
- [ ] Contacts urgence définis
- [ ] Plan reprise activité créé
- [ ] Formation équipe sécurité effectuée

---

**Date dernière révision:** ___________  
**Responsable sécurité:** ___________  
**Prochaine révision:** ___________
