"""Synthetic fixed-route contracts, deliberately not Bengaluru/live observations."""

import io
from datetime import date, datetime, timedelta, timezone
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo

import httpx
import pytest
from app.transit.contracts import Manifest, RealtimeObservation
from app.transit.ingestion import activate, ingest
from app.transit.models import GtfsStop, TransitDataset, TransitFeed
from app.transit.providers import ProviderAdapter, ProviderUnavailable
from app.transit.validation import FeedRejected, service_active, validate_feed
from conftest import auth
from sqlalchemy import func, select
from sqlalchemy.orm import Session


def manifest(**changes):
    values = dict(
        provider="synthetic",
        data_mode="simulation",
        source_url="https://example.org/synthetic.zip",
        license_id="CC0-1.0",
        license_url="https://creativecommons.org/publicdomain/zero/1.0/",
        attribution="NammaMove synthetic test fixture; no real observations",
        authorization="simulation",
        authorization_reference="authored test fixture",
        publisher="NammaMove tests",
        authority="synthetic",
        retrieved_at=datetime.now(timezone.utc),
        version="fixture-v1",
    )
    values.update(changes)
    return Manifest(**values)


def tables():
    return {
        "agency.txt": "agency_id,agency_name,agency_url,agency_timezone\nA,Synthetic transit,https://example.org,Asia/Kolkata\n",
        "stops.txt": "stop_id,stop_name,stop_lat,stop_lon\nS1,Synthetic central,12.97,77.59\nS2,Synthetic east,12.98,77.60\n",
        "routes.txt": "route_id,agency_id,route_short_name,route_long_name,route_type\nR,A,TEST,Synthetic route,3\n",
        "calendar.txt": "service_id,monday,tuesday,wednesday,thursday,friday,saturday,sunday,start_date,end_date\nC,1,1,1,1,1,1,1,20260101,20261231\n",
        "calendar_dates.txt": "service_id,date,exception_type\nC,20260102,2\n",
        "trips.txt": "route_id,service_id,trip_id,direction_id,shape_id\nR,C,T,0,H\n",
        "stop_times.txt": "trip_id,arrival_time,departure_time,stop_id,stop_sequence\nT,24:50:00,24:50:00,S1,1\nT,25:10:00,25:10:00,S2,2\n",
        "shapes.txt": "shape_id,shape_pt_lat,shape_pt_lon,shape_pt_sequence,shape_dist_traveled\nH,12.97,77.59,1,0\nH,12.98,77.60,2,1500\n",
        "transfers.txt": "from_stop_id,to_stop_id,transfer_type,min_transfer_time\nS2,S1,2,120\n",
    }


def archive(values=None):
    buffer = io.BytesIO()
    with ZipFile(buffer, "w", ZIP_DEFLATED) as target:
        for name, contents in (tables() if values is None else values).items():
            member = ZipInfo(name, date_time=(2026, 1, 1, 0, 0, 0))
            member.compress_type = ZIP_DEFLATED
            target.writestr(member, contents)
    return buffer.getvalue()


def test_normalization_overnight_calendar_shapes_direction():
    data = validate_feed(archive())
    assert data.tables["stop_times"][-1]["arrival_seconds"] == 25 * 3600 + 600
    assert not service_active(
        data.tables["services"][0], data.tables["calendar_dates"], date(2026, 1, 2)
    )
    assert service_active(
        data.tables["services"][0], data.tables["calendar_dates"], date(2026, 1, 3)
    )
    assert data.report["network"]["directed_edge_sample"] == [["S1", "S2"]]
    assert data.tables["trips"][0]["direction_id"] == 0
    assert data.report["network"]["weak_components"] == 1
    assert len(data.tables["shape_points"]) == 2


