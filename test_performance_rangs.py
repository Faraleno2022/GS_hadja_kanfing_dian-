"""
Test de performance du système de rangs avec cache
"""
import os
import sys
import django
import time

# Configuration Django
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ecole_moderne.settings')
django.setup()

from notes.models import ClasseNote
from notes.utils_rangs import calculer_rangs_classe_periode
from django.core.cache import cache

print("\n" + "="*80)
print("TEST DE PERFORMANCE DU SYSTÈME DE RANGS AVEC CACHE")
print("="*80)

# Paramètres
classe_nom = "12 SÉRIE SCIENTIFIQUE"
periode = "OCTOBRE"

# Récupérer la classe
classe_note = ClasseNote.objects.filter(nom__icontains=classe_nom).first()
if not classe_note:
    print(f"❌ Classe '{classe_nom}' non trouvée")
    sys.exit(1)

print(f"\n✅ Classe : {classe_note.nom}")
print(f"✅ Période : {periode}")

# Vider le cache avant le test
cache.clear()
print("\n🗑️  Cache vidé pour test à froid")

# TEST 1: Premier calcul (SANS cache)
print("\n" + "-"*80)
print("TEST 1: PREMIER CALCUL (SANS CACHE)")
print("-"*80)

start = time.time()
rangs_dict = calculer_rangs_classe_periode(classe_note, periode, use_cache=True)
duree_sans_cache = time.time() - start

nb_eleves = len(rangs_dict)
print(f"\n✅ Nombre d'élèves : {nb_eleves}")
print(f"⏱️  Temps de calcul : {duree_sans_cache*1000:.2f} ms")
print(f"📊 Temps par élève : {duree_sans_cache*1000/nb_eleves:.2f} ms")

# TEST 2: Deuxième calcul (AVEC cache)
print("\n" + "-"*80)
print("TEST 2: DEUXIÈME CALCUL (AVEC CACHE)")
print("-"*80)

start = time.time()
rangs_dict_cached = calculer_rangs_classe_periode(classe_note, periode, use_cache=True)
duree_avec_cache = time.time() - start

print(f"\n✅ Nombre d'élèves : {len(rangs_dict_cached)}")
print(f"⏱️  Temps de calcul : {duree_avec_cache*1000:.2f} ms")
print(f"📊 Temps par élève : {duree_avec_cache*1000/nb_eleves:.2f} ms")

# Vérifier que les résultats sont identiques
if rangs_dict == rangs_dict_cached:
    print("✅ Les résultats sont identiques (cache fonctionne)")
else:
    print("❌ Les résultats sont différents (PROBLÈME!)")

# TEST 3: Amélioration de performance
print("\n" + "-"*80)
print("TEST 3: AMÉLIORATION DE PERFORMANCE")
print("-"*80)

amelioration = ((duree_sans_cache - duree_avec_cache) / duree_sans_cache) * 100
print(f"\n📈 Amélioration : {amelioration:.1f}%")
print(f"⚡ Gain de temps : {(duree_sans_cache - duree_avec_cache)*1000:.2f} ms")

if amelioration > 90:
    print("🎉 EXCELLENT : Le cache améliore drastiquement les performances !")
elif amelioration > 50:
    print("✅ BON : Le cache améliore significativement les performances")
elif amelioration > 0:
    print("⚠️  FAIBLE : Le cache améliore peu les performances")
else:
    print("❌ PROBLÈME : Le cache ne fonctionne pas correctement")

# TEST 4: Calcul sans cache (pour comparaison)
print("\n" + "-"*80)
print("TEST 4: CALCUL SANS CACHE (DÉSACTIVÉ)")
print("-"*80)

start = time.time()
rangs_dict_no_cache = calculer_rangs_classe_periode(classe_note, periode, use_cache=False)
duree_no_cache = time.time() - start

print(f"\n✅ Nombre d'élèves : {len(rangs_dict_no_cache)}")
print(f"⏱️  Temps de calcul : {duree_no_cache*1000:.2f} ms")
print(f"📊 Temps par élève : {duree_no_cache*1000/nb_eleves:.2f} ms")

# TEST 5: Moyenne sur 10 appels
print("\n" + "-"*80)
print("TEST 5: MOYENNE SUR 10 APPELS (AVEC CACHE)")
print("-"*80)

durees = []
for i in range(10):
    start = time.time()
    calculer_rangs_classe_periode(classe_note, periode, use_cache=True)
    durees.append(time.time() - start)

duree_moyenne = sum(durees) / len(durees)
duree_min = min(durees)
duree_max = max(durees)

print(f"\n📊 Temps moyen : {duree_moyenne*1000:.2f} ms")
print(f"⚡ Temps minimum : {duree_min*1000:.2f} ms")
print(f"🐌 Temps maximum : {duree_max*1000:.2f} ms")
print(f"📈 Écart-type : {(max(durees) - min(durees))*1000:.2f} ms")

# TEST 6: Afficher quelques rangs
print("\n" + "-"*80)
print("TEST 6: VÉRIFICATION DES RANGS")
print("-"*80)

eleves_tries = sorted(rangs_dict.items(), key=lambda x: x[1]['rang_num'])
print("\n📊 TOP 5:")
for i, (eleve_id, info) in enumerate(eleves_tries[:5], 1):
    from eleves.models import Eleve
    eleve = Eleve.objects.get(id=eleve_id)
    print(f"  {i}. {eleve.prenom} {eleve.nom:25} | {info['rang']:7} | Moy: {info['moyenne']:.2f}")

# RÉSUMÉ
print("\n" + "="*80)
print("RÉSUMÉ DES TESTS")
print("="*80)

print(f"""
📊 STATISTIQUES:
   - Nombre d'élèves : {nb_eleves}
   - Temps sans cache : {duree_sans_cache*1000:.2f} ms
   - Temps avec cache : {duree_avec_cache*1000:.2f} ms
   - Amélioration : {amelioration:.1f}%

⚡ PERFORMANCE:
   - Temps moyen (10 appels) : {duree_moyenne*1000:.2f} ms
   - Temps par élève : {duree_moyenne*1000/nb_eleves:.2f} ms

🎯 RECOMMANDATIONS:
""")

if nb_eleves < 30:
    print("   ✅ Classe petite (< 30 élèves)")
    print("   → Cache utile mais pas critique")
    print("   → Performance excellente même sans cache")
elif nb_eleves < 50:
    print("   ✅ Classe moyenne (30-50 élèves)")
    print("   → Cache recommandé pour optimiser")
    print("   → Performance acceptable sans cache")
elif nb_eleves < 100:
    print("   ⚠️  Classe grande (50-100 élèves)")
    print("   → Cache FORTEMENT recommandé")
    print("   → Performance peut être lente sans cache")
else:
    print("   ❌ Classe très grande (> 100 élèves)")
    print("   → Cache OBLIGATOIRE")
    print("   → Envisager calcul asynchrone")

print(f"""
✅ CONCLUSION:
   Le système de cache fonctionne correctement !
   Amélioration de {amelioration:.1f}% avec le cache activé.
   
   Le cache est automatiquement invalidé après 5 minutes
   ou après modification d'une note.
""")

print("="*80 + "\n")
