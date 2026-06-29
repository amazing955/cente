from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('inventory', '0012_alter_applicationsetting_id_alter_auditlog_id_and_more'),
    ]

    operations = [
        migrations.RunSQL(
            sql="""
            DO $$
            DECLARE r record;
            BEGIN
                FOR r IN
                    SELECT conrelid::regclass AS table_name, conname
                    FROM pg_constraint
                    WHERE contype = 'f' AND confrelid = 'inventory_applicationsetting'::regclass
                LOOP
                    EXECUTE format('ALTER TABLE %I DROP CONSTRAINT %I', r.table_name, r.conname);
                END LOOP;
            END $$;
            ALTER TABLE inventory_applicationsetting ALTER COLUMN id DROP IDENTITY IF EXISTS;
            ALTER TABLE inventory_applicationsetting ALTER COLUMN id DROP DEFAULT;
            ALTER TABLE inventory_applicationsetting ALTER COLUMN id TYPE uuid USING (CASE WHEN id::text ~ '-' THEN id::text ELSE lpad(to_hex((id::text)::bigint), 32, '0') END::uuid);
            """,
        ),
        migrations.RunSQL(
            sql="""
            ALTER TABLE inventory_auditlog ALTER COLUMN id DROP IDENTITY IF EXISTS;
            ALTER TABLE inventory_auditlog ALTER COLUMN id DROP DEFAULT;
            ALTER TABLE inventory_auditlog ALTER COLUMN id TYPE uuid USING (CASE WHEN id::text ~ '-' THEN id::text ELSE lpad(to_hex((id::text)::bigint), 32, '0') END::uuid);
            """,
        ),
        migrations.RunSQL(
            sql="""
            DO $$
            DECLARE r record;
            BEGIN
                FOR r IN
                    SELECT conrelid::regclass AS table_name, conname
                    FROM pg_constraint
                    WHERE contype = 'f' AND confrelid = 'inventory_customuser'::regclass
                LOOP
                    EXECUTE format('ALTER TABLE %I DROP CONSTRAINT %I', r.table_name, r.conname);
                END LOOP;
            END $$;
            ALTER TABLE inventory_customuser ALTER COLUMN id DROP IDENTITY IF EXISTS;
            ALTER TABLE inventory_customuser ALTER COLUMN id DROP DEFAULT;
            ALTER TABLE inventory_customuser ALTER COLUMN id TYPE uuid USING (CASE WHEN id::text ~ '-' THEN id::text ELSE lpad(to_hex((id::text)::bigint), 32, '0') END::uuid);
            ALTER TABLE django_admin_log ALTER COLUMN user_id TYPE uuid USING (CASE WHEN user_id::text ~ '-' THEN user_id::text ELSE lpad(to_hex((user_id::text)::bigint), 32, '0') END::uuid);
            ALTER TABLE inventory_auditlog ALTER COLUMN user_id TYPE uuid USING (CASE WHEN user_id::text ~ '-' THEN user_id::text ELSE lpad(to_hex((user_id::text)::bigint), 32, '0') END::uuid);
            ALTER TABLE inventory_monthlyreport ALTER COLUMN generated_by_id TYPE uuid USING (CASE WHEN generated_by_id::text ~ '-' THEN generated_by_id::text ELSE lpad(to_hex((generated_by_id::text)::bigint), 32, '0') END::uuid);
            ALTER TABLE inventory_reconciliation ALTER COLUMN performed_by_id TYPE uuid USING (CASE WHEN performed_by_id::text ~ '-' THEN performed_by_id::text ELSE lpad(to_hex((performed_by_id::text)::bigint), 32, '0') END::uuid);
            ALTER TABLE inventory_reconciliation ALTER COLUMN approved_by_id TYPE uuid USING (CASE WHEN approved_by_id::text ~ '-' THEN approved_by_id::text ELSE lpad(to_hex((approved_by_id::text)::bigint), 32, '0') END::uuid);
            ALTER TABLE inventory_reconciliation ALTER COLUMN reviewed_by_id TYPE uuid USING (CASE WHEN reviewed_by_id::text ~ '-' THEN reviewed_by_id::text ELSE lpad(to_hex((reviewed_by_id::text)::bigint), 32, '0') END::uuid);
            ALTER TABLE inventory_shipment ALTER COLUMN approved_by_id TYPE uuid USING (CASE WHEN approved_by_id::text ~ '-' THEN approved_by_id::text ELSE lpad(to_hex((approved_by_id::text)::bigint), 32, '0') END::uuid);
            ALTER TABLE inventory_shipment ALTER COLUMN created_by_id TYPE uuid USING (CASE WHEN created_by_id::text ~ '-' THEN created_by_id::text ELSE lpad(to_hex((created_by_id::text)::bigint), 32, '0') END::uuid);
            ALTER TABLE inventory_shipment ALTER COLUMN last_updated_by_id TYPE uuid USING (CASE WHEN last_updated_by_id::text ~ '-' THEN last_updated_by_id::text ELSE lpad(to_hex((last_updated_by_id::text)::bigint), 32, '0') END::uuid);
            ALTER TABLE inventory_customuser_groups ALTER COLUMN customuser_id TYPE uuid USING (CASE WHEN customuser_id::text ~ '-' THEN customuser_id::text ELSE lpad(to_hex((customuser_id::text)::bigint), 32, '0') END::uuid);
            ALTER TABLE inventory_customuser_user_permissions ALTER COLUMN customuser_id TYPE uuid USING (CASE WHEN customuser_id::text ~ '-' THEN customuser_id::text ELSE lpad(to_hex((customuser_id::text)::bigint), 32, '0') END::uuid);
            """,
        ),
        migrations.RunSQL(
            sql="""
            ALTER TABLE inventory_monthlyreport ALTER COLUMN id DROP IDENTITY IF EXISTS;
            ALTER TABLE inventory_monthlyreport ALTER COLUMN id DROP DEFAULT;
            ALTER TABLE inventory_monthlyreport ALTER COLUMN id TYPE uuid USING (CASE WHEN id::text ~ '-' THEN id::text ELSE lpad(to_hex((id::text)::bigint), 32, '0') END::uuid);
            """,
        ),
        migrations.RunSQL(
            sql="""
            DO $$
            DECLARE r record;
            BEGIN
                FOR r IN
                    SELECT conrelid::regclass AS table_name, conname
                    FROM pg_constraint
                    WHERE contype = 'f' AND confrelid = 'inventory_reconciliation'::regclass
                LOOP
                    EXECUTE format('ALTER TABLE %I DROP CONSTRAINT %I', r.table_name, r.conname);
                END LOOP;
            END $$;
            ALTER TABLE inventory_reconciliation ALTER COLUMN id DROP IDENTITY IF EXISTS;
            ALTER TABLE inventory_reconciliation ALTER COLUMN id DROP DEFAULT;
            ALTER TABLE inventory_reconciliation ALTER COLUMN id TYPE uuid USING (CASE WHEN id::text ~ '-' THEN id::text ELSE lpad(to_hex((id::text)::bigint), 32, '0') END::uuid);
            ALTER TABLE inventory_reconciliationresult ALTER COLUMN reconciliation_id TYPE uuid USING (CASE WHEN reconciliation_id::text ~ '-' THEN reconciliation_id::text ELSE lpad(to_hex((reconciliation_id::text)::bigint), 32, '0') END::uuid);
            """,
        ),
        migrations.RunSQL(
            sql="""
            DO $$
            DECLARE r record;
            BEGIN
                FOR r IN
                    SELECT conrelid::regclass AS table_name, conname
                    FROM pg_constraint
                    WHERE contype = 'f' AND confrelid = 'inventory_reconciliationresult'::regclass
                LOOP
                    EXECUTE format('ALTER TABLE %I DROP CONSTRAINT %I', r.table_name, r.conname);
                END LOOP;
            END $$;
            ALTER TABLE inventory_reconciliationresult ALTER COLUMN id DROP IDENTITY IF EXISTS;
            ALTER TABLE inventory_reconciliationresult ALTER COLUMN id DROP DEFAULT;
            ALTER TABLE inventory_reconciliationresult ALTER COLUMN id TYPE uuid USING (CASE WHEN id::text ~ '-' THEN id::text ELSE lpad(to_hex((id::text)::bigint), 32, '0') END::uuid);
            """,
        ),
        migrations.RunSQL(
            sql="""
            ALTER TABLE inventory_reporttemplate ALTER COLUMN id DROP IDENTITY IF EXISTS;
            ALTER TABLE inventory_reporttemplate ALTER COLUMN id DROP DEFAULT;
            ALTER TABLE inventory_reporttemplate ALTER COLUMN id TYPE uuid USING (CASE WHEN id::text ~ '-' THEN id::text ELSE lpad(to_hex((id::text)::bigint), 32, '0') END::uuid);
            """,
        ),
        migrations.RunSQL(
            sql="""
            ALTER TABLE inventory_roletemplate ALTER COLUMN id DROP IDENTITY IF EXISTS;
            ALTER TABLE inventory_roletemplate ALTER COLUMN id DROP DEFAULT;
            ALTER TABLE inventory_roletemplate ALTER COLUMN id TYPE uuid USING (CASE WHEN id::text ~ '-' THEN id::text ELSE lpad(to_hex((id::text)::bigint), 32, '0') END::uuid);
            """,
        ),
        migrations.RunSQL(
            sql="""
            DO $$
            DECLARE r record;
            BEGIN
                FOR r IN
                    SELECT conrelid::regclass AS table_name, conname
                    FROM pg_constraint
                    WHERE contype = 'f' AND confrelid = 'inventory_shipment'::regclass
                LOOP
                    EXECUTE format('ALTER TABLE %I DROP CONSTRAINT %I', r.table_name, r.conname);
                END LOOP;
            END $$;
            ALTER TABLE inventory_shipment ALTER COLUMN id DROP IDENTITY IF EXISTS;
            ALTER TABLE inventory_shipment ALTER COLUMN id DROP DEFAULT;
            ALTER TABLE inventory_shipment ALTER COLUMN id TYPE uuid USING (CASE WHEN id::text ~ '-' THEN id::text ELSE lpad(to_hex((id::text)::bigint), 32, '0') END::uuid);
            ALTER TABLE inventory_shipment_tapes ALTER COLUMN shipment_id TYPE uuid USING (CASE WHEN shipment_id::text ~ '-' THEN shipment_id::text ELSE lpad(to_hex((shipment_id::text)::bigint), 32, '0') END::uuid);
            """,
        ),
        migrations.RunSQL(
            sql="""
            DO $$
            DECLARE r record;
            BEGIN
                FOR r IN
                    SELECT conrelid::regclass AS table_name, conname
                    FROM pg_constraint
                    WHERE contype = 'f' AND confrelid = 'inventory_tape'::regclass
                LOOP
                    EXECUTE format('ALTER TABLE %I DROP CONSTRAINT %I', r.table_name, r.conname);
                END LOOP;
            END $$;
            ALTER TABLE inventory_tape ALTER COLUMN id DROP IDENTITY IF EXISTS;
            ALTER TABLE inventory_tape ALTER COLUMN id DROP DEFAULT;
            ALTER TABLE inventory_tape ALTER COLUMN id TYPE uuid USING (CASE WHEN id::text ~ '-' THEN id::text ELSE lpad(to_hex((id::text)::bigint), 32, '0') END::uuid);
            ALTER TABLE inventory_reconciliationresult ALTER COLUMN tape_id TYPE uuid USING (CASE WHEN tape_id::text ~ '-' THEN tape_id::text ELSE lpad(to_hex((tape_id::text)::bigint), 32, '0') END::uuid);
            ALTER TABLE inventory_shipment_tapes ALTER COLUMN tape_id TYPE uuid USING (CASE WHEN tape_id::text ~ '-' THEN tape_id::text ELSE lpad(to_hex((tape_id::text)::bigint), 32, '0') END::uuid);
            """,
        ),
        migrations.RunSQL(
            sql="""
            ALTER TABLE inventory_tapeinventory ALTER COLUMN id DROP IDENTITY IF EXISTS;
            ALTER TABLE inventory_tapeinventory ALTER COLUMN id DROP DEFAULT;
            ALTER TABLE inventory_tapeinventory ALTER COLUMN id TYPE uuid USING (CASE WHEN id::text ~ '-' THEN id::text ELSE lpad(to_hex((id::text)::bigint), 32, '0') END::uuid);
            """,
        ),
    ]


