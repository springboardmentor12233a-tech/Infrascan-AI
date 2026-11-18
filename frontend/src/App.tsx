
import { useState } from 'react'
import Login from './Login'
import Dashboard from './pages/Dashboard'
import Assets from './Assets'
import Results from './pages/Results'
import './App.css'

type Asset = {
  id: number
  name: string
  type: string
  location: string
}

const API_URL = 'http://127.0.0.1:8000'

function App() {
  const [selectedFile, setSelectedFile] = useState<File | null>(null)
  const [selectedAssetId, setSelectedAssetId] = useState('')
  const [selectedModel, setSelectedModel] = useState('cnn')
  const [assets, setAssets] = useState<Asset[]>([])
  const [message, setMessage] = useState('')
  const [loading, setLoading] = useState(false)
  const [preview, setPreview] = useState('')
  const [segmentationMask, setSegmentationMask] = useState('')
  const [crackPixelPercentage, setCrackPixelPercentage] = useState<number | null>(null)
  const [showLogin, setShowLogin] = useState(true)
  const [showDashboard, setShowDashboard] = useState(false)
  const [showAssets, setShowAssets] = useState(false)
  const [showResults, setShowResults] = useState(false)
  const [assessmentResult, setAssessmentResult] = useState('')

  async function handleUpload(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault()

    if (!selectedFile) {
      setMessage('Please select an image first.')
      return
    }

    if (!selectedAssetId) {
      setMessage('Please select an infrastructure asset.')
      return
    }

    const token = localStorage.getItem('infrascan_token')

    if (!token) {
      setMessage('Please log in again.')
      return
    }

    setLoading(true)
    setMessage('')
    setAssessmentResult('')
    setSegmentationMask('')
    setCrackPixelPercentage(null)

    try {
      const formData = new FormData()
      formData.append('file', selectedFile)

      let endpoint = 'predict-m3'
      let url = ''

      if (selectedModel === 'vit') {
        endpoint = 'predict-vit'
        url = `${API_URL}/${endpoint}?asset_id=${selectedAssetId}`
      } else if (selectedModel === 'unet') {
        endpoint = 'predict-unet'
        url = `${API_URL}/${endpoint}`
      } else {
        url = `${API_URL}/${endpoint}?asset_id=${selectedAssetId}`
      }

      const response = await fetch(url, {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${token}`,
        },
        body: formData,
      })

      const data = await response.json()

      if (!response.ok) {
        throw new Error(data.detail || 'AI prediction failed.')
      }

      if (selectedModel === 'unet') {
        setSegmentationMask(
          `data:image/png;base64,${data.mask_base64}`
        )

        setCrackPixelPercentage(data.crack_pixel_percentage)

        setMessage(
          `U-Net segmentation completed. Crack pixels: ${data.crack_pixels}`
        )

        return
      }

      const confidence =
        data.confidence_percent ?? data.confidence ?? 0

      const resultText =
        `AI Prediction: ${data.prediction} | ` +
        `Confidence: ${confidence}% | ` +
        `Note: ${data.note ?? 'AI assessment completed.'}`

      setMessage(resultText)
      setAssessmentResult(resultText)
    } catch (error) {
      setMessage(
        error instanceof TypeError
          ? 'Could not connect to backend. Please start FastAPI server.'
          : error instanceof Error
            ? error.message
            : 'Prediction failed.'
      )
    } finally {
      setLoading(false)
    }
  }

  function handleFileChange(event: React.ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0] ?? null

    setSelectedFile(file)
    setMessage('')
    setAssessmentResult('')
    setSegmentationMask('')
    setCrackPixelPercentage(null)

    if (preview) {
      URL.revokeObjectURL(preview)
    }

    setPreview(file ? URL.createObjectURL(file) : '')
  }

  function handleLogin() {
    setShowLogin(false)
    setShowDashboard(true)
    setShowAssets(false)
    setShowResults(false)
  }

  function handleLogout() {
    localStorage.removeItem('infrascan_token')
    setShowLogin(true)
    setShowDashboard(false)
    setShowAssets(false)
    setShowResults(false)
  }

  async function handleNewInspection() {
    setShowLogin(false)
    setShowDashboard(false)
    setShowAssets(false)
    setShowResults(false)
    setMessage('')
    setAssessmentResult('')
    setSegmentationMask('')
    setCrackPixelPercentage(null)

    try {
      const token = localStorage.getItem('infrascan_token')

      if (!token) {
        throw new Error('Please log in again.')
      }

      const response = await fetch(`${API_URL}/assets`, {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      })

      const data = await response.json()

      if (!response.ok) {
        throw new Error(data.detail || 'Could not load assets.')
      }

      setAssets(data)
      setSelectedAssetId(data.length > 0 ? String(data[0].id) : '')

      if (data.length === 0) {
        setMessage('Please register an infrastructure asset first.')
      }
    } catch (error) {
      setMessage(
        error instanceof Error ? error.message : 'Unable to load assets.'
      )
    }
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
              Upload infrastructure images for AI-powered crack
              and damage assessment.
            </p>

            <section className="upload-card">
              <h2>Start a New Inspection</h2>
              <p>Select an asset and upload a JPG, PNG or WEBP image.</p>

              <form onSubmit={handleUpload}>
                <label>Select Infrastructure Asset</label>

                <select
                  value={selectedAssetId}
                  onChange={(event) => setSelectedAssetId(event.target.value)}
                  required
                >
                  <option value="">Choose an asset</option>
                  {assets.map((asset) => (
                    <option key={asset.id} value={asset.id}>
                      {asset.name} - {asset.type}
                    </option>
                  ))}
                </select>

                <label>Select AI Model</label>

                <select
                  value={selectedModel}
                  onChange={(event) => setSelectedModel(event.target.value)}
                  required
                >
                  <option value="cnn">Six-Class CNN</option>
                  <option value="vit">Vision Transformer (ViT)</option>
                  <option value="unet">U-Net Segmentation</option>
                </select>

                <label>Upload Inspection Image</label>

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

                <button
                  type="submit"
                  disabled={loading || assets.length === 0}
                >
                  {loading ? 'Analyzing...' : 'Analyze Image'}
                </button>
              </form>

              {message && (
                <p className="status-message">{message}</p>
              )}

              {segmentationMask && (
                <div className="segmentation-result">
                  <h3>U-Net Segmentation Mask</h3>

                  <img
                    src={segmentationMask}
                    alt="U-Net crack segmentation mask"
                    className="image-preview"
                  />

                  <p>
                    Crack Pixel Percentage:{' '}
                    <strong>{crackPixelPercentage}%</strong>
                  </p>

                  <p>
                    White pixels represent the regions detected by
                    the segmentation model.
                  </p>

                  <p>
                    <strong>Note:</strong> Experimental segmentation;
                    not validated for real-world safety decisions.
                  </p>
                </div>
              )}

              {assessmentResult && (
                <button type="button" onClick={handleOpenResults}>
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
