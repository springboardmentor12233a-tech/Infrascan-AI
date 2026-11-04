type DashboardProps = {
  onNewInspection: () => void;
  onOpenAssets: () => void;
  onOpenResults: () => void;
};

function BridgeArt() {
  return (
    <svg className="infra-bridge-art" viewBox="0 0 520 150" aria-hidden="true">
      <g fill="none" stroke="currentColor" strokeWidth="4" opacity=".65">
        <path d="M8 115H510M35 115L85 20L135 115M85 20V115M135 115L185 55L235 115" />
        <path d="M185 55V115M235 115L285 35L335 115M285 35V115M335 115L385 75L435 115M385 75V115" />
        <path d="M35 115Q185 5 335 115T510 115" strokeWidth="2" />
        {Array.from({ length: 18 }, (_, i) => (
          <path key={i} d={`M${45 + i * 26} ${115 - Math.sin((i / 17) * Math.PI) * 42}V115`} strokeWidth="1.5" />
        ))}
      </g>
    </svg>
  );
}

function LineIcon({ type }: { type: "assets" | "camera" | "shield" | "chart" | "home" | "results" }) {
  const paths: Record<typeof type, string> = {
    assets: "M12 3 2.5 8 12 13 21.5 8 12 3ZM2.5 12 12 17l9.5-5M2.5 16 12 21l9.5-5",
    camera: "M4 7h3l2-3h6l2 3h3a2 2 0 0 1 2 2v9a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V9a2 2 0 0 1 2-2Zm8 3a4 4 0 1 0 0 8 4 4 0 0 0 0-8Z",
    shield: "M12 3 20 6v5c0 5-3.5 8.5-8 10-4.5-1.5-8-5-8-10V6l8-3Zm-4 9 3 3 5-6",
    chart: "M4 20V12h4v8H4Zm6 0V7h4v13h-4Zm6 0V3h4v17h-4Z",
    home: "M3 10 12 3l9 7M5 9v12h5v-7h4v7h5V9",
    results: "M5 4h14v16H5zM8 8h8M8 12h8M8 16h5",
  };

  return (
    <svg viewBox="0 0 24 24" className="infra-line-icon" aria-hidden="true">
      <path d={paths[type]} />
    </svg>
  );
}

export default function Dashboard({
  onNewInspection,
  onOpenAssets,
  onOpenResults,
}: DashboardProps) {
  return (
    <div className="infra-dashboard">
      <header className="infra-topbar">
        <div className="infra-brand">
          <span className="infra-brand-bridge">⌁</span>
          <strong>InfraScan</strong>
          <i />
          <span>AI-Powered Infrastructure Inspection</span>
        </div>
        <div className="infra-profile">
          <span className="infra-bell">♧</span>
          <span className="infra-avatar">T</span>
          <strong>Tanishka</strong>
          <span>⌄</span>
        </div>
      </header>

      <aside className="infra-sidebar">
        <nav>
          <button className="infra-nav active">
            <LineIcon type="home" /> Dashboard
          </button>
          <button className="infra-nav" onClick={onOpenAssets}>
            <LineIcon type="assets" /> Assets
          </button>
          <button className="infra-nav" onClick={onNewInspection}>
            <LineIcon type="camera" /> New Inspection
          </button>
          <button className="infra-nav" onClick={onOpenResults}>
            <LineIcon type="chart" /> Results
          </button>
        </nav>
        <div className="infra-sidebar-bridge">
          <BridgeArt />
        </div>
        <button className="infra-logout" onClick={() => window.location.reload()}>
          ↪ <span>Logout</span>
        </button>
      </aside>

      <main className="infra-main">
        <section className="infra-welcome">
          <div>
            <h1>Welcome to <span>InfraScan</span> 👋</h1>
            <p>Monitor infrastructure, upload images, and review AI-assisted damage assessments.</p>
          </div>
          <BridgeArt />
        </section>

        <section className="infra-metrics">
          <article className="infra-metric blue">
            <span className="infra-icon-box"><LineIcon type="assets" /></span>
            <div><p>Total Assets</p><strong>12</strong></div>
          </article>
          <article className="infra-metric green">
            <span className="infra-icon-box"><LineIcon type="camera" /></span>
            <div><p>Inspections</p><strong>18</strong></div>
          </article>
          <article className="infra-metric gold">
            <span className="infra-icon-box"><LineIcon type="shield" /></span>
            <div><p>Damages Detected</p><strong>5</strong></div>
          </article>
          <article className="infra-metric purple">
            <span className="infra-icon-box"><LineIcon type="chart" /></span>
            <div><p>Avg. Confidence</p><strong>98.6%</strong></div>
          </article>
        </section>

        <section className="infra-panels">
          <article className="infra-panel">
            <span className="infra-icon-box blue"><LineIcon type="assets" /></span>
            <div className="infra-panel-copy">
              <h2>Infrastructure Assets</h2>
              <p>Manage bridges, roads, buildings, and other assets.</p>
              <button onClick={onOpenAssets}>Manage Assets <span>→</span></button>
            </div>
            <div className="infra-panel-art"><BridgeArt /></div>
          </article>

          <article className="infra-panel">
            <span className="infra-icon-box green"><LineIcon type="camera" /></span>
            <div className="infra-panel-copy">
              <h2>New Inspection</h2>
              <p>Upload an infrastructure image for crack analysis.</p>
              <button onClick={onNewInspection}>Upload Image <span>→</span></button>
            </div>
            <div className="infra-upload-art">
              <span>▧</span><b>+</b>
            </div>
          </article>

          <article className="infra-panel">
            <span className="infra-icon-box purple"><LineIcon type="chart" /></span>
            <div className="infra-panel-copy">
              <h2>Assessment Results</h2>
              <p>Review prediction labels and confidence scores.</p>
              <button onClick={onOpenResults}>View Results <span>→</span></button>
            </div>
            <div className="infra-result-art">
              <span>⌁</span><b>Crack Detected<br />98.6%</b>
            </div>
          </article>

          <article className="infra-panel infra-status">
            <span className="infra-icon-box purple">ⓘ</span>
            <div className="infra-panel-copy">
              <h2>Project Status</h2>
              <p>Prototype dashboard. Authentication and asset storage are not connected yet.</p>
            </div>
            <div className="infra-status-art">⚙</div>
          </article>
        </section>
      </main>
    </div>
  );
}