"""Independently authored CC0 synthetic GTFS and geographic grid; not real streets."""

import argparse
import csv
import hashlib
import io
import json
import struct
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo

OTP_IMAGE = "opentripplanner/opentripplanner:2.7.0@sha256:640870b240ad206d05634e7a066588804c6e23abebf37cbc02b0c9ba66073486"


def varint(value: int) -> bytes:
    result = bytearray()
    while value > 127:
        result.append((value & 127) | 128)
        value >>= 7
    result.append(value)
    return bytes(result)


def field(number: int, value: bytes | int) -> bytes:
    return varint(number << 3 | (2 if isinstance(value, bytes) else 0)) + (
        varint(len(value)) + value if isinstance(value, bytes) else varint(value)
    )


def zig(value: int) -> int:
    return value * 2 if value >= 0 else -value * 2 - 1


def pbf() -> bytes:
    """Small uncompressed OSM-PBF encoder for this authored fixture only."""
    strings = [
        "",
        "highway",
        "residential",
        "foot",
        "yes",
        "wheelchair",
        "surface",
        "asphalt",
        "name",
        "SYNTHETIC test street",
    ]
    table = b"".join(field(1, item.encode()) for item in strings)
    group = bytearray()
    for row in range(4):
        for col in range(41):
            identifier = row * 41 + col + 1
            latitude, longitude = 12.97 + row * 0.001, 77.59 + col * 0.001
            node = (
                field(1, zig(identifier))
                + field(8, zig(round(latitude * 1e7)))
                + field(9, zig(round(longitude * 1e7)))
            )
            group.extend(field(1, node))
    paths = [[row * 41 + col + 1 for col in range(41)] for row in range(4)]
    paths += [[row * 41 + col + 1 for row in range(4)] for col in range(41)]
    for identifier, refs in enumerate(paths, 1):
        previous = 0
        deltas = bytearray()
        for ref in refs:
            deltas.extend(varint(zig(ref - previous)))
            previous = ref
        way = (
            field(1, identifier)
            + field(2, bytes([1, 3, 5, 6, 8]))
            + field(3, bytes([2, 4, 4, 7, 9]))
            + field(8, bytes(deltas))
        )
        group.extend(field(3, way))

    def block(kind: str, payload: bytes) -> bytes:
        blob = field(1, payload)
        header = field(1, kind.encode()) + field(3, len(blob))
        return struct.pack(">I", len(header)) + header + blob

    return block("OSMHeader", field(4, b"OsmSchema-V0.6")) + block(
        "OSMData", field(1, table) + field(2, bytes(group))
    )


