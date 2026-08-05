"""Configuration constants for the shipping-cost engine.

All monetary values are integer Toman. Keeping every rule's figures in one
place is the single source of truth referenced by the engine and the tests.
"""
from zoneinfo import ZoneInfo

# --------------------------------------------------------------------------
# Timezone
# --------------------------------------------------------------------------
# Iran local time is UTC+03:30. Iran abolished DST in 2022, so this fixed
# offset is correct for all timestamps in the input data (2026).
IRAN_TZ = ZoneInfo("Asia/Tehran")

# --------------------------------------------------------------------------
# Rule 1 — Base cost by destination (city tier)
# --------------------------------------------------------------------------
BASE_COSTS = {
    "tehran": 25_000,
    "provincial_capital": 35_000,
    "other": 50_000,
}

# --------------------------------------------------------------------------
# Rule 3 — Weight surcharge (per shipment)
# --------------------------------------------------------------------------
WEIGHT_FREE_ALLOWANCE_GRAMS = 1_000   # first 1 kg is free
WEIGHT_BRACKET_GRAMS = 500            # surviving 500 g above the allowance
WEIGHT_SURCHARGE = 5_000              # added per bracket

# --------------------------------------------------------------------------
# Rules 4 & 5 — Free shipping
# --------------------------------------------------------------------------
PLUS_MEMBERSHIP = "plus"              # Rule 4: Plus members ship free
FREE_SHIPPING_THRESHOLD = 500_000     # Rule 5: orders above this net value

# --------------------------------------------------------------------------
# Rule 6 — Bulky items
# --------------------------------------------------------------------------
BULKY_SHIPPING_FEE = 150_000          # fixed fee per bulky item (not per shipment)

# --------------------------------------------------------------------------
# Rule 7 — Night surcharge (23:00 <= hour < 06:00, Iran local time)
# --------------------------------------------------------------------------
NIGHT_SURCHARGE_PERCENT = 10          # 10%
NIGHT_START_HOUR = 23                 # inclusive
NIGHT_END_HOUR = 6                    # exclusive (06:00 is not night)

# --------------------------------------------------------------------------
# Rule 8 — Cash on delivery
# --------------------------------------------------------------------------
COD_FEE = 10_000                      # labor fee, per shipment
CASH_ON_DELIVERY = "cash_on_delivery"

# --------------------------------------------------------------------------
# Rule 9 — Order-level shipping ceiling
# --------------------------------------------------------------------------
SHIPPING_CAP = 200_000
