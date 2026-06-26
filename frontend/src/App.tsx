import { lazy, Suspense, useState } from "react";
import { TopNav, type View } from "./components/TopNav";
import { DemoPage } from "./pages/DemoPage";
import { AuditPage } from "./pages/AuditPage";
import { AboutPage } from "./pages/AboutPage";
import { ErrorBoundary } from "./components/ErrorBoundary";

// three.js is heavy — load the silk background as a separate async chunk.
const Silk = lazy(() => import("./components/Silk"));

export default function App() {
  const [view, setView] = useState<View>("demo");

  return (
    <div className="app-shell">
      <div className="silk-bg" aria-hidden="true">
        <ErrorBoundary>
          <Suspense fallback={null}>
            <Silk speed={4.5} scale={1.1} color="#243b57" noiseIntensity={1.3} rotation={0.12} />
          </Suspense>
        </ErrorBoundary>
      </div>
      <TopNav view={view} onNavigate={setView} />
      {view === "demo" && <DemoPage />}
      {view === "audit" && <AuditPage />}
      {view === "about" && <AboutPage />}
    </div>
  );
}
