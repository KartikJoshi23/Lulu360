import { HealthPill } from "./HealthPill";

export type View = "demo" | "audit" | "about";

const LINKS: { id: View; label: string }[] = [
  { id: "demo", label: "Demo" },
  { id: "audit", label: "Audit Log" },
  { id: "about", label: "About" },
];

export function TopNav({ view, onNavigate }: { view: View; onNavigate: (v: View) => void }) {
  return (
    <nav className="topnav">
      <div className="container topnav-inner">
        <div className="brand">
          <span className="brand-mark">L</span>
          <span>
            LuluCare&nbsp;360 <small>· AI Co-Pilot</small>
          </span>
        </div>
        <div className="nav-links">
          {LINKS.map((l) => (
            <button
              key={l.id}
              className={`nav-link${view === l.id ? " active" : ""}`}
              onClick={() => onNavigate(l.id)}
            >
              {l.label}
            </button>
          ))}
        </div>
        <span className="nav-spacer" />
        <HealthPill />
      </div>
    </nav>
  );
}
