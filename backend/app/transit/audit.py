"""Read-only, reproducible catalog audit; internal checks are not agency certification."""

import argparse
import json
import math
from collections import Counter, defaultdict
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from sqlalchemy import select, text
from sqlalchemy.orm import Session

from ..config import Settings
from ..database import Database
from . import models as m


def component_count(nodes: set[str], edges: set[tuple[str, str]], *, directed: bool) -> int:
    """Count weak or strong components iteratively, without recursion limits."""
    adjacency: dict[str, set[str]] = {node: set() for node in nodes}
    reverse: dict[str, set[str]] = {node: set() for node in nodes}
    for origin, target in edges:
        if origin not in nodes or target not in nodes:
            continue
        adjacency[origin].add(target)
        reverse[target].add(origin)
        if not directed:
            adjacency[target].add(origin)
            reverse[origin].add(target)
    visited: set[str] = set()
    order: list[str] = []
    for node in sorted(nodes):
        stack = [(node, False)]
        while stack:
            current, finished = stack.pop()
            if finished:
                order.append(current)
            elif current not in visited:
                visited.add(current)
                stack.append((current, True))
                stack.extend(
                    (neighbor, False) for neighbor in adjacency[current] if neighbor not in visited
                )
    visited.clear()
    components = 0
    for node in reversed(order):
        if node in visited:
            continue
        components += 1
        pending = [node]
        while pending:
            current = pending.pop()
            if current not in visited:
                visited.add(current)
                pending.extend(reverse[current] - visited)
    return components


