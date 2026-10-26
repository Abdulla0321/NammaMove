"""Bounded GTFS fixed-route validation. Never invent times or reverse links."""

import csv
import io
import math
import re
import stat
import unicodedata
from collections import defaultdict
from dataclasses import dataclass
from datetime import date, datetime
from typing import Any, NoReturn
from zipfile import BadZipFile, ZipFile

MAX_ZIP_BYTES = 50 * 1024 * 1024
MAX_EXPANDED_BYTES = 256 * 1024 * 1024
MAX_ROWS = 2_000_000
MAX_TIME = 168 * 3600 - 1
RowData = dict[str, Any]


class FeedRejected(ValueError):
    def __init__(self, code: str, file: str = "archive", row: int = 0) -> None:
        self.code, self.file, self.row = code, file, row
        super().__init__(code)

    def report(self) -> dict[str, object]:
        return {
            "errors": [
                {
                    "code": self.code,
                    "file": self.file
                    if self.file
                    in {
                        "agency.txt",
                        "stops.txt",
                        "routes.txt",
                        "trips.txt",
                        "stop_times.txt",
                        "calendar.txt",
                        "calendar_dates.txt",
                        "shapes.txt",
                        "transfers.txt",
                        "frequencies.txt",
                    }
                    else "archive",
                    "row": self.row,
                }
            ],
            "warnings": [],
        }


@dataclass
class Row:
    values: dict[str, str]
    file: str
    line: int

    def fail(self, code: str) -> NoReturn:
        raise FeedRejected(code, self.file, self.line)

    def text(self, key: str, default: str = "", *, required: bool = False, limit: int = 200) -> str:
        value = self.values.get(key, default)
        if (required and not value) or len(value) > limit or any(ord(c) < 32 for c in value):
            self.fail("invalid_" + key)
        return value

    def integer(
        self, key: str, default: str = "", *, low: int = 0, high: int = 2_147_483_647
    ) -> int:
        raw = self.text(key, default) or default
        if not re.fullmatch(r"[0-9]+", raw):
            self.fail("invalid_" + key)
        value = int(raw)
        if not low <= value <= high:
            self.fail("invalid_" + key)
        return value

    def number(self, key: str, *, low: float, high: float) -> float:
        try:
            value = float(self.text(key, required=True))
        except ValueError:
            self.fail("invalid_" + key)
            raise AssertionError("unreachable")
        if not math.isfinite(value) or not low <= value <= high:
            self.fail("invalid_" + key)
        return value

    def seconds(self, key: str) -> int | None:
        raw = self.text(key)
        if not raw:
            return None
        match = re.fullmatch(r"([0-9]{1,3}):([0-5][0-9]):([0-5][0-9])", raw)
        if not match:
            self.fail("invalid_" + key)
            raise AssertionError("unreachable")
        value = int(match[1]) * 3600 + int(match[2]) * 60 + int(match[3])
        if value > MAX_TIME:
            self.fail("unsupported_service_day_duration")
        return value

    def day(self, key: str) -> date:
        raw = self.text(key, required=True)
        try:
            if not re.fullmatch(r"[0-9]{8}", raw):
                raise ValueError
            return datetime.strptime(raw, "%Y%m%d").date()
        except ValueError:
            self.fail("invalid_" + key)
            raise AssertionError("unreachable")


@dataclass
class ValidatedFeed:
    tables: dict[str, list[RowData]]
    service_start: date
    service_end: date
    report: dict[str, object]


