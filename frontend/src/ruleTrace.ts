// Derives which Economist rule fired from the frozen `reason` string.
//
// The decision contract (CLAUDE.md §2.1) is immutable, so we cannot add a
// `rule` field to the backend response. Instead we recognise the distinctive
// note each rule in choose_action() emits and map it to a human label here, in
// the presentation layer only. Order mirrors the 8-rule precedence table.

export interface RuleTrace {
  id: string;        // short tag, e.g. "Rule 5"
  label: string;     // what the rule represents
}

const TABLE: { match: RegExp; id: string; label: string }[] = [
  { match: /General_Query service inquiry/i, id: "Service",  label: "Service inquiry — answer, no payout" },
  { match: /claim CONTRADICTED/i,            id: "Rule 1",   label: "Claim contradicted by record" },
  { match: /ABUSE_FLAG: capped/i,            id: "Rule 2b",  label: "Confirmed promise, abuser — capped" },
  { match: /CONFIRMED logged promise/i,      id: "Rule 2",   label: "Honour logged promise" },
  { match: /LIKELY_ABUSER -> acknowledge/i,  id: "Rule 3",   label: "Likely abuser — abuse never pays" },
  { match: /new\/first-purchase account/i,   id: "Rule 4",   label: "New / first-purchase — capped coupon" },
  { match: /GENUINE \+ Damaged_Defective/i,  id: "Rule 5",   label: "Genuine product defect — refund" },
  { match: /High frustration \+ HIGH value/i,id: "Rule 6",   label: "Genuine, high-value, upset — generous coupon" },
  { match: /Medium \+ LOW value/i,           id: "Rule 7",   label: "Genuine, medium, low-value — wallet credit" },
  { match: /Medium frustration -> standard/i,id: "Rule 7b",  label: "Genuine, medium frustration — standard coupon" },
  { match: /routine \/ Low frustration/i,    id: "Rule 8",   label: "Genuine routine — acknowledge" },
];

export function ruleTrace(reason: string): RuleTrace | null {
  for (const r of TABLE) {
    if (r.match.test(reason)) return { id: r.id, label: r.label };
  }
  return null;
}

/** The escalation valve overrides the chosen action after the fact; the note
 *  records it with a distinctive marker. */
export function wasEscalationOverride(reason: string): boolean {
  return /OVERRIDE: escalated to human/i.test(reason);
}
