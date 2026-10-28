
import { useState } from 'react'
import Login from './pages/Login'
import Dashboard from './pages/Dashboard'
import Assets from './pages/Assets'
import Results from './pages/Results'
import './App.css'

type InspectionResult = {
  filename: string
  size_bytes: number
  image_width: number
  image_height: number
  edge_pixels: number
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

  async function handleUpload(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault()

    if (!selectedFile) {
      setMessage('Please select an image first.')
      return
    }

    setLoading(true)
    setMessage('Uploading image...')
    setInspection(null)
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
        throw new Error(
          uploadData.detail || 'Image upload failed.'
        )
      }

      // Upload has succeeded. Keep this success even if
      // the following image-processing request fails.
      setMessage(`Image uploaded successfully: ${uploadData.filename}`)

      // Step 2: Run basic image processing without PyTorch.
      try {
        const detectionData = new FormData()
        detectionData.append('file', selectedFile)

        const detectionResponse = await fetch(
          'http://127.0.0.1:8000/detect-cracks',
          {
            method: 'POST',
            body: detectionData,
          }
        )

        const detection = await detectionResponse.json()

        if (!detectionResponse.ok) {
          throw new Error(
            detection.detail || 'Image processing failed.'
          )
        }

        const result: InspectionResult = {
          filename: uploadData.filename,
          size_bytes: uploadData.size_bytes,
          image_width: detection.image_width,
          image_height: detection.image_height,
          edge_pixels: detection.edge_pixels,
          note: detection.note,
        }

        setInspection(result)

        const resultText =
          `Image uploaded successfully. ` +
          `Image size: ${result.image_width} × ${result.image_height}. ` +
          `Edge pixels: ${result.edge_pixels}. ` +
          `This is basic image processing, not an AI prediction.`

        setAssessmentResult(resultText)
        setMessage('Upload successful! Image processing completed.')
      } catch (processingError) {
        const detail =
          processingError instanceof Error
            ? processingError.message
            : 'Unknown processing error.'

        setMessage(
          `Image uploaded successfully, but processing failed: ${detail}`
        )
      }
    } catch (error) {
      setMessage(
        error instanceof Error
          ? `Upload failed: ${error.message}`
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
              <p>Select a JPG, PNG or WEBP image (maximum 10 MB).</p>

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
                  <h2>Image Processing Result</h2>
                  <p><strong>Saved filename:</strong> {inspection.filename}</p>
                  <p>
                    <strong>File size:</strong>{' '}
                    {(inspection.size_bytes / 1024).toFixed(1)} KB
                  </p>
                  <p>
                    <strong>Image dimensions:</strong>{' '}
                    {inspection.image_width} × {inspection.image_height}
                  </p>
                  <p>
                    <strong>Edge pixels detected:</strong>{' '}
                    {inspection.edge_pixels}
                  </p>
                  <p>{inspection.note}</p>
                  <p>
                    <strong>AI prediction:</strong> Not available yet.
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
