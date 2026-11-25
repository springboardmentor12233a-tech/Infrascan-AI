import React, { useEffect, useRef, useState } from 'react'
import L from 'leaflet'
import 'leaflet/dist/leaflet.css'
import { Navbar } from '../components/Navbar'
import { useAuth } from '../context/AuthContext'
import { mapApi } from '../api/client'
import type {
  MapAssetProperties,
  MapDamageProperties,
  MapFeature,
  HotspotCell,
  RegionSummary,
  RouteStop,
} from '../api/client'

// Severity color palette
delete (L.Icon.Default.prototype as any)._getIconUrl
L.Icon.Default.mergeOptions({
  iconRetinaUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-icon-2x.png',
  iconUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-icon.png',
  shadowUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-shadow.png',
})

const SEVERITY_COLORS: Record<string, string> = {
  none: '#6B7280',      // Gray
  minor: '#10B981',     // Green
  moderate: '#F59E0B',  // Yellow
  severe: '#F97316',    // Orange
  critical: '#EF4444',  // Red
  restricted: '#9CA3AF',// Neutral light gray
}

// Configurable OSM tile URL
const TILE_URL = import.meta.env.VITE_MAP_TILE_URL || 'https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png'
const TILE_ATTRIBUTION = '&copy; <a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noreferrer">OpenStreetMap contributors</a>'

