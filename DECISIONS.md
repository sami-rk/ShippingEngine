# DECISIONS.md — Bazaar Shipping-Cost Engine

**Language:** Python 3

This document is the core deliverable of the exercise. Its purpose is to record, for **every** place where the operational rules in the task description are ambiguous, incomplete, or contradictory:

For six of the decisions, I also quantify **how the final totals would change** if the opposite decision had been taken.

---

## The 9 rules (as given)

| # | Rule |
|---|------|
| 1 | Base cost by destination: Tehran 25,000 · provincial capitals 35,000 · other cities 50,000 |
| 2 | Each order is split into shipments by seller; shipping is calculated separately per shipment |
| 3 | Per shipment, for every 500 g above 1 kg, +5,000 is added |
| 4 | "Plus" members have free shipping |
| 5 | Orders above 500,000 have free shipping |
| 6 | Bulky items are not covered by free shipping and have a fixed 150,000 shipping cost |
| 7 | Orders registered between 23:00–06:00 get a +10% shipping surcharge |
| 8 | Cash-on-delivery adds +10,000 labor fee |
| 9 | Shipping-cost ceiling per order is 200,000 |

---

## Decision summary (15 decisions)

| # | Topic | Ambiguity / contradiction | Decision | Triggering order(s) |
|---|-------|---------------------------|----------|---------------------|
| D1 | Base cost source | `destination_city` vs `city_tier` conflict | Use **`city_tier`** field | ORD-1021 |
| D2 | "Above 500,000" — gross or net | discount field semantics for threshold | Use **net** (after discount) | ORD-1006, ORD-1028 |
| D3 | "Above 500,000" — order or shipment | per-order wording vs per-shipment calc | **Per-order** | ORD-1007 |
| D4 | Weight bracket rounding | non-multiple excess weight | **Ceil** (round up) | ORD-1005, ORD-1003 |
| D5 | Bulky 150,000 — item or shipment | "a fixed 150,000" | **Per bulky item** | ORD-1020 |
| D6 | Mixed bulky + non-bulky shipment | same seller, both types | **Split model** | ORD-1009, ORD-1010 |
| D7 | `discount` — per-unit or line-total | dimensions of discount field | **Line-total** | ORD-1028 |
| D8 | Night window timezone | UTC timestamp (ORD-1013) | **Convert to Iran time** first | ORD-1013 |
| D9 | Night window 06:00 boundary | inclusive or exclusive | **Exclusive** `[23:00, 06:00)` | ORD-1012 |
| D10 | COD fee — order or shipment | order-level field, per-shipment calc | **Per shipment** | ORD-1016, ORD-1019, ORD-1024 |
| D11 | Cap 200,000 — order or shipment | "per order" wording | **Per order** (on total) | ORD-1017, ORD-1018, ORD-1019 |
| D12 | Free shipping vs COD fee | is COD waived by free shipping | **COD still applies** | ORD-1015, ORD-1023 |
| D13 | Night/COD on bulky fixed fee | is "fixed" immune to add-ons | **Add-ons apply** | ORD-1024 |
| D14 | Order of operations | sequencing of rules 1–9 | **Pipeline A** (night on base+weight+bulky; COD after; cap last) | ORD-1024, ORD-1023 |
| D15 | Cap representation in output | shipment fees vs capped total | **Pre-cap per-shipment; total = min(sum, 200,000)** | ORD-1020, ORD-1017 |

---

## Detailed decisions

### D1 — Base cost: which field drives the tier?
- **Ambiguity:** Rule 1 says the base cost is "based on destination," but each order carries two related fields: `destination_city` (a Persian free-text name) and `city_tier` (a structured enum: `tehran` / `provincial_capital` / `other`).
- **Contradiction:** **ORD-1021** has `destination_city = "تهران"` (Tehran) but `city_tier = "other"`. Using the city name implies 25,000 (Tehran); using the tier implies 50,000 (other).
- **Decision:** Use the **`city_tier`** field. ORD-1021 → base 50,000.
- **Why not the other option:** `city_tier` is the normalized, categorical field whose whole purpose is this classification. Using the free-text city name would require a (Tehran / provincial-center / other) lookup table that is **never provided** in the task, making the engine unreliable and non-deterministic for any city not literally in the sample. The structured field is authoritative; `destination_city` is treated as a display label.
- **Activates:** ORD-1021.

