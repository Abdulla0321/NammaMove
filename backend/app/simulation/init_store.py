"""Provision a local simulation-only database."""

from argparse import ArgumentParser
from pathlib import Path

from .tracking import SimulationStore


def main() -> None:
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("database", type=Path)
    args = parser.parse_args()
    SimulationStore(args.database).initialize()


if __name__ == "__main__":
    main()
