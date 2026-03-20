from django.db import migrations

class Migration(migrations.Migration):

    dependencies = [
        ("paiements", "0006_echeancierpaiement_paiements_e_annee_s_aa73e4_idx_and_more"),
    ]

    operations = [
        migrations.RunSQL(
            sql="""
            ALTER TABLE paiements_echeancierpaiement
                ADD COLUMN IF NOT EXISTS frais_inscription_du decimal(10,0) NOT NULL DEFAULT 0,
                ADD COLUMN IF NOT EXISTS tranche_1_due decimal(10,0) NOT NULL DEFAULT 0,
                ADD COLUMN IF NOT EXISTS tranche_2_due decimal(10,0) NOT NULL DEFAULT 0,
                ADD COLUMN IF NOT EXISTS tranche_3_due decimal(10,0) NOT NULL DEFAULT 0,
                ADD COLUMN IF NOT EXISTS frais_inscription_paye decimal(10,0) NOT NULL DEFAULT 0,
                ADD COLUMN IF NOT EXISTS tranche_1_payee decimal(10,0) NOT NULL DEFAULT 0,
                ADD COLUMN IF NOT EXISTS tranche_2_payee decimal(10,0) NOT NULL DEFAULT 0,
                ADD COLUMN IF NOT EXISTS tranche_3_payee decimal(10,0) NOT NULL DEFAULT 0,
                ADD COLUMN IF NOT EXISTS date_echeance_inscription date NULL,
                ADD COLUMN IF NOT EXISTS date_echeance_tranche_1 date NULL,
                ADD COLUMN IF NOT EXISTS date_echeance_tranche_2 date NULL,
                ADD COLUMN IF NOT EXISTS date_echeance_tranche_3 date NULL
            """,
            reverse_sql=migrations.RunSQL.noop,
        ),
    ]