def read_archive(payload: bytes) -> dict[str, list[Row]]:
    if len(payload) > MAX_ZIP_BYTES:
        raise FeedRejected("archive_too_large")
    try:
        archive = ZipFile(io.BytesIO(payload))
    except (BadZipFile, OSError):
        raise FeedRejected("invalid_zip") from None
    with archive:
        members = archive.infolist()
        if len(members) > 100 or sum(i.file_size for i in members) > MAX_EXPANDED_BYTES:
            raise FeedRejected("expanded_archive_too_large")
        seen: set[str] = set()
        files: dict[str, list[Row]] = {}
        count = 0
        for member in members:
            name = member.filename
            if (
                member.is_dir()
                or "/" in name
                or "\\" in name
                or name in {".", ".."}
                or name in seen
                or member.flag_bits & 1
                or stat.S_ISLNK(member.external_attr >> 16)
            ):
                raise FeedRejected("unsafe_or_duplicate_zip_member")
            seen.add(name)
            if not name.endswith(".txt"):
                continue
            if member.file_size > MAX_EXPANDED_BYTES or (
                member.compress_size and member.file_size / member.compress_size > 1000
            ):
                raise FeedRejected("suspicious_compression_ratio")
            try:
                source = archive.read(member).decode("utf-8-sig")
                reader = csv.DictReader(io.StringIO(source, newline=""), strict=True)
                headers = reader.fieldnames
                if (
                    not headers
                    or any(not h for h in headers)
                    or len({h.strip() for h in headers}) != len(headers)
                ):
                    raise FeedRejected("invalid_csv_header", name)
                reader.fieldnames = [h.strip() for h in headers]
                rows = []
                for raw in reader:
                    count += 1
                    if count > MAX_ROWS:
                        raise FeedRejected("row_budget_exceeded", name)
                    if None in raw or any(value is None for value in raw.values()):
                        raise FeedRejected("invalid_csv_width", name, reader.line_num)
                    values = {
                        str(k): unicodedata.normalize("NFC", str(v).strip()) for k, v in raw.items()
                    }
                    if any(len(v) > 2000 or any(ord(c) < 32 for c in v) for v in values.values()):
                        raise FeedRejected("invalid_field_text", name, reader.line_num)
                    rows.append(Row(values, name, reader.line_num))
                files[name] = rows
            except FeedRejected:
                raise
            except (
                UnicodeError,
                csv.Error,
                BadZipFile,
                RuntimeError,
                NotImplementedError,
                OSError,
            ):
                raise FeedRejected("invalid_csv_or_encoding", name) from None
    for required in ("agency.txt", "stops.txt", "routes.txt", "trips.txt", "stop_times.txt"):
        if not files.get(required):
            raise FeedRejected("missing_or_empty_required_table", required)
    if not files.get("calendar.txt") and not files.get("calendar_dates.txt"):
        raise FeedRejected("missing_service_calendar")
    return files


def unique(row: Row, seen: set[object], key: object) -> None:
    if key in seen:
        row.fail("duplicate_record")
    seen.add(key)


