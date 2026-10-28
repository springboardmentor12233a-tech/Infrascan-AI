type DashboardProps = {
  onNewInspection: () => void
  onOpenAssets: () => void
  onOpenResults: () => void
}

function Dashboard({
  onNewInspection,
  onOpenAssets,
  onOpenResults
}: DashboardProps) {
  return (
    <main className="dashboard-page">
      <header className="dashboard-header">
        <h1>InfraScan</h1>
        <p>AI-Powered Infrastructure Inspection</p>
      </header>

      <section className="dashboard-welcome">
        <h2>Welcome to Your Dashboard</h2>
        <p>
          Monitor infrastructure, upload images, and review
          AI-assisted damage assessments.
        </p>
      </section>

      <section className="dashboard-grid">
        <article
          className="dashboard-card"
          onClick={onOpenAssets}
          onKeyDown={(event) => {
            if (event.key === 'Enter' || event.key === ' ') {
              event.preventDefault()
              onOpenAssets()
            }
          }}
          style={{ cursor: 'pointer' }}
          role="button"
          tabIndex={0}
        >
          <h3>Infrastructure Assets</h3>
          <p>Manage bridges, roads, buildings, and other assets.</p>
          <span>Click to manage assets</span>
        </article>

        <article
          className="dashboard-card"
          onClick={onNewInspection}
          onKeyDown={(event) => {
            if (event.key === 'Enter' || event.key === ' ') {
              event.preventDefault()
              onNewInspection()
            }
          }}
          style={{ cursor: 'pointer' }}
          role="button"
          tabIndex={0}
        >
          <h3>New Inspection</h3>
          <p>Upload an infrastructure image for crack analysis.</p>
          <span>Click here to upload an image</span>
        </article>

        <article
  className="dashboard-card"
  onClick={onOpenResults}
  onKeyDown={(event) => {
    if (event.key === 'Enter' || event.key === ' ') {
      event.preventDefault()
      onOpenResults()
    }
  }}
  style={{ cursor: 'pointer' }}
  role="button"
  tabIndex={0}
>
  <h3>Assessment Results</h3>
  <p>Review prediction labels and confidence scores.</p>
  <span>Click to view assessment results</span>
</article>
      </section>

      <p className="dashboard-note">
        Prototype dashboard. Authentication and asset storage are
        not connected yet.
      </p>
    </main>
  )
}

export default Dashboard