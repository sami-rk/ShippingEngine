"""Individual business rules used by the shipping pipeline.

Each public function implements one rule in isolation so it can be unit-tested
independently of the full pipeline.
"""
from __future__ import annotations

import math
from datetime import datetime

from shipping_engine.config import (
    IRAN_TZ,
    NIGHT_END_HOUR,
    NIGHT_START_HOUR,
    WEIGHT_BRACKET_GRAMS,
    WEIGHT_FREE_ALLOWANCE_GRAMS,
    WEIGHT_SURCHARGE,
)
from shipping_engine.models import Item, Order


def order_net_value(order: Order) -> int:
    """Total payable (net) value of an order, after discounts.

    Each line contributes ``unit_price * quantity - discount``, i.e. the
    ``discount`` is a line-total discount (decision D7), and is floored at zero. The
    result drives the Rule 5 free-shipping threshold, measured on **net** (not
    gross) value and per **order** (decisions D2 and D3).
    """
    return sum(_line_net_value(item) for item in order.items)


def _line_net_value(item: Item) -> int:
    """Net value of a single line, never below zero."""
    return max(0, item.unit_price * item.quantity - item.discount)


def is_night_order(created_at: datetime) -> bool:
    """Whether an order was placed within the night-surcharge window.

    The window is ``[23:00, 06:00)`` in **Iran local time**:

    - the timestamp is first converted to Iran time (decision D8), so a UTC
      or any-offset ``created_at`` is interpreted by its local clock hour;
    - ``23:00`` is inclusive and ``06:00`` is exclusive (decision D9).
    """
    hour = created_at.astimezone(IRAN_TZ).hour
    return hour >= NIGHT_START_HOUR or hour < NIGHT_END_HOUR


def weight_surcharge(weight_grams: int) -> int:
    """Rule 3: surcharge for a shipment's weight above the free allowance.

    Charged per whole 500 g bracket beyond the first 1 kg, always rounding
    **up** (decision D4): ``ceil((weight - 1000) / 500) * 5000``. Weights at or
    below the free allowance incur no surcharge.
    """
    if weight_grams <= WEIGHT_FREE_ALLOWANCE_GRAMS:
        return 0
    excess = weight_grams - WEIGHT_FREE_ALLOWANCE_GRAMS
    return math.ceil(excess / WEIGHT_BRACKET_GRAMS) * WEIGHT_SURCHARGE

