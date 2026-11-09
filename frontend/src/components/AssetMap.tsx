import React, { useEffect, useRef } from 'react';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';
import { InfrastructureAsset } from '../types';
import { useNavigate } from 'react-router-dom';

interface AssetMapProps {
  assets: InfrastructureAsset[];
  height?: string;
  selectedAssetId?: number;
}

export const AssetMap: React.FC<AssetMapProps> = ({
  assets,
  height = '400px',
  selectedAssetId,
}) => {
  const mapContainerRef = useRef<HTMLDivElement>(null);
  const mapInstanceRef = useRef<L.Map | null>(null);
  const markersRef = useRef<L.Marker[]>([]);
  const navigate = useNavigate();

  useEffect(() => {
    if (!mapContainerRef.current) return;

    // Initialize map if not yet initialized
    if (!mapInstanceRef.current) {
      const map = L.map(mapContainerRef.current, {
        center: [37.7749, -122.4194], // Default view (San Francisco Bay area where sample assets are located)
        zoom: 10,
        scrollWheelZoom: false,
      });

      L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
        maxZoom: 19,
      }).addTo(map);

      mapInstanceRef.current = map;
    }

    const map = mapInstanceRef.current;

    // Clear old markers
    markersRef.current.forEach((marker) => marker.remove());
    markersRef.current = [];

    const validAssets = assets.filter(
      (a) => typeof a.latitude === 'number' && typeof a.longitude === 'number'
    );

    if (validAssets.length === 0) return;

    const bounds = L.latLngBounds([]);

    validAssets.forEach((asset) => {
      const isSelected = selectedAssetId === asset.id;

      // Color based on asset type
      const typeStr = (asset.type || '').toLowerCase();
      const colorMap: Record<string, string> = {
        bridge: '#2563eb', // Blue
        tunnel: '#7c3aed', // Purple
        dam: '#0891b2',    // Cyan
        road: '#059669',   // Emerald
      };
      const pinColor = colorMap[typeStr] || '#2563eb';

      const customIcon = L.divIcon({
        className: 'custom-map-marker',
        html: `
          <div style="
            background-color: ${pinColor};
            width: ${isSelected ? '28px' : '22px'};
            height: ${isSelected ? '28px' : '22px'};
            border-radius: 50%;
            border: 3px solid white;
            box-shadow: 0 4px 6px -1px rgba(0,0,0,0.3);
            display: flex;
            align-items: center;
            justify-content: center;
            color: white;
            font-size: 10px;
            font-weight: bold;
            transition: all 0.2s ease;
          ">
            ${asset.asset_code.split('-')[0] || '●'}
          </div>
        `,
        iconSize: [28, 28],
        iconAnchor: [14, 14],
      });

      const marker = L.marker([asset.latitude!, asset.longitude!], { icon: customIcon });

      const popupContent = document.createElement('div');
      popupContent.className = 'p-1 font-sans';
      popupContent.innerHTML = `
        <div style="min-width: 180px;">
          <div style="display: flex; align-items: center; gap: 6px; margin-bottom: 4px;">
            <span style="font-size: 10px; font-weight: bold; background-color: #f1f5f9; padding: 2px 6px; border-radius: 4px; color: #334155;">
              ${asset.asset_code}
            </span>
            <span style="font-size: 10px; text-transform: uppercase; color: #64748b; font-weight: 600;">
              ${asset.type}
            </span>
          </div>
          <h4 style="font-weight: bold; font-size: 13px; color: #0f172a; margin: 0 0 4px 0;">
            ${asset.name}
          </h4>
          <p style="font-size: 11px; color: #64748b; margin: 0 0 6px 0;">
            ${asset.location_text ? `${asset.location_text}, ` : ''}${asset.material_type || 'Reinforced Concrete'}
          </p>
          <div style="font-size: 10px; color: #94a3b8; font-family: monospace; margin-bottom: 8px;">
            GPS: ${asset.latitude!.toFixed(4)}, ${asset.longitude!.toFixed(4)}
          </div>
          <button id="view-asset-${asset.id}" style="
            width: 100%;
            background-color: #2563eb;
            color: white;
            padding: 4px 8px;
            border-radius: 6px;
            font-size: 11px;
            font-weight: 600;
            border: none;
            cursor: pointer;
          ">
            Open Asset & Inspections &rarr;
          </button>
        </div>
      `;

      marker.bindPopup(popupContent);
      marker.on('popupopen', () => {
        const btn = document.getElementById(`view-asset-${asset.id}`);
        if (btn) {
          btn.onclick = () => navigate(`/assets/${asset.id}`);
        }
      });

      marker.addTo(map);
      markersRef.current.push(marker);
      bounds.extend([asset.latitude!, asset.longitude!]);
    });

    if (validAssets.length > 0) {
      map.fitBounds(bounds, { padding: [40, 40], maxZoom: 13 });
    }
  }, [assets, selectedAssetId, navigate]);

  return (
    <div className="card overflow-hidden shadow-sm border border-gray-200">
      <div className="bg-slate-900 px-4 py-3 flex items-center justify-between text-white">
        <div className="flex items-center gap-2">
          <span className="w-2.5 h-2.5 rounded-full bg-emerald-400 animate-pulse"></span>
          <h3 className="text-xs font-bold uppercase tracking-wider">
            Interactive GIS Infrastructure Map ({assets.length} Assets)
          </h3>
        </div>
        <div className="flex items-center gap-3 text-[11px] text-slate-300">
          <span className="flex items-center gap-1">
            <span className="w-2 h-2 rounded-full bg-blue-500"></span> Bridges
          </span>
          <span className="flex items-center gap-1">
            <span className="w-2 h-2 rounded-full bg-purple-500"></span> Tunnels
          </span>
          <span className="flex items-center gap-1">
            <span className="w-2 h-2 rounded-full bg-cyan-500"></span> Dams
          </span>
        </div>
      </div>
      <div ref={mapContainerRef} style={{ height, width: '100%' }} />
    </div>
  );
};
