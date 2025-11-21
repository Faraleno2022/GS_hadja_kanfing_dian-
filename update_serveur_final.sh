#!/bin/bash
# Script de mise à jour finale du serveur avec vérification

echo "=========================================="
echo "MISE À JOUR FINALE DU SERVEUR"
echo "=========================================="

cd /home/myschoolgn/GS_hadja_kanfing_dian-

# 1. Vérifier le commit actuel
echo ""
echo "1. Commit actuel sur le serveur:"
git log -1 --oneline

# 2. Fetch et pull
echo ""
echo "2. Récupération des dernières modifications..."
git fetch origin
git pull origin main

# 3. Vérifier le nouveau commit
echo ""
echo "3. Nouveau commit:"
git log -1 --oneline

# 4. Vérifier que la correction est présente
echo ""
echo "4. Vérification de la correction dans bulletin_dynamique..."
if grep -q "calculer_rang_intelligent" notes/views.py; then
    echo "✅ calculer_rang_intelligent trouvé dans views.py"
    
    # Compter les occurrences
    count=$(grep -c "calculer_rang_intelligent" notes/views.py)
    echo "   Nombre d'utilisations: $count"
else
    echo "❌ calculer_rang_intelligent NON trouvé!"
    echo "   Le pull n'a peut-être pas fonctionné"
fi

# 5. Vérifier qu'il n'y a plus de rang_actuel = idx
echo ""
echo "5. Vérification absence du bug..."
if grep -q "rang_actuel = idx" notes/views.py; then
    echo "⚠️  Bug 'rang_actuel = idx' encore présent!"
    grep -n "rang_actuel = idx" notes/views.py
else
    echo "✅ Bug 'rang_actuel = idx' corrigé"
fi

# 6. Redémarrer le serveur
echo ""
echo "6. Redémarrage du serveur..."
touch ecole_moderne/wsgi.py
echo "✅ Serveur redémarré"

# 7. Test rapide de cohérence
echo ""
echo "7. Test rapide de cohérence..."
python << 'PYEOF'
import os, sys, django
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ecole_moderne.settings')
django.setup()

from eleves.models import Eleve
from notes.models import ClasseNote
from notes.export_classement import _generer_classement_general

eleve = Eleve.objects.filter(nom__icontains="LOUAMMOU", prenom__icontains="Jean", statut='ACTIF').first()
if eleve:
    eleves = Eleve.objects.filter(classe=eleve.classe, statut='ACTIF')
    notes = eleve.noteeleve_set.filter(evaluation__periode='OCTOBRE')
    if notes.exists():
        classe_note = notes.first().evaluation.matiere.classe
        classement_data, _ = _generer_classement_general(eleves, classe_note, 'mensuelle', 'OCTOBRE')
        
        for data in classement_data:
            if data.get('matricule') == eleve.matricule:
                print(f"\n✅ LOUAMMOU Jean David : {data.get('rang')} - {data.get('moyenne'):.2f}/20")
                if '10ème' in data.get('rang', ''):
                    print("✅ RANG CORRECT!")
                else:
                    print(f"⚠️  Rang attendu: 10ème/18, obtenu: {data.get('rang')}")
                break
    else:
        print("⚠️  Pas de notes OCTOBRE pour cet élève")
else:
    print("⚠️  Élève LOUAMMOU non trouvé")
PYEOF

echo ""
echo "=========================================="
echo "✅ MISE À JOUR TERMINÉE"
echo "=========================================="
echo ""
echo "Prochaines étapes:"
echo "1. Tester le bulletin web: https://www.myschoolgn.space/notes/bulletin-dynamique/"
echo "2. Vérifier que LOUAMMOU Jean David affiche 10ème/18"
echo "3. Comparer avec le classement général"
echo ""
