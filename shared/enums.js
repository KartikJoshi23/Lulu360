// shared/enums.js - mirror of shared/enums.py for the React layer.
// Integration Rule 3: the dashboard imports these constants; it never re-types
// a string literal. Keep this file identical in meaning to enums.py.
//
// Like enums.py, this is a SUPERSET that exposes every naming alias used across
// the four modules (bare, *_VALUES, and prefixed ACTION_/REFUND_/FRUST_/TIER_/
// VALUE_ forms). The string VALUES are frozen and identical to the Python side.

// --- Reader axis 1: issue types --------------------------------------------
export const ISSUE_TYPES = [
  "Delivery", "Damaged_Defective", "Refund_Return", "Billing",
  "Product_Quality", "App_Technical", "General_Query",
];
export const ISSUE_DELIVERY = "Delivery";
export const ISSUE_DAMAGED_DEFECTIVE = "Damaged_Defective";
export const ISSUE_REFUND_RETURN = "Refund_Return";
export const ISSUE_BILLING = "Billing";
export const ISSUE_PRODUCT_QUALITY = "Product_Quality";
export const ISSUE_APP_TECHNICAL = "App_Technical";
export const ISSUE_GENERAL_QUERY = "General_Query";

// --- Reader axis 2: frustration --------------------------------------------
export const FRUSTRATION_LEVELS = ["Low", "Medium", "High"];
export const FRUSTRATION = FRUSTRATION_LEVELS;
export const FRUST_LOW = "Low";
export const FRUST_MEDIUM = "Medium";
export const FRUST_HIGH = "High";

// --- Investigator: genuineness ---------------------------------------------
export const GENUINE = "GENUINE";
export const SUSPICIOUS = "SUSPICIOUS";
export const LIKELY_ABUSER = "LIKELY_ABUSER";
export const GENUINENESS_VALUES = [GENUINE, SUSPICIOUS, LIKELY_ABUSER];
export const GENUINENESS = GENUINENESS_VALUES;

// --- Investigator: claim status --------------------------------------------
export const CONFIRMED = "CONFIRMED";
export const CONTRADICTED = "CONTRADICTED";
export const UNVERIFIED = "UNVERIFIED";
export const CLAIM_STATUS_VALUES = [CONFIRMED, CONTRADICTED, UNVERIFIED];
export const CLAIM_STATUS = CLAIM_STATUS_VALUES;

// --- Economist: action -----------------------------------------------------
export const ACKNOWLEDGE = "ACKNOWLEDGE";
export const COUPON = "COUPON";
export const WALLET_CREDIT = "WALLET_CREDIT";
export const REFUND = "REFUND";
export const ESCALATE = "ESCALATE";
export const ACTION_VALUES = [ACKNOWLEDGE, COUPON, WALLET_CREDIT, REFUND, ESCALATE];
export const ACTIONS = ACTION_VALUES;
export const ACTION_ACKNOWLEDGE = ACKNOWLEDGE;
export const ACTION_COUPON = COUPON;
export const ACTION_WALLET_CREDIT = WALLET_CREDIT;
export const ACTION_REFUND = REFUND;
export const ACTION_ESCALATE = ESCALATE;

// --- Economist: refund logistics -------------------------------------------
export const PICKUP = "PICKUP";
export const KEEP_ITEM = "KEEP_ITEM";
export const NONE_REFUND = "NONE";
export const NONE = "NONE";
export const REFUND_TYPE_VALUES = [PICKUP, KEEP_ITEM, NONE_REFUND];
export const REFUND_TYPES = REFUND_TYPE_VALUES;
export const REFUND_PICKUP = PICKUP;
export const REFUND_KEEP_ITEM = KEEP_ITEM;
export const REFUND_NONE = NONE_REFUND;

// --- Economist: internal value bands ---------------------------------------
export const VALUE_HIGH = "HIGH";
export const VALUE_MEDIUM = "MEDIUM";
export const VALUE_LOW = "LOW";
export const VALUE_BANDS = [VALUE_HIGH, VALUE_MEDIUM, VALUE_LOW];

// --- Loyalty tiers ----------------------------------------------------------
export const LOYALTY_TIERS = ["Bronze", "Silver", "Gold", "Platinum"];
export const TIER_BRONZE = "Bronze";
export const TIER_SILVER = "Silver";
export const TIER_GOLD = "Gold";
export const TIER_PLATINUM = "Platinum";

// --- The one email rule -----------------------------------------------------
export const EMAIL_FIRING_ACTIONS = [COUPON, REFUND, WALLET_CREDIT];
export const EMAIL_ACTIONS = EMAIL_FIRING_ACTIONS;

// --- Currency ---------------------------------------------------------------
export const CURRENCY = "AED";
