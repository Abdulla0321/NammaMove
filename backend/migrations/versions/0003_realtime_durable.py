"""Additive private synthetic ingestion evidence and restart watermarks.

No existing data, roles, credentials or active datasets are changed. Downgrade
removes ONLY the two new tables, including their synthetic evidence/checkpoints.
"""

import sqlalchemy as sa
from alembic import op

revision = "0003_realtime_durable"
down_revision = "0002_transit_data"
branch_labels = None
depends_on = None

TABLES = ("ingestion_sources", "ingestion_generations")


def upgrade():
    op.create_table(
        "ingestion_sources",
        sa.Column("id", sa.String(100), primary_key=True),
        sa.Column("dataset_id", sa.Uuid(), nullable=False),
        sa.Column("binding_digest", sa.String(64), nullable=False),
        sa.Column("data_mode", sa.String(10), nullable=False),
        sa.Column("evidence_seconds", sa.Integer(), nullable=False),
        sa.Column("max_generations", sa.Integer(), nullable=False),
        sa.Column("header_at", sa.DateTime(timezone=True)),
        sa.Column("fingerprint", sa.String(64)),
        sa.Column("received_at", sa.DateTime(timezone=True)),
        sa.Column("checkpoint", sa.Text()),
        sa.Column("checkpoint_digest", sa.String(64)),
        sa.Column("guards_digest", sa.String(64)),
        sa.ForeignKeyConstraint(
            ["dataset_id"], ["nammamove.transit_datasets.id"], ondelete="RESTRICT"
        ),
        sa.CheckConstraint("data_mode = 'simulation'", name="ingestion_source_simulation"),
        sa.CheckConstraint(
            "evidence_seconds BETWEEN 900 AND 86400 AND max_generations BETWEEN 1 AND 1000",
            name="ingestion_source_bounds",
        ),
        sa.CheckConstraint(
            "(header_at IS NULL AND fingerprint IS NULL AND received_at IS NULL AND checkpoint IS NULL AND checkpoint_digest IS NULL AND guards_digest IS NULL) OR (header_at IS NOT NULL AND fingerprint IS NOT NULL AND received_at IS NOT NULL AND received_at >= header_at AND checkpoint IS NOT NULL AND checkpoint_digest IS NOT NULL AND guards_digest IS NOT NULL)",
            name="ingestion_watermark_complete",
        ),
        sa.CheckConstraint("length(checkpoint) <= 4194304", name="ingestion_checkpoint_bound"),
        schema="nammamove",
    )
    op.create_table(
        "ingestion_generations",
        sa.Column("source_id", sa.String(100), primary_key=True),
        sa.Column("identity", sa.String(64), primary_key=True),
        sa.Column("fingerprint", sa.String(64), nullable=False),
        sa.Column("outcome", sa.String(20), nullable=False),
        sa.Column("header_at", sa.DateTime(timezone=True)),
        sa.Column("received_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("data_mode", sa.String(10), nullable=False),
        sa.Column("guards_digest", sa.String(64)),
        sa.ForeignKeyConstraint(
            ["source_id"], ["nammamove.ingestion_sources.id"], ondelete="RESTRICT"
        ),
        sa.CheckConstraint("data_mode = 'simulation'", name="ingestion_generation_simulation"),
        sa.CheckConstraint("expires_at > received_at", name="ingestion_evidence_expiry"),
        sa.CheckConstraint(
            "(outcome = 'accepted' AND guards_digest IS NOT NULL) OR (outcome <> 'accepted' AND guards_digest IS NULL)",
            name="ingestion_accepted_guards",
        ),
        sa.CheckConstraint(
            "outcome IN ('accepted','rejected','out_of_order','conflict','quarantined','capacity')",
            name="ingestion_generation_outcome",
        ),
        schema="nammamove",
    )
    op.create_index(
        "ix_ingestion_generations_expires_at",
        "ingestion_generations",
        ["expires_at"],
        schema="nammamove",
    )
    # Membership in a provisioned NOLOGIN group, never JWT/request metadata.
    member = "EXISTS (SELECT 1 FROM pg_roles r WHERE r.rolname = 'nammamove_ingestion' AND pg_has_role(current_user, r.oid, 'member'))"
    for table in TABLES:
        op.execute(f"ALTER TABLE nammamove.{table} ENABLE ROW LEVEL SECURITY")
        op.execute(f"REVOKE ALL ON nammamove.{table} FROM PUBLIC")
        op.execute(f"CREATE POLICY ingestion_read ON nammamove.{table} FOR SELECT USING ({member})")
        command = "UPDATE" if table == "ingestion_sources" else "INSERT"
        clause = (
            f"USING ({member}) WITH CHECK ({member})"
            if command == "UPDATE"
            else f"WITH CHECK ({member})"
        )
        op.execute(f"CREATE POLICY ingestion_write ON nammamove.{table} FOR {command} {clause}")
        op.execute(
            f"DO $$ BEGIN IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname='nammamove_api') THEN REVOKE ALL ON nammamove.{table} FROM nammamove_api; END IF; END $$"
        )


def downgrade():
    op.drop_index(
        "ix_ingestion_generations_expires_at",
        table_name="ingestion_generations",
        schema="nammamove",
    )
    op.drop_table("ingestion_generations", schema="nammamove")
    op.drop_table("ingestion_sources", schema="nammamove")
