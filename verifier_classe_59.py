#!/usr/bin/env python
import os, sys, django
sys.path.append('.')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ecole_moderne.settings')
django.setup()

from notes.models import ClasseNote
from eleves.models import Classe as ClasseEleve

# Vérifier la classe 59
classe_note = ClasseNote.objects.get(pk=59)
print(f'ClasseNote 59: "{classe_note.nom}" - {classe_note.ecole.nom}')

# Chercher ClasseEleve correspondante
classe_eleve = ClasseEleve.objects.filter(
    nom=classe_note.nom,
    annee_scolaire=classe_note.annee_scolaire,
    ecole=classe_note.ecole
).first()

if classe_eleve:
    print(f'✅ Correspondance trouvée: ClasseEleve {classe_eleve.id}')
else:
    print('❌ Pas de correspondance exacte')
    # Chercher la classe élève utilisée
    classe_eleve_utilisee = ClasseEleve.objects.get(pk=8)
    print(f'ClasseEleve utilisée: "{classe_eleve_utilisee.nom}" - {classe_eleve_utilisee.ecole.nom}')
