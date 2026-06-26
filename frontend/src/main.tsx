import { createRoot } from "react-dom/client";
import App from "./App";
import "./theme.css";

// Note: React.StrictMode is intentionally omitted. Its dev-only double-mount
// disposes/recreates the WebGL context behind the <Silk /> background and throws
// transient errors; the <ErrorBoundary> around Silk remains as the safety net.
createRoot(document.getElementById("root")!).render(<App />);