def validate_feed(payload: bytes) -> ValidatedFeed:
    files = read_archive(payload)
    tables: dict[str, list[RowData]] = {
        name: []
        for name in (
            "agencies",
            "stops",
            "routes",
            "services",
            "calendar_dates",
            "shapes",
            "shape_points",
            "trips",
            "stop_times",
            "transfers",
            "frequencies",
        )
    }
    warnings: list[str] = []
    agencies: dict[str, RowData] = {}
    for r in files["agency.txt"]:
        key = r.text("agency_id", "default", required=True)
        if key in agencies:
            r.fail("duplicate_record")
        zone = r.text("agency_timezone", required=True)
        if zone not in {"Asia/Kolkata", "Asia/Calcutta"}:
            r.fail("unsupported_timezone")
        agencies[key] = {
            "external_id": key,
            "name": r.text("agency_name", required=True),
            "url": r.text("agency_url", required=True, limit=500),
            "timezone": "Asia/Kolkata",
        }
    tables["agencies"] = list(agencies.values())
    stops: dict[str, RowData] = {}
    for r in files["stops.txt"]:
        key = r.text("stop_id", required=True)
        if key in stops:
            r.fail("duplicate_record")
        stops[key] = {
            "external_id": key,
            "name": r.text("stop_name", required=True),
            "latitude": r.number("stop_lat", low=-90, high=90),
            "longitude": r.number("stop_lon", low=-180, high=180),
            "location_type": r.integer("location_type", "0", high=4),
            "parent_station": r.text("parent_station") or None,
            "wheelchair_boarding": r.integer("wheelchair_boarding", "0", high=2),
        }
    for station in stops.values():
        parent = station["parent_station"]
        if parent and (
            parent not in stops
            or stops[parent]["location_type"] != 1
            or parent == station["external_id"]
            or station["location_type"] == 1
        ):
            raise FeedRejected("invalid_parent_station", "stops.txt")
    tables["stops"] = list(stops.values())
    routes: dict[str, RowData] = {}
    for r in files["routes.txt"]:
        key = r.text("route_id", required=True)
        if key in routes:
            r.fail("duplicate_record")
        agency = r.text("agency_id") or (next(iter(agencies)) if len(agencies) == 1 else "")
        if agency not in agencies:
            r.fail("missing_agency_reference")
        short, long = r.text("route_short_name"), r.text("route_long_name")
        if not short and not long:
            r.fail("missing_route_name")
        kind = r.integer("route_type", high=3)
        routes[key] = {
            "external_id": key,
            "agency_id": agency,
            "short_name": short,
            "long_name": long,
            "route_type": kind,
        }
    tables["routes"] = list(routes.values())
    services: dict[str, RowData] = {}
    weekdays = ("monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday")
    for r in files.get("calendar.txt", []):
        key = r.text("service_id", required=True)
        if key in services:
            r.fail("duplicate_record")
        start, end = r.day("start_date"), r.day("end_date")
        if end < start:
            r.fail("calendar_range_reversed")
        mask = sum(r.integer(day, high=1) << i for i, day in enumerate(weekdays))
        services[key] = {"external_id": key, "weekdays": mask, "start_date": start, "end_date": end}
    seen: set[object] = set()
    exceptions: dict[str, list[date]] = defaultdict(list)
    for r in files.get("calendar_dates.txt", []):
        key = r.text("service_id", required=True)
        day = r.day("date")
        unique(r, seen, (key, day))
        kind = r.integer("exception_type", low=1, high=2)

        exceptions[key].append(day)
        tables["calendar_dates"].append({"service_id": key, "date": day, "exception_type": kind})
    for key, days in exceptions.items():
        if key not in services and not any(
            e["service_id"] == key and e["exception_type"] == 1 for e in tables["calendar_dates"]
        ):
            raise FeedRejected("removal_without_service_calendar", "calendar_dates.txt")
        if key not in services:
            services[key] = {
                "external_id": key,
                "weekdays": 0,
                "start_date": min(days),
                "end_date": max(days),
            }
    tables["services"] = list(services.values())
    shape_groups: dict[str, list[RowData]] = defaultdict(list)
    seen = set()
    for r in files.get("shapes.txt", []):
        key = r.text("shape_id", required=True)
        sequence = r.integer("shape_pt_sequence")
        unique(r, seen, (key, sequence))
        distance = (
            r.number("shape_dist_traveled", low=0, high=1e12)
            if r.text("shape_dist_traveled")
            else None
        )
        shape_groups[key].append(
            {
                "shape_id": key,
                "sequence": sequence,
                "latitude": r.number("shape_pt_lat", low=-90, high=90),
                "longitude": r.number("shape_pt_lon", low=-180, high=180),
                "distance": distance,
            }
        )
    for key, points in shape_groups.items():
        points.sort(key=lambda p: p["sequence"])
        if len(points) < 2:
            raise FeedRejected("shape_needs_two_points", "shapes.txt")
        previous = -1.0
        for point in points:
            if point["distance"] is not None:
                if point["distance"] < previous:
                    raise FeedRejected("shape_distance_reversed", "shapes.txt")
                previous = point["distance"]
        tables["shapes"].append({"external_id": key})
        tables["shape_points"].extend(points)
    trips: dict[str, RowData] = {}
    for r in files["trips.txt"]:
        key = r.text("trip_id", required=True)
        if key in trips:
            r.fail("duplicate_record")
        route, service, shape = (
            r.text("route_id", required=True),
            r.text("service_id", required=True),
            r.text("shape_id") or None,
        )
        if route not in routes:
            r.fail("missing_route_reference")
        if service not in services:
            r.fail("missing_service_reference")
        if shape and shape not in shape_groups:
            r.fail("missing_shape_reference")
        direction = r.integer("direction_id", high=1) if r.text("direction_id") else None
        trips[key] = {
            "external_id": key,
            "route_id": route,
            "service_id": service,
            "shape_id": shape,
            "direction_id": direction,
            "headsign": r.text("trip_headsign"),
        }
    tables["trips"] = list(trips.values())
    times: dict[str, list[RowData]] = defaultdict(list)
    seen = set()
    for r in files["stop_times.txt"]:
        trip, stop = r.text("trip_id", required=True), r.text("stop_id", required=True)
        if trip not in trips:
            r.fail("missing_trip_reference")
        if stop not in stops or stops[stop]["location_type"] != 0:
            r.fail("missing_or_non_platform_stop_reference")
        sequence = r.integer("stop_sequence")
        unique(r, seen, (trip, sequence))
        arrival, departure = r.seconds("arrival_time"), r.seconds("departure_time")
        timepoint = r.integer("timepoint", "1", high=1)
        if (
            (arrival is None) != (departure is None)
            or (arrival is None and timepoint != 0)
            or (arrival is not None and departure is not None and departure < arrival)
        ):
            r.fail("invalid_stop_time_interval")
        if (
            any(
                r.text(key) not in {"", "1"} for key in ("continuous_pickup", "continuous_drop_off")
            )
            or r.text("start_pickup_drop_off_window")
            or r.text("end_pickup_drop_off_window")
        ):
            r.fail("unsupported_flex_or_continuous_service")
        times[trip].append(
            {
                "trip_id": trip,
                "sequence": sequence,
                "stop_id": stop,
                "arrival_seconds": arrival,
                "departure_seconds": departure,
                "timepoint": timepoint,
                "pickup_type": r.integer("pickup_type", "0", high=3),
                "drop_off_type": r.integer("drop_off_type", "0", high=3),
            }
        )
    trip_stops: dict[str, set[str]] = {}
    route_stops: dict[str, set[str]] = defaultdict(set)
    edges: set[tuple[str, str]] = set()
    served: set[str] = set()
    for key in trips:
        points = sorted(times.get(key, []), key=lambda p: p["sequence"])
        if (
            len(points) < 2
            or points[0]["arrival_seconds"] is None
            or points[-1]["arrival_seconds"] is None
        ):
            raise FeedRejected("trip_needs_timed_endpoints", "stop_times.txt")
        previous = -1
        for point in points:
            if point["arrival_seconds"] is not None:
                if point["arrival_seconds"] < previous:
                    raise FeedRejected("inconsistent_trip_schedule", "stop_times.txt")
                previous = point["departure_seconds"]
            served.add(point["stop_id"])
        edges.update((a["stop_id"], b["stop_id"]) for a, b in zip(points, points[1:]))
        trip_stops[key] = {p["stop_id"] for p in points}
        trip_stops[key].update(
            stops[p["stop_id"]]["parent_station"]
            for p in points
            if stops[p["stop_id"]]["parent_station"]
        )
        route_stops[trips[key]["route_id"]].update(trip_stops[key])
        tables["stop_times"].extend(points)
    seen = set()
    transfer_edges: set[tuple[str, str]] = set()
    for r in files.get("transfers.txt", []):
        origin, target = r.text("from_stop_id", required=True), r.text("to_stop_id", required=True)
        if origin not in stops or target not in stops:
            r.fail("missing_transfer_stop")
        kind = r.integer("transfer_type", "0", high=3)
        qualifiers = {
            key: r.text(key)
            for key in ("from_route_id", "to_route_id", "from_trip_id", "to_trip_id")
        }
        for field, value in qualifiers.items():
            if value and value not in (trips if "trip" in field else routes):
                r.fail("missing_transfer_scope")
        for prefix in ("from", "to"):
            trip_id, route_id = qualifiers[prefix + "_trip_id"], qualifiers[prefix + "_route_id"]
            if trip_id and route_id and trips[trip_id]["route_id"] != route_id:
                r.fail("inconsistent_transfer_scope")
            scoped_stop = origin if prefix == "from" else target
            if route_id and scoped_stop not in route_stops[route_id]:
                r.fail("inconsistent_transfer_stop")
            if trip_id and scoped_stop not in trip_stops[trip_id]:
                r.fail("inconsistent_transfer_stop")
        unique(r, seen, (origin, target, *qualifiers.values()))
        minimum = r.integer("min_transfer_time") if r.text("min_transfer_time") else None
        if kind == 2 and minimum is None:
            r.fail("missing_min_transfer_time")
        tables["transfers"].append(
            {
                "from_stop_id": origin,
                "to_stop_id": target,
                "transfer_type": kind,
                "min_transfer_seconds": minimum,
                **qualifiers,
            }
        )
        if kind != 3:
            transfer_edges.add((origin, target))
    windows: dict[str, list[tuple[int, int]]] = defaultdict(list)
    seen = set()
    for r in files.get("frequencies.txt", []):
        trip = r.text("trip_id", required=True)
        if trip not in trips:
            r.fail("missing_frequency_trip")
        window_start, window_end = r.seconds("start_time"), r.seconds("end_time")
        if window_start is None or window_end is None or window_end <= window_start:
            r.fail("invalid_frequency_window")
        unique(r, seen, (trip, window_start))
        windows[trip].append((window_start, window_end))
        tables["frequencies"].append(
            {
                "trip_id": trip,
                "start_seconds": window_start,
                "end_seconds": window_end,
                "headway_seconds": r.integer("headway_secs", low=1),
                "exact_times": r.integer("exact_times", "0", high=1),
            }
        )
    for spans in windows.values():
        spans.sort()
        if any(b[0] < a[1] for a, b in zip(spans, spans[1:])):
            raise FeedRejected("overlapping_frequency_windows", "frequencies.txt")
    parents = {key: key for key in stops}

    def root(key: str) -> str:
        while parents[key] != key:
            parents[key] = parents[parents[key]]
            key = parents[key]
        return key

    for a, b in edges | transfer_edges:
        parents[root(a)] = root(b)
    components = len({root(key) for key in served})
    if components > 1:
        warnings.append("disconnected_network")
    if "transfers.txt" not in files:
        warnings.append("transfers_not_provided")
    if "shapes.txt" not in files:
        warnings.append("shapes_not_provided")
    if any(p["arrival_seconds"] is None for p in tables["stop_times"]):
        warnings.append("untimed_intermediate_stops_preserved")
    supported = {
        "agency.txt",
        "stops.txt",
        "routes.txt",
        "trips.txt",
        "stop_times.txt",
        "calendar.txt",
        "calendar_dates.txt",
        "shapes.txt",
        "transfers.txt",
        "frequencies.txt",
    }
    if set(files) - supported:
        warnings.append("optional_tables_not_imported")
    report: dict[str, object] = {
        "errors": [],
        "warnings": warnings,
        "counts": {key: len(value) for key, value in tables.items()},
        "network": {
            "directed_edge_count": len(edges),
            "weak_components": components,
            "unserved_platforms": sum(
                s["location_type"] == 0 and key not in served for key, s in stops.items()
            ),
            "transfer_edges": len(transfer_edges),
            "directed_edge_sample": [list(edge) for edge in sorted(edges)[:20]],
            "structural_only": True,
        },
    }
    starts = [s["start_date"] for s in services.values()] + [
        day for days in exceptions.values() for day in days
    ]
    ends = [s["end_date"] for s in services.values()] + [
        day for days in exceptions.values() for day in days
    ]
    return ValidatedFeed(tables, min(starts), max(ends), report)


def service_active(service: RowData, exceptions: list[RowData], day: date) -> bool:
    for exception in exceptions:
        if exception["service_id"] == service["external_id"] and exception["date"] == day:
            return bool(exception["exception_type"] == 1)
    return bool(
        service["start_date"] <= day <= service["end_date"]
        and service["weekdays"] & (1 << day.weekday())
    )