def audit_dataset(db: Session, dataset_id: UUID) -> dict[str, Any]:
    dataset = db.get(m.TransitDataset, dataset_id)
    if dataset is None or dataset.state != "validated":
        raise ValueError("A readable validated dataset is required")
    feed = db.get(m.TransitFeed, dataset.feed_id)
    assert feed is not None

    def rows(model: Any) -> list[Any]:
        return list(db.scalars(select(model).where(model.dataset_id == dataset.id)))

    stops = {stop.external_id: stop for stop in rows(m.GtfsStop)}
    routes = rows(m.GtfsRoute)
    trips = {trip.external_id: trip for trip in rows(m.GtfsTrip)}
    services = {service.external_id for service in rows(m.GtfsService)}
    times: dict[str, list[m.GtfsStopTime]] = defaultdict(list)
    all_times = rows(m.GtfsStopTime)
    for point in all_times:
        times[point.trip_id].append(point)
    for points in times.values():
        points.sort(key=lambda point: point.sequence)

    def physical(stop_id: str) -> str:
        stop = stops[stop_id]
        return stop.parent_station or stop_id

    edges: set[tuple[str, str]] = set()
    served: set[str] = set()
    reversed_time_trips = 0
    orphan_time_references = 0
    overnight_trips = 0
    for key, points in times.items():
        previous = -1
        reversed_time = False
        overnight = False
        for point in points:
            if key not in trips or point.stop_id not in stops:
                orphan_time_references += 1
                continue
            served.add(point.stop_id)
            if point.arrival_seconds is not None and point.departure_seconds is not None:
                reversed_time |= (
                    point.arrival_seconds < previous
                    or point.departure_seconds < point.arrival_seconds
                )
                previous = point.departure_seconds
                overnight |= point.departure_seconds >= 86400
        reversed_time_trips += int(reversed_time)
        overnight_trips += int(overnight)
        edges.update(
            (a.stop_id, b.stop_id)
            for a, b in zip(points, points[1:])
            if a.stop_id in stops and b.stop_id in stops
        )
    transfers = rows(m.GtfsTransfer)
    transfer_edges = {
        (t.from_stop_id, t.to_stop_id)
        for t in transfers
        if t.transfer_type != 3 and t.from_stop_id in stops and t.to_stop_id in stops
    }
    route_reports = []
    route_station_sets: dict[str, set[str]] = {}
    for route in sorted(routes, key=lambda route: route.external_id):
        selected = [trip for trip in trips.values() if trip.route_id == route.external_id]
        ordered: dict[int, tuple[str, ...]] = {}
        for direction in (0, 1):
            patterns = [
                tuple(
                    physical(point.stop_id)
                    for point in times[trip.external_id]
                    if point.stop_id in stops
                )
                for trip in selected
                if trip.direction_id == direction
            ]
            ordered[direction] = max(
                patterns, key=lambda pattern: (len(pattern), pattern), default=()
            )
        stations = {
            physical(point.stop_id)
            for trip in selected
            for point in times[trip.external_id]
            if point.stop_id in stops
        }
        route_station_sets[route.external_id] = stations
        route_reports.append(
            {
                "route_id": route.external_id,
                "name": route.long_name,
                "trip_count": len(selected),
                "physical_station_count": len(stations),
                "direction_trip_counts": {
                    str(direction): sum(t.direction_id == direction for t in selected)
                    for direction in (0, 1, None)
                },
                "longest_direction_patterns_reverse": bool(
                    ordered[0] and ordered[0] == tuple(reversed(ordered[1]))
                ),
                "agency_direction_mapping_verified": False,
            }
        )
    shapes = rows(m.GtfsShapePoint)
    invalid_coordinates = sum(
        not (
            math.isfinite(s.latitude)
            and math.isfinite(s.longitude)
            and -90 <= s.latitude <= 90
            and -180 <= s.longitude <= 180
        )
        for s in [*stops.values(), *shapes]
    )
    # A broad screening rectangle only; not an authoritative service-area polygon.
    outside_screen = sum(
        not (12.5 <= s.latitude <= 13.5 and 77.0 <= s.longitude <= 78.2) for s in stops.values()
    )
    return {
        "audited_at": datetime.now(timezone.utc).isoformat(),
        "environment": "explicitly selected database; not city-wide inventory",
        "provider": feed.provider,
        "data_mode": feed.data_mode,
        "authority": dataset.authority,
        "dataset_id": str(dataset.id),
        "active": feed.active_dataset_id == dataset.id,
        "source_url": dataset.source_url,
        "checksum": dataset.checksum,
        "source_version": dataset.version,
        "license_id": dataset.license_id,
        "attribution": dataset.attribution,
        "quality_notes": dataset.quality_notes,
        "service_start": str(dataset.service_start),
        "service_end": str(dataset.service_end),
        "counts": {
            "operators": len(rows(m.GtfsAgency)),
            "routes": len(routes),
            "stops": len(stops),
            "trips": len(trips),
            "stop_times": len(all_times),
            "transfers": len(transfers),
            "shape_points": len(shapes),
            "stop_location_types": {
                str(k): v
                for k, v in sorted(Counter(s.location_type for s in stops.values()).items())
            },
        },
        "routes": route_reports,
        "route_pair_shared_station_counts": {
            a + ":" + b: len(route_station_sets[a] & route_station_sets[b])
            for a in sorted(route_station_sets)
            for b in sorted(route_station_sets)
            if a < b
        },
        "checks": {
            "invalid_coordinates": invalid_coordinates,
            "outside_advisory_bengaluru_rectangle": outside_screen,
            "orphan_stop_time_references": orphan_time_references,
            "orphan_trip_service_references": sum(
                t.service_id not in services for t in trips.values()
            ),
            "orphan_transfer_stop_references": sum(
                t.from_stop_id not in stops or t.to_stop_id not in stops for t in transfers
            ),
            "trip_time_regressions": reversed_time_trips,
            "overnight_trip_count": overnight_trips,
            "timepoint_counts": {
                str(k): v for k, v in sorted(Counter(t.timepoint for t in all_times).items())
            },
            "directed_ride_edges": len(edges),
            "allowed_transfer_edges": len(transfer_edges),
            "weak_components_with_explicit_transfers": component_count(
                served, edges | transfer_edges, directed=False
            ),
            "strong_components_with_explicit_transfers": component_count(
                served, edges | transfer_edges, directed=True
            ),
        },
        "interpretation": {
            "agency_schedule_accuracy_verified": False,
            "geographic_screen_is_official_boundary": False,
            "missing_provider_means_cancelled": False,
            "walking_or_accessibility_feasibility_verified": False,
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Read-only audit of an existing validated static snapshot; use maintenance connection"
    )
    parser.add_argument("--dataset", type=UUID, required=True)
    args = parser.parse_args()
    database = Database(Settings())
    if database.sessions is None:
        parser.error("DATABASE_URL is required")
    try:
        with database.sessions.begin() as db:
            db.execute(text("SET TRANSACTION READ ONLY"))
            report = audit_dataset(db, args.dataset)
        print(json.dumps(report, indent=2))
    finally:
        database.dispose()


if __name__ == "__main__":
    main()
