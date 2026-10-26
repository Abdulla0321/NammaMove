"""Run from root: python -m app.transit (set PYTHONPATH=backend)."""

import argparse
import json
from pathlib import Path
from uuid import UUID

import httpx
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from ..config import Settings
from ..database import Database
from ..observability import configure_logging, logger
from .contracts import Manifest
from .ingestion import activate, ingest
from .providers import ProviderAdapter, ProviderUnavailable
from .validation import MAX_ZIP_BYTES


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Owner-only static feed import / rollback; no live service updates"
    )
    sub = parser.add_subparsers(dest="command", required=True)
    load = sub.add_parser("import")
    load.add_argument("--manifest", required=True, type=Path)
    source = load.add_mutually_exclusive_group(required=True)
    source.add_argument("--file", type=Path)
    source.add_argument("--download", action="store_true")
    load.add_argument("--stage", action="store_true")
    rollback = sub.add_parser("activate")
    rollback.add_argument("--feed", required=True)
    rollback.add_argument("--dataset", required=True, type=UUID)
    args = parser.parse_args()
    configure_logging()
    database = Database(Settings())
    if database.sessions is None:
        parser.error("Migration-owner DATABASE_URL required")
    try:
        with database.sessions.begin() as session:
            if not session.scalar(
                text(
                    "SELECT current_user = pg_get_userbyid(nspowner) OR (SELECT rolsuper FROM pg_roles WHERE rolname=current_user) FROM pg_namespace WHERE nspname='nammamove'"
                )
            ):
                raise ValueError("Import requires the migration schema owner")
            if args.command == "activate":
                dataset = activate(session, args.feed, args.dataset)
            else:
                manifest = Manifest.model_validate_json(args.manifest.read_bytes())
                if args.file:
                    with args.file.open("rb") as file:
                        payload = file.read(MAX_ZIP_BYTES + 1)
                else:
                    with httpx.Client() as client:
                        payload = ProviderAdapter(manifest.provider, manifest.source_url).fetch(
                            client
                        )
                dataset = ingest(session, payload, manifest, promote=not args.stage)
            result = {
                "dataset_id": str(dataset.id),
                "state": dataset.state,
                "report": dataset.report,
            }
        logger.info(
            "transit.import.committed",
            extra={
                "fields": {
                    "dataset_id": result["dataset_id"],
                    "state": result["state"],
                    "command": args.command,
                }
            },
        )
        print(json.dumps(result))
        if result["state"] != "validated":
            raise SystemExit(2)
    except (ValueError, OSError, SQLAlchemyError, ProviderUnavailable):
        parser.exit(
            1,
            "Import/activation failed; database transaction rolled back. Check configuration and owner access without logging credentials.\n",
        )
    finally:
        database.dispose()


if __name__ == "__main__":
    main()
