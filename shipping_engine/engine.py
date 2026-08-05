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
    CASH_ON_DELIVERY,
    COD_FEE,
    FREE_SHIPPING_THRESHOLD,
    NIGHT_SURCHARGE_PERCENT,
    PLUS_MEMBERSHIP,
    SHIPPING_CAP,
)
from shipping_engine.models import Item, Order, Shipment, OrderResult
from shipping_engine.rules import is_night_order, order_net_value, weight_surcharge


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


def compute_order_shipping(order: Order) -> OrderResult:
    """Compute the full shipping result for a single order.

    - groups items into shipments by seller (Rule 2);
    - derives the per-order context: free shipping (Plus or net > threshold —
      decisions D2/D3), night window (D8/D9) and cash-on-delivery (D10);
    - prices each shipment with ``compute_shipment_fee``;
    - sums the shipments and applies the per-order 200,000 cap last (decision
      D11 / D14). Shipments are reported pre-cap; the total is the capped sum
      (decision D15). Shipments are sorted by ``seller_id`` for determinism.
    """
    qualify_free = (
        order.membership == PLUS_MEMBERSHIP
        or order_net_value(order) > FREE_SHIPPING_THRESHOLD
    )
    is_night = is_night_order(order.created_at)
    is_cod = order.payment_method == CASH_ON_DELIVERY

    by_seller: dict[str, list[Item]] = {}
    for item in order.items:
        by_seller.setdefault(item.seller_id, []).append(item)

    shipments = [
        Shipment(
            seller_id=seller_id,
            shipping_fee=compute_shipment_fee(
                tuple(items), order.city_tier, qualify_free, is_night, is_cod
            ),
        )
        for seller_id, items in sorted(by_seller.items())
    ]

    raw_total = sum(shipment.shipping_fee for shipment in shipments)
    return OrderResult(
        order_id=order.order_id,
        shipments=tuple(shipments),
        total_shipping_fee=min(raw_total, SHIPPING_CAP),
    )

