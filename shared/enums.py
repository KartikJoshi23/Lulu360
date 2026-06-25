"""
shared/enums.py — the single source of truth for every string value that
crosses a module boundary in LuluCare 360 (Implementation Plan Sec.5, Rule 3).

No teammate re-types a literal like "Likely_Abuser" or "Acknowledge" in branch
logic. All modules import from here so that casing is byte-identical to the
mirror in shared/enums.js.

Casing convention (frozen, Implementation Plan Sec.5):
  - UPPER_SNAKE  : genuineness, claim_status, action, refund_type
  - TitleCase    : issue_type, loyalty_tier
  - Low|Medium|High : frustration

------------------------------------------------------------------------------
Naming note (integration reconciliation, Task 2)
------------------------------------------------------------------------------
The four modules were built by different owners against three different *naming*
schemes for the SAME string values:

  * Module 2 / Investigator  -> bare names + ``*_VALUES`` tuples
                                (ACKNOWLEDGE, NONE_REFUND, ACTION_VALUES, ...)
  * Modules 1/3/4 placeholders + the JS mirror
                                -> bare names + short tuples + CURRENCY
                                (NONE, ACTIONS, EMAIL_ACTIONS, ...)
  * Module 3 (the real Economist) + CLAUDE.md Sec.3
                                -> prefixed names
                                (ACTION_ACKNOWLEDGE, REFUND_PICKUP, FRUST_*,
                                 TIER_*, VALUE_*, ISSUE_DAMAGED_DEFECTIVE)

The actual string VALUES are identical across all three; only the constant
*names* differed. Rather than rewrite three modules, this file is now a
**superset**: it defines every alias so every module imports cleanly from this
one source and no module needs a local fallback. The values remain frozen.
"""

# ===========================================================================
# Reader axis 1 — issue types (TitleCase, exactly as in messages.csv)
# ===========================================================================
ISSUE_TYPES = (
    "Delivery",
    "Damaged_Defective",
    "Refund_Return",
    "Billing",
    "Product_Quality",
    "App_Technical",
    "General_Query",
)
# Prefixed aliases (Convention C, used by the real Economist).
ISSUE_DELIVERY = "Delivery"
ISSUE_DAMAGED_DEFECTIVE = "Damaged_Defective"
ISSUE_REFUND_RETURN = "Refund_Return"
ISSUE_BILLING = "Billing"
ISSUE_PRODUCT_QUALITY = "Product_Quality"
ISSUE_APP_TECHNICAL = "App_Technical"
ISSUE_GENERAL_QUERY = "General_Query"

# ===========================================================================
# Reader axis 2 — frustration levels
# ===========================================================================
FRUSTRATION_LEVELS = ("Low", "Medium", "High")
FRUSTRATION = FRUSTRATION_LEVELS          # Convention B alias
FRUST_LOW, FRUST_MEDIUM, FRUST_HIGH = "Low", "Medium", "High"   # Convention C

# ===========================================================================
# Investigator — genuineness verdict (UPPER_SNAKE)
# ===========================================================================
GENUINE = "GENUINE"
SUSPICIOUS = "SUSPICIOUS"
LIKELY_ABUSER = "LIKELY_ABUSER"
GENUINENESS_VALUES = (GENUINE, SUSPICIOUS, LIKELY_ABUSER)
GENUINENESS = GENUINENESS_VALUES          # Convention B alias

# ===========================================================================
# Investigator — claim verification status (UPPER_SNAKE)
# ===========================================================================
CONFIRMED = "CONFIRMED"
CONTRADICTED = "CONTRADICTED"
UNVERIFIED = "UNVERIFIED"
CLAIM_STATUS_VALUES = (CONFIRMED, CONTRADICTED, UNVERIFIED)
CLAIM_STATUS = CLAIM_STATUS_VALUES        # Convention B alias

# ===========================================================================
# Economist — action (UPPER_SNAKE)
# ===========================================================================
ACKNOWLEDGE = "ACKNOWLEDGE"
COUPON = "COUPON"
WALLET_CREDIT = "WALLET_CREDIT"
REFUND = "REFUND"
ESCALATE = "ESCALATE"
ACTION_VALUES = (ACKNOWLEDGE, COUPON, WALLET_CREDIT, REFUND, ESCALATE)
ACTIONS = ACTION_VALUES                   # Convention B alias
# Prefixed aliases (Convention C, used by the real Economist).
ACTION_ACKNOWLEDGE = ACKNOWLEDGE
ACTION_COUPON = COUPON
ACTION_WALLET_CREDIT = WALLET_CREDIT
ACTION_REFUND = REFUND
ACTION_ESCALATE = ESCALATE

# ===========================================================================
# Economist — refund logistics (UPPER_SNAKE)
# ===========================================================================
PICKUP = "PICKUP"
KEEP_ITEM = "KEEP_ITEM"
NONE_REFUND = "NONE"
NONE = "NONE"                             # Convention B alias
REFUND_TYPE_VALUES = (PICKUP, KEEP_ITEM, NONE_REFUND)
REFUND_TYPES = REFUND_TYPE_VALUES         # Convention B alias
# Prefixed aliases (Convention C).
REFUND_PICKUP = PICKUP
REFUND_KEEP_ITEM = KEEP_ITEM
REFUND_NONE = NONE_REFUND

# ===========================================================================
# Economist — internal value bands (UPPER; never cross to the customer)
# ===========================================================================
VALUE_HIGH, VALUE_MEDIUM, VALUE_LOW = "HIGH", "MEDIUM", "LOW"
VALUE_BANDS = (VALUE_HIGH, VALUE_MEDIUM, VALUE_LOW)

# ===========================================================================
# Customer loyalty tiers (TitleCase)
# ===========================================================================
LOYALTY_TIERS = ("Bronze", "Silver", "Gold", "Platinum")
TIER_BRONZE, TIER_SILVER, TIER_GOLD, TIER_PLATINUM = (
    "Bronze", "Silver", "Gold", "Platinum",
)

# ===========================================================================
# The ONE email rule (Implementation Plan Sec.5, Rule 9). The Economist sets
# email_trigger from this set; the Voice obeys it and never recomputes it.
# ACKNOWLEDGE and ESCALATE never email.
# ===========================================================================
EMAIL_FIRING_ACTIONS = (COUPON, REFUND, WALLET_CREDIT)
EMAIL_ACTIONS = frozenset(EMAIL_FIRING_ACTIONS)   # Convention B alias

# ===========================================================================
# Currency for customer-facing amounts. Lulu operates in the UAE -> AED.
# ===========================================================================
CURRENCY = "AED"
