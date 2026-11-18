"""Source-scoped non-owner workers; no roles, credentials or bindings created."""

import sqlalchemy as sa
from alembic import op

revision = "0004_ingestion_scope"
down_revision = "0003_realtime_durable"
branch_labels = None
depends_on = None

CATALOG = (
    "transit_feeds",
    "transit_datasets",
    "gtfs_agencies",
    "gtfs_calendar_dates",
    "gtfs_frequencies",
    "gtfs_routes",
    "gtfs_services",
    "gtfs_shape_points",
    "gtfs_shapes",
    "gtfs_stop_times",
    "gtfs_stops",
    "gtfs_transfers",
    "gtfs_trips",
)
MEMBER = "EXISTS (SELECT 1 FROM pg_roles r WHERE r.rolname='nammamove_ingestion' AND pg_has_role(current_user,r.oid,'member'))"


def upgrade():
    op.create_table(
        "ingestion_workers",
        sa.Column("worker_name", sa.String(63), primary_key=True),
        sa.Column("source_id", sa.String(100), primary_key=True),
        sa.ForeignKeyConstraint(
            ["source_id"], ["nammamove.ingestion_sources.id"], ondelete="RESTRICT"
        ),
        schema="nammamove",
    )
    op.execute("ALTER TABLE nammamove.ingestion_workers ENABLE ROW LEVEL SECURITY")
    op.execute("REVOKE ALL ON nammamove.ingestion_workers FROM PUBLIC")
    op.execute(
        "CREATE POLICY worker_self ON nammamove.ingestion_workers FOR SELECT USING (worker_name = current_user)"
    )
    # Owner-executed barrier view avoids granting API access to private source
    # tables just to evaluate catalog policies. current_user remains the invoker
    # in a view (unlike SECURITY DEFINER functions). No caller-supplied identity.
    op.execute(
        "CREATE VIEW nammamove.ingestion_worker_scope WITH (security_barrier=true) AS SELECT w.source_id,s.dataset_id,d.feed_id FROM nammamove.ingestion_workers w JOIN nammamove.ingestion_sources s ON s.id=w.source_id JOIN nammamove.transit_datasets d ON d.id=s.dataset_id WHERE w.worker_name=current_user"
    )
    op.execute("GRANT SELECT ON nammamove.ingestion_worker_scope TO PUBLIC")
    for table, column in (("ingestion_sources", "id"), ("ingestion_generations", "source_id")):
        scope = f"{column} IN (SELECT source_id FROM nammamove.ingestion_worker_scope)"
        op.execute(
            f"CREATE POLICY worker_scope ON nammamove.{table} AS RESTRICTIVE FOR ALL USING ({scope}) WITH CHECK ({scope})"
        )
    op.execute(
        f"CREATE POLICY ingestion_delete ON nammamove.ingestion_generations FOR DELETE USING (({MEMBER}) AND expires_at <= statement_timestamp())"
    )
    for table in CATALOG:
        if table == "transit_feeds":
            scope = "id IN (SELECT feed_id FROM nammamove.ingestion_worker_scope)"
        elif table == "transit_datasets":
            scope = "id IN (SELECT dataset_id FROM nammamove.ingestion_worker_scope)"
        else:
            scope = "dataset_id IN (SELECT dataset_id FROM nammamove.ingestion_worker_scope)"
        # Restrictive policies intersect ALL permissive policies, including catalog_read.
        op.execute(
            f"CREATE POLICY worker_catalog_scope ON nammamove.{table} AS RESTRICTIVE FOR SELECT USING (NOT ({MEMBER}) OR ({scope}))"
        )
        op.execute(
            f"CREATE POLICY worker_catalog_read ON nammamove.{table} FOR SELECT USING (({MEMBER}) AND ({scope}))"
        )
    op.execute(
        "DO $$ BEGIN IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname='nammamove_api') THEN REVOKE ALL ON nammamove.ingestion_workers FROM nammamove_api; END IF; END $$"
    )


def downgrade():
    for table in CATALOG:
        op.execute(f"DROP POLICY worker_catalog_read ON nammamove.{table}")
        op.execute(f"DROP POLICY worker_catalog_scope ON nammamove.{table}")
    op.execute("DROP POLICY ingestion_delete ON nammamove.ingestion_generations")
    for table in ("ingestion_sources", "ingestion_generations"):
        op.execute(f"DROP POLICY worker_scope ON nammamove.{table}")
    op.execute("DROP VIEW nammamove.ingestion_worker_scope")
    op.drop_table("ingestion_workers", schema="nammamove")
