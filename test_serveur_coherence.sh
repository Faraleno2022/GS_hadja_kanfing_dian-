#!/bin/bash
# Script de test de cohérence sur le serveur

echo "=========================================="
echo "TEST DE COHÉRENCE SUR LE SERVEUR"
echo "=========================================="

# 1. Vérifier que le code est à jour
echo ""
echo "1. Vérification du code..."
git log -1 --oneline

# 2. Vérifier les migrations
echo ""
echo "2. Vérification des migrations..."
python manage.py showmigrations utilisateurs | tail -5

# 3. Tester la cohérence (si le script existe)
echo ""
echo "3. Test de cohérence..."
if [ -f "test_coherence_complete.py" ]; then
    python test_coherence_complete.py
else
    echo "⚠️  Script test_coherence_complete.py non trouvé"
    echo "Créons un test rapide..."
    
    # Test rapide inline
    python << 'PYEOF'
import os
import sys
import django

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ecole_moderne.settings')
django.setup()

from eleves.models import Eleve
from notes.models import ClasseNote
from notes.export_classement import _generer_classement_general

print("\n🔍 Test rapide de cohérence...")

# Trouver une classe avec des élèves
eleves = Eleve.objects.filter(statut='ACTIF')[:20]
if not eleves.exists():
    print("❌ Aucun élève actif trouvé")
    sys.exit(1)

classe_eleve = eleves.first().classe
classe_note = ClasseNote.objects.filter(nom__icontains=classe_eleve.nom.split()[0]).first()

if not classe_note:
    print("❌ ClasseNote non trouvée")
    sys.exit(1)

print(f"\nClasse testée : {classe_eleve.nom}")
print(f"Nombre d'élèves : {eleves.count()}")

# Générer le classement
try:
    classement_data, titre = _generer_classement_general(
        eleves, classe_note, 'mensuelle', 'OCTOBRE'
    )
    
    print(f"\n✅ Classement généré avec succès")
    print(f"   Élèves classés : {len([d for d in classement_data if d.get('moyenne') is not None])}")
    
    # Afficher le top 5
    print(f"\n📊 Top 5 :")
    for i, data in enumerate(classement_data[:5], 1):
        if data.get('moyenne') is not None:
            print(f"   {data.get('rang')} - {data.get('nom_complet')} : {data.get('moyenne'):.2f}")
    
    print("\n✅ Test de cohérence : OK")
    
except Exception as e:
    print(f"\n❌ Erreur : {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

PYEOF
fi

# 4. Redémarrer le serveur
echo ""
echo "4. Redémarrage du serveur..."
touch ecole_moderne/wsgi.py
echo "✅ Serveur redémarré"

# 5. Vérifier les logs
echo ""
echo "5. Dernières lignes des logs (si disponibles)..."
if [ -f "/var/log/uwsgi/app/myschoolgn.log" ]; then
    tail -20 /var/log/uwsgi/app/myschoolgn.log
else
    echo "⚠️  Logs non accessibles"
fi

echo ""
echo "=========================================="
echo "✅ VÉRIFICATION TERMINÉE"
echo "=========================================="
echo ""
echo "Prochaines étapes :"
echo "1. Accéder à : https://www.myschoolgn.space/notes/bulletin-dynamique/"
echo "2. Générer un nouveau bulletin pour LOUAMMOU Jean David"
echo "3. Vérifier que le rang affiché est maintenant 10ème/18"
echo ""
