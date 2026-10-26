"""Seal/verify immutable graph artifacts; never overwrite an existing sealed release."""

import argparse
import csv
import hashlib
import io
import json
from pathlib import Path
from typing import cast
from zipfile import ZipFile

from ..transit.validation import validate_feed
from .contracts import GraphManifest
from .fixture import OTP_IMAGE

INPUTS = {
    "synthetic.gtfs.zip",
    "synthetic.osm.pbf",
    "build-config.json",
    "otp-config.json",
    "router-config.json",
}


def verify_release(folder: Path, *, sealed: bool = True) -> GraphManifest | dict[str, object]:
    raw = json.loads((folder / "manifest.json").read_text())
    if not isinstance(raw, dict):
        raise ValueError("Invalid graph manifest")
    if raw.get("otp_image") != OTP_IMAGE or set(raw.get("inputs", {})) != INPUTS:
        raise ValueError("Unapproved OTP image or input profile")
    for name, digest in raw["inputs"].items():
        if hashlib.sha256((folder / name).read_bytes()).hexdigest() != digest:
            raise ValueError("Graph input checksum mismatch")
    expected = hashlib.sha256(
        json.dumps({"image": OTP_IMAGE, "inputs": raw["inputs"]}, sort_keys=True).encode()
    ).hexdigest()
    if expected != raw["graph_id"]:
        raise ValueError("Graph identity mismatch")
    validated = validate_feed((folder / "synthetic.gtfs.zip").read_bytes())
    source_stops = {
        row["external_id"]: {"latitude": row["latitude"], "longitude": row["longitude"]}
        for row in validated.tables["stops"]
    }
    if raw.get("stops") != source_stops and not sealed:
        raise ValueError("Stop manifest differs from source")
    with ZipFile(folder / "synthetic.gtfs.zip") as archive:
        attributes = list(csv.DictReader(io.StringIO(archive.read("fare_attributes.txt").decode())))
        rules = list(csv.DictReader(io.StringIO(archive.read("fare_rules.txt").decode())))
    prices = {
        row["fare_id"]: int(row["price"])
        for row in attributes
        if row["currency_type"] == "INR" and row["transfers"] == "0"
    }
    source_fares = {row["route_id"]: prices[row["fare_id"]] for row in rules}
    if raw.get("route_fares_inr") != source_fares:
        raise ValueError("Fare manifest differs from source")
    if sealed:
        manifest = GraphManifest.model_validate(raw)
        if {
            key: {"latitude": value.latitude, "longitude": value.longitude}
            for key, value in manifest.stops.items()
        } != source_stops:
            raise ValueError("Stop manifest differs from source")
        if (
            manifest.service_start != validated.service_start
            or manifest.service_end != validated.service_end
        ):
            raise ValueError("Service coverage differs from source")
        if hashlib.sha256((folder / "graph.obj").read_bytes()).hexdigest() != manifest.graph_sha256:
            raise ValueError("Graph artifact checksum mismatch")
        return manifest
    return cast(dict[str, object], raw)


def seal(folder: Path) -> GraphManifest:
    if "graph_sha256" in json.loads((folder / "manifest.json").read_text()):
        raise ValueError("Release already sealed")
    raw = verify_release(folder, sealed=False)
    assert isinstance(raw, dict)
    if "graph_sha256" in raw:
        raise ValueError("Release already sealed")
    raw["graph_sha256"] = hashlib.sha256((folder / "graph.obj").read_bytes()).hexdigest()
    manifest = GraphManifest.model_validate(raw)
    staged = folder / "manifest.pending.json"
    staged.write_text(manifest.model_dump_json(indent=2) + "\n")
    staged.replace(folder / "manifest.json")
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Seal or verify a synthetic graph release after successful OTP build"
    )
    parser.add_argument("command", choices=["seal", "verify"])
    parser.add_argument("folder", type=Path)
    args = parser.parse_args()
    manifest = seal(args.folder) if args.command == "seal" else verify_release(args.folder)
    assert isinstance(manifest, GraphManifest)
    print(
        json.dumps(
            {
                "graph_id": manifest.graph_id,
                "graph_sha256": manifest.graph_sha256,
                "verified": True,
                "data_mode": "simulation",
            }
        )
    )


if __name__ == "__main__":
    main()
