// shared/enums.js - byte-for-byte mirror of shared/enums.py for the React layer.
// Integration Rule 3: the dashboard imports these constants; it never re-types
// a string literal. Keep this file identical in meaning to enums.py.

export const ISSUE_TYPES = [
  "Delivery", "Damaged_Defective", "Refund_Return", "Billing",
  "Product_Quality", "App_Technical", "General_Query",
];
export const FRUSTRATION = ["Low", "Medium", "High"];

export const GENUINE = "GENUINE";
export const SUSPICIOUS = "SUSPICIOUS";
export const LIKELY_ABUSER = "LIKELY_ABUSER";
export const GENUINENESS = [GENUINE, SUSPICIOUS, LIKELY_ABUSER];

export const CONFIRMED = "CONFIRMED";
export const CONTRADICTED = "CONTRADICTED";
export const UNVERIFIED = "UNVERIFIED";
export const CLAIM_STATUS = [CONFIRMED, CONTRADICTED, UNVERIFIED];

export const ACKNOWLEDGE = "ACKNOWLEDGE";
export const COUPON = "COUPON";
export const WALLET_CREDIT = "WALLET_CREDIT";
export const REFUND = "REFUND";
export const ESCALATE = "ESCALATE";
export const ACTIONS = [ACKNOWLEDGE, COUPON, WALLET_CREDIT, REFUND, ESCALATE];

export const PICKUP = "PICKUP";
export const KEEP_ITEM = "KEEP_ITEM";
export const NONE = "NONE";
export const REFUND_TYPES = [PICKUP, KEEP_ITEM, NONE];

// The one email rule, named once.
export const EMAIL_ACTIONS = [COUPON, REFUND, WALLET_CREDIT];

export const LOYALTY_TIERS = ["Bronze", "Silver", "Gold", "Platinum"];
export const CURRENCY = "AED";
