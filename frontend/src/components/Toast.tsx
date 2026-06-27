import { useEffect } from "react";

/** A single transient toast, bottom-right. Auto-dismisses after `duration` ms
 *  and calls `onClose`. Purely presentational — the parent owns visibility. */
export function Toast({
  message,
  onClose,
  duration = 3600,
}: {
  message: string;
  onClose: () => void;
  duration?: number;
}) {
  useEffect(() => {
    const t = window.setTimeout(onClose, duration);
    return () => window.clearTimeout(t);
  }, [message, duration, onClose]);

  return (
    <div className="toast" role="status" aria-live="polite">
      <span className="toast-dot" />
      <span>{message}</span>
      <button className="toast-x" onClick={onClose} aria-label="Dismiss">×</button>
    </div>
  );
}
