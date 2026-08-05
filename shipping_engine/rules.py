"""Individual business rules used by the shipping pipeline.

Each public function implements one rule in isolation so it can be unit-tested
independently of the full pipeline.
"""
from __future__ import annotations

from shipping_engine.models import Item, Order


def order_net_value(order: Order) -> int:
    """Total payable (net) value of an order, after discounts.

    Each line contributes ``unit_price * quantity - discount`` — i.e. the
    ``discount`` is a line-total discount (decision D7) — floored at zero. The
    result drives the Rule 5 free-shipping threshold, measured on **net** (not
    gross) value and per **order** (decisions D2 and D3).
    """
    return sum(_line_net_value(item) for item in order.items)


def _line_net_value(item: Item) -> int:
    """Net value of a single line, never below zero."""
    return max(0, item.unit_price * item.quantity - item.discount)
