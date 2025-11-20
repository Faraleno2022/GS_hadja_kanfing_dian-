"""
Générer un PDF du classement avec ReportLab pour vérification
"""
import os
import sys
import django

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ecole_moderne.settings')
django.setup()

from eleves.models import Eleve
from notes.models import ClasseNote
from notes.export_classement import _generer_classement_general
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib import colors
from reportlab.lib.units import cm

print("=" * 100)
print("GENERATION DU CLASSEMENT PDF")
print("=" * 100)

# Récupérer la classe de test
eleves = Eleve.objects.filter(matricule__startswith='L12SC-', statut='ACTIF').order_by('nom', 'prenom')
if not eleves.exists():
    print("\nERREUR : Aucun élève L12SC trouvé")
    sys.exit(1)

classe_eleve = eleves.first().classe
classe_note = ClasseNote.objects.filter(nom__icontains="12 SERIE").first()

print(f"\nClasse : {classe_eleve.nom}")
print(f"Nombre d'élèves : {eleves.count()}")

# Générer le classement
classement_data, titre = _generer_classement_general(
    eleves, classe_note, 'mensuelle', 'OCTOBRE'
)

# Créer le PDF
pdf_path = 'CLASSEMENT_GENERAL_OCTOBRE_2025.pdf'
c = canvas.Canvas(pdf_path, pagesize=A4)
width, height = A4

# En-tête
c.setFont("Helvetica-Bold", 16)
c.drawCentredString(width/2, height - 2*cm, "GROUPE SCOLAIRE HADJA KANFING DIANE")

c.setFont("Helvetica-Bold", 14)
c.drawCentredString(width/2, height - 3*cm, "CLASSEMENT GÉNÉRAL - OCTOBRE 2025")

c.setFont("Helvetica", 12)
c.drawCentredString(width/2, height - 3.8*cm, f"Classe : {classe_eleve.nom}")
c.drawCentredString(width/2, height - 4.4*cm, f"Effectif : {len([d for d in classement_data if d.get('moyenne') is not None])} élèves")

# Tableau
y = height - 6*cm
c.setFont("Helvetica-Bold", 10)
c.drawString(2*cm, y, "Rang")
c.drawString(4.5*cm, y, "Matricule")
c.drawString(8*cm, y, "Nom et Prénom")
c.drawString(16*cm, y, "Moyenne")

# Ligne de séparation
y -= 0.3*cm
c.line(2*cm, y, width - 2*cm, y)

# Données
y -= 0.5*cm
c.setFont("Helvetica", 9)

for i, data in enumerate(classement_data, 1):
    if data.get('moyenne') is not None:
        rang = data.get('rang', 'N/A')
        matricule = data.get('matricule', 'N/A')
        nom = data.get('nom_complet', 'N/A')
        moyenne = data.get('moyenne')
        
        # Alterner les couleurs
        if i % 2 == 0:
            c.setFillColorRGB(0.95, 0.95, 0.95)
            c.rect(1.8*cm, y - 0.2*cm, width - 3.6*cm, 0.5*cm, fill=1, stroke=0)
            c.setFillColorRGB(0, 0, 0)
        
        # Mettre en évidence le top 3
        if i <= 3:
            c.setFont("Helvetica-Bold", 9)
        else:
            c.setFont("Helvetica", 9)
        
        c.drawString(2*cm, y, rang)
        c.drawString(4.5*cm, y, matricule)
        c.drawString(8*cm, y, nom[:35])  # Tronquer si trop long
        c.drawString(16*cm, y, f"{moyenne:.2f}")
        
        y -= 0.6*cm
        
        # Nouvelle page si nécessaire
        if y < 3*cm:
            c.showPage()
            y = height - 2*cm
            c.setFont("Helvetica", 9)

# Pied de page
c.setFont("Helvetica-Oblique", 8)
c.drawCentredString(width/2, 2*cm, "Document généré automatiquement - Système de Gestion Scolaire")
c.drawCentredString(width/2, 1.5*cm, "Année Scolaire 2025-2026")

c.save()

print(f"\n✅ Classement PDF généré : {pdf_path}")
print(f"\nRésumé du classement :")
print(f"{'Rang':<15} {'Matricule':<15} {'Nom':<40} {'Moyenne':<10}")
print("-" * 85)

for i, data in enumerate(classement_data[:10], 1):  # Top 10
    if data.get('moyenne') is not None:
        rang = data.get('rang')
        matricule = data.get('matricule')
        nom = data.get('nom_complet')
        moyenne = data.get('moyenne')
        print(f"{rang:<15} {matricule:<15} {nom:<40} {moyenne:<10.2f}")

print("\n" + "=" * 100)
print("ÉLÈVE TEST : DIALLO ALPHA OUSMANE")
print("=" * 100)

eleve_test = eleves.filter(nom__icontains="DIALLO", prenom__icontains="Alpha Ousmane").first()
if eleve_test:
    for data in classement_data:
        if data.get('matricule') == eleve_test.matricule:
            print(f"\nMatricule : {data.get('matricule')}")
            print(f"Rang : {data.get('rang')}")
            print(f"Moyenne : {data.get('moyenne'):.2f}")
            print(f"\n✅ Ce rang devrait correspondre exactement au rang affiché dans son bulletin !")
            break

print("\n" + "=" * 100)
