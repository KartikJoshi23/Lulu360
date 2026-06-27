import type { ReactNode } from "react";

/** A collapsible "why was this decided" disclosure. Built on native
 *  <details>/<summary> so it is keyboard-accessible and needs no JS state. */
export function WhyBox({ title, children }: { title: string; children: ReactNode }) {
  return (
    <details className="why">
      <summary className="why-summary">
        <svg className="why-caret" viewBox="0 0 16 16" width="13" height="13" aria-hidden="true">
          <path d="M6 4l4 4-4 4" fill="none" stroke="currentColor" strokeWidth="2"
            strokeLinecap="round" strokeLinejoin="round" />
        </svg>
        {title}
      </summary>
      <div className="why-body">{children}</div>
    </details>
  );
}

/** One labelled evidence row inside a WhyBox. */
export function WhyFactor({ label, value, tone }: { label: string; value: string; tone?: "good" | "warn" | "bad" }) {
  return (
    <div className="why-row">
      <span className="why-k">{label}</span>
      <span className={`why-v${tone ? ` ${tone}` : ""}`}>{value}</span>
    </div>
  );
}
