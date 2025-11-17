#!/bin/bash
# Script de correction URGENTE pour le serveur - Fix evaluations_qs

echo "🚨 CORRECTION URGENTE: Fix evaluations_qs sur le serveur"
echo "=========================================================="
echo ""

cd /home/myschoolgn/GS_hadja_kanfing_dian- || exit 1

# Vérifier l'état actuel
echo "📋 État actuel du dépôt:"
git status
echo ""

# Voir les modifications locales
echo "📝 Modifications locales détectées:"
git diff notes/views.py | head -20
echo ""

# Sauvegarder les modifications locales
echo "💾 Sauvegarde des modifications locales (git stash)..."
git stash
echo ""

# Récupérer la dernière version depuis GitHub
echo "📥 Récupération de la dernière version depuis GitHub..."
git fetch origin
echo ""

# Forcer la mise à jour
echo "🔄 Mise à jour forcée vers origin/main..."
git reset --hard origin/main
echo ""

# Vérifier la version installée
echo "✅ Version installée:"
git log -1 --oneline
echo ""

# Vérifier que le fix est appliqué
echo "🔍 Vérification du fix (doit afficher 'evaluations' et non 'evaluations_qs'):"
grep -n "for evaluation in evaluation" notes/views.py | head -5
echo ""

# Nettoyer les caches Python
echo "🧹 Nettoyage des caches Python..."
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null
find . -type f -name "*.pyc" -delete 2>/dev/null
echo "   ✓ Caches supprimés"
echo ""

# Redémarrer le serveur
echo "🔄 Redémarrage du serveur uWSGI..."
touch ecole_moderne/wsgi.py
echo "   ✓ Serveur redémarré"
echo ""

echo "✅ ✅ ✅ CORRECTION TERMINÉE AVEC SUCCÈS! ✅ ✅ ✅"
echo ""
echo "🎯 Actions effectuées:"
echo "   1. Modifications locales sauvegardées (git stash)"
echo "   2. Code mis à jour depuis GitHub"
echo "   3. Caches Python nettoyés"
echo "   4. Serveur redémarré"
echo ""
echo "🔗 Testez maintenant:"
echo "   https://www.myschoolgn.space/notes/bulletins/classe/pdf/?classe_id=6&periode=OCTOBRE&system_type=mensuel"
echo ""
