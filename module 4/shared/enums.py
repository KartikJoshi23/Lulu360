"""
shared/enums.py - Single source of truth for every allowed value (Python side).

Integration Rule 3 (Implementation Plan, Section 5): no teammate re-types a
string literal like 'Likely_Abuser' or 'Acknowledge'. Branch logic compares
against THESE constants, never against hand-typed strings. A byte-identical
mirror lives in shared/enums.js for the React layer.

Casing is fixed:
  * UPPER_SNAKE -> genuineness, claim_status, action, refund_type
  * TitleCase   -> issue_type, loyalty_tier
  * Low|Medium|High -> frustration
"""

# --- Reader axis -----------------------------------------------------------
ISSUE_TYPES = (
    "Delivery", "Damaged_Defective", "Refund_Return", "Billing",
    "Product_Quality", "App_Technical", "General_Query",
)
FRUSTRATION = ("Low", "Medium", "High")

# --- Investigator axis -----------------------------------------------------
GENUINE = "GENUINE"
SUSPICIOUS = "SUSPICIOUS"
LIKELY_ABUSER = "LIKELY_ABUSER"
GENUINENESS = (GENUINE, SUSPICIOUS, LIKELY_ABUSER)

CONFIRMED = "CONFIRMED"
CONTRADICTED = "CONTRADICTED"
UNVERIFIED = "UNVERIFIED"
CLAIM_STATUS = (CONFIRMED, CONTRADICTED, UNVERIFIED)

# --- Economist axis --------------------------------------------------------
ACKNOWLEDGE = "ACKNOWLEDGE"
COUPON = "COUPON"
WALLET_CREDIT = "WALLET_CREDIT"
REFUND = "REFUND"
ESCALATE = "ESCALATE"
ACTIONS = (ACKNOWLEDGE, COUPON, WALLET_CREDIT, REFUND, ESCALATE)

PICKUP = "PICKUP"
KEEP_ITEM = "KEEP_ITEM"
NONE = "NONE"
REFUND_TYPES = (PICKUP, KEEP_ITEM, NONE)

# The ONE email rule, named once. Integration Rule 9: the Economist sets
# email_trigger using this set; the Voice merely obeys email_trigger and
# never recomputes it. ACKNOWLEDGE and ESCALATE are deliberately excluded.
EMAIL_ACTIONS = frozenset({COUPON, REFUND, WALLET_CREDIT})

LOYALTY_TIERS = ("Bronze", "Silver", "Gold", "Platinum")

# Currency for customer-facing amounts. Lulu operates in the UAE -> AED.
CURRENCY = "AED"
