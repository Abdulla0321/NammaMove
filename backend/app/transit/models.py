from datetime import date as DateValue
from datetime import datetime
from uuid import UUID

from sqlalchemy import (
    JSON,
    CheckConstraint,
    Date,
    DateTime,
    Float,
    ForeignKey,
    ForeignKeyConstraint,
    Integer,
    String,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column

from ..models import FK, Base, Record


class TransitFeed(Base):
    __tablename__ = "transit_feeds"
    id: Mapped[str] = mapped_column(String(50), primary_key=True)
    provider: Mapped[str] = mapped_column(String(20))
    data_mode: Mapped[str] = mapped_column(String(15))
    active_dataset_id: Mapped[UUID | None] = mapped_column(Uuid)
    last_attempt_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_success_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_error_code: Mapped[str | None] = mapped_column(String(60))
    __table_args__ = (
        UniqueConstraint("provider", "data_mode"),
        CheckConstraint("provider IN ('bmtc','bmrcl','synthetic')", name="transit_provider"),
        CheckConstraint("data_mode IN ('scheduled','simulation')", name="transit_data_mode"),
        ForeignKeyConstraint(
            ["active_dataset_id", "id"],
            [FK + "transit_datasets.id", FK + "transit_datasets.feed_id"],
            name="fk_active_dataset_same_feed",
            use_alter=True,
            deferrable=True,
            initially="DEFERRED",
        ),
    )


class TransitDataset(Record, Base):
    __tablename__ = "transit_datasets"
    feed_id: Mapped[str] = mapped_column(
        ForeignKey(FK + "transit_feeds.id", ondelete="RESTRICT"), index=True
    )
    checksum: Mapped[str] = mapped_column(String(64))
    manifest_digest: Mapped[str] = mapped_column(String(64))
    source_url: Mapped[str] = mapped_column(String(500))
    license_id: Mapped[str] = mapped_column(String(80))
    license_url: Mapped[str] = mapped_column(String(500))
    attribution: Mapped[str] = mapped_column(String(500))
    authorization: Mapped[str] = mapped_column(String(20))
    authorization_reference: Mapped[str] = mapped_column(String(200))
    publisher: Mapped[str] = mapped_column(String(120))
    authority: Mapped[str] = mapped_column(String(20))
    retrieved_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    version: Mapped[str] = mapped_column(String(160))
    quality_notes: Mapped[list[str]] = mapped_column(JSON, default=list)
    service_start: Mapped[DateValue | None] = mapped_column(Date)
    service_end: Mapped[DateValue | None] = mapped_column(Date)
    timezone: Mapped[str] = mapped_column(String(50), default="Asia/Kolkata")
    state: Mapped[str] = mapped_column(String(20))
    report: Mapped[dict[str, object]] = mapped_column(JSON)
    __table_args__ = (
        UniqueConstraint("feed_id", "checksum", "manifest_digest"),
        UniqueConstraint("id", "feed_id"),
        CheckConstraint("state IN ('validated','quarantined')", name="transit_dataset_state"),
        CheckConstraint(
            "\"authorization\" IN ('open','authorized','simulation')", name="transit_authorization"
        ),
        CheckConstraint(
            "authority IN ('agency','community','synthetic')", name="transit_authority"
        ),
        CheckConstraint(
            "service_start IS NULL OR service_end >= service_start", name="transit_coverage_order"
        ),
    )


class DatasetRow:
    dataset_id: Mapped[UUID] = mapped_column(
        ForeignKey(FK + "transit_datasets.id", ondelete="CASCADE"), primary_key=True
    )


class GtfsAgency(DatasetRow, Base):
    __tablename__ = "gtfs_agencies"
    external_id: Mapped[str] = mapped_column(String(200), primary_key=True)
    name: Mapped[str] = mapped_column(String(200))
    url: Mapped[str] = mapped_column(String(500))
    timezone: Mapped[str] = mapped_column(String(50))


class GtfsStop(DatasetRow, Base):
    __tablename__ = "gtfs_stops"
    external_id: Mapped[str] = mapped_column(String(200), primary_key=True)
    name: Mapped[str] = mapped_column(String(200), index=True)
    latitude: Mapped[float] = mapped_column(Float)
    longitude: Mapped[float] = mapped_column(Float)
    location_type: Mapped[int] = mapped_column(Integer)
    parent_station: Mapped[str | None] = mapped_column(String(200))
    wheelchair_boarding: Mapped[int] = mapped_column(Integer)
    __table_args__ = (
        CheckConstraint(
            "latitude BETWEEN -90 AND 90 AND longitude BETWEEN -180 AND 180",
            name="gtfs_stop_coordinates",
        ),
        CheckConstraint("location_type BETWEEN 0 AND 4", name="gtfs_location_type"),
        CheckConstraint("wheelchair_boarding BETWEEN 0 AND 2", name="gtfs_stop_accessibility"),
    )


class GtfsRoute(DatasetRow, Base):
    __tablename__ = "gtfs_routes"
    external_id: Mapped[str] = mapped_column(String(200), primary_key=True)
    agency_id: Mapped[str] = mapped_column(String(200))
    short_name: Mapped[str] = mapped_column(String(200), index=True)
    long_name: Mapped[str] = mapped_column(String(200))
    route_type: Mapped[int] = mapped_column(Integer)
    __table_args__ = (
        ForeignKeyConstraint(
            ["dataset_id", "agency_id"],
            [FK + "gtfs_agencies.dataset_id", FK + "gtfs_agencies.external_id"],
        ),
        CheckConstraint("route_type IN (0,1,2,3)", name="gtfs_route_type"),
    )


class GtfsService(DatasetRow, Base):
    __tablename__ = "gtfs_services"
    external_id: Mapped[str] = mapped_column(String(200), primary_key=True)
    weekdays: Mapped[int] = mapped_column(Integer)
    start_date: Mapped[DateValue] = mapped_column(Date)
    end_date: Mapped[DateValue] = mapped_column(Date)
    __table_args__ = (
        CheckConstraint(
            "weekdays BETWEEN 0 AND 127 AND end_date >= start_date", name="gtfs_service_calendar"
        ),
    )


class GtfsCalendarDate(DatasetRow, Base):
    __tablename__ = "gtfs_calendar_dates"
    service_id: Mapped[str] = mapped_column(String(200), primary_key=True)
    date: Mapped[DateValue] = mapped_column(Date, primary_key=True)
    exception_type: Mapped[int] = mapped_column(Integer)
    __table_args__ = (
        ForeignKeyConstraint(
            ["dataset_id", "service_id"],
            [FK + "gtfs_services.dataset_id", FK + "gtfs_services.external_id"],
        ),
        CheckConstraint("exception_type IN (1,2)", name="gtfs_calendar_exception"),
    )


class GtfsShape(DatasetRow, Base):
    __tablename__ = "gtfs_shapes"
    external_id: Mapped[str] = mapped_column(String(200), primary_key=True)


class GtfsShapePoint(DatasetRow, Base):
    __tablename__ = "gtfs_shape_points"
    shape_id: Mapped[str] = mapped_column(String(200), primary_key=True)
    sequence: Mapped[int] = mapped_column(Integer, primary_key=True)
    latitude: Mapped[float] = mapped_column(Float)
    longitude: Mapped[float] = mapped_column(Float)
    distance: Mapped[float | None] = mapped_column(Float)
    __table_args__ = (
        ForeignKeyConstraint(
            ["dataset_id", "shape_id"],
            [FK + "gtfs_shapes.dataset_id", FK + "gtfs_shapes.external_id"],
        ),
        CheckConstraint(
            "sequence >= 0 AND latitude BETWEEN -90 AND 90 AND longitude BETWEEN -180 AND 180 AND (distance IS NULL OR distance >= 0)",
            name="gtfs_shape_bounds",
        ),
    )


class GtfsTrip(DatasetRow, Base):
    __tablename__ = "gtfs_trips"
    external_id: Mapped[str] = mapped_column(String(200), primary_key=True)
    route_id: Mapped[str] = mapped_column(String(200), index=True)
    service_id: Mapped[str] = mapped_column(String(200))
    shape_id: Mapped[str | None] = mapped_column(String(200))
    direction_id: Mapped[int | None] = mapped_column(Integer)
    headsign: Mapped[str] = mapped_column(String(200))
    __table_args__ = (
        ForeignKeyConstraint(
            ["dataset_id", "route_id"],
            [FK + "gtfs_routes.dataset_id", FK + "gtfs_routes.external_id"],
        ),
        ForeignKeyConstraint(
            ["dataset_id", "service_id"],
            [FK + "gtfs_services.dataset_id", FK + "gtfs_services.external_id"],
        ),
        ForeignKeyConstraint(
            ["dataset_id", "shape_id"],
            [FK + "gtfs_shapes.dataset_id", FK + "gtfs_shapes.external_id"],
        ),
        CheckConstraint("direction_id IS NULL OR direction_id IN (0,1)", name="gtfs_direction"),
    )


class GtfsStopTime(DatasetRow, Base):
    __tablename__ = "gtfs_stop_times"
    trip_id: Mapped[str] = mapped_column(String(200), primary_key=True)
    sequence: Mapped[int] = mapped_column(Integer, primary_key=True)
    stop_id: Mapped[str] = mapped_column(String(200), index=True)
    arrival_seconds: Mapped[int | None] = mapped_column(Integer)
    departure_seconds: Mapped[int | None] = mapped_column(Integer)
    timepoint: Mapped[int] = mapped_column(Integer)
    pickup_type: Mapped[int] = mapped_column(Integer)
    drop_off_type: Mapped[int] = mapped_column(Integer)
    __table_args__ = (
        ForeignKeyConstraint(
            ["dataset_id", "trip_id"], [FK + "gtfs_trips.dataset_id", FK + "gtfs_trips.external_id"]
        ),
        ForeignKeyConstraint(
            ["dataset_id", "stop_id"], [FK + "gtfs_stops.dataset_id", FK + "gtfs_stops.external_id"]
        ),
        CheckConstraint(
            "sequence >= 0 AND ((arrival_seconds IS NULL AND departure_seconds IS NULL AND timepoint = 0) OR (arrival_seconds IS NOT NULL AND departure_seconds IS NOT NULL AND arrival_seconds >= 0 AND departure_seconds >= arrival_seconds))",
            name="gtfs_time_order",
        ),
        CheckConstraint(
            "timepoint IN (0,1) AND pickup_type BETWEEN 0 AND 3 AND drop_off_type BETWEEN 0 AND 3",
            name="gtfs_stop_time_flags",
        ),
    )


class GtfsTransfer(Record, Base):
    __tablename__ = "gtfs_transfers"
    dataset_id: Mapped[UUID] = mapped_column(
        ForeignKey(FK + "transit_datasets.id", ondelete="CASCADE"), index=True
    )
    from_stop_id: Mapped[str] = mapped_column(String(200))
    to_stop_id: Mapped[str] = mapped_column(String(200))
    transfer_type: Mapped[int] = mapped_column(Integer)
    min_transfer_seconds: Mapped[int | None] = mapped_column(Integer)
    from_route_id: Mapped[str] = mapped_column(String(200))
    to_route_id: Mapped[str] = mapped_column(String(200))
    from_trip_id: Mapped[str] = mapped_column(String(200))
    to_trip_id: Mapped[str] = mapped_column(String(200))
    __table_args__ = (
        ForeignKeyConstraint(
            ["dataset_id", "from_stop_id"],
            [FK + "gtfs_stops.dataset_id", FK + "gtfs_stops.external_id"],
            name="fk_gtfs_transfer_from_stop",
        ),
        ForeignKeyConstraint(
            ["dataset_id", "to_stop_id"],
            [FK + "gtfs_stops.dataset_id", FK + "gtfs_stops.external_id"],
            name="fk_gtfs_transfer_to_stop",
        ),
        UniqueConstraint(
            "dataset_id",
            "from_stop_id",
            "to_stop_id",
            "from_route_id",
            "to_route_id",
            "from_trip_id",
            "to_trip_id",
        ),
        CheckConstraint(
            "transfer_type BETWEEN 0 AND 3 AND (min_transfer_seconds IS NULL OR min_transfer_seconds >= 0) AND (transfer_type != 2 OR min_transfer_seconds IS NOT NULL)",
            name="gtfs_transfer_rules",
        ),
    )


TRANSIT_TABLES = {
    "transit_feeds",
    "transit_datasets",
    "gtfs_agencies",
    "gtfs_stops",
    "gtfs_routes",
    "gtfs_services",
    "gtfs_calendar_dates",
    "gtfs_shapes",
    "gtfs_shape_points",
    "gtfs_trips",
    "gtfs_stop_times",
    "gtfs_transfers",
    "gtfs_frequencies",
}


class GtfsFrequency(DatasetRow, Base):
    __tablename__ = "gtfs_frequencies"
    trip_id: Mapped[str] = mapped_column(String(200), primary_key=True)
    start_seconds: Mapped[int] = mapped_column(Integer, primary_key=True)
    end_seconds: Mapped[int] = mapped_column(Integer)
    headway_seconds: Mapped[int] = mapped_column(Integer)
    exact_times: Mapped[int] = mapped_column(Integer)
    __table_args__ = (
        ForeignKeyConstraint(
            ["dataset_id", "trip_id"], [FK + "gtfs_trips.dataset_id", FK + "gtfs_trips.external_id"]
        ),
        CheckConstraint(
            "start_seconds >= 0 AND end_seconds > start_seconds AND headway_seconds > 0 AND exact_times IN (0,1)",
            name="gtfs_frequency_window",
        ),
    )
