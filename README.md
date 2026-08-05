# Bazaar Shipping-Cost Engine

Exercise 1 of the technical assignment — a small engine that computes shipping
fees for *Bazaar* marketplace orders according to the nine rules in
`01-shipping-engine.pdf`. Implementation language: **Python 3**.

## What it does

- Reads the input document `orders.json` (an array of marketplace orders, each
  with several seller line items).
- Splits each order into shipments by seller and prices each shipment through
  the nine rules (base cost by city tier, weight surcharge, free shipping,
  bulky fixed fee, night surcharge, cash-on-delivery fee, and a per-order
  ceiling).
- Writes the result to `results.json` in the schema described in the task.

Every ambiguous, incomplete, or contradictory part of the rules — and the
decision taken for each — is documented with full rationale in
**[`DECISIONS.md`](DECISIONS.md)**. The `results.json` numbers are consistent
with those stated decisions.

## Requirements

- Python **3.10+** (uses `zoneinfo` for the Iran timezone and
  `from __future__ import annotations`).
- `pytest` — required only to run the test suite.

## Project layout

```
shipping_engine/
  __init__.py   package marker + module overview
  config.py     all rule constants (single source of truth)
  models.py     data classes: Item, Order, Shipment, OrderResult
  io.py         load_orders / save_results
  rules.py      order_net_value / is_night_order / weight_surcharge
  engine.py     compute_shipment_fee / compute_order_shipping
  cli.py        main() command-line entry point
orders.json     input data
results.json    generated output
test_shipping.py  one test per decision (D1–D15) + all-orders snapshot
DECISIONS.md    the decision log (primary deliverable)
```

## Usage

The engine is a Python package; run it as a module. The default input/output
paths (`../orders.json` / `../results.json`) are relative to the directory you
run from *inside* the package, so run it from `shipping_engine/` with the
repository root on the module path:

```bash
cd shipping_engine
PYTHONPATH=.. python -m shipping_engine.cli
```

This reads `../orders.json` and writes `../results.json` (the repository root).

To use different files:

```bash
python -m shipping_engine.cli -i ../orders.json -o ../results.json
```

## Running the tests

Tests resolve paths relative to the test file, so they work from anywhere. From
the repository root:

```bash
pytest -q            # or: <venv>/bin/pytest -q
```

The suite asserts one focused behaviour per decision (D1–D15) and snapshots all
27 order totals, so it guards the engine against regressions relative to the
documented decisions.
