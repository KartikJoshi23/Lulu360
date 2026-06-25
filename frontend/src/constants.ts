// Semantic colour + label maps for badges. Keys are the frozen enum string
// values from shared/enums (genuineness, claim_status, action, refund_type).

export type Severity = "trust" | "caution" | "alert" | "action" | "neutral";

export const SEVERITY_COLOR: Record<Severity, string> = {
  trust: "var(--c-trust)",
  caution: "var(--c-caution)",
  alert: "var(--c-alert)",
  action: "var(--c-action)",
  neutral: "var(--c-neutral)",
};

export const GENUINENESS_SEVERITY: Record<string, Severity> = {
  GENUINE: "trust",
  SUSPICIOUS: "caution",
  LIKELY_ABUSER: "alert",
};

export const CLAIM_SEVERITY: Record<string, Severity> = {
  CONFIRMED: "trust",
  UNVERIFIED: "caution",
  CONTRADICTED: "alert",
};

export const ACTION_SEVERITY: Record<string, Severity> = {
  REFUND: "action",
  COUPON: "action",
  WALLET_CREDIT: "action",
  ACKNOWLEDGE: "neutral",
  ESCALATE: "alert",
};

export const ACTION_LABEL: Record<string, string> = {
  REFUND: "Refund",
  COUPON: "Coupon",
  WALLET_CREDIT: "Wallet Credit",
  ACKNOWLEDGE: "Acknowledge",
  ESCALATE: "Escalate",
};

export const REFUND_TYPE_LABEL: Record<string, string> = {
  PICKUP: "Courier pickup",
  KEEP_ITEM: "Keep the item",
  NONE: "—",
};
