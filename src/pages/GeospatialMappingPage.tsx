import { useEffect, useRef, useState } from 'react'
import L from 'leaflet'
import { Search, MapPin } from 'lucide-react'
import { MOCK_ASSETS } from '@/data/mockData'
import { StatusBadge } from '@/components/ui/StatusBadge'
import { DemoBanner } from '@/components/ui/DemoBanner'
import type { InfrastructureAsset } from '@/types'

const STATUS_COLOR: Record<string, string> = {
  Critical: '#EF4444',
  'Maintenance Required': '#F97316',
  'Under Inspection': '#0891B2',
  Operational: '#10B981',
  Archived: '#94A3B8',
}

export function GeospatialMappingPage() {
  const mapContainerRef = useRef<HTMLDivElement>(null)
  const mapInstanceRef = useRef<L.Map | null>(null)
  const [search, setSearch] = useState('')
  const [statusFilter, setStatusFilter] = useState('All')
  const [selectedAsset, setSelectedAsset] = useState<InfrastructureAsset>(MOCK_ASSETS[0])

  const filteredAssets = MOCK_ASSETS.filter((a) => {
    const matchesSearch =
      a.name.toLowerCase().includes(search.toLowerCase()) ||
      a.location.toLowerCase().includes(search.toLowerCase())
    const matchesStatus = statusFilter === 'All' || a.status === statusFilter
    return matchesSearch && matchesStatus
  })

  useEffect(() => {
    if (!mapContainerRef.current || mapInstanceRef.current) return

    const map = L.map(mapContainerRef.current).setView([12.9716, 77.5946], 11)
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
      attribution: '&copy; OpenStreetMap contributors',
    }).addTo(map)

    mapInstanceRef.current = map
    return () => {
      map.remove()
      mapInstanceRef.current = null
    }
  }, [])

  useEffect(() => {
    const map = mapInstanceRef.current
    if (!map) return

    // Clear existing circleMarkers
    map.eachLayer((layer) => {
      if (layer instanceof L.CircleMarker) {
        map.removeLayer(layer)
      }
    })

    filteredAssets.forEach((asset) => {
      const color = STATUS_COLOR[asset.status] || '#0891B2'
      const marker = L.circleMarker(asset.coordinates, {
        radius: asset.status === 'Critical' ? 11 : 8,
        fillColor: color,
        color: '#FFFFFF',
        weight: 2,
        opacity: 1,
        fillOpacity: 0.9,
      }).addTo(map)

      marker.bindTooltip(`${asset.name} (${asset.status})`, { direction: 'top' })
      marker.on('click', () => setSelectedAsset(asset))
    })
  }, [filteredAssets])

  return (
    <div className="space-y-4">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div>
          <h1 className="text-xl font-semibold text-slate-900">Geospatial Damage Mapping</h1>
          <p className="text-xs text-slate-500 mt-0.5">
            Interactive spatial distribution of monitored infrastructure assets and severity markers
          </p>
        </div>
        <div className="flex items-center gap-2">
          <div className="relative">
            <Search className="w-3.5 h-3.5 text-slate-400 absolute left-2.5 top-2.5" />
            <input
              type="text"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search map..."
              className="pl-8 pr-3 py-1.5 text-xs border border-slate-200 rounded-md bg-white"
            />
          </div>
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="px-2.5 py-1.5 text-xs border border-slate-200 rounded-md bg-white"
          >
            <option value="All">All Statuses</option>
            <option value="Critical">Critical</option>
            <option value="Maintenance Required">Maintenance Required</option>
            <option value="Under Inspection">Under Inspection</option>
            <option value="Operational">Operational</option>
          </select>
        </div>
      </div>

      <DemoBanner message="Demonstration Coordinates: Geospatial markers use simulated demonstration coordinates and do not represent actual field inspection records." />

      <div className="grid lg:grid-cols-12 gap-5">
        <div className="lg:col-span-8 bg-white rounded-lg border border-slate-200 overflow-hidden shadow-xs">
          <div ref={mapContainerRef} className="h-[500px] w-full" />
        </div>

        <div className="lg:col-span-4 bg-white rounded-lg border border-slate-200 p-5 space-y-4">
          <div className="flex items-start justify-between gap-2">
            <div>
              <span className="text-[11px] font-mono text-slate-500">{selectedAsset.id}</span>
              <h2 className="text-base font-semibold text-slate-900">{selectedAsset.name}</h2>
            </div>
            <StatusBadge status={selectedAsset.status} />
          </div>

          <div className="text-xs space-y-2.5 pt-2 border-t border-slate-100">
            <div className="flex justify-between">
              <span className="text-slate-500">Type</span>
              <span className="font-medium text-slate-900">{selectedAsset.type}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-slate-500">Location</span>
              <span className="font-medium text-slate-900 text-right">{selectedAsset.location}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-slate-500">Demo Coordinates</span>
              <span className="font-mono text-slate-700">
                {selectedAsset.coordinates[0].toFixed(4)}, {selectedAsset.coordinates[1].toFixed(4)}
              </span>
            </div>
            <div className="flex justify-between">
              <span className="text-slate-500">Condition Score</span>
              <span className="font-mono font-semibold text-slate-900">{selectedAsset.conditionScore}/100</span>
            </div>
            <div className="flex justify-between">
              <span className="text-slate-500">Active Findings</span>
              <span className="font-semibold text-red-600">{selectedAsset.activeFindingsCount}</span>
            </div>
          </div>

          <div className="pt-3 border-t border-slate-100">
            <p className="text-[11px] font-semibold uppercase tracking-wider text-slate-500 mb-2">
              Filtered Assets ({filteredAssets.length})
            </p>
            <div className="space-y-1.5 max-h-48 overflow-y-auto">
              {filteredAssets.map((a) => (
                <button
                  key={a.id}
                  onClick={() => {
                    setSelectedAsset(a)
                    mapInstanceRef.current?.setView(a.coordinates, 14)
                  }}
                  className={`w-full text-left px-2.5 py-2 rounded text-xs flex items-center justify-between transition-colors ${
                    selectedAsset.id === a.id ? 'bg-cyan-50 text-cyan-900 font-medium' : 'hover:bg-slate-50 text-slate-700'
                  }`}
                >
                  <span className="truncate flex items-center gap-1.5">
                    <MapPin className="w-3 h-3 shrink-0" /> {a.name}
                  </span>
                </button>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