@pytest.mark.parametrize(
    "file,old,new,code",
    [
        ("stops.txt", "12.97", "91", "invalid_stop_lat"),
        ("stops.txt", "12.97", "NaN", "invalid_stop_lat"),
        ("stop_times.txt", ",S2,", ",MISSING,", "missing_or_non_platform_stop_reference"),
        ("stop_times.txt", "25:10:00", "23:10:00", "inconsistent_trip_schedule"),
        ("trips.txt", "R,C,T", "MISSING,C,T", "missing_route_reference"),
        ("trips.txt", "R,C,T", "R,MISSING,T", "missing_service_reference"),
        ("trips.txt", ",0,H", ",2,H", "invalid_direction_id"),
        ("calendar.txt", "20261231", "20250101", "calendar_range_reversed"),
        ("shapes.txt", ",1500", ",-1", "invalid_shape_dist_traveled"),
        ("transfers.txt", ",120", ",", "missing_min_transfer_time"),
    ],
)
def test_invalid_feeds(file, old, new, code):
    values = tables()
    values[file] = values[file].replace(old, new)
    with pytest.raises(FeedRejected, match=code):
        validate_feed(archive(values))


@pytest.mark.parametrize(
    "file",
    [
        "stops.txt",
        "routes.txt",
        "trips.txt",
        "stop_times.txt",
        "calendar.txt",
        "calendar_dates.txt",
        "shapes.txt",
        "transfers.txt",
    ],
)
def test_duplicate_records(file):
    values = tables()
    values[file] += values[file].splitlines()[1] + "\n"
    with pytest.raises(FeedRejected, match="duplicate_record"):
        validate_feed(archive(values))


@pytest.mark.parametrize(
    "payload", [b"not a ZIP", archive({"../stops.txt": "bad"}), archive({"stops.txt": ""})]
)
def test_malformed_archives(payload):
    with pytest.raises(FeedRejected):
        validate_feed(payload)


def test_calendar_dates_only_and_frequencies():
    values = tables()
    del values["calendar.txt"]
    values["calendar_dates.txt"] = "service_id,date,exception_type\nC,20260102,2\nC,20260103,1\n"
    values["frequencies.txt"] = (
        "trip_id,start_time,end_time,headway_secs,exact_times\nT,24:00:00,26:00:00,600,0\n"
    )
    feed = validate_feed(archive(values))
    assert feed.tables["services"][0]["weekdays"] == 0
    assert feed.tables["frequencies"][0]["exact_times"] == 0
    values["frequencies.txt"] += "T,25:00:00,27:00:00,600,0\n"
    with pytest.raises(FeedRejected, match="overlapping_frequency_windows"):
        validate_feed(archive(values))


def test_atomic_quarantine_idempotence_and_rollback(secured):
    _, _, engine, *_ = secured
    with Session(engine) as db, db.begin():
        first = ingest(db, archive(), manifest())
        first_id = first.id
        assert ingest(db, archive(), manifest()).id == first_id
        rejected = ingest(db, b"broken", manifest())
        assert rejected.state == "quarantined"
        assert db.get(TransitFeed, "synthetic:simulation").active_dataset_id == first_id
        assert db.scalar(select(func.count()).select_from(GtfsStop)) == 2
        with pytest.raises(ValueError):
            activate(db, "synthetic:simulation", rejected.id)
        values = tables()
        values["stops.txt"] = values["stops.txt"].replace(
            "Synthetic east", "Synthetic east revised"
        )
        second = ingest(db, archive(values), manifest(version="fixture-v2"))
        assert db.get(TransitFeed, "synthetic:simulation").active_dataset_id == second.id
        activate(db, "synthetic:simulation", first_id)
        assert db.get(TransitFeed, "synthetic:simulation").active_dataset_id == first_id
        assert db.scalar(select(func.count()).select_from(GtfsStop)) == 4
    with Session(engine) as db:
        try:
            with db.begin():
                ingest(db, archive(), manifest(version="will-rollback"))
                raise RuntimeError("injected failure")
        except RuntimeError:
            pass
        assert db.scalar(select(func.count()).select_from(TransitDataset)) == 3


def test_protected_search_and_labels(secured):
    _, client, engine, token, *_ = secured
    with Session(engine) as db, db.begin():
        ingest(db, archive(), manifest())
    path = "/v1/transit/stops?provider=synthetic&mode=simulation"
    assert client.get(path).status_code == 401
    headers = auth(token())
    result = client.get(path, headers=headers)
    assert result.status_code == 200, result.text
    assert len(result.json()["stops"]) == 2
    assert result.json()["dataset"]["freshness"] == "simulation"
    assert result.json()["dataset"]["service_status"] == "unknown"
    assert client.get(path + "&q=%25", headers=headers).json()["stops"] == []
    assert client.get(path + "&latitude=12.97", headers=headers).status_code == 422
    assert client.get(path + "&latitude=12.97&longitude=77.59", headers=headers).status_code == 503
    assert client.get("/v1/transit/stops?provider=bmtc", headers=headers).status_code == 503
    result = client.get(
        "/v1/transit/routes?provider=synthetic&mode=simulation&stop_id=S2", headers=headers
    )
    assert result.json()["routes"][0]["external_id"] == "R"
    result = client.get(
        "/v1/transit/patterns?provider=synthetic&mode=simulation&route_id=R", headers=headers
    )
    assert [p["stop_id"] for p in result.json()["patterns"][0]["stops"]] == ["S1", "S2"]


