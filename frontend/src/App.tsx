import { useState } from 'react'
import Login from './pages/Login'
import Dashboard from './pages/Dashboard'
import Assets from './pages/Assets'
import Results from './pages/Results'
import './App.css'

type InspectionResult = {
  filename: string
  size_bytes: number
  count: number
  detections: {
    class_id: number
    class_name: string
    confidence: number
    box_xyxy: number[]
  }[]
}

type PredictionResult = {
  prediction: string
  confidence_percent: number
  classes: string[]
  note: string
}

function App() {
  const [selectedFile, setSelectedFile] = useState<File | null>(null)
  const [message, setMessage] = useState('')
  const [loading, setLoading] = useState(false)
  const [preview, setPreview] = useState('')
  const [showLogin, setShowLogin] = useState(true)
  const [showDashboard, setShowDashboard] = useState(false)
  const [showAssets, setShowAssets] = useState(false)
  const [showResults, setShowResults] = useState(false)
  const [assessmentResult, setAssessmentResult] = useState('')
  const [inspection, setInspection] = useState<InspectionResult | null>(null)
  const [prediction, setPrediction] = useState<PredictionResult | null>(null)

  async function handleUpload(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault()

    if (!selectedFile) {
      setMessage('Please select an image first.')
      return
    }

    setLoading(true)
    setMessage('Uploading image...')
    setInspection(null)
    setPrediction(null)
    setAssessmentResult('')

    try {
      // Step 1: Upload and save the image on the backend.
      const formData = new FormData()
      formData.append('file', selectedFile)

      const uploadResponse = await fetch(
        'http://127.0.0.1:8000/upload-image',
        {
          method: 'POST',
          body: formData,
        }
      )

      const uploadData = await uploadResponse.json()

      if (!uploadResponse.ok) {
        throw new Error(uploadData.detail || 'Image upload failed.')
      }

      setMessage(`Image uploaded successfully: ${uploadData.filename}`)

      // Step 2: Run the existing AI classification endpoint.
      const token = localStorage.getItem('infrascan_token')

      if (!token) {
        throw new Error('Please log in again.')
      }

      const predictionData = new FormData()
      predictionData.append('file', selectedFile)

      const predictionResponse = await fetch(
        'http://127.0.0.1:8000/predict-crack',
        {
          method: 'POST',
          headers: {
            Authorization: `Bearer ${token}`,
          },
          body: predictionData,
        }
      )

      const predictionResult = await predictionResponse.json()

      if (!predictionResponse.ok) {
        throw new Error(
          predictionResult.detail || 'AI prediction failed.'
        )
      }

      setPrediction(predictionResult)

      // Step 3: Run YOLO crack detection.
      const detectionData = new FormData()
      detectionData.append('file', selectedFile)

      const detectionResponse = await fetch(
        'http://127.0.0.1:8000/detect-yolo',
        {
          method: 'POST',
          body: detectionData,
        }
      )

      const detection = await detectionResponse.json()

      if (!detectionResponse.ok) {
        throw new Error(
          detection.detail || 'YOLO detection failed.'
        )
      }

      const result: InspectionResult = {
        filename: uploadData.filename,
        size_bytes: uploadData.size_bytes,
        count: detection.count,
        detections: detection.detections,
      }

      setInspection(result)

      const detectionSummary = result.detections.length
        ? result.detections
            .map(
              (item, index) =>
                `Crack ${index + 1}: ${item.class_name}, ` +
                `${(item.confidence * 100).toFixed(2)}% confidence, ` +
                `box [${item.box_xyxy.join(', ')}]`
            )
            .join('\n')
        : 'No cracks detected in this image.'

      const predictionSummary = predictionResult
        ? `AI prediction: ${predictionResult.prediction} ` +
          `(${predictionResult.confidence_percent}% confidence).`
        : 'AI prediction is unavailable.'

      setAssessmentResult(
        `YOLO detections: ${result.count}\n` +
        `${detectionSummary}\n\n${predictionSummary}`
      )

      setMessage('Upload successful! YOLO detection completed.')
    } catch (error) {
      setMessage(
        error instanceof Error
          ? `Processing failed: ${error.message}`
          : 'Could not connect to the backend.'
      )
    } finally {
      setLoading(false)
    }
  }

  function handleFileChange(
    event: React.ChangeEvent<HTMLInputElement>
  ) {
    const file = event.target.files?.[0] ?? null

    if (preview) {
      URL.revokeObjectURL(preview)
    }

    setSelectedFile(file)
    setPreview(file ? URL.createObjectURL(file) : '')
    setMessage('')
    setAssessmentResult('')
    setPrediction(null)
    setInspection(null)
  }

  function handleLogin() {
    setShowLogin(false)
    setShowDashboard(true)
    setShowAssets(false)
    setShowResults(false)
  }

  function handleLogout() {
    setShowLogin(true)
    setShowDashboard(false)
    setShowAssets(false)
    setShowResults(false)
  }

  function handleNewInspection() {
    setShowLogin(false)
    setShowDashboard(false)
    setShowAssets(false)
    setShowResults(false)
  }

  function handleOpenAssets() {
    setShowLogin(false)
    setShowDashboard(false)
    setShowAssets(true)
    setShowResults(false)
  }

  function handleOpenResults() {
    setShowLogin(false)
    setShowDashboard(false)
    setShowAssets(false)
    setShowResults(true)
  }

  function handleBackToDashboard() {
    setShowLogin(false)
    setShowDashboard(true)
    setShowAssets(false)
    setShowResults(false)
  }

  return (
    <div className="app">
      {showLogin ? (
        <Login
          onBack={() => setShowLogin(false)}
          onLogin={handleLogin}
        />
      ) : showDashboard ? (
        <>
          <header className="navbar">
            <h2>InfraScan</h2>
            <span>AI-Powered Infrastructure Inspection</span>
            <button type="button" onClick={handleLogout}>
              Logout
            </button>
          </header>

          <Dashboard
            onNewInspection={handleNewInspection}
            onOpenAssets={handleOpenAssets}
            onOpenResults={handleOpenResults}
          />
        </>
      ) : showAssets ? (
        <>
          <header className="navbar">
            <h2>InfraScan</h2>
            <span>AI-Powered Infrastructure Inspection</span>
            <button type="button" onClick={handleBackToDashboard}>
              Back to Dashboard
            </button>
            <button type="button" onClick={handleLogout}>
              Logout
            </button>
          </header>
          <Assets />
        </>
      ) : showResults ? (
        <>
          <header className="navbar">
            <h2>InfraScan</h2>
            <span>AI-Powered Infrastructure Inspection</span>
            <button type="button" onClick={handleBackToDashboard}>
              Back to Dashboard
            </button>
            <button type="button" onClick={handleLogout}>
              Logout
            </button>
          </header>
          <Results
            result={assessmentResult}
            onBack={handleBackToDashboard}
          />
        </>
      ) : (
        <>
          <header className="navbar">
            <h2>InfraScan</h2>
            <span>AI-Powered Infrastructure Inspection</span>
            <button type="button" onClick={handleBackToDashboard}>
              Dashboard
            </button>
            <button type="button" onClick={handleLogout}>
              Logout
            </button>
          </header>

          <main className="main-content">
            <p className="eyebrow">
              SMART INFRASTRUCTURE MONITORING
            </p>

            <h1>Detect Cracks. Protect Infrastructure.</h1>

            <p className="description">
              Upload infrastructure images for image processing
              and damage assessment.
            </p>

            <section className="upload-card">
              <h2>Start a New Inspection</h2>
              <p>
                Select a JPG, PNG or WEBP image of concrete or
                infrastructure (maximum 10 MB).
              </p>

              <form onSubmit={handleUpload}>
                <input
                  type="file"
                  accept=".jpg,.jpeg,.png,.webp"
                  onChange={handleFileChange}
                  required
                />

                {preview && (
                  <img
                    className="image-preview"
                    src={preview}
                    alt="Selected inspection"
                  />
                )}

                <button type="submit" disabled={loading}>
                  {loading ? 'Processing...' : 'Upload Image'}
                </button>
              </form>

              {message && (
                <p className="status-message" role="status">
                  {message}
                </p>
              )}

              {inspection && (
                <section className="inspection-result">
                  <h2>YOLO Detection Result</h2>

                  <p>
                    <strong>Saved filename:</strong>{' '}
                    {inspection.filename}
                  </p>

                  <p>
                    <strong>File size:</strong>{' '}
                    {(inspection.size_bytes / 1024).toFixed(1)} KB
                  </p>

                  <p>
                    <strong>Cracks detected:</strong>{' '}
                    {inspection.count}
                  </p>

                  {inspection.detections.length > 0 ? (
                    <ul>
                      {inspection.detections.map((item, index) => (
                        <li key={`${item.class_id}-${index}`}>
                          <strong>{item.class_name}</strong>
                          {' — '}
                          {(item.confidence * 100).toFixed(2)}%
                          {' confidence — Box: ['}
                          {item.box_xyxy.join(', ')}
                          {']'}
                        </li>
                      ))}
                    </ul>
                  ) : (
                    <p>No cracks detected in this image.</p>
                  )}

                  {prediction && (
                    <p>
                      <strong>AI prediction:</strong>{' '}
                      {prediction.prediction}
                      {' ('}
                      {prediction.confidence_percent}% confidence)
                    </p>
                  )}

                  <p>
                    YOLO results are model predictions, not a safety
                    assessment. Human engineering review is required.
                  </p>
                </section>
              )}

              {assessmentResult && (
                <button
                  type="button"
                  onClick={handleOpenResults}
                >
                  View Assessment Results
                </button>
              )}
            </section>

            <p className="footer-note">
              InfraScan · AI-assisted assessment · Human engineering
              review required
            </p>
          </main>
        </>
      )}
    </div>
  )
}

export default App