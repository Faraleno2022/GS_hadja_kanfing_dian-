"""
Script de test pour vérifier l'ajustement des colonnes dans le PDF
"""
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.units import cm

# Configuration actuelle
headers = ["École", "Classe", "Matricule", "Nom", "Responsable", "Téléphone"]
col_widths = [4.5*cm, 4.5*cm, 3*cm, 5.5*cm, 5*cm, 3*cm]

# Page en format paysage A4
width, height = landscape(A4)
margin = 2*cm

# Largeur disponible
available_width = width - 2*margin

# Largeur totale utilisée (sans la colonne École qui n'est pas affichée dans le tableau)
total_width = sum(col_widths[1:])  # Classe + Matricule + Nom + Responsable + Téléphone

print("=" * 60)
print("ANALYSE DES COLONNES DU PDF")
print("=" * 60)
print(f"\nFormat: A4 Paysage (Landscape)")
print(f"Largeur totale de la page: {width/cm:.2f} cm")
print(f"Hauteur de la page: {height/cm:.2f} cm")
print(f"Marges (gauche + droite): {2*margin/cm:.2f} cm")
print(f"Largeur disponible: {available_width/cm:.2f} cm")

print(f"\n{'Colonne':<20} {'Largeur (cm)':<15} {'Max chars'}")
print("-" * 60)

max_chars = [27, 13, 28, 25, 13]  # Classe, Matricule, Nom, Responsable, Téléphone
for i, (header, width_val) in enumerate(zip(headers[1:], col_widths[1:])):
    print(f"{header:<20} {width_val/cm:<15.2f} {max_chars[i]}")

print("-" * 60)
print(f"{'TOTAL':<20} {total_width/cm:<15.2f}")
print(f"\nEspace restant: {(available_width - total_width)/cm:.2f} cm")

if total_width <= available_width:
    print("\n✅ Les colonnes tiennent dans la page (pas de chevauchement)")
else:
    print(f"\n❌ ATTENTION: Dépassement de {(total_width - available_width)/cm:.2f} cm")

print("\n" + "=" * 60)
print("EXEMPLES DE DONNÉES")
print("=" * 60)

# Exemples de données longues
exemples = [
    ("12 SÉRIE SCIENTIFIQUE", "L12SC-019", "BANGOURA AMINATA", "HAWA YOULA"),
    ("11 SÉRIE SCIENTIFIQUE", "L11SC-017", "DIALLO THIERNO HAMIDOU", "ALHASSANE DIALLO"),
    ("12 SÉRIE LITTÉRAIRE", "L12SL-011", "SYSAVANÉ FATOUMATA KANNY", "FATOUMATA BINTA BANS"),
]

for classe, matricule, nom, responsable in exemples:
    print(f"\nClasse: {classe[:30] if len(classe) > 30 else classe}")
    print(f"  Longueur: {len(classe)} chars → {'OK' if len(classe) <= 30 else 'TRONQUÉ'}")
    print(f"Matricule: {matricule[:15] if len(matricule) > 15 else matricule}")
    print(f"  Longueur: {len(matricule)} chars → {'OK' if len(matricule) <= 15 else 'TRONQUÉ'}")
    print(f"Nom: {nom[:28] if len(nom) > 28 else nom}")
    print(f"  Longueur: {len(nom)} chars → {'OK' if len(nom) <= 28 else 'TRONQUÉ'}")
    print(f"Responsable: {responsable[:25] if len(responsable) > 25 else responsable}")
    print(f"  Longueur: {len(responsable)} chars → {'OK' if len(responsable) <= 25 else 'TRONQUÉ'}")

print("\n" + "=" * 60)
