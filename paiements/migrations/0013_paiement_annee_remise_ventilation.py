from datetime import date
from decimal import Decimal, ROUND_HALF_UP

from django.db import migrations, models


ZERO = Decimal('0')


def _annee_scolaire(value):
    debut = value.year if value.month >= 9 else value.year - 1
    return f'{debut}-{debut + 1}'


def _repartir(total, bases, numeros):
    resultat = {1: ZERO, 2: ZERO, 3: ZERO}
    total = max(ZERO, Decimal(str(total or 0)))
    capacites = {
        numero: max(ZERO, Decimal(str(bases.get(numero, 0) or 0)))
        for numero in numeros
    }
    total_base = sum(capacites.values(), ZERO)
    if total <= 0:
        return resultat
    if total_base <= 0:
        capacites = {numero: Decimal('1') for numero in numeros}
        total_base = Decimal(len(numeros))

    restant = total
    for index, numero in enumerate(numeros):
        if index == len(numeros) - 1:
            part = restant
        else:
            part = (total * capacites[numero] / total_base).quantize(
                Decimal('1'), rounding=ROUND_HALF_UP
            )
            part = min(restant, max(ZERO, part))
        resultat[numero] = part
        restant -= part
    return resultat


def renseigner_annees_et_ventilations(apps, schema_editor):
    Paiement = apps.get_model('paiements', 'Paiement')
    PaiementRemise = apps.get_model('paiements', 'PaiementRemise')
    EcheancierPaiement = apps.get_model('paiements', 'EcheancierPaiement')

    for paiement in Paiement.objects.filter(annee_scolaire='').iterator():
        valeur = paiement.date_paiement or date.today()
        paiement.annee_scolaire = _annee_scolaire(valeur)
        paiement.save(update_fields=['annee_scolaire'])

    for lien in PaiementRemise.objects.select_related('paiement').iterator():
        numeros = [
            numero
            for numero, applique in (
                (1, lien.applique_tranche_1),
                (2, lien.applique_tranche_2),
                (3, lien.applique_tranche_3),
            )
            if applique
        ]
        # Avant l'ajout de la portée, toutes les remises visaient la
        # scolarité globale. On les reprend sur T1+T2+T3, jamais l'admission.
        if not numeros:
            numeros = [1, 2, 3]
            lien.applique_tranche_1 = True
            lien.applique_tranche_2 = True
            lien.applique_tranche_3 = True

        echeancier = EcheancierPaiement.objects.filter(
            eleve_id=lien.paiement.eleve_id,
            annee_scolaire=lien.paiement.annee_scolaire,
        ).first()
        bases = {1: ZERO, 2: ZERO, 3: ZERO}
        if echeancier:
            bases = {
                1: echeancier.tranche_1_due,
                2: echeancier.tranche_2_due,
                3: echeancier.tranche_3_due,
            }
        ventilation = _repartir(lien.montant_remise, bases, numeros)
        lien.montant_tranche_1 = ventilation[1]
        lien.montant_tranche_2 = ventilation[2]
        lien.montant_tranche_3 = ventilation[3]
        lien.save(update_fields=[
            'applique_tranche_1', 'applique_tranche_2', 'applique_tranche_3',
            'montant_tranche_1', 'montant_tranche_2', 'montant_tranche_3',
        ])


class Migration(migrations.Migration):

    dependencies = [
        ('paiements', '0012_paiementremise_motif'),
    ]

    operations = [
        migrations.AddField(
            model_name='paiement',
            name='annee_scolaire',
            field=models.CharField(
                blank=True,
                db_index=True,
                default='',
                help_text='Année comptable à laquelle ce paiement doit être affecté.',
                max_length=9,
                verbose_name='Année scolaire',
            ),
        ),
        migrations.AddField(
            model_name='paiementremise',
            name='montant_tranche_1',
            field=models.DecimalField(
                decimal_places=0,
                default=Decimal('0'),
                max_digits=12,
                verbose_name='Remise affectée à la 1ère tranche (GNF)',
            ),
        ),
        migrations.AddField(
            model_name='paiementremise',
            name='montant_tranche_2',
            field=models.DecimalField(
                decimal_places=0,
                default=Decimal('0'),
                max_digits=12,
                verbose_name='Remise affectée à la 2ème tranche (GNF)',
            ),
        ),
        migrations.AddField(
            model_name='paiementremise',
            name='montant_tranche_3',
            field=models.DecimalField(
                decimal_places=0,
                default=Decimal('0'),
                max_digits=12,
                verbose_name='Remise affectée à la 3ème tranche (GNF)',
            ),
        ),
        migrations.RunPython(
            renseigner_annees_et_ventilations,
            migrations.RunPython.noop,
        ),
    ]
