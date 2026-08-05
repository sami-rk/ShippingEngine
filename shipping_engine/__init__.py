"""Bazaar shipping-cost calculation engine.

Computes shipping fees for marketplace orders according to the nine rules in
the exercise description. The engine is split into small modules:

- ``config``  — all constants
- ``models``  — data classes (Item, Order, Shipment, OrderResult)
- ``io``      — load/save JSON
- ``rules``   — individual business rules (net value, night window, weight)
- ``engine``  — the shipping pipeline
- ``cli``     — command-line entry point
"""

__version__ = "0.1.0"
