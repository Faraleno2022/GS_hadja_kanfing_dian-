#!/usr/bin/env python
"""
Diagnostic et correction du mapping des classes entre local et serveur
"""

import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ecole_moderne.settings')
django.setup()

def diagnostiquer_mapping_classes():
    """Diagnostiquer le mapping des classes entre ClasseNote et ClasseEleve"""
    
    try:
        from notes.models import ClasseNote
        from eleves.models import Classe as ClasseEleve
        from eleves.models import Eleve
        
        print("🔧 DIAGNOSTIC MAPPING CLASSES")
        print("=" * 60)
        
        # 1. Lister toutes les ClasseNote
        print("\n📋 CLASSENOTES (notes) :")
        classes_notes = ClasseNote.objects.all()
        
        mapping_dict = {}
        problemes = []
        
        for cn in classes_notes:
            print(f"  • {cn.nom} (ID: {cn.id}) - École: {cn.ecole.nom if cn.ecole else 'N/A'}")
            
            # Chercher la classe élève correspondante
            classe_eleve = None
            
            # Méthode 1: Par mapping explicite
            mapping_explicite = {
                59: 8,   # 11ème Série littéraire
                60: 9,   # 11ème Série scientifique
                # Ajouter d'autres mappings si nécessaire
            }
            
            if cn.id in mapping_explicite:
                classe_eleve = ClasseEleve.objects.filter(id=mapping_explicite[cn.id]).first()
                if classe_eleve:
                    mapping_dict[cn.id] = classe_eleve.id
                    print(f"    ✅ Mapping explicite -> ClasseEleve ID: {classe_eleve.id}")
                else:
                    problemes.append(f"Mapping explicite {cn.id} -> {mapping_explicite[cn.id]} non trouvé")
            
            # Méthode 2: Par nom exact
            if not classe_eleve:
                classe_eleve = ClasseEleve.objects.filter(
                    nom=cn.nom,
                    annee_scolaire=cn.annee_scolaire,
                    ecole=cn.ecole
                ).first()
                
                if classe_eleve:
                    mapping_dict[cn.id] = classe_eleve.id
                    print(f"    ✅ Mapping par nom -> ClasseEleve ID: {classe_eleve.id}")
                else:
                    problemes.append(f"Pas de mapping trouvé pour {cn.nom} (ID: {cn.id})")
        
        print(f"\n📊 RÉSUMÉ MAPPING :")
        print(f"  • Classes trouvées : {classes_notes.count()}")
        print(f"  • Mapping réussis : {len(mapping_dict)}")
        print(f"  • Problèmes : {len(problemes)}")
        
        if problemes:
            print(f"\n❌ PROBLÈMES :")
            for prob in problemes:
                print(f"  • {prob}")
        
        # 2. Vérifier les élèves par classe
        print(f"\n👥 VÉRIFICATION ÉLÈVES PAR CLASSE :")
        
        for cn_id, ce_id in mapping_dict.items():
            cn = ClasseNote.objects.get(id=cn_id)
            ce = ClasseEleve.objects.get(id=ce_id)
            
            eleves = Eleve.objects.filter(classe=ce, statut='ACTIF')
            
            print(f"\n📚 {cn.nom} :")
            print(f"  • ClasseNote ID : {cn.id}")
            print(f"  • ClasseEleve ID : {ce.id}")
            print(f"  • Élèves actifs : {eleves.count()}")
            
            # Vérifier les notes pour OCTOBRE
            from notes.models import Evaluation, NoteEleve
            
            evaluations_octobre = Evaluation.objects.filter(
                classe_note=cn,
                periode='OCTOBRE'
            )
            
            notes_octobre = NoteEleve.objects.filter(
                evaluation__in=evaluations_octobre
            )
            
            print(f"  • Évaluations OCTOBRE : {evaluations_octobre.count()}")
            print(f"  • Notes OCTOBRE : {notes_octobre.count()}")
            
            if eleves.count() > 0 and notes_octobre.count() == 0:
                print(f"  ❌ PROBLÈME : Élèves mais pas de notes OCTOBRE")
            elif eleves.count() > 0 and notes_octobre.count() > 0:
                print(f"  ✅ OK : Élèves et notes présentes")
            else:
                print(f"  ⚠️  INFO : Pas d'élèves ou pas de notes")
        
        # 3. Générer le script de correction
        print(f"\n🔧 GÉNÉRATION SCRIPT DE CORRECTION :")
        
        correction_script = """#!/usr/bin/env python
# Script de correction automatique du mapping des classes

import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ecole_moderne.settings')
django.setup()

def corriger_mapping_classes():
    from notes.models import ClasseNote, MatiereNote, Evaluation, NoteEleve
    from eleves.models import Eleve, Classe as ClasseEleve
    
    print("🔧 CORRECTION MAPPING CLASSES")
    
"""
        
        # Ajouter les mappings corrects
        correction_script += "    # Mapping des classes\n"
        for cn_id, ce_id in mapping_dict.items():
            cn = ClasseNote.objects.get(id=cn_id)
            correction_script += f"    # {cn.nom} : ClasseNote ID {cn_id} -> ClasseEleve ID {ce_id}\n"
        
        correction_script += """
    
    # Pour chaque classe problématique, créer les notes manquantes
    classes_a_corriger = [
"""
        
        for cn_id in mapping_dict.keys():
            cn = ClasseNote.objects.get(id=cn_id)
            correction_script += f"        {cn_id},  # {cn.nom}\n"
        
        correction_script += """    ]
    
    for classe_id in classes_a_corriger:
        print(f"\\n📚 Correction classe ID {classe_id}")
        
        # Utiliser le script de correction existant
        from corriger_classement_classe_specifique import corriger_classement_classe_specifique
        corriger_classement_classe_specifique(classe_id=classe_id)

if __name__ == "__main__":
    corriger_mapping_classes()
"""
        
        # Sauvegarder le script
        with open('corriger_mapping_classes_serveur.py', 'w', encoding='utf-8') as f:
            f.write(correction_script)
        
        print(f"  ✅ Script créé : corriger_mapping_classes_serveur.py")
        
        # 4. Instructions
        print(f"\n🚀 INSTRUCTIONS SERVEUR :")
        print(f"  1. Mettre à jour le code : git pull origin main")
        print(f"  2. Exécuter le diagnostic : python diagnostiquer_mapping_classes.py")
        print(f"  3. Corriger le mapping : python corriger_mapping_classes_serveur.py")
        print(f"  4. Redémarrer le serveur : touch ecole_moderne/wsgi.py")
        print(f"  5. Tester l'export PDF")
        
        return True
        
    except Exception as e:
        print(f"❌ Erreur : {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    diagnostiquer_mapping_classes()
