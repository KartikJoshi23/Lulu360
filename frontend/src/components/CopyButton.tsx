import { useState } from "react";

/** Small ghost button that copies `text` to the clipboard and flips to a
 *  "Copied" confirmation for ~1.4s. Falls back silently if the Clipboard API
 *  is unavailable (e.g. non-secure context). */
export function CopyButton({ text, label = "Copy" }: { text: string; label?: string }) {
  const [copied, setCopied] = useState(false);

  async function copy() {
    try {
      await navigator.clipboard.writeText(text);
    } catch {
      // Fallback for non-secure contexts: a hidden textarea + execCommand.
      const ta = document.createElement("textarea");
      ta.value = text;
      ta.style.position = "fixed";
      ta.style.opacity = "0";
      document.body.appendChild(ta);
      ta.select();
      try { document.execCommand("copy"); } catch { /* give up quietly */ }
      document.body.removeChild(ta);
    }
    setCopied(true);
    window.setTimeout(() => setCopied(false), 1400);
  }

  return (
    <button
      type="button"
      className={`copy-btn${copied ? " is-copied" : ""}`}
      onClick={copy}
      aria-label={copied ? "Copied to clipboard" : `${label} to clipboard`}
    >
      {copied ? (
        <>
          <svg viewBox="0 0 16 16" width="13" height="13" aria-hidden="true">
            <path d="M13.5 4.5l-7 7L3 8" fill="none" stroke="currentColor" strokeWidth="2"
              strokeLinecap="round" strokeLinejoin="round" />
          </svg>
          Copied
        </>
      ) : (
        <>
          <svg viewBox="0 0 16 16" width="13" height="13" aria-hidden="true">
            <rect x="5" y="5" width="8" height="9" rx="1.5" fill="none" stroke="currentColor" strokeWidth="1.5" />
            <path d="M11 5V3.5A1.5 1.5 0 009.5 2H4a2 2 0 00-2 2v6.5A1.5 1.5 0 003.5 12"
              fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
          </svg>
          {label}
        </>
      )}
    </button>
  );
}
