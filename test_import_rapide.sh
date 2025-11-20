#!/bin/bash
# Test rapide des fonctions d'import sur le serveur

echo "================================================================================"
echo "TEST RAPIDE DES FONCTIONS D'IMPORT"
echo "================================================================================"

cd /home/myschoolgn/GS_hadja_kanfing_dian-

# TEST 1: Import de Notes
echo ""
echo "--------------------------------------------------------------------------------"
echo "TEST 1: IMPORT DE NOTES"
echo "--------------------------------------------------------------------------------"

python test_import_notes.py

if [ $? -eq 0 ]; then
    echo "✅ Test import notes : RÉUSSI"
else
    echo "❌ Test import notes : ÉCHOUÉ"
fi

# TEST 2: Import d'Élèves
echo ""
echo "--------------------------------------------------------------------------------"
echo "TEST 2: IMPORT D'ÉLÈVES"
echo "--------------------------------------------------------------------------------"

python test_import_eleves.py

if [ $? -eq 0 ]; then
    echo "✅ Test import élèves : RÉUSSI"
else
    echo "❌ Test import élèves : ÉCHOUÉ"
fi

# RÉSUMÉ
echo ""
echo "================================================================================"
echo "RÉSUMÉ DES TESTS"
echo "================================================================================"
echo ""
echo "📋 URLS À TESTER MANUELLEMENT:"
echo ""
echo "1. Import de notes:"
echo "   https://www.myschoolgn.space/notes/importer/"
echo ""
echo "2. Import d'élèves:"
echo "   https://www.myschoolgn.space/eleves/importer/"
echo ""
echo "3. Template notes:"
echo "   https://www.myschoolgn.space/notes/template-import/?classe_id=7&matiere_id=1&type=MENSUELLE"
echo ""
echo "4. Template élèves:"
echo "   https://www.myschoolgn.space/eleves/template-eleves/?classe_id=7"
echo ""
echo "================================================================================"
echo "✅ Tests automatiques terminés !"
echo "📖 Consultez GUIDE_IMPORT_COMPLET.md pour plus de détails"
echo "================================================================================"
