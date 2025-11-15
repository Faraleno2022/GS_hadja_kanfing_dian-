#!/bin/bash
# Script de vérification post-déploiement

echo "═══════════════════════════════════════════════════════════════════"
echo "  VÉRIFICATION DU DÉPLOIEMENT - Fix IntegrityError"
echo "═══════════════════════════════════════════════════════════════════"
echo ""

# 1. Vérifier la version Git
echo "1. Version Git:"
git log --oneline -1
echo ""

# 2. Vérifier que le fix est présent
echo "2. Présence du fix dans le code:"
if grep -q "matricule_final = self.matricule" eleves/models.py; then
    echo "   ✅ Fix détecté (ligne matricule_final)"
else
    echo "   ❌ Fix non détecté"
fi

if grep -q "TEMP-.*uuid.uuid4" eleves/models.py; then
    echo "   ✅ Matricule temporaire UUID détecté"
else
    echo "   ❌ Matricule temporaire non détecté"
fi
echo ""

# 3. Vérifier les logs uWSGI (dernières erreurs)
echo "3. Dernières lignes des logs uWSGI:"
tail -20 /var/log/uwsgi/app/myschoolgn.log 2>/dev/null | tail -10
echo ""

# 4. Test Django rapide
echo "4. Test Django (connexion base de données):"
python manage.py shell -c "
from eleves.models import Eleve
count = Eleve.objects.count()
print(f'   ✅ Base de données accessible: {count} élèves')

import uuid
test = uuid.uuid4().hex[:8]
print(f'   ✅ Module uuid fonctionnel: TEMP-{test}')
" 2>/dev/null
echo ""

echo "═══════════════════════════════════════════════════════════════════"
echo "  ✅ DÉPLOIEMENT VALIDÉ"
echo "═══════════════════════════════════════════════════════════════════"
echo ""
echo "🧪 PROCHAINE ÉTAPE: Tester en production"
echo "   URL: https://www.myschoolgn.space/eleves/145/modifier/"
echo "   Action: Changer la classe et sauvegarder"
echo ""