def test_provider_outage_and_bounded_download():
    with httpx.Client(transport=httpx.MockTransport(lambda request: httpx.Response(503))) as client:
        for provider in ("bmtc", "bmrcl"):
            with pytest.raises(ProviderUnavailable, match="provider_not_configured"):
                ProviderAdapter(provider).fetch(client)
            with pytest.raises(ProviderUnavailable, match="provider_http_failure"):
                ProviderAdapter(provider, "https://example.org/feed.zip").fetch(client)

    def timeout(request):
        raise httpx.ReadTimeout("sensitive URL must not escape")

    with httpx.Client(transport=httpx.MockTransport(timeout)) as client:
        with pytest.raises(ProviderUnavailable, match="^provider_unavailable$"):
            ProviderAdapter("bmtc", "https://example.org/feed.zip").fetch(client)


@pytest.mark.parametrize(
    "seconds,expected", [(0, "live"), (300, "live"), (301, "stale"), (-31, "unavailable")]
)
def test_realtime_freshness_not_cancellation(seconds, expected):
    now = datetime.now(timezone.utc)
    assert (
        RealtimeObservation(observed_at=now - timedelta(seconds=seconds)).freshness(now) == expected
    )
    assert RealtimeObservation().freshness(now) == "unavailable"
    assert RealtimeObservation(mode="simulation").freshness(now) == "simulation"


def test_provenance_rejects_fabricated_schedule_and_future():
    for change in (
        {"data_mode": "scheduled"},
        {"retrieved_at": datetime.now(timezone.utc) + timedelta(days=1)},
        {"source_url": "https://user:secret@example.org/feed"},
    ):
        with pytest.raises(ValueError):
            manifest(**change)


def test_date_filtered_patterns_and_transfers(secured):
    _, client, engine, token, *_ = secured
    with Session(engine) as db, db.begin():
        ingest(db, archive(), manifest())
    headers = auth(token())
    path = "/v1/transit/patterns?provider=synthetic&mode=simulation&route_id=R"
    assert client.get(path + "&service_date=2026-01-02", headers=headers).json()["patterns"] == []
    assert (
        len(client.get(path + "&service_date=2026-01-03", headers=headers).json()["patterns"]) == 1
    )
    assert client.get(path + "&service_date=2025-12-31", headers=headers).json()["patterns"] == []
    result = client.get(
        "/v1/transit/transfers?provider=synthetic&mode=simulation&stop_id=S2", headers=headers
    ).json()
    assert result["transfers"][0]["min_transfer_seconds"] == 120
    assert result["inferred_walking_links"] is False


def test_staged_import_and_provider_mode_isolation(secured):
    _, _, engine, *_ = secured
    with Session(engine) as db, db.begin():
        staged = ingest(db, archive(), manifest(), promote=False)
        assert db.get(TransitFeed, "synthetic:simulation").active_dataset_id is None
        activate(db, "synthetic:simulation", staged.id)
        source = manifest(
            provider="bmtc",
            data_mode="scheduled",
            authorization="open",
            authority="community",
            quality_notes=["Synthetic input used solely to test scheduled-provider isolation."],
        )
        scheduled = ingest(db, archive(), source)
        assert db.get(TransitFeed, "bmtc:scheduled").active_dataset_id == scheduled.id
        assert db.get(TransitFeed, "synthetic:simulation").active_dataset_id == staged.id
        with pytest.raises(ValueError):
            activate(db, "bmtc:scheduled", staged.id)
        wrong = manifest(
            provider="bmrcl", data_mode="scheduled", authorization="authorized", authority="agency"
        )
        rejected = ingest(db, archive(), wrong)
        assert rejected.report["errors"][0]["code"] == "provider_route_type_mismatch"
        assert db.get(TransitFeed, "bmrcl:scheduled").active_dataset_id is None


