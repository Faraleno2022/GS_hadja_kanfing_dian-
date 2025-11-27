#!/usr/bin/env python
"""
Diagnostic corrigé du mapping des classes (sans classe_note)
"""

import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ecole_moderne.settings')
django.setup()

def diagnostiquer_mapping_classes_corrige():
    """Diagnostic corrigé du mapping des classes"""
    
    try:
        from notes.models import ClasseNote, MatiereNote, Evaluation, NoteEleve
        from eleves.models import Classe as ClasseEleve
        from eleves.models import Eleve
        
        print("🔧 DIAGNOSTIC MAPPING CLASSES - VERSION CORRIGÉE")
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
            
            # Vérifier les notes pour OCTOBRE (méthode corrigée)
            # Chercher les évaluations par matière et période
            matieres = MatiereNote.objects.filter(classe=cn, actif=True)
            
            total_evaluations = 0
            total_notes = 0
            
            for matiere in matieres:
                # Chercher les évaluations pour cette matière et période
                evaluations_octobre = Evaluation.objects.filter(
                    matiere=matiere,
                    periode='OCTOBRE'
                )
                total_evaluations += evaluations_octobre.count()
                
                # Compter les notes pour ces évaluations
                notes_octobre = NoteEleve.objects.filter(
                    evaluation__in=evaluations_octobre
                )
                total_notes += notes_octobre.count()
            
            print(f"  • Évaluations OCTOBRE : {total_evaluations}")
            print(f"  • Notes OCTOBRE : {total_notes}")
            
            if eleves.count() > 0 and total_notes == 0:
                print(f"  ❌ PROBLÈME : Élèves mais pas de notes OCTOBRE")
            elif eleves.count() > 0 and total_notes > 0:
                print(f"  ✅ OK : Élèves et notes présentes")
            else:
                print(f"  ⚠️  INFO : Pas d'élèves ou pas de notes")
        
        # 3. Identifier les classes problématiques pour le PDF
        print(f"\n🎯 CLASSES PROBLÉMATIQUES POUR PDF :")
        
        classes_problematiques = []
        
        for cn_id, ce_id in mapping_dict.items():
            cn = ClasseNote.objects.get(id=cn_id)
            ce = ClasseEleve.objects.get(id=ce_id)
            
            eleves = Eleve.objects.filter(classe=ce, statut='ACTIF')
            
            # Vérifier les notes
            matieres = MatiereNote.objects.filter(classe=cn, actif=True)
            total_notes = 0
            
            for matiere in matieres:
                evaluations_octobre = Evaluation.objects.filter(
                    matiere=matiere,
                    periode='OCTOBRE'
                )
                notes_octobre = NoteEleve.objects.filter(
                    evaluation__in=evaluations_octobre
                )
                total_notes += notes_octobre.count()
            
            # Si des élèves mais pas assez de notes
            if eleves.count() > 0 and total_notes < (eleves.count() * matieres.count() * 0.5):  # Moins de 50% des notes attendues
                classes_problematiques.append({
                    'classe_note': cn,
                    'classe_eleve': ce,
                    'eleves_count': eleves.count(),
                    'notes_count': total_notes,
                    'matieres_count': matieres.count()
                })
        
        if classes_problematiques:
            print(f"  ❌ Classes avec problème de notes :")
            for cp in classes_problematiques:
                print(f"    • {cp['classe_note'].nom} (ID: {cp['classe_note'].id})")
                print(f"      Élèves: {cp['eleves_count']}, Notes: {cp['notes_count']}, Matières: {cp['matieres_count']}")
        else:
            print(f"  ✅ Toutes les classes ont des notes suffisantes")
        
        # 4. Générer le script de correction
        print(f"\n🔧 GÉNÉRATION SCRIPT DE CORRECTION :")
        
        correction_script = """#!/usr/bin/env python
# Script de correction automatique des classes problématiques

import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ecole_moderne.settings')
django.setup()

def corriger_classes_problematiques():
    from notes.models import ClasseNote, MatiereNote, Evaluation, NoteEleve
    from eleves.models import Eleve, Classe as ClasseEleve
    
    print("🔧 CORRECTION CLASSES PROBLÉMATIQUES")
    
"""
        
        # Ajouter les classes problématiques
        if classes_problematiques:
            correction_script += "    # Classes à corriger\n"
            for cp in classes_problematiques:
                cn = cp['classe_note']
                correction_script += f"    # {cn.nom} (ID: {cn.id}) - {cp['eleves_count']} élèves, {cp['notes_count']} notes\n"
        
        correction_script += """
    
    # Classes spécifiques mentionnées par l'utilisateur
    classes_specifiques = [
        4,  # 11 SÉRIE LITTÉRAIRE
        5,  # 11 SÉRIE SCIENTIFIQUE
        7,  # 12 SÉRIE LITTÉRAIRE
        6,  # 12 SÉRIE SCIENTIFIQUE
    ]
    
    for classe_id in classes_specifiques:
        print(f"\\n📚 Correction classe ID {classe_id}")
        
        try:
            from corriger_classement_classe_specifique import corriger_classement_classe_specifique
            corriger_classement_classe_specifique(classe_id=classe_id)
            print(f"  ✅ Classe {classe_id} corrigée")
        except Exception as e:
            print(f"  ❌ Erreur classe {classe_id}: {str(e)}")

if __name__ == "__main__":
    corriger_classes_problematiques()
"""
        
        # Sauvegarder le script
        with open('corriger_classes_serveur.py', 'w', encoding='utf-8') as f:
            f.write(correction_script)
        
        print(f"  ✅ Script créé : corriger_classes_serveur.py")
        
        # 5. Instructions
        print(f"\n🚀 INSTRUCTIONS SERVEUR :")
        print(f"  1. Mettre à jour le code : git pull origin main")
        print(f"  2. Exécuter le diagnostic : python diagnostiquer_mapping_classes_corrige.py")
        print(f"  3. Corriger les classes : python corriger_classes_serveur.py")
        print(f"  4. Redémarrer le serveur : touch ecole_moderne/wsgi.py")
        print(f"  5. Tester l'export PDF avec l'URL -pdf-fix")
        
        print(f"\n🌟 URLS DE TEST :")
        print(f"  • 11 SÉRIE LITTÉRAIRE : /notes/exporter-classement-pdf-fix/?classe_id=4&matiere_id=41&periode=OCTOBRE")
        print(f"  • 11 SÉRIE SCIENTIFIQUE : /notes/exporter-classement-pdf-fix/?classe_id=5&matiere_id=XX&periode=OCTOBRE")
        print(f"  • 12 SÉRIE LITTÉRAIRE : /notes/exporter-classement-pdf-fix/?classe_id=7&matiere_id=69&periode=OCTOBRE")
        
        return True
        
    except Exception as e:
        print(f"❌ Erreur : {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    diagnostiquer_mapping_classes_corrige()
