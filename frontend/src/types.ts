// Shared response types — mirror backend/api/main.py pydantic models.

export interface ReaderOut {
  issue_type: string;
  frustration: string;
  confidence: number;
}

export interface InvestigatorOut {
  genuineness: string;
  claim_status: string;
  reason: string;
  signals?: Record<string, unknown> | null;
  flags?: string[] | null;
  confidence?: number | null;
}

export interface EconomistOut {
  action: string;
  refund_type: string;
  coupon_percent: number;
  wallet_credit: number;
  escalate: boolean;
  email_trigger: boolean;
  reason: string;
}

export interface EmailOut {
  to: string;
  subject: string;
  body: string;
}

export interface VoiceOut {
  reply_text: string;
  email: EmailOut | null;
}

export interface ResolveResponse {
  customer_id: string;
  message: string;
  reader: ReaderOut;
  investigator: InvestigatorOut;
  economist: EconomistOut;
  voice: VoiceOut;
  email_fired: boolean;
  audit_id: string | null;
  automation: { escalated: boolean };
}

export interface HealthResponse {
  status: string;
  reader_backend: string; // "lstm" | "keyword"
  flan_enabled: boolean;
}

export interface StatsResponse {
  total: number;
  escalated: number;
  emails_sent: number;
  automation_rate: number;
  by_action: Record<string, number>;
}

export interface AuditRow {
  audit_id: string;
  timestamp: string;
  customer_id: string;
  action: string;
  refund_type: string;
  coupon_percent: number;
  wallet_credit: number;
  email: EmailOut;
}
