// Typed API client. Talks to the FastAPI backend, or serves precomputed
// fixtures when VITE_DEMO_MODE === "true" (static Netlify demo / backend down).

import type {
  ResolveResponse,
  HealthResponse,
  StatsResponse,
  AuditRow,
  CustomerCatalogEntry,
  RunAllSummary,
} from "../types";
import { DEMO_DATA, DEMO_PRESETS } from "../demoData";

const BASE = (import.meta.env.VITE_API_BASE_URL ?? "http://127.0.0.1:8010").replace(/\/$/, "");
export const DEMO_MODE = String(import.meta.env.VITE_DEMO_MODE).toLowerCase() === "true";

export { DEMO_PRESETS };

class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
    this.name = "ApiError";
  }
}

async function getJSON<T>(path: string): Promise<T> {
  const res = await fetch(`${BASE}${path}`);
  if (!res.ok) throw new ApiError(res.status, `GET ${path} failed (${res.status})`);
  return res.json() as Promise<T>;
}

// ---- demo-mode helpers -----------------------------------------------------
function demoStats(): StatsResponse {
  const rows = Object.values(DEMO_DATA);
  const escalated = rows.filter((r) => r.economist.escalate).length;
  const by_action: Record<string, number> = {};
  for (const r of rows) by_action[r.economist.action] = (by_action[r.economist.action] ?? 0) + 1;
  return {
    total: rows.length,
    escalated,
    emails_sent: rows.filter((r) => r.email_fired).length,
    automation_rate: rows.length ? Number(((rows.length - escalated) / rows.length).toFixed(4)) : 0,
    by_action,
  };
}

function demoAudit(): AuditRow[] {
  return Object.values(DEMO_DATA)
    .filter((r) => r.email_fired && r.voice.email)
    .map((r, i) => ({
      audit_id: r.audit_id ?? `A${String(i + 1).padStart(4, "0")}`,
      timestamp: new Date().toISOString(),
      customer_id: r.customer_id,
      action: r.economist.action,
      refund_type: r.economist.refund_type,
      coupon_percent: r.economist.coupon_percent,
      wallet_credit: r.economist.wallet_credit,
      message: r.message,
      reply_text: r.voice.reply_text,
      email: r.voice.email!,
    }));
}

// ---- public API ------------------------------------------------------------
export async function resolve(message: string, customerId: string): Promise<ResolveResponse> {
  if (DEMO_MODE) {
    const hit = DEMO_DATA[customerId];
    if (!hit) throw new ApiError(404, `No demo fixture for ${customerId}. Try a preset chip.`);
    // Reflect the typed message back so the UI feels live.
    return { ...hit, message };
  }
  const res = await fetch(`${BASE}/resolve`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message, customer_id: customerId }),
  });
  if (res.status === 404) throw new ApiError(404, `Unknown customer_id: ${customerId}`);
  if (!res.ok) throw new ApiError(res.status, `Resolve failed (${res.status})`);
  return res.json() as Promise<ResolveResponse>;
}

export async function getHealth(): Promise<HealthResponse> {
  if (DEMO_MODE) return { status: "demo", reader_backend: "keyword", flan_enabled: false };
  return getJSON<HealthResponse>("/health");
}

export async function getStats(): Promise<StatsResponse> {
  if (DEMO_MODE) return demoStats();
  return getJSON<StatsResponse>("/stats");
}

export async function getAudit(): Promise<AuditRow[]> {
  if (DEMO_MODE) return demoAudit();
  const { audit_log } = await getJSON<{ audit_log: AuditRow[] }>("/audit");
  return audit_log;
}

export async function runAll(): Promise<RunAllSummary> {
  if (DEMO_MODE) {
    // No live backend in demo mode — report the fixtures as the "run".
    const s = demoStats();
    return { ...s, messages_processed: s.total };
  }
  const res = await fetch(`${BASE}/run-all`, { method: "POST" });
  if (!res.ok) throw new ApiError(res.status, `Run-all failed (${res.status})`);
  return res.json() as Promise<RunAllSummary>;
}

export async function getCustomers(): Promise<CustomerCatalogEntry[]> {
  if (DEMO_MODE) {
    // Derive a small catalog from the demo fixtures so the picker still works.
    return Object.values(DEMO_DATA).map((r) => ({
      customer_id: r.customer_id,
      loyalty_tier: "",
      messages: [
        {
          message_id: r.customer_id,
          text: r.message,
          issue_type: r.reader.issue_type,
          frustration: r.reader.frustration,
        },
      ],
    }));
  }
  return getJSON<CustomerCatalogEntry[]>("/customers");
}
