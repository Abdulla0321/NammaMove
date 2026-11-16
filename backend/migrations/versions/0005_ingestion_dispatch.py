"""Bounded metadata-only synthetic dispatch; no roles, feeds or startup work."""

import sqlalchemy as sa
from alembic import op

revision = "0005_ingestion_dispatch"
down_revision = "0004_ingestion_scope"
branch_labels = None
depends_on = None


def upgrade():
    for column, default in (
        ("dispatch_capacity", "8"),
        ("dispatch_attempts", "3"),
        ("dispatch_lease_seconds", "10"),
    ):
        op.add_column(
            "ingestion_sources",
            sa.Column(column, sa.Integer(), nullable=False, server_default=default),
            schema="nammamove",
        )
    op.create_check_constraint(
        "ingestion_dispatch_bounds",
        "ingestion_sources",
        "dispatch_capacity BETWEEN 1 AND 32 AND dispatch_attempts BETWEEN 1 AND 5 AND dispatch_lease_seconds BETWEEN 1 AND 60",
        schema="nammamove",
    )
    op.create_table(
        "ingestion_dispatch",
        sa.Column("source_id", sa.String(100), primary_key=True),
        sa.Column("identity", sa.String(64), primary_key=True),
        sa.Column("header_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("received_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("binding_digest", sa.String(64), nullable=False),
        sa.Column("guards_digest", sa.String(64), nullable=False),
        sa.Column("data_mode", sa.String(10), nullable=False),
        sa.Column("state", sa.String(12), nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False),
        sa.Column("due_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("token", sa.Uuid()),
        sa.Column("lease_until", sa.DateTime(timezone=True)),
        sa.ForeignKeyConstraint(
            ["source_id"], ["nammamove.ingestion_sources.id"], ondelete="RESTRICT"
        ),
        sa.CheckConstraint("data_mode = 'simulation'", name="dispatch_simulation"),
        sa.CheckConstraint(
            "state IN ('pending','leased','completed','superseded','expired','exhausted','invalid') AND attempts BETWEEN 0 AND 5",
            name="dispatch_state",
        ),
        sa.CheckConstraint(
            "received_at >= header_at AND expires_at > received_at AND expires_at <= received_at + interval '86400 seconds'",
            name="dispatch_expiry",
        ),
        sa.CheckConstraint(
            "(state = 'leased' AND token IS NOT NULL AND lease_until IS NOT NULL) OR (state <> 'leased' AND token IS NULL AND lease_until IS NULL)",
            name="dispatch_lease",
        ),
        schema="nammamove",
    )
    op.execute("ALTER TABLE nammamove.ingestion_dispatch ENABLE ROW LEVEL SECURITY")
    op.execute("REVOKE ALL ON nammamove.ingestion_dispatch FROM PUBLIC")
    member = "EXISTS (SELECT 1 FROM pg_roles r WHERE r.rolname='nammamove_ingestion' AND pg_has_role(current_user,r.oid,'member'))"
    scope = "source_id IN (SELECT source_id FROM nammamove.ingestion_worker_scope)"
    op.execute(
        f"CREATE POLICY dispatch_scope ON nammamove.ingestion_dispatch AS RESTRICTIVE FOR ALL USING ({scope}) WITH CHECK ({scope})"
    )
    for action in ("SELECT", "INSERT", "UPDATE", "DELETE"):
        condition = member + (
            " AND expires_at <= statement_timestamp()" if action == "DELETE" else ""
        )
        clause = f"WITH CHECK ({condition})" if action == "INSERT" else f"USING ({condition})"
        if action == "UPDATE":
            clause += f" WITH CHECK ({condition})"
        op.execute(
            f"CREATE POLICY dispatch_{action.lower()} ON nammamove.ingestion_dispatch FOR {action} {clause}"
        )
    op.execute(
        "DO $$ BEGIN IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname='nammamove_api') THEN REVOKE ALL ON nammamove.ingestion_dispatch FROM nammamove_api; END IF; END $$"
    )


def downgrade():
    op.drop_table("ingestion_dispatch", schema="nammamove")
    op.drop_constraint("ingestion_dispatch_bounds", "ingestion_sources", schema="nammamove")
    for column in ("dispatch_capacity", "dispatch_attempts", "dispatch_lease_seconds"):
        op.drop_column("ingestion_sources", column, schema="nammamove")
