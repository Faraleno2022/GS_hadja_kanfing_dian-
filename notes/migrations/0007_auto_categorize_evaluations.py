from django.db import migrations

def categorize_from_title(apps, schema_editor):
    Evaluation = apps.get_model('notes', 'Evaluation')
    # Mettre COMPOSITION si le titre contient 'composition' (insensible à la casse), sinon COURS
    qs = Evaluation.objects.all()
    for ev in qs.iterator():
        title = (getattr(ev, 'titre', '') or '').lower()
        if 'composition' in title or 'compostion' in title or 'compo' in title or 'exam' in title:
            new_cat = 'COMPOSITION'
        else:
            new_cat = 'COURS'
        if getattr(ev, 'categorie', None) != new_cat:
            ev.categorie = new_cat
            ev.save(update_fields=['categorie'])

def reverse_noop(apps, schema_editor):
    # Pas de rollback fiable
    pass

class Migration(migrations.Migration):

    dependencies = [
        ('notes', '0006_evaluation_categorie_and_more'),
    ]

    operations = [
        migrations.RunPython(categorize_from_title, reverse_noop),
    ]
