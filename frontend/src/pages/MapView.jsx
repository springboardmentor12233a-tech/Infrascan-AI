import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';

export default function MapView() {
  const { authFetch } = useAuth();
  const [inspections, setInspections] = useState([]);
  const [mapLoaded, setMapLoaded] = useState(false);

  useEffect(() => {
    authFetch('/api/inspections')
      .then(r => r.json())
      .then(data => {
        setInspections(Array.isArray(data) ? data : []);
      })
      .catch(console.error);
  }, []);

  useEffect(() => {
    if (window.L && inspections.length > 0) {
      const container = document.getElementById('leaflet-map-container');
      if (!container) return;

      // Clean existing leaflet instance if any
      if (window._currentLeafletMap) {
        window._currentLeafletMap.remove();
      }

      // Initialize map centered around default region (Delhi/NCR with markers)
      const validPoints = inspections.filter(i => i.latitude && i.longitude);
      const defaultCenter = validPoints.length > 0
        ? [validPoints[0].latitude, validPoints[0].longitude]
        : [28.6139, 77.2090];

      const map = window.L.map('leaflet-map-container').setView(defaultCenter, 11);
      window._currentLeafletMap = map;

      // OpenStreetMap tile layer
      window.L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
        maxZoom: 19
      }).addTo(map);

      // Add pins
      validPoints.forEach(insp => {
        const res = insp.result;
        let color = '#10b981'; // green
        if (res?.severity_level?.includes('Minor')) color = '#3b82f6';
        if (res?.severity_level?.includes('Moderate')) color = '#f59e0b';
        if (res?.severity_level?.includes('Severe')) color = '#f97316';
        if (res?.severity_level?.includes('Critical')) color = '#ef4444';

        const customIcon = window.L.divIcon({
          className: 'custom-map-pin',
          html: `<div style="background-color: ${color}; width: 18px; height: 18px; border-radius: 50%; border: 3px solid white; box-shadow: 0 0 10px rgba(0,0,0,0.5);"></div>`,
          iconSize: [18, 18],
          iconAnchor: [9, 9]
        });

        const popupContent = `
          <div style="font-family: sans-serif; color: #0f172a; padding: 4px; min-width: 180px;">
            <strong style="font-size: 13px;">${insp.asset_name || 'Infrastructure Inspection'}</strong>
            <div style="font-size: 11px; color: #64748b; margin-top: 2px;">${insp.inspector_name}</div>
            <div style="margin-top: 6px; font-size: 12px;"><strong>Severity:</strong> ${res?.severity_level || 'N/A'}</div>
            <div style="font-size: 11px;"><strong>Area:</strong> ${res?.crack_area_px || 0} px</div>
            <div style="margin-top: 8px;">
              <a href="/inspections/${insp.id}" style="color: #2563eb; font-weight: bold; font-size: 11px; text-decoration: none;">View Full Inspection &rarr;</a>
            </div>
          </div>
        `;

        window.L.marker([insp.latitude, insp.longitude], { icon: customIcon })
          .addTo(map)
          .bindPopup(popupContent);
      });

      setMapLoaded(true);
    }
  }, [inspections]);

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-6">
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-black text-white tracking-tight">Geospatial Damage Mapping</h1>
          <p className="text-sm text-slate-400 mt-1">
            OpenStreetMap & Leaflet mapping displaying geolocated infrastructure inspections and severity hotspots.
          </p>
        </div>
        <div className="text-xs text-slate-400 bg-slate-900/80 px-3 py-1.5 rounded-lg border border-slate-800">
          * Coordinates derived from EXIF metadata or manual entry &mdash; <strong>never fabricated</strong>.
        </div>
      </div>

      {/* Map Legend */}
      <div className="glass-card p-3.5 rounded-xl border border-slate-800 flex flex-wrap items-center gap-5 text-xs">
        <span className="text-slate-400 font-semibold uppercase tracking-wider text-[11px]">Severity Legend:</span>
        <div className="flex items-center gap-1.5">
          <span className="w-3 h-3 rounded-full bg-emerald-500"></span>
          <span className="text-slate-300">No Visible Damage</span>
        </div>
        <div className="flex items-center gap-1.5">
          <span className="w-3 h-3 rounded-full bg-blue-500"></span>
          <span className="text-slate-300">Minor Damage</span>
        </div>
        <div className="flex items-center gap-1.5">
          <span className="w-3 h-3 rounded-full bg-amber-500"></span>
          <span className="text-slate-300">Moderate Damage</span>
        </div>
        <div className="flex items-center gap-1.5">
          <span className="w-3 h-3 rounded-full bg-orange-500"></span>
          <span className="text-slate-300">Severe Damage</span>
        </div>
        <div className="flex items-center gap-1.5">
          <span className="w-3 h-3 rounded-full bg-rose-500"></span>
          <span className="text-slate-300">Critical Review Required</span>
        </div>
      </div>

      {/* Map Container */}
      <div className="glass-card rounded-2xl border border-slate-800 overflow-hidden h-[600px] relative">
        <div id="leaflet-map-container" className="w-full h-full z-10"></div>
      </div>
    </div>
  );
}
