#!/bin/bash
# Import notes 6ème Année
python manage.py shell << 'EOF'
from notes.models import *
from eleves.models import *
from decimal import Decimal

# Trouve classe
c = ClasseNote.objects.filter(nom__icontains="6").first()
print(f"Classe: {c.nom}")

# Crée matières
mats = ["Dictée", "Histoire", "Rédaction", "Géographie", "Calcul", "Sciences", "Civique", "Lecture", "Anglais"]
for m in mats:
    MatiereNote.objects.get_or_create(nom=m, classe=c, defaults={'coefficient': 1})
print(f"✅ {len(mats)} matières créées")

# Import notes (exemple)
eleve = Eleve.objects.filter(classe__nom__icontains="6").first()
matiere = MatiereNote.objects.filter(classe=c, nom="Histoire").first()
NoteMensuelle.objects.create(eleve=eleve, matiere=matiere, note=Decimal("7.5"), periode="NOVEMBRE", annee_scolaire="2024-2025")
print("✅ Notes importées")
EOF
