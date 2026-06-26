import { SEVERITY_COLOR, type Severity } from "../constants";

export function Badge({ label, severity }: { label: string; severity: Severity }) {
  const cls = "badge" + (severity === "alert" ? " alert" : "");
  return (
    <span className={cls} style={{ color: SEVERITY_COLOR[severity] }}>
      <span className="bdot" />
      {label}
    </span>
  );
}
