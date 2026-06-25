export function FlagChips({ flags }: { flags?: string[] | null }) {
  if (!flags || flags.length === 0) return null;
  return (
    <div className="chips" style={{ marginTop: 10 }}>
      {flags.map((f) => (
        <span key={f} className="chip" style={{ cursor: "default" }}>
          {f}
        </span>
      ))}
    </div>
  );
}
