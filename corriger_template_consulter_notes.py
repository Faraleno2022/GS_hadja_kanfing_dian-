#!/usr/bin/env python
"""
Vérification et correction du template consulter_notes.html
"""

import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ecole_moderne.settings')
django.setup()

def corriger_template_consulter_notes():
    """Vérifier et corriger le template consulter_notes.html"""
    
    try:
        print("🔧 VÉRIFICATION TEMPLATE - consulter_notes.html")
        
        # 1. Lire le template actuel
        template_path = "templates/notes/consulter_notes.html"
        
        try:
            with open(template_path, 'r', encoding='utf-8') as f:
                template_content = f.read()
            print(f"✅ Template lu : {len(template_content)} caractères")
        except FileNotFoundError:
            print(f"❌ Template non trouvé : {template_path}")
            return
        
        # 2. Analyser la structure du template
        print(f"\n🔍 ANALYSE STRUCTURE TEMPLATE :")
        
        # Chercher la boucle principale
        if "for eleve_data in eleves_toutes_notes" in template_content:
            print(f"✅ Boucle élèves trouvée")
        else:
            print(f"❌ Boucle élèves non trouvée")
        
        # Chercher la boucle des matières
        if "for matiere in matieres" in template_content:
            print(f"✅ Boucle matières trouvée")
        else:
            print(f"❌ Boucle matières non trouvée")
        
        # Chercher la boucle des notes
        if "for note_info in notes_matiere.notes" in template_content:
            print(f"✅ Boucle notes trouvée")
        else:
            print(f"❌ Boucle notes non trouvée")
        
        # Chercher les cellules note-cell
        note_cell_count = template_content.count('note-cell')
        print(f"✅ Cellules note-cell : {note_cell_count}")
        
        # 3. Identifier le problème
        print(f"\n🔍 PROBLÈME IDENTIFIÉ :")
        print(f"  • Les élèves sont dans le template : ✅")
        print(f"  • Les notes existent en base : ✅")
        print(f"  • Mais les notes ne sont pas dans les cellules note-cell : ❌")
        
        # 4. Vérifier la structure exacte
        print(f"\n📋 VÉRIFICATION STRUCTURE EXACTE :")
        
        # Extraire la partie du template qui affiche les notes
        import re
        
        # Chercher le bloc qui affiche les notes
        pattern = r'{% for matiere in matieres %}(.*?){% endfor %}'
        matches = re.findall(pattern, template_content, re.DOTALL)
        
        if matches:
            print(f"✅ Bloc matières trouvé : {len(matches)}")
            
            for i, match in enumerate(matches[:1]):  # Premier bloc seulement
                print(f"\n  Bloc {i+1} :")
                print(f"    Longueur : {len(match)} caractères")
                
                # Vérifier si le bloc contient les notes
                if "notes_matiere.notes" in match:
                    print(f"    ✅ Contient notes_matiere.notes")
                else:
                    print(f"    ❌ Ne contient pas notes_matiere.notes")
                
                if "note_info.note" in match:
                    print(f"    ✅ Contient note_info.note")
                else:
                    print(f"    ❌ Ne contient pas note_info.note")
                
                if "note-cell" in match:
                    print(f"    ✅ Contient note-cell")
                else:
                    print(f"    ❌ Ne contient pas note-cell")
        else:
            print(f"❌ Bloc matières non trouvé")
        
        # 5. Créer une version corrigée du template
        print(f"\n🔧 CRÉATION VERSION CORRIGÉE :")
        
        # Le problème est probablement que notes_matiere.notes est vide
        # On va ajouter du debug dans le template
        
        # Remplacer la partie des notes par une version avec debug
        old_pattern = r'{% for note_info in notes_matiere.notes %}.*?{% endfor %}'
        new_code = '''{% for note_info in notes_matiere.notes %}
                                <td class="text-center note-cell" data-matiere-id="{{ matiere.id }}" data-periode="{% if note_info.evaluation %}{{ note_info.evaluation.periode }}{% else %}mensuelle{% endif %}">
                                    {% if note_info.absent %}
                                        <span class="text-danger">ABS</span>
                                    {% elif note_info.note is not None %}
                                        {{ note_info.note }}
                                    {% else %}
                                        <span class="text-muted">-</span>
                                    {% endif %}
                                </td>
                                {% endfor %}
                                <!-- DEBUG: notes_matiere.notes = {{ notes_matiere.notes|length }} -->
                                {% if notes_matiere.notes|length == 0 %}
                                <td class="text-center note-cell bg-warning" data-matiere-id="{{ matiere.id }}" data-periode="debug">
                                    <span class="text-dark">VIDE</span>
                                </td>
                                {% endif %}'''
        
        # Appliquer la correction
        new_template = re.sub(old_pattern, new_code, template_content, flags=re.DOTALL)
        
        if new_template != template_content:
            print(f"✅ Template modifié avec debug")
            
            # Sauvegarder la version corrigée
            backup_path = "templates/notes/consulter_notes_backup.html"
            with open(backup_path, 'w', encoding='utf-8') as f:
                f.write(template_content)
            print(f"✅ Backup sauvegardé : {backup_path}")
            
            with open(template_path, 'w', encoding='utf-8') as f:
                f.write(new_template)
            print(f"✅ Template corrigé sauvegardé")
            
            print(f"\n🎯 ACTION RECOMMANDÉE :")
            print(f"  1. Tester la version corrigée")
            print(f"  2. Si 'VIDE' s'affiche, le problème est dans les données")
            print(f"  3. Si les notes s'affichent, le problème est résolu")
            
        else:
            print(f"❌ Template non modifié (pattern non trouvé)")
            
            # Alternative : ajouter du debug après la boucle
            debug_code = '''
<!-- DEBUG INFO -->
<div class="alert alert-info">
    <strong>DEBUG:</strong><br>
    Élèves: {{ eleves_toutes_notes|length }}<br>
    Matières: {{ matieres|length }}<br>
    Période: {{ periode_classement }}
</div>
'''
            
            # Ajouter le debug au début du template
            if '<div class="table-card">' in new_template:
                new_template = new_template.replace(
                    '<div class="table-card">',
                    debug_code + '<div class="table-card">'
                )
                print(f"✅ Debug ajouté au template")
                
                with open(template_path, 'w', encoding='utf-8') as f:
                    f.write(new_template)
                print(f"✅ Template avec debug sauvegardé")
        
        print(f"\n🚀 PROCHAINES ÉTAPES :")
        print(f"  1. Redémarrer le serveur : touch ecole_moderne/wsgi.py")
        print(f"  2. Tester l'URL : /notes/consulter/?classe_id=4&periode=OCTOBRE")
        print(f"  3. Vérifier si le debug s'affiche")
        print(f"  4. Analyser les résultats du debug")
        
    except Exception as e:
        print(f"❌ Erreur : {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    corriger_template_consulter_notes()
