"""
Benchmark CLI

Run with::

    python -m benchmarks            # human-readable scorecard
    python -m benchmarks --json     # machine-readable JSON summary
"""

from __future__ import annotations

import argparse
import json
import sys

from benchmarks.runner import run_benchmark


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the Quarky benchmark harness.")
    parser.add_argument("--json", action="store_true", help="emit JSON instead of a table")
    args = parser.parse_args(argv)

    card = run_benchmark()
    if args.json:
        print(json.dumps(card.to_dict(), indent=2))
    else:
        print(card.render())
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
