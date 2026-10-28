
import { useEffect, useState } from 'react'

type Asset = {
  id: number
  name: string
  type: string
  location: string
}

const API_URL = 'http://127.0.0.1:8000'

function Assets() {
  const [name, setName] = useState('')
  const [type, setType] = useState('Bridge')
  const [location, setLocation] = useState('')
  const [assets, setAssets] = useState<Asset[]>([])
  const [message, setMessage] = useState('')
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)

  async function loadAssets() {
    setLoading(true)

    try {
      const token = localStorage.getItem('infrascan_token')

      if (!token) {
        throw new Error('Please log in again to view assets.')
      }

      const response = await fetch(`${API_URL}/assets`, {
        method: 'GET',
        headers: {
          Authorization: `Bearer ${token}`,
        },
      })

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}))
        throw new Error(
          errorData.detail || `Could not load assets (${response.status}).`
        )
      }

      const data: Asset[] = await response.json()
      setAssets(data)
      setMessage('')
    } catch (error) {
      setMessage(
        error instanceof Error
          ? error.message
          : 'Could not connect to the backend.'
      )
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    void loadAssets()
  }, [])

  async function handleAddAsset(
    event: React.FormEvent<HTMLFormElement>
  ) {
    event.preventDefault()
    setSaving(true)
    setMessage('')

    try {
      const token = localStorage.getItem('infrascan_token')

      if (!token) {
        throw new Error('Please log in again to save an asset.')
      }

      const response = await fetch(`${API_URL}/assets`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          name: name.trim(),
          asset_type: type,
          location: location.trim(),
        }),
      })

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}))
        throw new Error(
          errorData.detail || `Asset save failed (${response.status}).`
        )
      }

      const savedAsset: Asset = await response.json()

      setAssets((previous) => [savedAsset, ...previous])
      setName('')
      setLocation('')
      setMessage('Asset saved successfully!')
    } catch (error) {
      setMessage(
        error instanceof Error
          ? error.message
          : 'Could not save the asset.'
      )
    } finally {
      setSaving(false)
    }
  }

  return (
    <main className="main-content">
      <h1>Infrastructure Assets</h1>
      <p>Add and view bridges, roads, buildings, and other assets.</p>

      <section className="upload-card">
        <h2>Add New Asset</h2>

        <form onSubmit={handleAddAsset}>
          <label htmlFor="asset-name">Asset Name</label>
          <input
            id="asset-name"
            value={name}
            onChange={(event) => setName(event.target.value)}
            placeholder="e.g. Bridge A"
            required
            maxLength={150}
          />

          <label htmlFor="asset-type">Asset Type</label>
          <select
            id="asset-type"
            value={type}
            onChange={(event) => setType(event.target.value)}
          >
            <option>Bridge</option>
            <option>Road</option>
            <option>Building</option>
            <option>Other</option>
          </select>

          <label htmlFor="asset-location">Location</label>
          <input
            id="asset-location"
            value={location}
            onChange={(event) => setLocation(event.target.value)}
            placeholder="e.g. Bhopal"
            required
            maxLength={200}
          />

          <button type="submit" disabled={saving}>
            {saving ? 'Saving...' : 'Add Asset'}
          </button>
        </form>

        {message && (
          <p className="status-message" role="status">
            {message}
          </p>
        )}
      </section>

      <section className="upload-card">
        <h2>Saved Assets ({assets.length})</h2>

        {loading ? (
          <p>Loading assets...</p>
        ) : assets.length === 0 ? (
          <p>No assets added yet.</p>
        ) : (
          assets.map((asset) => (
            <article key={asset.id}>
              <h3>{asset.name}</h3>
              <p>Type: {asset.type}</p>
              <p>Location: {asset.location}</p>
            </article>
          ))
        )}

        <button
          type="button"
          onClick={() => void loadAssets()}
          disabled={loading}
        >
          Refresh Assets
        </button>
      </section>
    </main>
  )
}

export default Assets