### D2 — "Order above 500,000": gross or net (after discount)?
- **Ambiguity:** Rule 5 grants free shipping above 500,000, but items carry a `discount`, so it is unclear whether "order value" is the gross total (`Σ unit_price × quantity`) or the net total (`Σ (unit_price × quantity − discount)`).
- **Decision:** Use **net** (after discount).
- **Why not gross:** The `discount` field is otherwise meaningless to every shipping rule (Rule 5 is the only price-based rule). Using net makes the provided data matter; it also matches real-world "spend threshold" promos, which are usually evaluated on the final payable amount. It is also the more conservative choice (fewer free-shipping grants).
- **Consequences:** ORD-1006 (gross 520,000 / net **480,000**) and ORD-1028 (gross 600,000 / net **480,000**) do **not** qualify for free shipping. ORD-1023 (net 450,000) is a Plus member so it is free regardless.
- **Activates:** ORD-1006, ORD-1028 (and ORD-1023, though its outcome is unaffected).

### D3 — "Order above 500,000": order-level or per-shipment threshold?
- **Ambiguity:** Rule 2 computes shipping per shipment, but Rule 5 says "**orders** above 500,000". An order can contain several seller shipments.
- **Decision:** Evaluate the threshold **per order** (total net value of the whole order). When it qualifies, every **non-bulky** shipment in that order becomes free; bulky shipments still cost 150,000 (Rule 6).
- **Why not per-shipment:** The rule literally says "orders," and the 500,000 threshold represents the customer's total spend on the order, not per-package. A per-shipment check would contradict the word "orders" and is unusual (a shipment is a packaging grouping, not a spend unit).
- **Consequences:** ORD-1007 (total net 600,000, two 300,000 shipments) → both shipments free → total 0.
- **Activates:** ORD-1007.

### D4 — Weight surcharge: round up or down per 500 g?
- **Ambiguity:** Rule 3 adds 5,000 "for every 500 g above 1 kg." When the excess is not an exact multiple of 500 g, does it round up or down?
- **Decision:** **Round up (ceil).** Surcharge = `ceil((weight − 1000) / 500) × 5000` when `weight > 1000`; otherwise 0.
- **Why not floor:** Shipping weight brackets always charge upward in real carriers — you ship the actual weight, so a 1,100 g excess needs a third 500 g bracket. Floor would undercharge for the physically shipped weight.
- **Consequences:** ORD-1005 (2,100 g → excess 1,100 g → 3 brackets → +15,000); ORD-1003 (1,200 g → excess 200 g → 1 bracket → +5,000). Orders with exact multiples (e.g. ORD-1004, ORD-1017) are unaffected.
- **Related assumption:** shipment weight = `Σ (weight_grams × quantity)` across the shipment's items; the first 1,000 g is a free allowance (≤ 1,000 g → no surcharge; ORD-1025 at exactly 1,000 g → no surcharge).
- **Activates:** ORD-1005, ORD-1003, ORD-1025.

### D5 — Bulky fixed fee: per shipment or per bulky item?
- **Ambiguity:** Rule 6 gives bulky items "a fixed shipping cost of 150,000." A shipment can hold several bulky items from the same seller.
- **Decision:** Charge 150,000 **per bulky item** (i.e., per bulky unit).
- **Why not per-shipment:** The alternative interpretation (150,000 for the whole shipment no matter how many bulky items) was considered, but charging per item is chosen here because each bulky unit represents a separately handled, oversized package. (This was a genuinely close call; the opposite choice is quantified in the impact section below.)
- **Consequences:** ORD-1020 (2 bulky items, one shipment) → 300,000 before the cap.
- **Activates:** ORD-1020.


### D6 — Mixed shipment (bulky + non-bulky, same seller)
- **Ambiguity:** Rule 2 groups items by seller into one shipment. ORD-1009 and ORD-1010 each have a **bulky appliance and a non-bulky item from the same seller**, so both types end up in one shipment. Rule 6 does not say how to price such a shipment.
- **Decision:** Use a **split model**. Each bulky item is charged its fixed 150,000 (all-in, replacing base + weight for that item). The non-bulky items in the same shipment are charged normally (base + weight). The shipment fee is the sum of the two parts.
- **Why not "bulky dominates":** Making a bulky item swallow the whole shipment would give the non-bulky items' weight and base cost away for free, undercharging for what is actually shipped. The split model applies each rule to the item type it governs.
- **Consequences:**
  - ORD-1009 (Isfahan): bulky 150,000 + books (500 g, no surcharge; but net order 700,000 ≥ 500,000 → free) → **150,000**.
  - ORD-1010 (Kerman): bulky 150,000 + kitchen 2,600 g (base 35,000 + 4×5,000 = 55,000; net order 340,000 < 500,000, not free) → **205,000** (pre-cap).
