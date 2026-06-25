import { SEVERITY_COLOR, type Severity } from "../constants";

export function Badge({ label, severity }: { label: string; severity: Severity }) {
  return (
    <span className="badge" style={{ color: SEVERITY_COLOR[severity] }}>
      <span className="bdot" />
      {label}
    </span>
  );
}