export const MapPage: React.FC = () => {
  const { user } = useAuth()
  const mapContainerRef = useRef<HTMLDivElement>(null)
  const mapInstanceRef = useRef<L.Map | null>(null)
  const markersLayerGroupRef = useRef<L.LayerGroup | null>(null)

  // Active layer selection
  const [activeLayer, setActiveLayer] = useState<'assets' | 'damage' | 'hotspots' | 'route'>('assets')

  // Filters
  const [assetType, setAssetType] = useState<string>('')
  const [selectedSeverities, setSelectedSeverities] = useState<string[]>([])
  const [district, setDistrict] = useState<string>('')
  const [dateFrom, setDateFrom] = useState<string>('')
  const [dateTo, setDateTo] = useState<string>('')
  const [reviewStatus, setReviewStatus] = useState<string>('')
  const [priority, setPriority] = useState<string>('')

  // Route calculation state
  const [routeInspectorId, setRouteInspectorId] = useState<number>(user?.user_id || 1)
  const [routeDate, setRouteDate] = useState<string>(new Date().toISOString().split('T')[0])
  const [routeStops, setRouteStops] = useState<RouteStop[]>([])
  const [routeDistanceKm, setRouteDistanceKm] = useState<number>(0)
  const [routeMessage, setRouteMessage] = useState<string>('')

  // Data states
  const [loading, setLoading] = useState<boolean>(true)
  const [, setError] = useState<string | null>(null)
  const [assetFeatures, setAssetFeatures] = useState<MapFeature<MapAssetProperties>[]>([])
  const [damageFeatures, setDamageFeatures] = useState<MapFeature<MapDamageProperties>[]>([])
  const [hotspotCells, setHotspotCells] = useState<HotspotCell[]>([])
  const [regionSummaries, setRegionSummaries] = useState<RegionSummary[]>([])

  // 1. Initialize Leaflet Map
  useEffect(() => {
    if (!mapContainerRef.current || mapInstanceRef.current) return

    // Center on default coordinate (Chennai region / India baseline)
    const map = L.map(mapContainerRef.current, {
      center: [13.04, 80.20],
      zoom: 11,
      zoomControl: true,
    })

    const tileLayer = L.tileLayer(TILE_URL, {
      attribution: TILE_ATTRIBUTION,
      maxZoom: 19,
    })

    tileLayer.on('tileerror', () => {
      console.warn('Map tile failed to load from configured tile server.')
    })

    tileLayer.addTo(map)

    const markersGroup = L.layerGroup().addTo(map)
    markersLayerGroupRef.current = markersGroup
    mapInstanceRef.current = map

    // Ensure map sizes accurately when tab or view becomes active
    const handleResize = () => {
      map.invalidateSize()
    }
    window.addEventListener('resize', handleResize)
    document.addEventListener('visibilitychange', handleResize)
    const resizeTimer = setTimeout(handleResize, 300)

    return () => {
      window.removeEventListener('resize', handleResize)
      document.removeEventListener('visibilitychange', handleResize)
      clearTimeout(resizeTimer)
      map.remove()
      mapInstanceRef.current = null
    }
  }, [])

  // 2. Fetch Map Data based on Active Layer & Filters
  const fetchMapData = async () => {
    setLoading(true)
    setError(null)
    try {
      const params: Record<string, any> = {}
      if (assetType) params.asset_type = assetType
      if (selectedSeverities.length > 0) params.severity = selectedSeverities
      if (district) params.district = district
      if (dateFrom) params.date_from = dateFrom
      if (dateTo) params.date_to = dateTo
      if (reviewStatus) params.review_status = reviewStatus
      if (priority) params.priority = priority

      if (activeLayer === 'assets') {
        const data = await mapApi.getAssets(params)
        setAssetFeatures(data.features || [])
      } else if (activeLayer === 'damage') {
        const data = await mapApi.getDamage(params)
        setDamageFeatures(data.features || [])
      } else if (activeLayer === 'hotspots') {
        const data = await mapApi.getHotspots(params)
        setHotspotCells(data.grid || [])
      } else if (activeLayer === 'route') {
        if (routeInspectorId && routeDate) {
          const data = await mapApi.getRoute(routeInspectorId, routeDate)
          setRouteStops(data.ordered_stops || [])
          setRouteDistanceKm(data.total_distance_km || 0)
          setRouteMessage(data.message || '')
        }
      }

      // Always fetch region summaries for the sidebar
      const summaryData = await mapApi.getSummary()
      setRegionSummaries(summaryData.regions || [])
    } catch (err: any) {
      console.error('Failed to load map data:', err)
      setError(err.response?.data?.detail || 'Failed to load map data. Please check your connection.')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchMapData()
  }, [activeLayer, assetType, selectedSeverities, district, dateFrom, dateTo, reviewStatus, priority])

  // Real-time listener: refresh marker conditions when live events arrive
  useEffect(() => {
    const handleLiveEvent = (e: Event) => {
      const customEvent = e as CustomEvent
      const type = customEvent.detail?.type || ''
      if (
        type.startsWith('asset.') ||
        type.startsWith('severity.') ||
        type.startsWith('priority.') ||
        type.startsWith('task.')
      ) {
        fetchMapData()
      }
    }
    window.addEventListener('infrascan:event', handleLiveEvent)
    return () => window.removeEventListener('infrascan:event', handleLiveEvent)
  }, [activeLayer, assetType, selectedSeverities, district, dateFrom, dateTo, reviewStatus, priority])

  // 3. Render Leaflet Markers & Layers whenever data changes
  useEffect(() => {
    const map = mapInstanceRef.current
    const layerGroup = markersLayerGroupRef.current
    if (!map || !layerGroup) return

    layerGroup.clearLayers()
    const bounds = L.latLngBounds([])

    // A. ASSETS LAYER
    if (activeLayer === 'assets') {
      assetFeatures.forEach((feat) => {
        const [lon, lat] = feat.geometry.coordinates
        if (typeof lat !== 'number' || typeof lon !== 'number' || isNaN(lat) || isNaN(lon)) return

        const p = feat.properties
        const sev = p.current_condition.severity.toLowerCase()
        const color = SEVERITY_COLORS[sev] || SEVERITY_COLORS.none
        const isProvisional = p.current_condition.provisional === true

        // Create SVG circle marker
        const marker = L.circleMarker([lat, lon], {
          radius: 9,
          fillColor: isProvisional ? '#FFFFFF' : color,
          color: color,
          weight: isProvisional ? 3 : 2,
          opacity: 1,
          fillOpacity: isProvisional ? 0.4 : 0.85,
          dashArray: isProvisional ? '3, 4' : undefined,
        })

        const scoreText = p.current_condition.score !== null ? `${p.current_condition.score.toFixed(1)} / 100` : 'Restricted / N/A'
        const dateText = p.current_condition.last_inspection_date || 'Never inspected'
        const provisionalBadge = isProvisional ? '<span style="color: #F59E0B; font-weight: bold;">(Provisional AI)</span>' : '<span style="color: #10B981; font-weight: bold;">(Engineer Reviewed)</span>'
        const overdueBadge = p.overdue ? '<span style="background: #FEE2E2; color: #DC2626; padding: 2px 6px; border-radius: 4px; font-size: 11px; font-weight: bold;">OVERDUE</span>' : ''

        const popupHtml = `
          <div style="font-family: sans-serif; min-width: 220px; line-height: 1.4;">
            <div style="font-weight: bold; font-size: 14px; margin-bottom: 4px; color: #1E293B;">
              ${p.name} ${overdueBadge}
            </div>
            <div style="font-size: 12px; color: #64748B; margin-bottom: 6px;">
              ${p.type.toUpperCase()} &bull; ${p.material} &bull; ${p.district}
            </div>
            <div style="background: #F8FAFC; padding: 6px 8px; border-radius: 4px; font-size: 12px; margin-bottom: 8px;">
              <div><strong>Condition:</strong> <span style="text-transform: capitalize; color: ${color}; font-weight: bold;">${sev}</span> ${provisionalBadge}</div>
              <div><strong>Score:</strong> ${scoreText}</div>
              <div><strong>Last Inspected:</strong> ${dateText}</div>
              ${p.priority ? `<div><strong>Priority:</strong> <span style="font-weight: bold;">${p.priority}</span></div>` : ''}
              ${p.current_condition.pending_review_count ? `<div><strong>Pending Reviews:</strong> ${p.current_condition.pending_review_count}</div>` : ''}
            </div>
            <div style="display: flex; gap: 8px;">
              <a href="/assets/${p.id}" style="font-size: 11px; color: #4F46E5; font-weight: 600; text-decoration: none;">View Asset Details &rarr;</a>
            </div>
          </div>
        `

        marker.bindPopup(popupHtml)
        marker.addTo(layerGroup)
        bounds.extend([lat, lon])
      })
    }

    // B. DAMAGE MARKERS LAYER
    else if (activeLayer === 'damage') {
      damageFeatures.forEach((feat) => {
        const [lon, lat] = feat.geometry.coordinates
        if (typeof lat !== 'number' || typeof lon !== 'number' || isNaN(lat) || isNaN(lon)) return

        const p = feat.properties
        const sev = p.severity.toLowerCase()
        const color = SEVERITY_COLORS[sev] || SEVERITY_COLORS.none
        const isExif = p.location_source === 'image_exif'

        const marker = L.circleMarker([lat, lon], {
          radius: 7,
          fillColor: color,
          color: isExif ? '#1E293B' : '#94A3B8',
          weight: isExif ? 2 : 1,
          opacity: 1,
          fillOpacity: 0.85,
        })

        const popupHtml = `
          <div style="font-family: sans-serif; min-width: 200px; line-height: 1.4;">
            <div style="font-weight: bold; font-size: 13px; color: #1E293B;">Damage Observation</div>
            <div style="font-size: 11px; color: #64748B;">Asset: ${p.asset_name}</div>
            <div style="font-size: 11px; color: #64748B;">Source: <strong style="color: ${isExif ? '#059669' : '#D97706'}">${p.location_source === 'image_exif' ? 'Photo EXIF GPS' : 'Asset Location'}</strong></div>
            <hr style="margin: 4px 0; border: none; border-top: 1px solid #E2E8F0;" />
            <div style="font-size: 12px;"><strong>Severity:</strong> <span style="text-transform: capitalize; color: ${color}; font-weight: bold;">${sev}</span></div>
            <div style="font-size: 12px;"><strong>Defects:</strong> ${p.damage_types.join(', ')}</div>
            <div style="font-size: 12px;"><strong>Detections:</strong> ${p.detection_count} box(es)</div>
            <div style="font-size: 12px;"><strong>Date:</strong> ${p.date}</div>
            <div style="margin-top: 6px;">
              <a href="/inspections/${p.inspection_id}" style="font-size: 11px; color: #4F46E5; font-weight: 600; text-decoration: none;">Open Inspection &rarr;</a>
            </div>
          </div>
        `

        marker.bindPopup(popupHtml)
        marker.addTo(layerGroup)
        bounds.extend([lat, lon])
      })
    }

    // C. HOTSPOTS LAYER
    else if (activeLayer === 'hotspots') {
      hotspotCells.forEach((cell) => {
        const [lat, lon] = cell.cell_centre
        const color = SEVERITY_COLORS[cell.max_severity] || SEVERITY_COLORS.minor
        const radius = Math.min(35, Math.max(12, cell.count * 6))

        const circle = L.circleMarker([lat, lon], {
          radius: radius,
          fillColor: color,
          color: color,
          weight: 1,
          opacity: 0.8,
          fillOpacity: Math.min(0.7, 0.25 + (cell.mean_score / 100) * 0.45),
        })

        const popupHtml = `
          <div style="font-family: sans-serif; font-size: 12px; line-height: 1.4;">
            <div style="font-weight: bold; color: #1E293B;">Damage Cluster</div>
            <div><strong>Observations:</strong> ${cell.count}</div>
            <div><strong>Mean Score:</strong> ${cell.mean_score.toFixed(1)} / 100</div>
            <div><strong>Max Severity:</strong> <span style="color: ${color}; font-weight: bold; text-transform: capitalize;">${cell.max_severity}</span></div>
          </div>
        `
        circle.bindPopup(popupHtml)
        circle.addTo(layerGroup)
        bounds.extend([lat, lon])
      })
    }

    // D. INSPECTION ROUTE LAYER
    else if (activeLayer === 'route' && routeStops.length > 0) {
      const latlngs: [number, number][] = []

      routeStops.forEach((stop) => {
        latlngs.push([stop.lat, stop.lon])

        // Custom numbered marker
        const icon = L.divIcon({
          className: 'custom-route-marker',
          html: `<div style="background: #4F46E5; color: white; width: 26px; height: 26px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 12px; font-weight: bold; border: 2px solid white; box-shadow: 0 2px 4px rgba(0,0,0,0.3);">${stop.stop_number}</div>`,
          iconSize: [26, 26],
          iconAnchor: [13, 13],
        })

        const marker = L.marker([stop.lat, stop.lon], { icon })
        marker.bindPopup(`
          <div style="font-family: sans-serif; font-size: 12px;">
            <div style="font-weight: bold; font-size: 13px;">Stop #${stop.stop_number}: ${stop.asset_name}</div>
            <div style="color: #64748B;">${stop.asset_type.toUpperCase()} &bull; ${stop.district}</div>
            <div style="margin-top: 4px;"><a href="/inspections/${stop.inspection_id}" style="color: #4F46E5; text-decoration: none;">View Inspection &rarr;</a></div>
          </div>
        `)
        marker.addTo(layerGroup)
        bounds.extend([stop.lat, stop.lon])
      })

      // Draw route connecting polyline
      const polyline = L.polyline(latlngs, {
        color: '#4F46E5',
        weight: 3,
        dashArray: '6, 8',
        opacity: 0.85,
      })
      polyline.addTo(layerGroup)
    }

    // Fit map bounds if features exist
    if (bounds.isValid() && bounds.getNorthEast().lat !== bounds.getSouthWest().lat) {
      map.fitBounds(bounds, { padding: [40, 40], maxZoom: 15 })
    }
  }, [activeLayer, assetFeatures, damageFeatures, hotspotCells, routeStops])

  // Handle severity filter toggle
  const toggleSeverity = (sev: string) => {
    setSelectedSeverities((prev) =>
      prev.includes(sev) ? prev.filter((s) => s !== sev) : [...prev, sev],
    )
  }

  return (
    <div className="min-h-screen bg-slate-50 flex flex-col">
      <Navbar />

      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-6">
        {/* Header & Disclaimers */}
        <div className="mb-4">
          <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
            <div>
              <h1 className="text-2xl font-bold text-slate-900 tracking-tight">Geospatial Damage & Asset Map</h1>
              <p className="text-sm text-slate-500">
                Visualizing infrastructure assets, localized damage observations, distress clusters, and planned inspector routing.
              </p>
            </div>

            {/* Layer Switcher Buttons */}
            <div className="inline-flex rounded-md shadow-sm bg-white p-1 border border-slate-200">
              <button
                type="button"
                onClick={() => setActiveLayer('assets')}
                className={`px-3 py-1.5 text-xs font-medium rounded ${
                  activeLayer === 'assets' ? 'bg-indigo-600 text-white' : 'text-slate-700 hover:bg-slate-100'
                }`}
              >
                Assets
              </button>
              <button
                type="button"
                onClick={() => setActiveLayer('damage')}
                className={`px-3 py-1.5 text-xs font-medium rounded ${
                  activeLayer === 'damage' ? 'bg-indigo-600 text-white' : 'text-slate-700 hover:bg-slate-100'
                }`}
              >
                Damage Markers
              </button>
              <button
                type="button"
                onClick={() => setActiveLayer('hotspots')}
                className={`px-3 py-1.5 text-xs font-medium rounded ${
                  activeLayer === 'hotspots' ? 'bg-indigo-600 text-white' : 'text-slate-700 hover:bg-slate-100'
                }`}
              >
                Hotspots
              </button>
              <button
                type="button"
                onClick={() => setActiveLayer('route')}
                className={`px-3 py-1.5 text-xs font-medium rounded ${
                  activeLayer === 'route' ? 'bg-indigo-600 text-white' : 'text-slate-700 hover:bg-slate-100'
                }`}
              >
                Inspection Route
              </button>
            </div>
          </div>

          {/* Mandatory Safety Notice */}
          <div className="mt-3 bg-amber-50 border-l-4 border-amber-400 p-3 rounded-r text-xs text-amber-900">
            <span className="font-bold">CRITICAL NOTICE:</span> AI result for engineer review, not a final structural safety verdict. Locations are points; GPS from photos may be missing or inaccurate.
          </div>
        </div>

        {/* Filter Bar */}
        <div className="bg-white p-4 rounded-lg shadow-sm border border-slate-200 mb-6">
          <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-6 gap-3">
            {/* Asset Type */}
            <div>
              <label className="block text-xs font-medium text-slate-700 mb-1">Asset Type</label>
              <select
                value={assetType}
                onChange={(e) => setAssetType(e.target.value)}
                className="w-full text-xs rounded border-slate-300 py-1.5 px-2 bg-slate-50 focus:bg-white"
              >
                <option value="">All Types</option>
                <option value="bridge">Bridge</option>
                <option value="road">Road</option>
                <option value="tunnel">Tunnel</option>
                <option value="building">Building</option>
                <option value="dam">Dam</option>
                <option value="retaining_wall">Retaining Wall</option>
              </select>
            </div>

            {/* District */}
            <div>
              <label className="block text-xs font-medium text-slate-700 mb-1">District</label>
              <input
                type="text"
                placeholder="Filter district..."
                value={district}
                onChange={(e) => setDistrict(e.target.value)}
                className="w-full text-xs rounded border border-slate-300 py-1 px-2 bg-slate-50 focus:bg-white"
              />
            </div>

            {/* Review Status */}
            <div>
              <label className="block text-xs font-medium text-slate-700 mb-1">Review Status</label>
              <select
                value={reviewStatus}
                onChange={(e) => setReviewStatus(e.target.value)}
                className="w-full text-xs rounded border-slate-300 py-1.5 px-2 bg-slate-50 focus:bg-white"
              >
                <option value="">All Statuses</option>
                <option value="pending">Provisional (Pending Review)</option>
                <option value="reviewed">Engineer Reviewed</option>
              </select>
            </div>

            {/* Date Range From */}
            <div>
              <label className="block text-xs font-medium text-slate-700 mb-1">Date From</label>
              <input
                type="date"
                value={dateFrom}
                onChange={(e) => setDateFrom(e.target.value)}
                className="w-full text-xs rounded border border-slate-300 py-1 px-2 bg-slate-50 focus:bg-white"
              />
            </div>

            {/* Date Range To */}
            <div>
              <label className="block text-xs font-medium text-slate-700 mb-1">Date To</label>
              <input
                type="date"
                value={dateTo}
                onChange={(e) => setDateTo(e.target.value)}
                className="w-full text-xs rounded border border-slate-300 py-1 px-2 bg-slate-50 focus:bg-white"
              />
            </div>

            {/* Reset Filters */}
            <div className="flex items-end">
              <button
                type="button"
                onClick={() => {
                  setAssetType('')
                  setSelectedSeverities([])
                  setDistrict('')
                  setDateFrom('')
                  setDateTo('')
                  setReviewStatus('')
                  setPriority('')
                }}
                className="w-full text-xs bg-slate-100 hover:bg-slate-200 text-slate-700 py-1.5 px-3 rounded border border-slate-200 font-medium"
              >
                Reset Filters
              </button>
            </div>
          </div>

          {/* Severity Badges Filter */}
          <div className="mt-3 pt-3 border-t border-slate-100 flex flex-wrap items-center gap-2">
            <span className="text-xs font-medium text-slate-500 mr-1">Severity:</span>
            {['none', 'minor', 'moderate', 'severe', 'critical'].map((sev) => {
              const active = selectedSeverities.includes(sev)
              const color = SEVERITY_COLORS[sev]
              return (
                <button
                  key={sev}
                  type="button"
                  onClick={() => toggleSeverity(sev)}
                  style={{
                    backgroundColor: active ? color : '#F1F5F9',
                    color: active ? '#FFFFFF' : '#475569',
                    borderColor: color,
                  }}
                  className="px-2.5 py-0.5 rounded-full text-xs font-semibold border transition-all"
                >
                  {sev.toUpperCase()}
                </button>
              )
            })}
          </div>

          {/* Route Controls (only when Route layer active) */}
          {activeLayer === 'route' && (
            <div className="mt-3 pt-3 border-t border-indigo-100 bg-indigo-50/50 p-3 rounded flex flex-wrap items-center gap-3">
              <span className="text-xs font-bold text-indigo-900">Route Controls:</span>
              <div className="flex items-center gap-2">
                <label className="text-xs text-slate-700">Inspector ID:</label>
                <input
                  type="number"
                  value={routeInspectorId}
                  onChange={(e) => setRouteInspectorId(parseInt(e.target.value) || 1)}
                  className="w-20 text-xs rounded border border-slate-300 py-1 px-2 bg-white"
                />
              </div>
              <div className="flex items-center gap-2">
                <label className="text-xs text-slate-700">Date:</label>
                <input
                  type="date"
                  value={routeDate}
                  onChange={(e) => setRouteDate(e.target.value)}
                  className="text-xs rounded border border-slate-300 py-1 px-2 bg-white"
                />
              </div>
              <button
                type="button"
                onClick={fetchMapData}
                className="text-xs bg-indigo-600 hover:bg-indigo-700 text-white font-semibold py-1 px-3 rounded shadow-sm"
              >
                Compute Route
              </button>
              {routeDistanceKm > 0 && (
                <span className="text-xs font-semibold text-indigo-800 ml-auto">
                  {routeStops.length} stops &bull; Total: {routeDistanceKm} km (straight-line order, not a road route)
                </span>
              )}
            </div>
          )}
        </div>

        {/* Map & Region Summary Layout */}
        <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
          {/* Leaflet Map Container */}
          <div className="lg:col-span-3 bg-white rounded-lg shadow-sm border border-slate-200 overflow-hidden relative">
            <div
              ref={mapContainerRef}
              style={{ height: '620px', width: '100%', zIndex: 10 }}
              className="bg-slate-100"
            />

            {/* Map Legend Overlay */}
            <div className="absolute bottom-4 left-4 bg-white/95 backdrop-blur-sm p-3 rounded-lg shadow-md border border-slate-200 text-xs z-20 pointer-events-auto">
              <div className="font-bold text-slate-800 mb-2">Severity Legend</div>
              <div className="grid grid-cols-2 gap-x-4 gap-y-1">
                <div className="flex items-center gap-1.5">
                  <span className="w-3 h-3 rounded-full bg-slate-500 inline-block"></span>
                  <span>None (No damage detected by AI)</span>
                </div>
                <div className="flex items-center gap-1.5">
                  <span className="w-3 h-3 rounded-full bg-emerald-500 inline-block"></span>
                  <span>Minor</span>
                </div>
                <div className="flex items-center gap-1.5">
                  <span className="w-3 h-3 rounded-full bg-amber-500 inline-block"></span>
                  <span>Moderate</span>
                </div>
                <div className="flex items-center gap-1.5">
                  <span className="w-3 h-3 rounded-full bg-orange-500 inline-block"></span>
                  <span>Severe</span>
                </div>
                <div className="flex items-center gap-1.5">
                  <span className="w-3 h-3 rounded-full bg-red-600 inline-block"></span>
                  <span>Critical</span>
                </div>
                <div className="flex items-center gap-1.5">
                  <span className="w-3 h-3 rounded-full border-2 border-dashed border-amber-500 bg-white inline-block"></span>
                  <span>Provisional AI</span>
                </div>
              </div>
            </div>

            {/* Empty State Banner if no results */}
            {!loading && activeLayer === 'assets' && assetFeatures.length === 0 && (
              <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 bg-white/95 p-4 rounded-lg shadow-lg border border-slate-300 text-center z-20">
                <p className="text-sm font-semibold text-slate-700">No assets match the selected filters.</p>
                <p className="text-xs text-slate-500 mt-1">No damage detected by the AI. This is not evidence that there is no damage.</p>
              </div>
            )}
            {!loading && activeLayer === 'damage' && damageFeatures.length === 0 && (
              <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 bg-white/95 p-4 rounded-lg shadow-lg border border-slate-300 text-center z-20">
                <p className="text-sm font-semibold text-slate-700">No damage markers found for the current query.</p>
                <p className="text-xs text-slate-500 mt-1">No damage detected by the AI. This is not evidence that there is no damage.</p>
              </div>
            )}
            {!loading && activeLayer === 'route' && routeStops.length === 0 && (
              <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 bg-white/95 p-4 rounded-lg shadow-lg border border-slate-300 text-center z-20">
                <p className="text-sm font-semibold text-slate-700">{routeMessage || 'No inspection route stops for this inspector on the specified date.'}</p>
                <p className="text-xs text-slate-500 mt-1">Select an active inspection date or choose another inspector.</p>
              </div>
            )}
          </div>

          {/* Region Summary Table Sidebar */}
          <div className="bg-white rounded-lg shadow-sm border border-slate-200 p-4 flex flex-col h-[620px] overflow-hidden">
            <h2 className="text-sm font-bold text-slate-900 mb-2">Regional Condition Summary</h2>
            <p className="text-xs text-slate-500 mb-3">Aggregated triage metrics grouped by district or asset category.</p>

            <div className="flex-1 overflow-y-auto pr-1 space-y-3">
              {regionSummaries.length === 0 ? (
                <div className="text-xs text-slate-400 py-6 text-center">Loading regional statistics...</div>
              ) : (
                regionSummaries.map((reg) => (
                  <div key={reg.region} className="border border-slate-100 bg-slate-50/50 rounded-lg p-3 hover:bg-slate-50 transition-colors">
                    <div className="flex items-center justify-between mb-1">
                      <span className="font-bold text-xs text-slate-800">{reg.region}</span>
                      <span className="text-[11px] font-semibold text-indigo-600 bg-indigo-50 px-2 py-0.5 rounded-full">
                        {reg.total_assets} Assets
                      </span>
                    </div>

                    <div className="text-[11px] text-slate-600 mb-2">
                      Mean Score: <strong className="text-slate-800">{reg.mean_score.toFixed(1)}</strong>
                      {reg.number_overdue > 0 && (
                        <span className="text-red-600 ml-2 font-semibold">({reg.number_overdue} Overdue)</span>
                      )}
                    </div>

                    {/* Severity distribution mini-bar */}
                    <div className="flex h-1.5 w-full rounded-full overflow-hidden bg-slate-200 mb-2">
                      {['critical', 'severe', 'moderate', 'minor', 'none'].map((s) => {
                        const count = reg.counts_per_severity[s] || 0
                        if (count === 0) return null
                        const pct = (count / reg.total_assets) * 100
                        return (
                          <div
                            key={s}
                            style={{
                              width: `${pct}%`,
                              backgroundColor: SEVERITY_COLORS[s],
                            }}
                            title={`${s}: ${count}`}
                          />
                        )
                      })}
                    </div>

                    {/* Breakdown counts */}
                    <div className="grid grid-cols-3 gap-1 text-[10px] text-slate-500 text-center">
                      <div className="bg-white p-1 rounded border border-slate-100">
                        <span className="block font-bold text-red-600">{reg.counts_per_severity.critical || 0}</span>
                        Critical
                      </div>
                      <div className="bg-white p-1 rounded border border-slate-100">
                        <span className="block font-bold text-orange-500">{reg.counts_per_severity.severe || 0}</span>
                        Severe
                      </div>
                      <div className="bg-white p-1 rounded border border-slate-100">
                        <span className="block font-bold text-amber-500">{reg.counts_per_severity.moderate || 0}</span>
                        Moderate
                      </div>
                    </div>
                  </div>
                ))
              )}
            </div>

            <div className="pt-3 border-t border-slate-100 text-[11px] text-slate-400 text-center">
              Updated live from inspection database
            </div>
          </div>
        </div>
      </main>
    </div>
  )
}

export default MapPage
