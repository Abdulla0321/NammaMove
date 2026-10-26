"""Actual PostGIS and non-owner policy acceptance, using synthetic feed records."""

from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Barrier
from uuid import uuid4

import pytest
from alembic import command
from app.transit.ingestion import activate, ingest
from app.transit.models import TransitDataset, TransitFeed
from app.transit.routes import stops
from sqlalchemy import event, func, select, text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session
from test_transit import archive, manifest, tables


@pytest.mark.postgres
def test_transit_spatial_atomic_import_and_actual_read_only_rls(postgres):
    engine, _ = postgres
    with Session(engine) as db, db.begin():
        first = ingest(db, archive(), manifest())
        first_id = first.id
        values = tables()
        values["stops.txt"] = values["stops.txt"].replace("Synthetic east", "Revised east")
        second = ingest(db, archive(values), manifest(version="second"))
        second_id = second.id
        rejected = ingest(db, b"invalid", manifest())
        assert rejected.state == "quarantined"
        assert db.get(TransitFeed, "synthetic:simulation").active_dataset_id == second_id
        activate(db, "synthetic:simulation", first_id)
        response = stops(
            db,
            provider="synthetic",
            mode="simulation",
            q="",
            latitude=12.97,
            longitude=77.59,
            radius_m=100,
            limit=10,
            offset=0,
        )
        assert [s["external_id"] for s in response["stops"]] == ["S1"]
        assert response["stops"][0]["distance_m"] < 1
        assert (
            db.scalar(
                text(
                    "SELECT public.ST_SRID(location::public.geometry) FROM nammamove.gtfs_stops LIMIT 1"
                )
            )
            == 4326
        )
    role = "nm_transit_" + uuid4().hex
    script = Path("backend/sql/runtime_role.sql").read_text()
    script = "\n".join(line for line in script.splitlines() if not line.lstrip().startswith("--"))
    with engine.connect() as connection:
        transaction = connection.begin()
        try:
            for statement in script.replace("nammamove_api", role).split(";"):
                if statement.strip():
                    connection.execute(text(statement))
            connection.execute(text(f"SET LOCAL ROLE {role}"))
            assert connection.scalar(text("SELECT count(*) FROM nammamove.gtfs_stops")) == 0
            connection.execute(
                text(
                    "SELECT set_config('nammamove.user_id',:user,true), set_config('nammamove.role','commuter',true)"
                ),
                {"user": str(uuid4())},
            )
            assert connection.scalar(text("SELECT count(*) FROM nammamove.gtfs_stops")) == 4
            assert connection.scalar(text("SELECT count(*) FROM nammamove.transit_datasets")) == 2
            for privilege in ("INSERT", "UPDATE", "DELETE"):
                assert not connection.scalar(
                    text(
                        "SELECT has_table_privilege(current_user,'nammamove.gtfs_stops',:privilege)"
                    ),
                    {"privilege": privilege},
                )
            with connection.begin_nested():
                with pytest.raises(DBAPIError):
                    with connection.begin_nested():
                        connection.execute(text("DELETE FROM nammamove.gtfs_stops"))
            connection.execute(text("SELECT set_config('nammamove.role','admin',true)"))
            assert connection.scalar(text("SELECT count(*) FROM nammamove.transit_datasets")) == 3
        finally:
            transaction.rollback()


@pytest.mark.postgres
def test_transit_failed_revision_rolls_back_to_phase01(postgres):
    engine, config = postgres
    command.downgrade(config, "0001_phase01")

    def fail(connection, cursor, statement, parameters, context, executemany):
        if "CREATE INDEX ix_gtfs_stops_location" in statement:
            raise RuntimeError("injected Phase 02 failure")

    event.listen(engine, "before_cursor_execute", fail)
    try:
        with engine.connect() as connection:
            config.attributes["connection"] = connection
            with pytest.raises(RuntimeError, match="injected Phase 02"):
                command.upgrade(config, "head")
    finally:
        event.remove(engine, "before_cursor_execute", fail)
        config.attributes.pop("connection", None)
    with engine.connect() as connection:
        assert (
            connection.scalar(text("SELECT version_num FROM nammamove.alembic_version"))
            == "0001_phase01"
        )
        assert connection.scalar(text("SELECT to_regclass('nammamove.transit_feeds')")) is None
        assert connection.scalar(text("SELECT to_regclass('nammamove.commuters')")) is not None
    command.upgrade(config, "head")


@pytest.mark.postgres
def test_concurrent_refresh_and_sql_failure_preserve_snapshot(postgres):
    engine, _ = postgres
    barrier = Barrier(2)

    def refresh():
        barrier.wait(timeout=10)
        with Session(engine) as db, db.begin():
            return ingest(db, archive(), manifest()).id

    with ThreadPoolExecutor(max_workers=2) as workers:
        futures = [workers.submit(refresh) for _ in range(2)]
        identifiers = [future.result(timeout=30) for future in futures]
    assert identifiers[0] == identifiers[1]

    def fail(connection, cursor, statement, parameters, context, executemany):
        if statement.startswith("INSERT INTO nammamove.gtfs_stop_times"):
            raise RuntimeError("injected normalized-row storage failure")

    event.listen(engine, "before_cursor_execute", fail)
    try:
        with pytest.raises(RuntimeError, match="injected normalized-row"):
            with Session(engine) as db, db.begin():
                ingest(db, archive(), manifest(version="must-rollback"))
    finally:
        event.remove(engine, "before_cursor_execute", fail)
    with Session(engine) as db:
        assert db.scalar(select(func.count()).select_from(TransitDataset)) == 1
        assert db.get(TransitFeed, "synthetic:simulation").active_dataset_id == identifiers[0]
        assert db.scalar(text("SELECT count(*) FROM nammamove.gtfs_stops")) == 2
