"""Phase 01 immutable schema, spatial index and API identity policies."""

import sqlalchemy as sa
from alembic import op

revision = "0001_phase01"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Extension creation may require an administrator; migration login owns schema.
    op.execute("CREATE EXTENSION IF NOT EXISTS postgis WITH SCHEMA public")
    # Reviewed and frozen initial schema.
    op.create_table(
        "commuters",
        sa.Column("display_name", sa.String(length=80), nullable=False),
        sa.Column("locale", sa.String(length=2), nullable=False),
        sa.Column("location_consent", sa.Boolean(), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("locale IN ('en','kn','hi')", name="commuter_locale"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_commuters")),
        schema="nammamove",
    )
    op.create_index(
        op.f("ix_commuters_created_at"),
        "commuters",
        ["created_at"],
        unique=False,
        schema="nammamove",
    )
    op.create_table(
        "operators",
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("data_mode", sa.String(length=10), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("data_mode IN ('simulation','live')", name="operator_mode"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_operators")),
        sa.UniqueConstraint("name", name=op.f("uq_operators_name")),
        schema="nammamove",
    )
    op.create_index(
        op.f("ix_operators_created_at"),
        "operators",
        ["created_at"],
        unique=False,
        schema="nammamove",
    )
    op.create_table(
        "audit_events",
        sa.Column("actor_id", sa.Uuid(), nullable=True),
        sa.Column("action", sa.String(length=50), nullable=False),
        sa.Column("entity_id", sa.Uuid(), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["actor_id"],
            ["nammamove.commuters.id"],
            name=op.f("fk_audit_events_actor_id_commuters"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_audit_events")),
        schema="nammamove",
    )
    op.create_index(
        op.f("ix_audit_events_actor_id"),
        "audit_events",
        ["actor_id"],
        unique=False,
        schema="nammamove",
    )
    op.create_index(
        op.f("ix_audit_events_created_at"),
        "audit_events",
        ["created_at"],
        unique=False,
        schema="nammamove",
    )
    op.create_table(
        "disruptions",
        sa.Column("reporter_id", sa.Uuid(), nullable=True),
        sa.Column("kind", sa.String(length=30), nullable=False),
        sa.Column("summary", sa.String(length=500), nullable=False),
        sa.Column("data_mode", sa.String(length=10), nullable=False),
        sa.Column("verification", sa.String(length=20), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("data_mode IN ('simulation','live')", name="disruption_mode"),
        sa.CheckConstraint(
            "verification != 'verified' OR (verified_at IS NOT NULL AND expires_at IS NOT NULL AND expires_at > verified_at)",
            name="verification_lifetime",
        ),
        sa.CheckConstraint(
            "verification IN ('unverified','verified','rejected','resolved')",
            name="disruption_verification",
        ),
        sa.CheckConstraint("confidence BETWEEN 0 AND 1", name="disruption_confidence"),
        sa.ForeignKeyConstraint(
            ["reporter_id"],
            ["nammamove.commuters.id"],
            name=op.f("fk_disruptions_reporter_id_commuters"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_disruptions")),
        schema="nammamove",
    )
    op.create_index(
        op.f("ix_disruptions_created_at"),
        "disruptions",
        ["created_at"],
        unique=False,
        schema="nammamove",
    )
    op.create_index(
        op.f("ix_disruptions_expires_at"),
        "disruptions",
        ["expires_at"],
        unique=False,
        schema="nammamove",
    )
    op.create_index(
        op.f("ix_disruptions_reporter_id"),
        "disruptions",
        ["reporter_id"],
        unique=False,
        schema="nammamove",
    )
    op.create_table(
        "feed_snapshots",
        sa.Column("operator_id", sa.Uuid(), nullable=False),
        sa.Column("checksum", sa.String(length=64), nullable=False),
        sa.Column("source", sa.String(length=200), nullable=False),
        sa.Column("license", sa.String(length=200), nullable=False),
        sa.Column("data_mode", sa.String(length=10), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("data_mode IN ('simulation','live')", name="snapshot_mode"),
        sa.ForeignKeyConstraint(
            ["operator_id"],
            ["nammamove.operators.id"],
            name=op.f("fk_feed_snapshots_operator_id_operators"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_feed_snapshots")),
        sa.UniqueConstraint("operator_id", "checksum", name=op.f("uq_feed_snapshots_operator_id")),
        schema="nammamove",
    )
    op.create_index(
        op.f("ix_feed_snapshots_created_at"),
        "feed_snapshots",
        ["created_at"],
        unique=False,
        schema="nammamove",
    )
    op.create_index(
        op.f("ix_feed_snapshots_operator_id"),
        "feed_snapshots",
        ["operator_id"],
        unique=False,
        schema="nammamove",
    )
    op.create_table(
        "journeys",
        sa.Column("commuter_id", sa.Uuid(), nullable=False),
        sa.Column("origin", sa.String(length=160), nullable=False),
        sa.Column("destination", sa.String(length=160), nullable=False),
        sa.Column("data_mode", sa.String(length=10), nullable=False),
        sa.Column("itinerary", sa.JSON(), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("data_mode IN ('simulation','live')", name="journey_mode"),
        sa.ForeignKeyConstraint(
            ["commuter_id"],
            ["nammamove.commuters.id"],
            name=op.f("fk_journeys_commuter_id_commuters"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_journeys")),
        schema="nammamove",
    )
    op.create_index(
        op.f("ix_journeys_commuter_id"),
        "journeys",
        ["commuter_id"],
        unique=False,
        schema="nammamove",
    )
    op.create_index(
        op.f("ix_journeys_created_at"), "journeys", ["created_at"], unique=False, schema="nammamove"
    )
    op.create_table(
        "notifications",
        sa.Column("commuter_id", sa.Uuid(), nullable=False),
        sa.Column("message", sa.String(length=500), nullable=False),
        sa.Column("read_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("data_mode", sa.String(length=10), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("data_mode IN ('simulation','live')", name="notification_mode"),
        sa.ForeignKeyConstraint(
            ["commuter_id"],
            ["nammamove.commuters.id"],
            name=op.f("fk_notifications_commuter_id_commuters"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_notifications")),
        schema="nammamove",
    )
    op.create_index(
        op.f("ix_notifications_commuter_id"),
        "notifications",
        ["commuter_id"],
        unique=False,
        schema="nammamove",
    )
    op.create_index(
        op.f("ix_notifications_created_at"),
        "notifications",
        ["created_at"],
        unique=False,
        schema="nammamove",
    )
    op.create_table(
        "stops",
        sa.Column("operator_id", sa.Uuid(), nullable=False),
        sa.Column("external_id", sa.String(length=100), nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("latitude", sa.Float(), nullable=False),
        sa.Column("longitude", sa.Float(), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "latitude BETWEEN -90 AND 90 AND longitude BETWEEN -180 AND 180",
            name="stop_coordinates",
        ),
        sa.ForeignKeyConstraint(
            ["operator_id"],
            ["nammamove.operators.id"],
            name=op.f("fk_stops_operator_id_operators"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_stops")),
        sa.UniqueConstraint("operator_id", "external_id", name=op.f("uq_stops_operator_id")),
        schema="nammamove",
    )
    op.create_index(
        op.f("ix_stops_created_at"), "stops", ["created_at"], unique=False, schema="nammamove"
    )
    op.create_index(
        op.f("ix_stops_operator_id"), "stops", ["operator_id"], unique=False, schema="nammamove"
    )
    op.create_table(
        "transit_routes",
        sa.Column("operator_id", sa.Uuid(), nullable=False),
        sa.Column("external_id", sa.String(length=100), nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("mode", sa.String(length=20), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("mode IN ('bus','metro','rail','walk')", name="route_mode"),
        sa.ForeignKeyConstraint(
            ["operator_id"],
            ["nammamove.operators.id"],
            name=op.f("fk_transit_routes_operator_id_operators"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_transit_routes")),
        sa.UniqueConstraint(
            "operator_id", "external_id", name=op.f("uq_transit_routes_operator_id")
        ),
        schema="nammamove",
    )
    op.create_index(
        op.f("ix_transit_routes_created_at"),
        "transit_routes",
        ["created_at"],
        unique=False,
        schema="nammamove",
    )
    op.create_index(
        op.f("ix_transit_routes_operator_id"),
        "transit_routes",
        ["operator_id"],
        unique=False,
        schema="nammamove",
    )
    op.create_table(
        "user_preferences",
        sa.Column("commuter_id", sa.Uuid(), nullable=False),
        sa.Column("step_free", sa.Boolean(), nullable=False),
        sa.Column("max_walk_minutes", sa.Integer(), nullable=False),
        sa.CheckConstraint("max_walk_minutes BETWEEN 0 AND 180", name="walk_limit"),
        sa.ForeignKeyConstraint(
            ["commuter_id"],
            ["nammamove.commuters.id"],
            name=op.f("fk_user_preferences_commuter_id_commuters"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("commuter_id", name=op.f("pk_user_preferences")),
        schema="nammamove",
    )
    op.create_table(
        "disruption_evidence",
        sa.Column("disruption_id", sa.Uuid(), nullable=False),
        sa.Column("actor_id", sa.Uuid(), nullable=True),
        sa.Column("source", sa.String(length=200), nullable=False),
        sa.Column("decision", sa.String(length=20), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("decision IN ('verified','rejected')", name="evidence_decision"),
        sa.ForeignKeyConstraint(
            ["actor_id"],
            ["nammamove.commuters.id"],
            name=op.f("fk_disruption_evidence_actor_id_commuters"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["disruption_id"],
            ["nammamove.disruptions.id"],
            name=op.f("fk_disruption_evidence_disruption_id_disruptions"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_disruption_evidence")),
        schema="nammamove",
    )
    op.create_index(
        op.f("ix_disruption_evidence_created_at"),
        "disruption_evidence",
        ["created_at"],
        unique=False,
        schema="nammamove",
    )
    op.create_index(
        op.f("ix_disruption_evidence_disruption_id"),
        "disruption_evidence",
        ["disruption_id"],
        unique=False,
        schema="nammamove",
    )
    op.create_table(
        "trips",
        sa.Column("route_id", sa.Uuid(), nullable=False),
        sa.Column("external_id", sa.String(length=100), nullable=False),
        sa.Column("service_id", sa.String(length=100), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["route_id"],
            ["nammamove.transit_routes.id"],
            name=op.f("fk_trips_route_id_transit_routes"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_trips")),
        sa.UniqueConstraint("route_id", "external_id", name=op.f("uq_trips_route_id")),
        schema="nammamove",
    )
    op.create_index(
        op.f("ix_trips_created_at"), "trips", ["created_at"], unique=False, schema="nammamove"
    )
    op.create_index(
        op.f("ix_trips_route_id"), "trips", ["route_id"], unique=False, schema="nammamove"
    )
    op.create_table(
        "stop_times",
        sa.Column("trip_id", sa.Uuid(), nullable=False),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("stop_id", sa.Uuid(), nullable=False),
        sa.Column("arrival_seconds", sa.Integer(), nullable=False),
        sa.Column("departure_seconds", sa.Integer(), nullable=False),
        sa.CheckConstraint(
            "sequence >= 0 AND arrival_seconds >= 0 AND departure_seconds >= arrival_seconds",
            name="stop_time_order",
        ),
        sa.ForeignKeyConstraint(
            ["stop_id"],
            ["nammamove.stops.id"],
            name=op.f("fk_stop_times_stop_id_stops"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["trip_id"],
            ["nammamove.trips.id"],
            name=op.f("fk_stop_times_trip_id_trips"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("trip_id", "sequence", name=op.f("pk_stop_times")),
        schema="nammamove",
    )
    op.create_index(
        op.f("ix_stop_times_stop_id"), "stop_times", ["stop_id"], unique=False, schema="nammamove"
    )
    op.create_table(
        "vehicles",
        sa.Column("operator_id", sa.Uuid(), nullable=False),
        sa.Column("external_id", sa.String(length=100), nullable=False),
        sa.Column("capacity", sa.Integer(), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("feed_status", sa.String(length=15), nullable=False),
        sa.Column("service_status", sa.String(length=25), nullable=False),
        sa.Column("cancellation_evidence_id", sa.Uuid(), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "feed_status IN ('live','stale','unavailable','simulation')", name="vehicle_feed_status"
        ),
        sa.CheckConstraint(
            "service_status != 'confirmed_cancelled' OR cancellation_evidence_id IS NOT NULL",
            name="cancellation_requires_evidence",
        ),
        sa.CheckConstraint(
            "service_status IN ('scheduled','delayed','uncertain','confirmed_cancelled')",
            name="vehicle_service_status",
        ),
        sa.CheckConstraint("capacity >= 0", name="vehicle_capacity"),
        sa.ForeignKeyConstraint(
            ["cancellation_evidence_id"],
            ["nammamove.disruption_evidence.id"],
            name=op.f("fk_vehicles_cancellation_evidence_id_disruption_evidence"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["operator_id"],
            ["nammamove.operators.id"],
            name=op.f("fk_vehicles_operator_id_operators"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_vehicles")),
        sa.UniqueConstraint("operator_id", "external_id", name=op.f("uq_vehicles_operator_id")),
        schema="nammamove",
    )
    op.create_index(
        op.f("ix_vehicles_created_at"), "vehicles", ["created_at"], unique=False, schema="nammamove"
    )
    op.create_index(
        op.f("ix_vehicles_operator_id"),
        "vehicles",
        ["operator_id"],
        unique=False,
        schema="nammamove",
    )
    op.execute(
        "ALTER TABLE nammamove.stops ADD COLUMN location public.geography(Point,4326) GENERATED ALWAYS AS (public.ST_SetSRID(public.ST_MakePoint(longitude,latitude),4326)::public.geography) STORED"
    )
    op.execute("CREATE INDEX ix_stops_location ON nammamove.stops USING gist(location)")

    # No access to this private schema through Supabase's default public API.
    op.execute("REVOKE ALL ON SCHEMA nammamove FROM PUBLIC")
    op.execute("REVOKE ALL ON ALL TABLES IN SCHEMA nammamove FROM PUBLIC")
    op.execute("ALTER TABLE nammamove.commuters ENABLE ROW LEVEL SECURITY")
    op.execute(
        "CREATE POLICY api_access ON nammamove.commuters USING (id = NULLIF(current_setting('nammamove.user_id', true), '')::uuid) WITH CHECK (id = NULLIF(current_setting('nammamove.user_id', true), '')::uuid)"
    )
    op.execute("ALTER TABLE nammamove.operators ENABLE ROW LEVEL SECURITY")
    op.execute(
        "CREATE POLICY catalog_read ON nammamove.operators FOR SELECT USING (NULLIF(current_setting('nammamove.user_id', true), '') IS NOT NULL)"
    )
    op.execute(
        "CREATE POLICY api_access ON nammamove.operators USING (current_setting('nammamove.role', true) = 'admin') WITH CHECK (current_setting('nammamove.role', true) = 'admin')"
    )
    op.execute("ALTER TABLE nammamove.audit_events ENABLE ROW LEVEL SECURITY")
    op.execute(
        "CREATE POLICY api_access ON nammamove.audit_events USING (actor_id = NULLIF(current_setting('nammamove.user_id', true), '')::uuid OR current_setting('nammamove.role', true) IN ('moderator','admin')) WITH CHECK (actor_id = NULLIF(current_setting('nammamove.user_id', true), '')::uuid OR current_setting('nammamove.role', true) IN ('moderator','admin'))"
    )
    op.execute("ALTER TABLE nammamove.disruptions ENABLE ROW LEVEL SECURITY")
    op.execute(
        "CREATE POLICY api_access ON nammamove.disruptions USING (reporter_id = NULLIF(current_setting('nammamove.user_id', true), '')::uuid OR current_setting('nammamove.role', true) IN ('moderator','admin')) WITH CHECK (reporter_id = NULLIF(current_setting('nammamove.user_id', true), '')::uuid OR current_setting('nammamove.role', true) IN ('moderator','admin'))"
    )
    op.execute("ALTER TABLE nammamove.feed_snapshots ENABLE ROW LEVEL SECURITY")
    op.execute(
        "CREATE POLICY catalog_read ON nammamove.feed_snapshots FOR SELECT USING (NULLIF(current_setting('nammamove.user_id', true), '') IS NOT NULL)"
    )
    op.execute(
        "CREATE POLICY api_access ON nammamove.feed_snapshots USING (current_setting('nammamove.role', true) = 'admin') WITH CHECK (current_setting('nammamove.role', true) = 'admin')"
    )
    op.execute("ALTER TABLE nammamove.journeys ENABLE ROW LEVEL SECURITY")
    op.execute(
        "CREATE POLICY api_access ON nammamove.journeys USING (commuter_id = NULLIF(current_setting('nammamove.user_id', true), '')::uuid) WITH CHECK (commuter_id = NULLIF(current_setting('nammamove.user_id', true), '')::uuid)"
    )
    op.execute("ALTER TABLE nammamove.notifications ENABLE ROW LEVEL SECURITY")
    op.execute(
        "CREATE POLICY api_access ON nammamove.notifications USING (commuter_id = NULLIF(current_setting('nammamove.user_id', true), '')::uuid) WITH CHECK (commuter_id = NULLIF(current_setting('nammamove.user_id', true), '')::uuid)"
    )
    op.execute("ALTER TABLE nammamove.stops ENABLE ROW LEVEL SECURITY")
    op.execute(
        "CREATE POLICY catalog_read ON nammamove.stops FOR SELECT USING (NULLIF(current_setting('nammamove.user_id', true), '') IS NOT NULL)"
    )
    op.execute(
        "CREATE POLICY api_access ON nammamove.stops USING (current_setting('nammamove.role', true) = 'admin') WITH CHECK (current_setting('nammamove.role', true) = 'admin')"
    )
    op.execute("ALTER TABLE nammamove.transit_routes ENABLE ROW LEVEL SECURITY")
    op.execute(
        "CREATE POLICY catalog_read ON nammamove.transit_routes FOR SELECT USING (NULLIF(current_setting('nammamove.user_id', true), '') IS NOT NULL)"
    )
    op.execute(
        "CREATE POLICY api_access ON nammamove.transit_routes USING (current_setting('nammamove.role', true) = 'admin') WITH CHECK (current_setting('nammamove.role', true) = 'admin')"
    )
    op.execute("ALTER TABLE nammamove.user_preferences ENABLE ROW LEVEL SECURITY")
    op.execute(
        "CREATE POLICY api_access ON nammamove.user_preferences USING (commuter_id = NULLIF(current_setting('nammamove.user_id', true), '')::uuid) WITH CHECK (commuter_id = NULLIF(current_setting('nammamove.user_id', true), '')::uuid)"
    )
    op.execute("ALTER TABLE nammamove.disruption_evidence ENABLE ROW LEVEL SECURITY")
    op.execute(
        "CREATE POLICY api_access ON nammamove.disruption_evidence USING (actor_id = NULLIF(current_setting('nammamove.user_id', true), '')::uuid OR current_setting('nammamove.role', true) IN ('moderator','admin')) WITH CHECK (actor_id = NULLIF(current_setting('nammamove.user_id', true), '')::uuid OR current_setting('nammamove.role', true) IN ('moderator','admin'))"
    )
    op.execute("ALTER TABLE nammamove.trips ENABLE ROW LEVEL SECURITY")
    op.execute(
        "CREATE POLICY catalog_read ON nammamove.trips FOR SELECT USING (NULLIF(current_setting('nammamove.user_id', true), '') IS NOT NULL)"
    )
    op.execute(
        "CREATE POLICY api_access ON nammamove.trips USING (current_setting('nammamove.role', true) = 'admin') WITH CHECK (current_setting('nammamove.role', true) = 'admin')"
    )
    op.execute("ALTER TABLE nammamove.stop_times ENABLE ROW LEVEL SECURITY")
    op.execute(
        "CREATE POLICY catalog_read ON nammamove.stop_times FOR SELECT USING (NULLIF(current_setting('nammamove.user_id', true), '') IS NOT NULL)"
    )
    op.execute(
        "CREATE POLICY api_access ON nammamove.stop_times USING (current_setting('nammamove.role', true) = 'admin') WITH CHECK (current_setting('nammamove.role', true) = 'admin')"
    )
    op.execute("ALTER TABLE nammamove.vehicles ENABLE ROW LEVEL SECURITY")
    op.execute(
        "CREATE POLICY catalog_read ON nammamove.vehicles FOR SELECT USING (NULLIF(current_setting('nammamove.user_id', true), '') IS NOT NULL)"
    )
    op.execute(
        "CREATE POLICY api_access ON nammamove.vehicles USING (current_setting('nammamove.role', true) = 'admin') WITH CHECK (current_setting('nammamove.role', true) = 'admin')"
    )


def downgrade() -> None:
    # Reviewed and frozen initial schema.
    op.drop_index(op.f("ix_vehicles_operator_id"), table_name="vehicles", schema="nammamove")
    op.drop_index(op.f("ix_vehicles_created_at"), table_name="vehicles", schema="nammamove")
    op.drop_table("vehicles", schema="nammamove")
    op.drop_index(op.f("ix_stop_times_stop_id"), table_name="stop_times", schema="nammamove")
    op.drop_table("stop_times", schema="nammamove")
    op.drop_index(op.f("ix_trips_route_id"), table_name="trips", schema="nammamove")
    op.drop_index(op.f("ix_trips_created_at"), table_name="trips", schema="nammamove")
    op.drop_table("trips", schema="nammamove")
    op.drop_index(
        op.f("ix_disruption_evidence_disruption_id"),
        table_name="disruption_evidence",
        schema="nammamove",
    )
    op.drop_index(
        op.f("ix_disruption_evidence_created_at"),
        table_name="disruption_evidence",
        schema="nammamove",
    )
    op.drop_table("disruption_evidence", schema="nammamove")
    op.drop_table("user_preferences", schema="nammamove")
    op.drop_index(
        op.f("ix_transit_routes_operator_id"), table_name="transit_routes", schema="nammamove"
    )
    op.drop_index(
        op.f("ix_transit_routes_created_at"), table_name="transit_routes", schema="nammamove"
    )
    op.drop_table("transit_routes", schema="nammamove")
    op.drop_index(op.f("ix_stops_operator_id"), table_name="stops", schema="nammamove")
    op.drop_index(op.f("ix_stops_created_at"), table_name="stops", schema="nammamove")
    op.drop_table("stops", schema="nammamove")
    op.drop_index(
        op.f("ix_notifications_created_at"), table_name="notifications", schema="nammamove"
    )
    op.drop_index(
        op.f("ix_notifications_commuter_id"), table_name="notifications", schema="nammamove"
    )
    op.drop_table("notifications", schema="nammamove")
    op.drop_index(op.f("ix_journeys_created_at"), table_name="journeys", schema="nammamove")
    op.drop_index(op.f("ix_journeys_commuter_id"), table_name="journeys", schema="nammamove")
    op.drop_table("journeys", schema="nammamove")
    op.drop_index(
        op.f("ix_feed_snapshots_operator_id"), table_name="feed_snapshots", schema="nammamove"
    )
    op.drop_index(
        op.f("ix_feed_snapshots_created_at"), table_name="feed_snapshots", schema="nammamove"
    )
    op.drop_table("feed_snapshots", schema="nammamove")
    op.drop_index(op.f("ix_disruptions_reporter_id"), table_name="disruptions", schema="nammamove")
    op.drop_index(op.f("ix_disruptions_expires_at"), table_name="disruptions", schema="nammamove")
    op.drop_index(op.f("ix_disruptions_created_at"), table_name="disruptions", schema="nammamove")
    op.drop_table("disruptions", schema="nammamove")
    op.drop_index(op.f("ix_audit_events_created_at"), table_name="audit_events", schema="nammamove")
    op.drop_index(op.f("ix_audit_events_actor_id"), table_name="audit_events", schema="nammamove")
    op.drop_table("audit_events", schema="nammamove")
    op.drop_index(op.f("ix_operators_created_at"), table_name="operators", schema="nammamove")
    op.drop_table("operators", schema="nammamove")
    op.drop_index(op.f("ix_commuters_created_at"), table_name="commuters", schema="nammamove")
    op.drop_table("commuters", schema="nammamove")
    # Keep shared PostGIS extension and schema/version table; Alembic owns its lifecycle.
