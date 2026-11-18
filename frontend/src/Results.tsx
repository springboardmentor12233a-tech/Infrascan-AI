type ResultsProps = {
  result: string
  onBack: () => void
}

function Results({ result, onBack }: ResultsProps) {
  return (
    <main className="main-content">
      <section className="upload-card">
        <h1>Assessment Results</h1>
        <p>AI-assisted infrastructure damage assessment</p>

        {result ? (
          <p className="status-message">{result}</p>
        ) : (
          <p>No assessment results yet. Please complete an inspection first.</p>
        )}

        <button type="button" onClick={onBack}>
          Back to Dashboard
        </button>
      </section>

      <p className="footer-note">
        Prototype results only. A qualified engineer must verify
        infrastructure damage before taking action.
      </p>
    </main>
  )
}

export default Results
