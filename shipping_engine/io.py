"""Input/output helpers for the shipping engine.

- ``load_orders``: parse the ``orders.json`` input array into ``Order``.
- ``save_results``: serialize ``OrderResult`` list to ``results.json``.
"""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from shipping_engine.models import Item, Order, OrderResult


def load_orders(path: str | Path) -> list[Order]:
    """Read and parse an orders JSON file into a list of ``Order`` objects."""
    with open(path, "r", encoding="utf-8") as fh:
        raw = json.load(fh)
    return [_parse_order(obj) for obj in raw]


def save_results(results: list[OrderResult], path: str | Path) -> None:
    """Write a list of computed results as a pretty-printed JSON array."""
    payload = [r.to_dict() for r in results]
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, ensure_ascii=False, indent=2)
        fh.write("\n")


def _parse_order(obj: dict) -> Order:
    """Convert one raw ``orders.json`` object into an ``Order``."""
    items = tuple(
        Item(
            item_id=i["item_id"],
            seller_id=i["seller_id"],
            category=i["category"],
            is_bulky=bool(i["is_bulky"]),
            weight_grams=int(i["weight_grams"]),
            unit_price=int(i["unit_price"]),
            quantity=int(i["quantity"]),
            discount=int(i["discount"]),
        )
        for i in obj["items"]
    )
    return Order(
        order_id=obj["order_id"],
        created_at=datetime.fromisoformat(obj["created_at"]),
        destination_city=obj["destination_city"],
        city_tier=obj["city_tier"],
        membership=obj["membership"],
        payment_method=obj["payment_method"],
        items=items,
    )