- **Activates:** ORD-1009, ORD-1010.

### D7 — `discount` field: per-unit or line-total?
- **Ambiguity:** Each item line has `unit_price`, `quantity`, and `discount`, but Rule 5 does not define how `discount` composes with quantity.
- **Decision:** Treat `discount` as the **line-total** discount: `net_line = unit_price × quantity − discount`.
- **Why not per-unit:** In common order-management schemas, a line-level `discount` is the aggregate discount for the whole line; `unit_price` is per-unit and `quantity` is the count. This is the more conventional reading.
- **Consequences:** ORD-1028 (300,000 × 2 = 600,000, discount 120,000) → net 480,000 (not 360,000 as per-unit). This does not change any free-shipping outcome in this dataset, but it matters for correctness/documentation.
- **Activates:** ORD-1028.

### D8 — Night window: timezone handling
- **Ambiguity:** Rule 7 defines the night window 23:00–06:00. Most timestamps carry `+03:30` (Iran), but **ORD-1013** carries `+00:00` (UTC).
- **Decision:** Convert `created_at` to **Iran local time** (`+03:30`) before evaluating the window.
- **Why not the literal hour:** A timestamp with a timezone offset is an absolute instant; the night window is an operational concept in Iran local time, so the local clock hour must be derived by converting to Iran time. Ignoring the offset would misclassify cross-timezone orders.
- **Consequences:** ORD-1013 (`23:00:00+00:00` = 02:30 Iran time) → inside the window → +10% applies → 27,500.
- **Activates:** ORD-1013.

### D9 — Night window: is 06:00 inclusive or exclusive?
- **Ambiguity:** "Between 23:00 and 06:00" — are the endpoints included? The 23:00 start is treated as inclusive (no order sits on it, and "between 23:00…" naturally includes it). The open question is the 06:00 end.
- **Decision:** Use a **half-open interval `[23:00, 06:00)`** — 06:00 is **exclusive** (not in the window).
- **Why not inclusive:** 06:00 marks the start of the day shift; the night surcharge covers up to (but not including) 06:00. This mirrors standard interval conventions (e.g., "store open 9–5" means you cannot enter at 17:00).
- **Consequences:** ORD-1012 (exactly `06:00:00+03:30`) → **not** night → no surcharge → 25,000.
- **Activates:** ORD-1012.

### D10 — COD fee: per order or per shipment?
- **Ambiguity:** Rule 8 adds a 10,000 labor fee for cash-on-delivery. `payment_method` is an order-level field, but Rule 2 computes shipping per shipment — so is the fee once per order or per shipment?
- **Decision:** Charge the 10,000 **per shipment**.
- **Why not per-order:** Rule 8 says the fee is "added **to shipping cost**," and Rule 2 establishes shipping cost **per shipment** — so naturally the fee attaches to each shipment's cost. Each shipment is also a separate physical package that may be collected/delivered separately, each incurring cash-handling labor. (This was a close call; the opposite is quantified below.)
- **Consequences:** ORD-1016 (3 shipments) → +30,000; ORD-1019 (2 shipments) → +20,000; ORD-1024 (2 shipments) → +20,000. ORD-1023/ORD-1015 (1 shipment) are unaffected.
- **Activates:** ORD-1016, ORD-1019, ORD-1024.


### D11 — Cap 200,000: per order or per shipment?
- **Ambiguity:** Rule 9 states a "shipping cost ceiling **per order**," but cost is computed per shipment.
- **Decision:** Apply the cap to the **order total** (the sum of all shipment fees).
- **Why not per-shipment:** The rule literally says "per order" (سقف هزینه ارسال هر سفارش). It is a customer-protection ceiling — "you won't pay more than 200,000 for shipping on your order." If capped per shipment, a 5-shipment order could cost up to 1,000,000, defeating the purpose of a ceiling.
- **Consequences:** ORD-1017 (375,000) → 200,000; ORD-1018 (280,500) → 200,000; ORD-1019 (285,000) → 200,000. ORD-1010 (205,000) → 200,000; ORD-1020 (300,000) → 200,000.
- **Activates:** ORD-1017, ORD-1018, ORD-1019, ORD-1010, ORD-1020.

