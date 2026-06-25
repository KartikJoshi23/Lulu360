import { useState } from "react";
import { TopNav, type View } from "./components/TopNav";
import { DemoPage } from "./pages/DemoPage";
import { AuditPage } from "./pages/AuditPage";
import { AboutPage } from "./pages/AboutPage";

export default function App() {
  const [view, setView] = useState<View>("demo");

  return (
    <div className="app-shell">
      <TopNav view={view} onNavigate={setView} />
      {view === "demo" && <DemoPage />}
      {view === "audit" && <AuditPage />}
      {view === "about" && <AboutPage />}
    </div>
  );
}
