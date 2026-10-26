"""Versioned static transit catalog and read-only runtime policies."""

import sqlalchemy as sa
from alembic import op

revision = "0002_transit_data"
down_revision = "0001_phase01"
branch_labels = None
depends_on = None

TABLES = [
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
    "transit_datasets",
    "transit_feeds",
]


def upgrade():
    op.create_table(
        "transit_feeds",
        sa.Column("id", sa.String(length=50), nullable=False),
        sa.Column("provider", sa.String(length=20), nullable=False),
        sa.Column("data_mode", sa.String(length=15), nullable=False),
        sa.Column("active_dataset_id", sa.Uuid(), nullable=True),
        sa.Column("last_attempt_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_success_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_error_code", sa.String(length=60), nullable=True),
        sa.CheckConstraint("data_mode IN ('scheduled','simulation')", name="transit_data_mode"),
        sa.CheckConstraint("provider IN ('bmtc','bmrcl','synthetic')", name="transit_provider"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_transit_feeds")),
        sa.UniqueConstraint("provider", "data_mode", name=op.f("uq_transit_feeds_provider")),
        schema="nammamove",
    )
    op.create_table(
        "transit_datasets",
        sa.Column("feed_id", sa.String(length=50), nullable=False),
        sa.Column("checksum", sa.String(length=64), nullable=False),
        sa.Column("manifest_digest", sa.String(length=64), nullable=False),
        sa.Column("source_url", sa.String(length=500), nullable=False),
        sa.Column("license_id", sa.String(length=80), nullable=False),
        sa.Column("license_url", sa.String(length=500), nullable=False),
        sa.Column("attribution", sa.String(length=500), nullable=False),
        sa.Column("authorization", sa.String(length=20), nullable=False),
        sa.Column("authorization_reference", sa.String(length=200), nullable=False),
        sa.Column("publisher", sa.String(length=120), nullable=False),
        sa.Column("authority", sa.String(length=20), nullable=False),
        sa.Column("retrieved_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("version", sa.String(length=160), nullable=False),
        sa.Column("quality_notes", sa.JSON(), nullable=False),
        sa.Column("service_start", sa.Date(), nullable=True),
        sa.Column("service_end", sa.Date(), nullable=True),
        sa.Column("timezone", sa.String(length=50), nullable=False),
        sa.Column("state", sa.String(length=20), nullable=False),
        sa.Column("report", sa.JSON(), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "authority IN ('agency','community','synthetic')", name="transit_authority"
        ),
        sa.CheckConstraint(
            "\"authorization\" IN ('open','authorized','simulation')", name="transit_authorization"
        ),
        sa.CheckConstraint("state IN ('validated','quarantined')", name="transit_dataset_state"),
        sa.CheckConstraint(
            "service_start IS NULL OR service_end >= service_start", name="transit_coverage_order"
        ),
        sa.ForeignKeyConstraint(
            ["feed_id"],
            ["nammamove.transit_feeds.id"],
            name=op.f("fk_transit_datasets_feed_id_transit_feeds"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_transit_datasets")),
        sa.UniqueConstraint(
            "feed_id", "checksum", "manifest_digest", name=op.f("uq_transit_datasets_feed_id")
        ),
        sa.UniqueConstraint("id", "feed_id", name=op.f("uq_transit_datasets_id")),
        schema="nammamove",
    )
    op.create_index(
        op.f("ix_transit_datasets_created_at"),
        "transit_datasets",
        ["created_at"],
        unique=False,
        schema="nammamove",
    )
    op.create_index(
        op.f("ix_transit_datasets_feed_id"),
        "transit_datasets",
        ["feed_id"],
        unique=False,
        schema="nammamove",
    )
    op.create_table(
        "gtfs_agencies",
        sa.Column("external_id", sa.String(length=200), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("url", sa.String(length=500), nullable=False),
        sa.Column("timezone", sa.String(length=50), nullable=False),
        sa.Column("dataset_id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(
            ["dataset_id"],
            ["nammamove.transit_datasets.id"],
            name=op.f("fk_gtfs_agencies_dataset_id_transit_datasets"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("external_id", "dataset_id", name=op.f("pk_gtfs_agencies")),
        schema="nammamove",
    )
    op.create_table(
        "gtfs_services",
        sa.Column("external_id", sa.String(length=200), nullable=False),
        sa.Column("weekdays", sa.Integer(), nullable=False),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("end_date", sa.Date(), nullable=False),
        sa.Column("dataset_id", sa.Uuid(), nullable=False),
        sa.CheckConstraint(
            "weekdays BETWEEN 0 AND 127 AND end_date >= start_date", name="gtfs_service_calendar"
        ),
        sa.ForeignKeyConstraint(
            ["dataset_id"],
            ["nammamove.transit_datasets.id"],
            name=op.f("fk_gtfs_services_dataset_id_transit_datasets"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("external_id", "dataset_id", name=op.f("pk_gtfs_services")),
        schema="nammamove",
    )
    op.create_table(
        "gtfs_shapes",
        sa.Column("external_id", sa.String(length=200), nullable=False),
        sa.Column("dataset_id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(
            ["dataset_id"],
            ["nammamove.transit_datasets.id"],
            name=op.f("fk_gtfs_shapes_dataset_id_transit_datasets"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("external_id", "dataset_id", name=op.f("pk_gtfs_shapes")),
        schema="nammamove",
    )
    op.create_table(
        "gtfs_stops",
        sa.Column("external_id", sa.String(length=200), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("latitude", sa.Float(), nullable=False),
        sa.Column("longitude", sa.Float(), nullable=False),
        sa.Column("location_type", sa.Integer(), nullable=False),
        sa.Column("parent_station", sa.String(length=200), nullable=True),
        sa.Column("wheelchair_boarding", sa.Integer(), nullable=False),
        sa.Column("dataset_id", sa.Uuid(), nullable=False),
        sa.CheckConstraint(
            "latitude BETWEEN -90 AND 90 AND longitude BETWEEN -180 AND 180",
            name="gtfs_stop_coordinates",
        ),
        sa.CheckConstraint("location_type BETWEEN 0 AND 4", name="gtfs_location_type"),
        sa.CheckConstraint("wheelchair_boarding BETWEEN 0 AND 2", name="gtfs_stop_accessibility"),
        sa.ForeignKeyConstraint(
            ["dataset_id"],
            ["nammamove.transit_datasets.id"],
            name=op.f("fk_gtfs_stops_dataset_id_transit_datasets"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("external_id", "dataset_id", name=op.f("pk_gtfs_stops")),
        schema="nammamove",
    )
    op.create_index(
        op.f("ix_gtfs_stops_name"), "gtfs_stops", ["name"], unique=False, schema="nammamove"
    )
    op.create_table(
        "gtfs_calendar_dates",
        sa.Column("service_id", sa.String(length=200), nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("exception_type", sa.Integer(), nullable=False),
        sa.Column("dataset_id", sa.Uuid(), nullable=False),
        sa.CheckConstraint("exception_type IN (1,2)", name="gtfs_calendar_exception"),
        sa.ForeignKeyConstraint(
            ["dataset_id", "service_id"],
            ["nammamove.gtfs_services.dataset_id", "nammamove.gtfs_services.external_id"],
            name=op.f("fk_gtfs_calendar_dates_dataset_id_gtfs_services"),
        ),
        sa.ForeignKeyConstraint(
            ["dataset_id"],
            ["nammamove.transit_datasets.id"],
            name=op.f("fk_gtfs_calendar_dates_dataset_id_transit_datasets"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint(
            "service_id", "date", "dataset_id", name=op.f("pk_gtfs_calendar_dates")
        ),
        schema="nammamove",
    )
    op.create_table(
        "gtfs_routes",
        sa.Column("external_id", sa.String(length=200), nullable=False),
        sa.Column("agency_id", sa.String(length=200), nullable=False),
        sa.Column("short_name", sa.String(length=200), nullable=False),
        sa.Column("long_name", sa.String(length=200), nullable=False),
        sa.Column("route_type", sa.Integer(), nullable=False),
        sa.Column("dataset_id", sa.Uuid(), nullable=False),
        sa.CheckConstraint("route_type IN (0,1,2,3)", name="gtfs_route_type"),
        sa.ForeignKeyConstraint(
            ["dataset_id", "agency_id"],
            ["nammamove.gtfs_agencies.dataset_id", "nammamove.gtfs_agencies.external_id"],
            name=op.f("fk_gtfs_routes_dataset_id_gtfs_agencies"),
        ),
        sa.ForeignKeyConstraint(
            ["dataset_id"],
            ["nammamove.transit_datasets.id"],
            name=op.f("fk_gtfs_routes_dataset_id_transit_datasets"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("external_id", "dataset_id", name=op.f("pk_gtfs_routes")),
        schema="nammamove",
    )
    op.create_index(
        op.f("ix_gtfs_routes_short_name"),
        "gtfs_routes",
        ["short_name"],
        unique=False,
        schema="nammamove",
    )
    op.create_table(
        "gtfs_shape_points",
        sa.Column("shape_id", sa.String(length=200), nullable=False),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("latitude", sa.Float(), nullable=False),
        sa.Column("longitude", sa.Float(), nullable=False),
        sa.Column("distance", sa.Float(), nullable=True),
        sa.Column("dataset_id", sa.Uuid(), nullable=False),
        sa.CheckConstraint(
            "sequence >= 0 AND latitude BETWEEN -90 AND 90 AND longitude BETWEEN -180 AND 180 AND (distance IS NULL OR distance >= 0)",
            name="gtfs_shape_bounds",
        ),
        sa.ForeignKeyConstraint(
            ["dataset_id", "shape_id"],
            ["nammamove.gtfs_shapes.dataset_id", "nammamove.gtfs_shapes.external_id"],
            name=op.f("fk_gtfs_shape_points_dataset_id_gtfs_shapes"),
        ),
        sa.ForeignKeyConstraint(
            ["dataset_id"],
            ["nammamove.transit_datasets.id"],
            name=op.f("fk_gtfs_shape_points_dataset_id_transit_datasets"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint(
            "shape_id", "sequence", "dataset_id", name=op.f("pk_gtfs_shape_points")
        ),
        schema="nammamove",
    )
    op.create_table(
        "gtfs_transfers",
        sa.Column("dataset_id", sa.Uuid(), nullable=False),
        sa.Column("from_stop_id", sa.String(length=200), nullable=False),
        sa.Column("to_stop_id", sa.String(length=200), nullable=False),
        sa.Column("transfer_type", sa.Integer(), nullable=False),
        sa.Column("min_transfer_seconds", sa.Integer(), nullable=True),
        sa.Column("from_route_id", sa.String(length=200), nullable=False),
        sa.Column("to_route_id", sa.String(length=200), nullable=False),
        sa.Column("from_trip_id", sa.String(length=200), nullable=False),
        sa.Column("to_trip_id", sa.String(length=200), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "transfer_type BETWEEN 0 AND 3 AND (min_transfer_seconds IS NULL OR min_transfer_seconds >= 0) AND (transfer_type != 2 OR min_transfer_seconds IS NOT NULL)",
            name="gtfs_transfer_rules",
        ),
        sa.ForeignKeyConstraint(
            ["dataset_id", "from_stop_id"],
            ["nammamove.gtfs_stops.dataset_id", "nammamove.gtfs_stops.external_id"],
            name="fk_gtfs_transfer_from_stop",
        ),
        sa.ForeignKeyConstraint(
            ["dataset_id", "to_stop_id"],
            ["nammamove.gtfs_stops.dataset_id", "nammamove.gtfs_stops.external_id"],
            name="fk_gtfs_transfer_to_stop",
        ),
        sa.ForeignKeyConstraint(
            ["dataset_id"],
            ["nammamove.transit_datasets.id"],
            name=op.f("fk_gtfs_transfers_dataset_id_transit_datasets"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_gtfs_transfers")),
        sa.UniqueConstraint(
            "dataset_id",
            "from_stop_id",
            "to_stop_id",
            "from_route_id",
            "to_route_id",
            "from_trip_id",
            "to_trip_id",
            name=op.f("uq_gtfs_transfers_dataset_id"),
        ),
        schema="nammamove",
    )
    op.create_index(
        op.f("ix_gtfs_transfers_created_at"),
        "gtfs_transfers",
        ["created_at"],
        unique=False,
        schema="nammamove",
    )
    op.create_index(
        op.f("ix_gtfs_transfers_dataset_id"),
        "gtfs_transfers",
        ["dataset_id"],
        unique=False,
        schema="nammamove",
    )
    op.create_table(
        "gtfs_trips",
        sa.Column("external_id", sa.String(length=200), nullable=False),
        sa.Column("route_id", sa.String(length=200), nullable=False),
        sa.Column("service_id", sa.String(length=200), nullable=False),
        sa.Column("shape_id", sa.String(length=200), nullable=True),
        sa.Column("direction_id", sa.Integer(), nullable=True),
        sa.Column("headsign", sa.String(length=200), nullable=False),
        sa.Column("dataset_id", sa.Uuid(), nullable=False),
        sa.CheckConstraint("direction_id IS NULL OR direction_id IN (0,1)", name="gtfs_direction"),
        sa.ForeignKeyConstraint(
            ["dataset_id", "route_id"],
            ["nammamove.gtfs_routes.dataset_id", "nammamove.gtfs_routes.external_id"],
            name=op.f("fk_gtfs_trips_dataset_id_gtfs_routes"),
        ),
        sa.ForeignKeyConstraint(
            ["dataset_id", "service_id"],
            ["nammamove.gtfs_services.dataset_id", "nammamove.gtfs_services.external_id"],
            name=op.f("fk_gtfs_trips_dataset_id_gtfs_services"),
        ),
        sa.ForeignKeyConstraint(
            ["dataset_id", "shape_id"],
            ["nammamove.gtfs_shapes.dataset_id", "nammamove.gtfs_shapes.external_id"],
            name=op.f("fk_gtfs_trips_dataset_id_gtfs_shapes"),
        ),
        sa.ForeignKeyConstraint(
            ["dataset_id"],
            ["nammamove.transit_datasets.id"],
            name=op.f("fk_gtfs_trips_dataset_id_transit_datasets"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("external_id", "dataset_id", name=op.f("pk_gtfs_trips")),
        schema="nammamove",
    )
    op.create_index(
        op.f("ix_gtfs_trips_route_id"), "gtfs_trips", ["route_id"], unique=False, schema="nammamove"
    )
    op.create_table(
        "gtfs_frequencies",
        sa.Column("trip_id", sa.String(length=200), nullable=False),
        sa.Column("start_seconds", sa.Integer(), nullable=False),
        sa.Column("end_seconds", sa.Integer(), nullable=False),
        sa.Column("headway_seconds", sa.Integer(), nullable=False),
        sa.Column("exact_times", sa.Integer(), nullable=False),
        sa.Column("dataset_id", sa.Uuid(), nullable=False),
        sa.CheckConstraint(
            "start_seconds >= 0 AND end_seconds > start_seconds AND headway_seconds > 0 AND exact_times IN (0,1)",
            name="gtfs_frequency_window",
        ),
        sa.ForeignKeyConstraint(
            ["dataset_id", "trip_id"],
            ["nammamove.gtfs_trips.dataset_id", "nammamove.gtfs_trips.external_id"],
            name=op.f("fk_gtfs_frequencies_dataset_id_gtfs_trips"),
        ),
        sa.ForeignKeyConstraint(
            ["dataset_id"],
            ["nammamove.transit_datasets.id"],
            name=op.f("fk_gtfs_frequencies_dataset_id_transit_datasets"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint(
            "trip_id", "start_seconds", "dataset_id", name=op.f("pk_gtfs_frequencies")
        ),
        schema="nammamove",
    )
    op.create_table(
        "gtfs_stop_times",
        sa.Column("trip_id", sa.String(length=200), nullable=False),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("stop_id", sa.String(length=200), nullable=False),
        sa.Column("arrival_seconds", sa.Integer(), nullable=True),
        sa.Column("departure_seconds", sa.Integer(), nullable=True),
        sa.Column("timepoint", sa.Integer(), nullable=False),
        sa.Column("pickup_type", sa.Integer(), nullable=False),
        sa.Column("drop_off_type", sa.Integer(), nullable=False),
        sa.Column("dataset_id", sa.Uuid(), nullable=False),
        sa.CheckConstraint(
            "sequence >= 0 AND ((arrival_seconds IS NULL AND departure_seconds IS NULL AND timepoint = 0) OR (arrival_seconds IS NOT NULL AND departure_seconds IS NOT NULL AND arrival_seconds >= 0 AND departure_seconds >= arrival_seconds))",
            name="gtfs_time_order",
        ),
        sa.CheckConstraint(
            "timepoint IN (0,1) AND pickup_type BETWEEN 0 AND 3 AND drop_off_type BETWEEN 0 AND 3",
            name="gtfs_stop_time_flags",
        ),
        sa.ForeignKeyConstraint(
            ["dataset_id", "stop_id"],
            ["nammamove.gtfs_stops.dataset_id", "nammamove.gtfs_stops.external_id"],
            name=op.f("fk_gtfs_stop_times_dataset_id_gtfs_stops"),
        ),
        sa.ForeignKeyConstraint(
            ["dataset_id", "trip_id"],
            ["nammamove.gtfs_trips.dataset_id", "nammamove.gtfs_trips.external_id"],
            name=op.f("fk_gtfs_stop_times_dataset_id_gtfs_trips"),
        ),
        sa.ForeignKeyConstraint(
            ["dataset_id"],
            ["nammamove.transit_datasets.id"],
            name=op.f("fk_gtfs_stop_times_dataset_id_transit_datasets"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint(
            "trip_id", "sequence", "dataset_id", name=op.f("pk_gtfs_stop_times")
        ),
        schema="nammamove",
    )
    op.create_index(
        op.f("ix_gtfs_stop_times_stop_id"),
        "gtfs_stop_times",
        ["stop_id"],
        unique=False,
        schema="nammamove",
    )
    op.create_foreign_key(
        "fk_active_dataset_same_feed",
        "transit_feeds",
        "transit_datasets",
        ["active_dataset_id", "id"],
        ["id", "feed_id"],
        source_schema="nammamove",
        referent_schema="nammamove",
        deferrable=True,
        initially="DEFERRED",
    )
    op.execute(
        "ALTER TABLE nammamove.gtfs_stops ADD COLUMN location public.geography(Point,4326) GENERATED ALWAYS AS (public.ST_SetSRID(public.ST_MakePoint(longitude,latitude),4326)::public.geography) STORED"
    )
    op.execute("CREATE INDEX ix_gtfs_stops_location ON nammamove.gtfs_stops USING gist(location)")
    for table in TABLES:
        op.execute(f"ALTER TABLE nammamove.{table} ENABLE ROW LEVEL SECURITY")
        op.execute(f"REVOKE ALL ON nammamove.{table} FROM PUBLIC")
        if table == "transit_feeds":
            condition = "NULLIF(current_setting('nammamove.user_id', true), '') IS NOT NULL"
        elif table == "transit_datasets":
            condition = "NULLIF(current_setting('nammamove.user_id', true), '') IS NOT NULL AND (current_setting('nammamove.role', true) = 'admin' OR state = 'validated')"
        else:
            condition = "dataset_id IN (SELECT id FROM nammamove.transit_datasets)"
        op.execute(
            f"CREATE POLICY catalog_read ON nammamove.{table} FOR SELECT USING ({condition})"
        )


def downgrade():
    op.drop_constraint(
        "fk_active_dataset_same_feed", "transit_feeds", schema="nammamove", type_="foreignkey"
    )
    op.drop_index(
        op.f("ix_gtfs_stop_times_stop_id"), table_name="gtfs_stop_times", schema="nammamove"
    )
    op.drop_table("gtfs_stop_times", schema="nammamove")
    op.drop_table("gtfs_frequencies", schema="nammamove")
    op.drop_index(op.f("ix_gtfs_trips_route_id"), table_name="gtfs_trips", schema="nammamove")
    op.drop_table("gtfs_trips", schema="nammamove")
    op.drop_index(
        op.f("ix_gtfs_transfers_dataset_id"), table_name="gtfs_transfers", schema="nammamove"
    )
    op.drop_index(
        op.f("ix_gtfs_transfers_created_at"), table_name="gtfs_transfers", schema="nammamove"
    )
    op.drop_table("gtfs_transfers", schema="nammamove")
    op.drop_table("gtfs_shape_points", schema="nammamove")
    op.drop_index(op.f("ix_gtfs_routes_short_name"), table_name="gtfs_routes", schema="nammamove")
    op.drop_table("gtfs_routes", schema="nammamove")
    op.drop_table("gtfs_calendar_dates", schema="nammamove")
    op.drop_index(op.f("ix_gtfs_stops_name"), table_name="gtfs_stops", schema="nammamove")
    op.drop_table("gtfs_stops", schema="nammamove")
    op.drop_table("gtfs_shapes", schema="nammamove")
    op.drop_table("gtfs_services", schema="nammamove")
    op.drop_table("gtfs_agencies", schema="nammamove")
    op.drop_index(
        op.f("ix_transit_datasets_feed_id"), table_name="transit_datasets", schema="nammamove"
    )
    op.drop_index(
        op.f("ix_transit_datasets_created_at"), table_name="transit_datasets", schema="nammamove"
    )
    op.drop_table("transit_datasets", schema="nammamove")
    op.drop_table("transit_feeds", schema="nammamove")