def make_fixture(target: Path) -> dict[str, object]:
    target.mkdir(parents=True, exist_ok=True)
    # Coordinates are authored grid points, not actual Bengaluru stops/roads.
    stops = {
        "A": (12.970, 77.590),
        "B": (12.970, 77.600),
        "C": (12.971, 77.600),
        "D": (12.971, 77.620),
    }
    stop_rows: list[list[str | int | float]] = [
        [key, "SIMULATION " + key, lat, lon, 1] for key, (lat, lon) in stops.items()
    ]
    tables: dict[str, list[list[str | int | float]]] = {
        "agency.txt": [
            ["agency_id", "agency_name", "agency_url", "agency_timezone"],
            [
                "NM",
                "SIMULATION NammaMove authored test operator",
                "https://example.org/namma-synthetic",
                "Asia/Kolkata",
            ],
        ],
        "stops.txt": [
            ["stop_id", "stop_name", "stop_lat", "stop_lon", "wheelchair_boarding"],
            *stop_rows,
        ],
        "routes.txt": [
            ["route_id", "agency_id", "route_short_name", "route_long_name", "route_type"],
            ["BUS", "NM", "BUS", "SIMULATION bus", 3],
            ["METRO", "NM", "METRO", "SIMULATION metro", 1],
            ["EXPRESS", "NM", "EXP", "SIMULATION express", 3],
            ["INACCESSIBLE", "NM", "STAIR", "SIMULATION inaccessible vehicle", 3],
        ],
        "calendar.txt": [
            [
                "service_id",
                "monday",
                "tuesday",
                "wednesday",
                "thursday",
                "friday",
                "saturday",
                "sunday",
                "start_date",
                "end_date",
            ],
            ["WEEKDAY", 1, 1, 1, 1, 1, 0, 0, "20260101", "20271231"],
        ],
        "calendar_dates.txt": [
            ["service_id", "date", "exception_type"],
            ["WEEKDAY", "20261027", 2],
        ],
        "trips.txt": [
            ["route_id", "service_id", "trip_id", "direction_id", "wheelchair_accessible"]
        ],
        "stop_times.txt": [
            ["trip_id", "arrival_time", "departure_time", "stop_id", "stop_sequence", "timepoint"]
        ],
        "transfers.txt": [
            ["from_stop_id", "to_stop_id", "transfer_type", "min_transfer_time"],
            ["B", "C", 2, 120],
        ],
        "fare_attributes.txt": [
            ["fare_id", "price", "currency_type", "payment_method", "transfers"],
            ["bus", 20, "INR", 0, 0],
            ["metro", 10, "INR", 0, 0],
            ["express", 50, "INR", 0, 0],
        ],
        "fare_rules.txt": [
            ["fare_id", "route_id"],
            ["bus", "BUS"],
            ["metro", "METRO"],
            ["express", "EXPRESS"],
        ],
        "feed_info.txt": [
            ["feed_publisher_name", "feed_publisher_url", "feed_lang", "feed_version"],
            [
                "NammaMove independently authored simulation",
                "https://example.org/namma-synthetic",
                "en",
                "phase03-fixture-v1",
            ],
        ],
    }
    trips = [
        ("BUS", "BUS_OUT", 0, 1, "A", "B", "08:00:00", "08:05:00"),
        ("METRO", "METRO_OUT", 0, 1, "C", "D", "08:12:00", "08:17:00"),
        ("EXPRESS", "EXP_OUT", 0, 1, "A", "D", "08:25:00", "08:35:00"),
        ("BUS", "BUS_BACK", 1, 1, "B", "A", "08:30:00", "08:35:00"),
        ("METRO", "METRO_BACK", 1, 1, "D", "C", "08:20:00", "08:25:00"),
        ("INACCESSIBLE", "STAIR_OUT", 0, 2, "A", "D", "08:01:00", "08:07:00"),
        ("BUS", "NIGHT", 0, 1, "A", "B", "24:05:00", "24:10:00"),
    ]
    for route, trip, direction, wheelchair, origin, destination, departure, arrival in trips:
        tables["trips.txt"].append([route, "WEEKDAY", trip, direction, wheelchair])
        tables["stop_times.txt"].extend(
            [
                [trip, departure, departure, origin, 1, 1],
                [trip, arrival, arrival, destination, 2, 1],
            ]
        )
    buffer = io.BytesIO()
    with ZipFile(buffer, "w") as archive:
        for name, rows in sorted(tables.items()):
            text = io.StringIO(newline="")
            csv.writer(text, lineterminator="\n").writerows(rows)
            member = ZipInfo(name, date_time=(2026, 1, 1, 0, 0, 0))
            member.compress_type = ZIP_DEFLATED
            archive.writestr(member, text.getvalue())
    (target / "synthetic.gtfs.zip").write_bytes(buffer.getvalue())
    (target / "synthetic.osm.pbf").write_bytes(pbf())
    for name, value in {
        "build-config.json": {"dataImportReport": True},
        "otp-config.json": {"otpFeatures": {"GtfsGraphQlApi": True}},
        "router-config.json": {"routingDefaults": {"transferSlack": 60}, "updaters": []},
    }.items():
        (target / name).write_text(json.dumps(value, sort_keys=True, indent=2) + "\n", newline="\n")
    hashes = {
        p.name: hashlib.sha256(p.read_bytes()).hexdigest()
        for p in sorted(target.iterdir())
        if p.name
        in {
            "synthetic.gtfs.zip",
            "synthetic.osm.pbf",
            "build-config.json",
            "otp-config.json",
            "router-config.json",
        }
    }
    version = hashlib.sha256(
        json.dumps({"image": OTP_IMAGE, "inputs": hashes}, sort_keys=True).encode()
    ).hexdigest()
    manifest = {
        "graph_id": version,
        "data_mode": "simulation",
        "license_id": "CC0-1.0",
        "attribution": "NammaMove independently authored synthetic GTFS and geographic grid; no real transit or OSM database contents.",
        "otp_version": "2.7.0",
        "otp_image": OTP_IMAGE,
        "route_fares_inr": {"BUS": 20, "METRO": 10, "EXPRESS": 50},
        "inputs": hashes,
        "stops": {key: {"latitude": lat, "longitude": lon} for key, (lat, lon) in stops.items()},
        "service_start": "2026-01-01",
        "service_end": "2027-12-31",
        "realtime_enabled": False,
    }
    (target / "manifest.json").write_text(
        json.dumps(manifest, sort_keys=True, indent=2) + "\n", newline="\n"
    )
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Create authored synthetic routing inputs; never real transport guidance"
    )
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists() and any(args.output.iterdir()):
        parser.error("Output must be new or empty; existing builds are immutable")
    print(json.dumps(make_fixture(args.output)))


if __name__ == "__main__":
    main()
