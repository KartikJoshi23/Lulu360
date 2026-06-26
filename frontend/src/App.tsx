import { useState } from "react";
import { TopNav, type View } from "./components/TopNav";
import { DemoPage } from "./pages/DemoPage";
import { AuditPage } from "./pages/AuditPage";
import { AboutPage } from "./pages/AboutPage";

export default function App() {
  const [view, setView] = useState<View>("demo");

  return (
    <div className="app-shell">
      <div className="aurora" aria-hidden="true">
        <span className="orb orb-1" />
        <span className="orb orb-2" />
        <span className="orb orb-3" />
      </div>
      <TopNav view={view} onNavigate={setView} />
      {view === "demo" && <DemoPage />}
      {view === "audit" && <AuditPage />}
      {view === "about" && <AboutPage />}
    </div>
  );
}
