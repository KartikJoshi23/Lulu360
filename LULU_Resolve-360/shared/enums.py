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
"""

# --- Reader axis 1: issue types (TitleCase, exactly as in messages.csv) -------
ISSUE_TYPES = (
    "Delivery",
    "Damaged_Defective",
    "Refund_Return",
    "Billing",
    "Product_Quality",
    "App_Technical",
    "General_Query",
)

# --- Reader axis 2: frustration levels ----------------------------------------
FRUSTRATION_LEVELS = ("Low", "Medium", "High")

# --- Investigator: genuineness verdict (UPPER_SNAKE) --------------------------
GENUINE = "GENUINE"
SUSPICIOUS = "SUSPICIOUS"
LIKELY_ABUSER = "LIKELY_ABUSER"
GENUINENESS_VALUES = (GENUINE, SUSPICIOUS, LIKELY_ABUSER)

# --- Investigator: claim verification status (UPPER_SNAKE) --------------------
CONFIRMED = "CONFIRMED"
CONTRADICTED = "CONTRADICTED"
UNVERIFIED = "UNVERIFIED"
CLAIM_STATUS_VALUES = (CONFIRMED, CONTRADICTED, UNVERIFIED)

# --- Economist: action (UPPER_SNAKE) ------------------------------------------
ACKNOWLEDGE = "ACKNOWLEDGE"
COUPON = "COUPON"
WALLET_CREDIT = "WALLET_CREDIT"
REFUND = "REFUND"
ESCALATE = "ESCALATE"
ACTION_VALUES = (ACKNOWLEDGE, COUPON, WALLET_CREDIT, REFUND, ESCALATE)

# --- Economist: refund logistics (UPPER_SNAKE) --------------------------------
PICKUP = "PICKUP"
KEEP_ITEM = "KEEP_ITEM"
NONE_REFUND = "NONE"
REFUND_TYPE_VALUES = (PICKUP, KEEP_ITEM, NONE_REFUND)

# --- Customer loyalty tiers (TitleCase) ---------------------------------------
LOYALTY_TIERS = ("Bronze", "Silver", "Gold", "Platinum")

# Actions that fire a customer email (Implementation Plan Sec.5, Rule 9).
# ACKNOWLEDGE and ESCALATE never email.
EMAIL_FIRING_ACTIONS = (COUPON, REFUND, WALLET_CREDIT)
