"""Command-line entry point for the shipping engine.

Run from the repository root with::

    python -m shipping_engine.cli [--input orders.json] [--output results.json]
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from shipping_engine.engine import compute_order_shipping
from shipping_engine.io import load_orders, save_results

DEFAULT_INPUT = Path("./orders.json")
DEFAULT_OUTPUT = Path("./results.json")


def main(argv: list[str] | None = None) -> int:
    """Load orders, compute their shipping fees, and write the results.

    Takes ``argv`` and returns an exit code so it is easy to call in tests; the
    ``__main__`` guard below forwards to ``sys.exit``.
    """
    parser = argparse.ArgumentParser(
        description="Compute shipping fees for Bazaar marketplace orders."
    )
    parser.add_argument(
        "-i",
        "--input",
        default=DEFAULT_INPUT,
        type=Path,
        help=f"path to input orders JSON (default: {DEFAULT_INPUT})",
    )
    parser.add_argument(
        "-o",
        "--output",
        default=DEFAULT_OUTPUT,
        type=Path,
        help=f"path to write results JSON (default: {DEFAULT_OUTPUT})",
    )
    args = parser.parse_args(argv)

    orders = load_orders(args.input)
    results = [compute_order_shipping(order) for order in orders]
    save_results(results, args.output)

    print(f"Processed {len(orders)} order(s) -> {args.output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