def test_zip_budget_and_unavailable_optional_tables(monkeypatch):
    import app.transit.validation as validation

    monkeypatch.setattr(validation, "MAX_ZIP_BYTES", 10)
    with pytest.raises(FeedRejected, match="archive_too_large"):
        validate_feed(archive())
    monkeypatch.setattr(validation, "MAX_ZIP_BYTES", 50 * 1024 * 1024)
    values = tables()
    del values["shapes.txt"]
    del values["transfers.txt"]
    values["trips.txt"] = values["trips.txt"].replace(",0,H", ",0,")
    feed = validate_feed(archive(values))
    assert "transfers_not_provided" in feed.report["warnings"]
    assert "shapes_not_provided" in feed.report["warnings"]
    assert feed.report["network"]["transfer_edges"] == 0


def test_scoped_transfer_respects_station_hierarchy_and_served_routes():
    values = tables()
    values["stops.txt"] = (
        "stop_id,stop_name,stop_lat,stop_lon,location_type,parent_station\nS1,Synthetic central,12.97,77.59,0,ST\nS2,Synthetic east,12.98,77.60,0,\nST,Synthetic station,12.97,77.59,1,\nUNUSED,Synthetic unused,12.99,77.61,0,\n"
    )
    values["transfers.txt"] = (
        "from_stop_id,to_stop_id,transfer_type,min_transfer_time,from_route_id,from_trip_id\nST,S2,2,120,R,T\n"
    )
    assert validate_feed(archive(values)).tables["transfers"][0]["from_stop_id"] == "ST"
    values["transfers.txt"] = values["transfers.txt"].replace(
        "ST,S2,2,120,R,T", "UNUSED,S2,2,120,R,"
    )
    with pytest.raises(FeedRejected, match="inconsistent_transfer_stop"):
        validate_feed(archive(values))


def test_read_only_coverage_audit_distinguishes_direction_and_overnight(secured):
    from app.transit.audit import audit_dataset

    _, _, engine, *_ = secured
    with Session(engine) as db, db.begin():
        dataset = ingest(db, archive(), manifest())
        before = db.scalar(select(func.count()).select_from(TransitDataset))
        report = audit_dataset(db, dataset.id)
        assert report["counts"]["operators"] == 1
        assert report["checks"]["overnight_trip_count"] == 1
        assert report["checks"]["weak_components_with_explicit_transfers"] == 1
        assert report["routes"][0]["longest_direction_patterns_reverse"] is False
        assert report["routes"][0]["agency_direction_mapping_verified"] is False
        assert report["interpretation"]["agency_schedule_accuracy_verified"] is False
        assert db.scalar(select(func.count()).select_from(TransitDataset)) == before


def test_pattern_response_exposes_approximate_times(secured):
    _, client, engine, token, *_ = secured
    values = tables()
    values["stop_times.txt"] = (
        values["stop_times.txt"]
        .replace("stop_sequence\n", "stop_sequence,timepoint\n")
        .replace(",S1,1\n", ",S1,1,0\n")
        .replace(",S2,2\n", ",S2,2,1\n")
    )
    with Session(engine) as db, db.begin():
        ingest(db, archive(values), manifest())
    result = client.get(
        "/v1/transit/patterns?provider=synthetic&mode=simulation&route_id=R", headers=auth(token())
    ).json()
    points = result["patterns"][0]["stops"]
    assert points[0]["timepoint"] == 0 and points[0]["timing_precision"] == "approximate"
    assert points[1]["timing_precision"] == "source_timepoint"
    assert result["dataset"]["agency_schedule_accuracy_verified"] is False


@pytest.mark.parametrize("directed,expected", [(False, 2), (True, 4)])
def test_connectivity_audit_does_not_confuse_weak_and_strong(directed, expected):
    from app.transit.audit import component_count

    assert (
        component_count({"a", "b", "c", "isolated"}, {("a", "b"), ("b", "c")}, directed=directed)
        == expected
    )
    assert (
        component_count({"a", "b", "c"}, {("a", "b"), ("b", "c"), ("c", "a")}, directed=True) == 1
    )
