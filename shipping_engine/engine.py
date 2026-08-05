"""Shipping pipeline: turns an order into priced shipments.

Two entry points:

- ``compute_shipment_fee`` — price a single seller's shipment (this step);
- ``compute_order_shipping`` — group items, apply per-order logic, sum and cap.

The order of operations follows Pipeline A (decision D14): base + weight, then
free-shipping zeroing, then bulky override, then night surcharge, then COD, and
finally the per-order cap.
"""
from __future__ import annotations

from shipping_engine.config import (
    BASE_COSTS,
    BULKY_SHIPPING_FEE,
    COD_FEE,
    NIGHT_SURCHARGE_PERCENT,
)
from shipping_engine.models import Item
from shipping_engine.rules import weight_surcharge


def compute_shipment_fee(
    items: tuple[Item, ...],
    city_tier: str,
    qualify_free: bool,
    is_night: bool,
    is_cod: bool,
) -> int:
    """Price a single shipment (one seller) for the given order context.

    - ``items`` — the shipment's items (already grouped by seller);
    - ``city_tier`` — drives the Rule 1 base cost;
    - ``qualify_free`` — True if the order qualifies for free shipping (Rules
      4/5, evaluated per order — decision D3);
    - ``is_night`` — True if inside the night window (Rule 7);
    - ``is_cod`` — True if cash-on-delivery (Rule 8).

    Applies the split model (decision D6): bulky items are charged their fixed
    per-item fee and are not covered by free shipping (Rule 6, decision D5);
    non-bulky items are charged base + weight (Rules 1 & 3), zeroed when the
    order qualifies for free shipping. The night surcharge is applied to the
    base + weight + bulky subtotal only (COD is added afterwards — decision
    D14), and the COD fee is charged per shipment (decision D10).
    """
    bulky_count = sum(item.quantity for item in items if item.is_bulky)
    non_bulky_weight = sum(
        item.weight_grams * item.quantity for item in items if not item.is_bulky
    )

    non_bulky = 0
    if non_bulky_weight > 0:
        non_bulky = BASE_COSTS[city_tier] + weight_surcharge(non_bulky_weight)
        if qualify_free:
            non_bulky = 0

    bulky = bulky_count * BULKY_SHIPPING_FEE

    subtotal = non_bulky + bulky
    if is_night:
        subtotal = _increase_by_percent(subtotal, NIGHT_SURCHARGE_PERCENT)
    if is_cod:
        subtotal += COD_FEE

    return subtotal


def _increase_by_percent(value: int, percent: int) -> int:
    """Return ``value`` increased by ``percent`` %, exact integer arithmetic."""
    return value * (100 + percent) // 100
