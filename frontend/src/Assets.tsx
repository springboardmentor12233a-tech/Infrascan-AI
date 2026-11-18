
import { useEffect, useState } from 'react'
import {
  MapContainer,
  TileLayer,
  Marker,
  Popup,
} from 'react-leaflet'
import L from 'leaflet'
import 'leaflet/dist/leaflet.css'

type Asset = {
  id: number
  name: string
  type: string
  location: string
  latitude: number | null
  longitude: number | null
}

const API_URL = 'http://127.0.0.1:8000'

const defaultIcon = L.icon({
  iconUrl:
    'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-icon.png',
  iconRetinaUrl:
    'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-icon-2x.png',
  shadowUrl:
    'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-shadow.png',
  iconSize: [25, 41],
  iconAnchor: [12, 41],
  popupAnchor: [1, -34],
  shadowSize: [41, 41],
})

function Assets() {
  const [name, setName] = useState('')
  const [type, setType] = useState('Bridge')
  const [location, setLocation] = useState('')
  const [latitude, setLatitude] = useState('')
  const [longitude, setLongitude] = useState('')

  const [assets, setAssets] = useState<Asset[]>([])
  const [message, setMessage] = useState('')
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)

  async function loadAssets() {
    try {
      const token = localStorage.getItem('infrascan_token')

      if (!token) {
        throw new Error('Please login first.')
      }

      const response = await fetch(`${API_URL}/assets`, {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      })

      if (!response.ok) {
        throw new Error('Could not load assets.')
      }

      const data: Asset[] = await response.json()
      setAssets(data)
      setMessage('')
    } catch (error) {
      setMessage(
        error instanceof Error
          ? error.message
          : 'Could not load assets.'
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
        throw new Error('Please login first.')
      }

      const hasLatitude = latitude.trim() !== ''
      const hasLongitude = longitude.trim() !== ''

      if (hasLatitude !== hasLongitude) {
        throw new Error(
          'Enter both latitude and longitude.'
        )
      }

      const lat = hasLatitude ? Number(latitude) : null
      const lng = hasLongitude ? Number(longitude) : null

      if (
        lat !== null &&
        (Number.isNaN(lat) || lat < -90 || lat > 90)
      ) {
        throw new Error('Invalid latitude.')
      }

      if (
        lng !== null &&
        (Number.isNaN(lng) || lng < -180 || lng > 180)
      ) {
        throw new Error('Invalid longitude.')
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
          latitude: lat,
          longitude: lng,
        }),
      })

      if (!response.ok) {
        const errorData = await response.json()
        throw new Error(
          errorData.detail || 'Asset save failed.'
        )
      }

      const savedAsset: Asset = await response.json()

      setAssets((previous) => [
        savedAsset,
        ...previous,
      ])

      setName('')
      setLocation('')
      setLatitude('')
      setLongitude('')

      setMessage('Asset successfully saved!')
    } catch (error) {
      setMessage(
        error instanceof Error
          ? error.message
          : 'Asset save failed.'
      )
    } finally {
      setSaving(false)
    }
  }

  const mappedAssets = assets.filter(
    (asset) =>
      asset.latitude !== null &&
      asset.longitude !== null
  )

  const mapCenter: [number, number] =
    mappedAssets.length > 0
      ? [
          mappedAssets[0].latitude!,
          mappedAssets[0].longitude!,
        ]
      : [23.2599, 77.4126]

  return (
    <main className="main-content">
      <h1>Infrastructure Assets</h1>

      <p>
        Add and view bridges, roads, buildings, and other assets.
      </p>

      <section className="upload-card">
        <h2>Add New Asset</h2>

        <form onSubmit={handleAddAsset}>
          <label>Asset Name</label>
          <input
            value={name}
            onChange={(event) =>
              setName(event.target.value)
            }
            placeholder="e.g. Bridge A"
            required
          />

          <label>Asset Type</label>
          <select
            value={type}
            onChange={(event) =>
              setType(event.target.value)
            }
          >
            <option>Bridge</option>
            <option>Road</option>
            <option>Building</option>
            <option>Other</option>
          </select>

          <label>Location</label>
          <input
            value={location}
            onChange={(event) =>
              setLocation(event.target.value)
            }
            placeholder="e.g. Bhopal"
            required
          />

          <label>Latitude</label>
          <input
            type="number"
            step="any"
            value={latitude}
            onChange={(event) =>
              setLatitude(event.target.value)
            }
            placeholder="e.g. 23.2599"
          />

          <label>Longitude</label>
          <input
            type="number"
            step="any"
            value={longitude}
            onChange={(event) =>
              setLongitude(event.target.value)
            }
            placeholder="e.g. 77.4126"
          />

          <button type="submit" disabled={saving}>
            {saving ? 'Saving...' : 'Add Asset'}
          </button>
        </form>

        {message && (
          <p className="status-message">{message}</p>
        )}
      </section>

      <section className="upload-card">
        <h2>Infrastructure Damage Map</h2>

        <p>
          Assets with GPS coordinates: {mappedAssets.length}
        </p>

        <MapContainer
          key={mapCenter.join(',')}
          center={mapCenter}
          zoom={mappedAssets.length > 0 ? 12 : 5}
          style={{
            height: '450px',
            width: '100%',
            borderRadius: '10px',
            zIndex: 1,
          }}
          scrollWheelZoom={true}
        >
          <TileLayer
            attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
            url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
          />

          {mappedAssets.map((asset) => (
            <Marker
              key={asset.id}
              position={[
                asset.latitude!,
                asset.longitude!,
              ]}
              icon={defaultIcon}
            >
              <Popup>
                <strong>{asset.name}</strong>
                <br />
                Type: {asset.type}
                <br />
                Location: {asset.location}
                <br />
                Latitude: {asset.latitude}
                <br />
                Longitude: {asset.longitude}
              </Popup>
            </Marker>
          ))}
        </MapContainer>

        {mappedAssets.length === 0 && (
          <p>
            No GPS locations available. Add coordinates
            to an asset to display its marker.
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
              <p>
                Coordinates:{' '}
                {asset.latitude !== null &&
                asset.longitude !== null
                  ? `${asset.latitude}, ${asset.longitude}`
                  : 'Not available'}
              </p>
            </article>
          ))
        )}
      </section>
    </main>
  )
}

export default Assets
