"""Data classes for the shipping-cost engine.

These mirror the input ``orders.json`` document and the output schema of
``results.json``. Input models are immutable (``frozen=True``) because they
represent a shipped document; the output ``OrderResult`` carries a ``to_dict``
helper used for JSON serialization.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class Item:
    """A single line item within an order."""

    item_id: str
    seller_id: str
    category: str
    is_bulky: bool
    weight_grams: int
    unit_price: int
    quantity: int
    discount: int


@dataclass(frozen=True)
class Order:
    """An order as read from ``orders.json``."""

    order_id: str
    created_at: datetime
    destination_city: str
    city_tier: str
    membership: str
    payment_method: str
    items: tuple[Item, ...]


@dataclass(frozen=True)
class Shipment:
    """One seller's shipment within an order result."""

    seller_id: str
    shipping_fee: int


@dataclass(frozen=True)
class OrderResult:
    """The computed shipping result for a single order."""

    order_id: str
    shipments: tuple[Shipment, ...]
    total_shipping_fee: int

    def to_dict(self) -> dict:
        return {
            "order_id": self.order_id,
            "shipments": [
                {"seller_id": s.seller_id, "shipping_fee": s.shipping_fee}
                for s in self.shipments
            ],
            "total_shipping_fee": self.total_shipping_fee,
        }
