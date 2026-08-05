"""Tests for the shipping-cost engine.

There is one test per documented decision (D1..D15) plus a snapshot over the
whole ``orders.json`` dataset, mirroring the decision documents in
``DECISIONS.md``. Paths are resolved relative to this file, so the tests work
regardless of the current working directory.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from shipping_engine.engine import compute_order_shipping
from shipping_engine.io import load_orders
from shipping_engine.rules import is_night_order, order_net_value, weight_surcharge

ORDERS_PATH = Path(__file__).resolve().parent / "orders.json"
ORDERS = {order.order_id: order for order in load_orders(ORDERS_PATH)}


def _fees(result) -> dict:
    """Map seller_id -> shipping_fee for a computed order result."""
    return {shipment.seller_id: shipment.shipping_fee for shipment in result.shipments}


# ---------------------------------------------------------------------------
# Decision tests
# ---------------------------------------------------------------------------

def test_d1_city_tier_over_city_name():
    # ORD-1021 has destination_city "Tehran" but city_tier "other" -> base 50,000.
    assert compute_order_shipping(ORDERS["ORD-1021"]).total_shipping_fee == 50_000


def test_d2_threshold_uses_net_value():
    # ORD-1006 gross 520,000 / net 480,000; ORD-1028 gross 600,000 / net 480,000.
    assert order_net_value(ORDERS["ORD-1006"]) == 480_000
    assert order_net_value(ORDERS["ORD-1028"]) == 480_000
    # Neither reaches 500,000 net, so neither ships free.
    assert compute_order_shipping(ORDERS["ORD-1006"]).total_shipping_fee == 25_000
    assert compute_order_shipping(ORDERS["ORD-1028"]).total_shipping_fee == 45_000


def test_d3_threshold_per_order():
    # ORD-1007: per-order net 600,000 qualifies -> every shipment free.
    result = compute_order_shipping(ORDERS["ORD-1007"])
    assert _fees(result) == {"SL-1": 0, "SL-2": 0}
    assert result.total_shipping_fee == 0


def test_d4_weight_rounds_up():
    assert weight_surcharge(1000) == 0      # free allowance boundary
    assert weight_surcharge(1200) == 5_000  # excess 200 -> 1 bracket
    assert weight_surcharge(2100) == 15_000  # excess 1100 -> 3 brackets (ceil)


def test_d5_bulky_fee_per_item():
    # ORD-1020: two bulky items in one shipment -> 300,000 before the cap.
    result = compute_order_shipping(ORDERS["ORD-1020"])
    assert len(result.shipments) == 1
    assert result.shipments[0].shipping_fee == 300_000
    assert result.total_shipping_fee == 200_000


def test_d6_mixed_shipment_split_model():
    # Same-seller bulky + non-bulky priced separately (split model).
    assert _fees(compute_order_shipping(ORDERS["ORD-1010"])) == {"SL-5": 205_000}
    assert _fees(compute_order_shipping(ORDERS["ORD-1009"])) == {"SL-5": 150_000}


def test_d7_discount_is_line_total():
    # 300,000 * 2 - 120,000 = 480,000 (line-total), not (300,000-120,000)*2.
    assert order_net_value(ORDERS["ORD-1028"]) == 480_000


def test_d8_night_window_timezone_conversion():
    # ORD-1013 is 23:00 UTC == 02:30 Iran -> inside the window.
    assert is_night_order(ORDERS["ORD-1013"].created_at) is True
    assert compute_order_shipping(ORDERS["ORD-1013"]).total_shipping_fee == 27_500


def test_d9_night_window_06_exclusive():
    # ORD-1012 is exactly 06:00 Iran -> not night (exclusive end).
    assert is_night_order(ORDERS["ORD-1012"].created_at) is False
    assert compute_order_shipping(ORDERS["ORD-1012"]).total_shipping_fee == 25_000


def test_d10_cod_fee_per_shipment():
    # ORD-1016: 3 shipments each base 35,000 + 10,000 COD.
    result = compute_order_shipping(ORDERS["ORD-1016"])
    assert _fees(result) == {"SL-1": 45_000, "SL-2": 45_000, "SL-3": 45_000}
    assert result.total_shipping_fee == 135_000


def test_d11_cap_on_order_total():
    # ORD-1017: five shipments of 75,000 sum to 375,000; capped at the order level.
    result = compute_order_shipping(ORDERS["ORD-1017"])
    assert len(result.shipments) == 5
    assert sum(s.shipping_fee for s in result.shipments) == 375_000
    assert result.total_shipping_fee == 200_000


def test_d12_free_shipping_keeps_cod_fee():
    # Plus member + COD still pays the 10,000 labor fee.
    assert compute_order_shipping(ORDERS["ORD-1015"]).total_shipping_fee == 10_000
    assert compute_order_shipping(ORDERS["ORD-1023"]).total_shipping_fee == 10_000


def test_d13_addons_apply_to_bulky():
    # ORD-1024 bulky: 150,000 * 1.1 night + 10,000 COD = 175,000.
    assert _fees(compute_order_shipping(ORDERS["ORD-1024"]))["SL-5"] == 175_000


def test_d14_order_of_operations():
    # ORD-1024 = 175,000 (bulky) + 10,000 (free+COD) = 185,000.
    assert compute_order_shipping(ORDERS["ORD-1024"]).total_shipping_fee == 185_000
    # ORD-1023 = 0 (free) + 10,000 COD = 10,000.
    assert compute_order_shipping(ORDERS["ORD-1023"]).total_shipping_fee == 10_000


def test_d15_cap_reported_separately_from_shipments():
    # ORD-1020: pre-cap shipment fee 300,000, but capped total 200,000.
    result = compute_order_shipping(ORDERS["ORD-1020"])
    assert sum(s.shipping_fee for s in result.shipments) == 300_000
    assert result.total_shipping_fee == 200_000


# ---------------------------------------------------------------------------
# Whole-dataset snapshot
# ---------------------------------------------------------------------------

EXPECTED_TOTALS = {
    "ORD-1001": 25_000, "ORD-1002": 70_000, "ORD-1027": 35_000,
    "ORD-1003": 30_000, "ORD-1004": 35_000, "ORD-1025": 25_000,
    "ORD-1005": 50_000, "ORD-1006": 25_000, "ORD-1028": 45_000,
    "ORD-1007": 0, "ORD-1008": 150_000, "ORD-1009": 150_000,
    "ORD-1010": 200_000, "ORD-1020": 200_000, "ORD-1026": 150_000,
    "ORD-1011": 27_500, "ORD-1012": 25_000, "ORD-1013": 27_500,
    "ORD-1014": 0, "ORD-1015": 10_000, "ORD-1016": 135_000,
    "ORD-1017": 200_000, "ORD-1018": 200_000, "ORD-1019": 200_000,
    "ORD-1021": 50_000, "ORD-1023": 10_000, "ORD-1024": 185_000,
}


@pytest.mark.parametrize("order_id,expected", sorted(EXPECTED_TOTALS.items()))
def test_snapshot_all_order_totals(order_id, expected):
    assert compute_order_shipping(ORDERS[order_id]).total_shipping_fee == expected

