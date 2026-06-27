// Derives which Economist rule fired from the frozen `reason` string.
//
// The decision contract (CLAUDE.md §2.1) is immutable, so we cannot add a
// `rule` field to the backend response. Instead we recognise the distinctive
// note each rule in choose_action() emits and map it to a human label here, in
// the presentation layer only. Order mirrors the 8-rule precedence table.

export interface RuleTrace {
  id: string;        // short tag, e.g. "Rule 5"
  label: string;     // what the rule represents
  detail: string;    // one-line policy rationale for the "why" disclosure
}

const TABLE: { match: RegExp; id: string; label: string; detail: string }[] = [
  { match: /General_Query service inquiry/i, id: "Service",  label: "Service inquiry — answer, no payout",
    detail: "A General_Query is a question, not a complaint, so it routes to a helpful answer with no compensation flow." },
  { match: /claim CONTRADICTED/i,            id: "Rule 1",   label: "Claim contradicted by record",
    detail: "Our own records actively disprove the claim, so no payout is made — highest-priority anti-abuse rule." },
  { match: /ABUSE_FLAG: capped/i,            id: "Rule 2b",  label: "Confirmed promise, abuser — capped",
    detail: "An agent logged a promise (our unfakeable record) so it is honoured, but capped to exactly that scope because history flags abuse." },
  { match: /CONFIRMED logged promise/i,      id: "Rule 2",   label: "Honour logged promise",
    detail: "An agent previously logged this promise in our system, so we honour exactly what was recorded." },
  { match: /LIKELY_ABUSER -> acknowledge/i,  id: "Rule 3",   label: "Likely abuser — abuse never pays",
    detail: "Account history (not the message tone) shows a gaming pattern, so we acknowledge only — anger is never treated as evidence." },
  { match: /new\/first-purchase account/i,   id: "Rule 4",   label: "New / first-purchase — capped coupon",
    detail: "A brand-new or first-purchase account can't be verified yet, so we offer a goodwill coupon that's generous but capped." },
  { match: /GENUINE \+ Damaged_Defective/i,  id: "Rule 5",   label: "Genuine product defect — refund",
    detail: "A trusted customer reporting a clear product defect gets a full refund; placed above the frustration rules so a calm genuine defect is never downgraded." },
  { match: /High frustration \+ HIGH value/i,id: "Rule 6",   label: "Genuine, high-value, upset — generous coupon",
    detail: "A genuine, high-value customer who is very frustrated gets a generous coupon to protect the relationship." },
  { match: /Medium \+ LOW value/i,           id: "Rule 7",   label: "Genuine, medium, low-value — wallet credit",
    detail: "Genuine but lower-value and moderately frustrated: a flat wallet credit is the proportionate gesture." },
  { match: /Medium frustration -> standard/i,id: "Rule 7b",  label: "Genuine, medium frustration — standard coupon",
    detail: "Genuine and moderately frustrated at medium/high value: a standard goodwill coupon." },
  { match: /routine \/ Low frustration/i,    id: "Rule 8",   label: "Genuine routine — acknowledge",
    detail: "Genuine but routine and low-frustration: a warm acknowledgement with no payout is proportionate." },
];

export function ruleTrace(reason: string): RuleTrace | null {
  for (const r of TABLE) {
    if (r.match.test(reason)) return { id: r.id, label: r.label, detail: r.detail };
  }
  return null;
}

/** The escalation valve overrides the chosen action after the fact; the note
 *  records it with a distinctive marker. */
export function wasEscalationOverride(reason: string): boolean {
  return /OVERRIDE: escalated to human/i.test(reason);
}