### D12 — Free shipping vs the COD fee
- **Ambiguity:** When an order qualifies for free shipping (Plus, or net > 500,000), the base + weight is zeroed. Is the 10,000 COD labor fee also waived?
- **Decision:** **No — the COD fee still applies.** Free shipping zeroes base + weight only; the COD labor fee is a separate payment-handling fee.
- **Why not waived:** "Free shipping" waives the *delivery* cost (base + weight). The COD fee (Rule 8, a کارمزد / labor fee) pays for cash collection, which a Plus or high-value customer still incurs if they choose to pay by cash. It is a payment fee, not a delivery fee. (The night surcharge is a percentage of shipping cost, so on a free order it is 10% of 0 = 0 and is unaffected.)
- **Consequences:** ORD-1015 (Plus + COD) → 0 + 10,000 = 10,000. ORD-1023 (Plus + COD + night) → 0 + 10,000 = 10,000.
- **Activates:** ORD-1015, ORD-1023.

### D13 — Night surcharge & COD on bulky shipments
- **Ambiguity:** Rule 6 gives bulky items a "fixed" 150,000. Does "fixed" mean immune to the night surcharge (Rule 7) and COD fee (Rule 8)?
- **Decision:** The night surcharge and COD fee **do apply** to bulky shipments; "fixed" means the per-item fee is a flat base (instead of a weight/destination-variable cost), not that it is exempt from other rules. The 200,000 cap also still applies to the order total.
- **Why not immune:** Treating "fixed" as all-in immunity would quietly exempt bulky orders from surcharges every other order pays. Reading "fixed" as "flat base" keeps the rules applying uniformly; bulky simply has no variable weight/destination component.
- **Consequences:** ORD-1024 (bulky 150,000 × 1.1 night = 165,000 + 10,000 COD = 175,000).
- **Activates:** ORD-1024.

### D14 — Order of operations
- **Ambiguity:** The task lists rules 1–9 but never states the sequence in which they combine.
- **Decision (Pipeline A):** Apply the rules **in the order they are listed**, then apply the cap last:
  1. base cost (Rule 1) + weight surcharge (Rule 3) per shipment;
  2. free shipping (Rules 4/5): if the order qualifies, zero the base + weight of **non-bulky** items;
  3. bulky (Rule 6): each bulky item = 150,000, which **overrides** the free-shipping zero;
  4. night surcharge (Rule 7): ×1.1 on the current subtotal (base + weight + bulky) — **COD is not yet included** because Rule 7 is listed before Rule 8;
  5. COD fee (Rule 8): +10,000 per shipment, added after the night surcharge;
  6. sum all shipment fees → order total;
  7. cap (Rule 9): `total = min(total, 200,000)`, applied last so it is a true final ceiling (capping earlier would let night/COD push the total back above 200,000).
- **Why not night-including-COD:** Rule 7 precedes Rule 8 in the listing, so the COD fee has not been added when the night percentage is computed. And the cap is listed last, so it is the final ceiling.
- **Consequences:** ORD-1024 → bulky 175,000 + non-bulky 10,000 = **185,000**. ORD-1023 → 0 (free) + 10,000 COD = **10,000**.
- **Activates:** ORD-1024, ORD-1023.

### D15 — How the cap appears in the output
- **Ambiguity:** The output schema has per-shipment `shipping_fee` values plus an order `total_shipping_fee`. When the per-order cap reduces the total below the sum of the shipment fees, how should the per-shipment values be reported?
- **Decision:** Report each shipment's **pre-cap** computed fee; set `total_shipping_fee = min(sum of shipments, 200,000)`. For capped orders, `sum(shipments) ≥ total`, and the difference is the order-level cap discount.
- **Why not distribute proportionally:** Distributing the cap proportionally would require arbitrary rounding and produce non-round per-shipment amounts (e.g. 101,957 + 98,043). Reporting the true computed fee per shipment is transparent and avoids inventing allocations.
- **Consequences:** ORD-1020 → shipment 300,000, total 200,000. ORD-1017 → five shipments of 75,000, total 200,000.
- **Activates:** ORD-1020, ORD-1017, ORD-1018, ORD-1019, ORD-1010.


