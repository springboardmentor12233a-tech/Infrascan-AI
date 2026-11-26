import React, { useState, useEffect } from 'react';
import { useAuth } from '../context/AuthContext';

export default function Assets() {
  const { authFetch } = useAuth();
  const [assets, setAssets] = useState([]);
  const [showModal, setShowModal] = useState(false);
  const [name, setName] = useState('');
  const [type, setType] = useState('Bridge');
  const [locationName, setLocationName] = useState('');
  const [lat, setLat] = useState('');
  const [lon, setLon] = useState('');
  const [constYear, setConstYear] = useState('2015');
  const [material, setMaterial] = useState('Reinforced Concrete');

  const fetchAssets = () => {
    authFetch('/api/assets')
      .then(r => r.json())
      .then(data => setAssets(data))
      .catch(console.error);
  };

  useEffect(() => {
    fetchAssets();
  }, []);

  const handleCreate = async (e) => {
    e.preventDefault();
    const payload = {
      name,
      type,
      location_name: locationName,
      latitude: lat ? parseFloat(lat) : null,
      longitude: lon ? parseFloat(lon) : null,
      construction_year: constYear ? parseInt(constYear) : null,
      material_type: material
    };

    try {
      const res = await authFetch('/api/assets', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      if (res.ok) {
        setShowModal(false);
        fetchAssets();
        setName('');
        setLocationName('');
        setLat('');
        setLon('');
      }
    } catch (err) {
      alert('Error creating asset: ' + err.message);
    }
  };

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-6">
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-black text-white tracking-tight">Infrastructure Asset Management</h1>
          <p className="text-sm text-slate-400 mt-1">Registry of bridges, tunnels, roads, dams, and structural concrete assets.</p>
        </div>
        <button
          onClick={() => setShowModal(true)}
          className="px-4 py-2 rounded-lg bg-blue-600 hover:bg-blue-500 text-xs font-semibold text-white shadow-md shadow-blue-500/20 transition"
        >
          + Register New Asset
        </button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
        {assets.map(asset => (
          <div key={asset.id} className="glass-card p-5 rounded-2xl border border-slate-800 space-y-3 glass-card-hover">
            <div className="flex items-start justify-between">
              <div>
                <span className="text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded bg-blue-500/20 text-blue-400 border border-blue-500/30">
                  {asset.type}
                </span>
                <h3 className="text-base font-bold text-white mt-1.5">{asset.name}</h3>
              </div>
              <span className="text-xs font-mono text-slate-500">#{asset.id}</span>
            </div>

            <div className="space-y-1 text-xs text-slate-300">
              <div className="text-slate-400">{asset.location_name || 'Location unassigned'}</div>
              <div>Material: <strong className="text-white">{asset.material_type}</strong></div>
              <div>Built: <strong className="text-white">{asset.construction_year || 'Unknown'}</strong></div>
              {asset.latitude && asset.longitude && (
                <div className="font-mono text-[11px] text-slate-400 mt-1">
                  GPS: {asset.latitude}, {asset.longitude}
                </div>
              )}
            </div>
          </div>
        ))}
      </div>

      {/* Modal */}
      {showModal && (
        <div className="fixed inset-0 z-50 bg-slate-950/80 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="glass-card p-6 rounded-2xl border border-slate-700 w-full max-w-md space-y-4">
            <h2 className="text-lg font-bold text-white">Register Infrastructure Asset</h2>
            <form onSubmit={handleCreate} className="space-y-3 text-xs">
              <div>
                <label className="text-slate-300 font-semibold block mb-1">Asset Name</label>
                <input
                  type="text"
                  required
                  value={name}
                  onChange={e => setName(e.target.value)}
                  placeholder="e.g. Yamuna Expressway Flyover P14"
                  className="w-full bg-slate-900 border border-slate-700 rounded-lg p-2.5 text-white"
                />
              </div>

              <div>
                <label className="text-slate-300 font-semibold block mb-1">Infrastructure Type</label>
                <select
                  value={type}
                  onChange={e => setType(e.target.value)}
                  className="w-full bg-slate-900 border border-slate-700 rounded-lg p-2.5 text-white"
                >
                  <option value="Bridge">Bridge</option>
                  <option value="Road">Road / Pavement</option>
                  <option value="Tunnel">Tunnel</option>
                  <option value="Wall">Retaining Wall</option>
                  <option value="Building">Building</option>
                  <option value="Dam">Dam</option>
                  <option value="Concrete Structure">General Concrete Structure</option>
                </select>
              </div>

              <div>
                <label className="text-slate-300 font-semibold block mb-1">Location Description</label>
                <input
                  type="text"
                  value={locationName}
                  onChange={e => setLocationName(e.target.value)}
                  placeholder="City, Highway, Sector..."
                  className="w-full bg-slate-900 border border-slate-700 rounded-lg p-2.5 text-white"
                />
              </div>

              <div className="grid grid-cols-2 gap-2">
                <div>
                  <label className="text-slate-300 font-semibold block mb-1">Latitude</label>
                  <input
                    type="number"
                    step="0.0001"
                    value={lat}
                    onChange={e => setLat(e.target.value)}
                    placeholder="28.5355"
                    className="w-full bg-slate-900 border border-slate-700 rounded-lg p-2.5 text-white"
                  />
                </div>
                <div>
                  <label className="text-slate-300 font-semibold block mb-1">Longitude</label>
                  <input
                    type="number"
                    step="0.0001"
                    value={lon}
                    onChange={e => setLon(e.target.value)}
                    placeholder="77.3910"
                    className="w-full bg-slate-900 border border-slate-700 rounded-lg p-2.5 text-white"
                  />
                </div>
              </div>

              <div className="flex justify-end gap-2 pt-2">
                <button
                  type="button"
                  onClick={() => setShowModal(false)}
                  className="px-4 py-2 rounded-lg bg-slate-800 text-slate-300 hover:text-white"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-4 py-2 rounded-lg bg-blue-600 hover:bg-blue-500 text-white font-semibold"
                >
                  Save Asset
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