---

## Opposite-decision impact analysis

For each of the following, the final totals are recomputed **as if the opposite decision had been taken**. Only the affected orders are shown.

### Impact 1 — D2: gross instead of net (threshold)
| Order | Chosen (net) | Opposite (gross) | Δ |
|-------|--------------|------------------|---|
| ORD-1006 | 25,000 | 0 (gross 520,000 ≥ 500,000) | **−25,000** |
| ORD-1028 | 45,000 | 0 (gross 600,000 ≥ 500,000) | **−45,000** |
| ORD-1023 | 10,000 | 10,000 (Plus, unaffected) | 0 |
| **Net effect** | | | **−70,000** |

### Impact 2 — D5: bulky per-shipment instead of per-item
| Order | Chosen (per-item) | Opposite (per-shipment) | Δ |
|-------|-------------------|--------------------------|---|
| ORD-1020 (2 bulky, 1 shipment) | shipment 300,000, total 200,000 | shipment 150,000, total 200,000 | 0 on total (cap absorbs it); shipment fee differs by 150,000 |

The per-order cap masks the difference at the total level, but the reported per-shipment fee changes by 150,000.

### Impact 3 — D10: COD per-order instead of per-shipment
| Order | Chosen (per-shipment) | Opposite (per-order) | Δ |
|-------|------------------------|----------------------|---|
| ORD-1016 (3 shipments, COD) | 135,000 | 115,000 | **−20,000** |
| ORD-1024 (2 shipments, COD) | 185,000 | 175,000 | **−10,000** |
| ORD-1019 (2 shipments, COD) | 200,000 (capped) | 200,000 (capped) | 0 |
| ORD-1023 (1 shipment, COD) | 10,000 | 10,000 | 0 |
| **Net effect** | | | **−30,000** |

### Impact 4 — D4: floor instead of ceil (weight rounding)
| Order | Chosen (ceil) | Opposite (floor) | Δ |
|-------|---------------|------------------|---|
| ORD-1005 (excess 1,100 g) | 50,000 (3 brackets) | 45,000 (2 brackets) | **−5,000** |
| ORD-1003 (excess 200 g) | 30,000 (1 bracket) | 25,000 (0 brackets) | **−5,000** |
| **Net effect** | | | **−10,000** |

### Impact 5 — D11: cap per-shipment instead of per-order
| Order | Chosen (per-order) | Opposite (per-shipment) | Δ |
|-------|---------------------|--------------------------|---|
| ORD-1017 (5 × 75,000) | 200,000 | 375,000 (each < 200,000) | **+175,000** |
| ORD-1018 (143,000 + 137,500) | 200,000 | 280,500 | **+80,500** |
| ORD-1019 (145,000 + 140,000) | 200,000 | 285,000 | **+85,000** |
| ORD-1010 / ORD-1020 (single shipment) | 200,000 | 200,000 | 0 |
| **Net effect** | | | **+340,500** |

### Impact 6 — D1 and D9 — smaller, illustrative
- **D1 (city name instead of `city_tier`):** ORD-1021 → 50,000 becomes 25,000 (**−25,000**).
- **D9 (06:00 inclusive instead of exclusive):** ORD-1012 → 25,000 becomes 27,500 (**+2,500**).

---

## Assumptions and untested cases

These cases are not triggered by any order in `orders.json` but are stated for completeness:

- **Bulky fee with quantity > 1:** All bulky items in the data have `quantity = 1`. Consistent with D5 and the per-item reading, a bulky line with `quantity = n` is charged `150,000 × n`. Untested.
- **`is_bulky` vs `category`:** `is_bulky` (boolean) is used as the source of truth. In the data every `is_bulky == true` item has `category == "appliance"` and vice versa, so the two never conflict. Untested conflict case: use `is_bulky`.
- **Weight = Σ(weight_grams × quantity):** total shipment weight is the quantity-weighted sum. Consistent with Rule 3's "per shipment" wording.
- **Night-surcharge rounding:** computed with integer math (`subtotal * 11 // 10`). In this dataset every affected subtotal is a multiple of 5,000, so the result is always a whole number; for hypothetical non-multiples the surcharge floors. Untested.
- **Shipment output order:** shipments are sorted by `seller_id` for deterministic output. The schema does not require a particular order.

---

## Implementation design decisions

This section records the choices that are about the *code itself* — techniques
or behaviors that are not obvious from the nine rules, could be questioned on
inspection, or rely on knowledge that is not universally expected. The rules-level
decisions D1–D15 are above; this is the layer below them.

### immutable (`frozen`) data classes

The input models (`Item`, `Order`) and output models (`Shipment`, `OrderResult`)
are declared as `@dataclass(frozen=True)` rather than plain mutable dataclasses.
Rationale:

- **They represent shipped documents, not working state.** An `Item`/`Order` is
  loaded once from `orders.json` and then read by the engine; there is no reason
  to change its fields after parsing. `Shipment`/`OrderResult` are the computed
  result, also treated as values.
- **It prevents accidental mutation.** A frozen dataclass raises
  `dataclasses.FrozenInstanceError` on any attempt to rebind an attribute, so a
  bug in the engine cannot silently corrupt an order's fields mid-computation.
- **It is automatically hashable.** `frozen=True` derives a `__hash__` from the
  fields, so instances can be used in sets or as dictionary keys. (An ordinary
  `frozen=False` dataclass is unhashable by default.)
- **It documents intent.** Immutability makes it explicit that these are value
  objects, which keeps the pipeline pure and easier to reason about and test.
- **Shallow-immutability nuance:** `frozen=True` only prevents rebinding the
  top-level attributes. To also prevent mutating the *contents* of the items
  collection, `Order.items` is a `tuple` (immutable) rather than a `list`. If it
  were a `list`, code could still call `order.items.append(...)` even though the
  `Order` object itself is frozen.

The alternative — mutability (`@dataclass`) — was rejected: it would permit
in-place modification with no compiler/runtime guard, increasing the risk of
order-corrupting bugs for no benefit in this read-only pipeline.

### Exact integer arithmetic for the night surcharge

- **Decision:** the 10% surcharge is `subtotal * (100 + percent) // 100` (see
  `_increase_by_percent` in `engine.py`) — never float multiplication.
- **Why it's notable:** `//` truncates. In this dataset every surcharge-bearing
  subtotal is a multiple of 5,000, so results are exact whole numbers; for a
  hypothetical non-multiple the surcharge would *floor*. Integer math is used
  deliberately to avoid float-representation surprises (e.g. `0.1 * 150000`) in
  a currency context, and the D14 tests pin this exact behaviour.

### Per-line net value floored at zero

- **Decision:** `net_line = max(0, unit_price * quantity - discount)` in
  `rules.py`.
- **Why it's notable:** a discount larger than the line's gross would otherwise
  produce a negative line value, which could drag an order's total below zero or
  skew the 500,000 free-shipping threshold (D2/D3) in counter-intuitive ways.
  The floor is a guard: no line in `orders.json` has `discount > gross`, so it
  is defensive rather than exercised by the data.

### Deterministic shipment ordering

- **Decision:** shipments are emitted sorted by `seller_id` in
  `compute_order_shipping`.
- **Why it's notable:** the output schema (see the task's example) does not
  require any order, and `json.dump` preserves object order. Sorting makes
  `results.json` stable and byte-identical across runs, so re-running the engine
  is diffable and the snapshot test never depends on dict-insertion order.

### CLI defaults are current-directory-relative

- **Decision:** `cli.py` defaults to `./orders.json` / `./results.json`, i.e.
  the command is designed to run from the repository root
  (`python -m shipping_engine.cli`).
- **Why it's notable:** an earlier version defaulted to `../orders.json` and
  required running from *inside* the package directory. The cwd-relative default
  is the more ordinary invocation. Docker/Compose sidestep the question entirely
  by passing explicit `-i`/`-o` paths (both the `Dockerfile` and `compose.yaml`
  do this), so the container never depends on the working directory.

---


## Result verification method

- A snapshot test asserts all 27 expected order totals (the values derived from these decisions).
- Each decision D1–D15 has a dedicated test asserting the specific behavior on its triggering order(s).
- The engine, tests, and `results.json` are generated from the same single source of truth (the constants and pipeline in `shipping_engine/`), so correctness against these documented decisions is automatically checked.
