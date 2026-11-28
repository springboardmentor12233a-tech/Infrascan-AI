import React, { useState, useEffect } from 'react';
import { useNavigate, useParams, Link } from 'react-router-dom';
import api from '../api/client';
import { Building2, ArrowLeft, Save, AlertCircle, Sparkles } from 'lucide-react';
import { AssetType } from '../types';

const ASSET_TYPES: AssetType[] = [
  'Building',
  'Bridge',
  'Road',
  'Tunnel',
  'Dam',
  'Concrete Structure',
  'Retaining Wall',
  'Industrial Structure',
];

export const AssetForm: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const isEdit = Boolean(id);
  const navigate = useNavigate();

  const [formData, setFormData] = useState({
    asset_code: '',
    name: '',
    type: 'Bridge' as AssetType,
    location_text: '',
    latitude: '',
    longitude: '',
    construction_year: '',
    material_type: '',
    responsible_department: '',
    inspection_frequency_days: '180',
    maintenance_history: '',
  });

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    if (isEdit) {
      setLoading(true);
      api.get(`/assets/${id}`)
        .then((res) => {
          const d = res.data;
          setFormData({
            asset_code: d.asset_code || '',
            name: d.name || '',
            type: d.type || 'Bridge',
            location_text: d.location_text || '',
            latitude: d.latitude !== null && d.latitude !== undefined ? String(d.latitude) : '',
            longitude: d.longitude !== null && d.longitude !== undefined ? String(d.longitude) : '',
            construction_year: d.construction_year ? String(d.construction_year) : '',
            material_type: d.material_type || '',
            responsible_department: d.responsible_department || '',
            inspection_frequency_days: d.inspection_frequency_days ? String(d.inspection_frequency_days) : '180',
            maintenance_history: d.maintenance_history || '',
          });
        })
        .catch((err) => setError(err.response?.data?.detail || 'Failed to load asset details'))
        .finally(() => setLoading(false));
    }
  }, [id, isEdit]);

  const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement>) => {
    setFormData({ ...formData, [e.target.name]: e.target.value });
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    const payload: any = {
      asset_code: formData.asset_code,
      name: formData.name,
      type: formData.type,
      location_text: formData.location_text || null,
      latitude: formData.latitude ? parseFloat(formData.latitude) : null,
      longitude: formData.longitude ? parseFloat(formData.longitude) : null,
      construction_year: formData.construction_year ? parseInt(formData.construction_year, 10) : null,
      material_type: formData.material_type || null,
      responsible_department: formData.responsible_department || null,
      inspection_frequency_days: formData.inspection_frequency_days ? parseInt(formData.inspection_frequency_days, 10) : null,
      maintenance_history: formData.maintenance_history || null,
    };

    try {
      if (isEdit) {
        await api.put(`/assets/${id}`, payload);
      } else {
        await api.post('/assets/', payload);
      }
      navigate('/assets');
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to save asset. Please check inputs.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      {/* Top Header */}
      <div className="card p-5 sm:p-6 flex items-center justify-between border-slate-200/80 bg-white">
        <div className="flex items-center gap-3">
          <Link 
            to="/assets" 
            className="p-2 rounded-xl border border-slate-200 bg-white hover:bg-slate-50 text-slate-600 transition-colors shadow-xs"
            title="Return to Asset Inventory"
          >
            <ArrowLeft className="w-5 h-5" />
          </Link>
          <div>
            <h1 className="text-xl sm:text-2xl font-bold text-slate-900 tracking-tight">
              {isEdit ? 'Edit Infrastructure Asset' : 'Register New Infrastructure Asset'}
            </h1>
            <p className="text-xs text-slate-500 mt-0.5">
              Configure engineering parameters, GPS coordinates, and inspection intervals.
            </p>
          </div>
        </div>
      </div>

      {error && (
        <div className="p-4 rounded-xl bg-rose-50 border border-rose-200 text-rose-700 text-xs flex items-center gap-2.5">
          <AlertCircle className="w-4 h-4 flex-shrink-0" />
          <span>{error}</span>
        </div>
      )}

      <form onSubmit={handleSubmit} className="card p-6 sm:p-8 space-y-6 border-slate-200/80 bg-white shadow-xs">
        <div className="border-b border-slate-100 pb-4">
          <h2 className="text-sm font-bold text-slate-900 uppercase tracking-wider flex items-center gap-2">
            <Building2 className="w-4 h-4 text-blue-600" />
            <span>Asset Identification & Classification</span>
          </h2>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-5 text-xs">
          {/* Asset Code */}
          <div>
            <label className="block text-xs font-bold uppercase tracking-wider text-slate-700 mb-1.5">
              Asset Code *
            </label>
            <input
              type="text"
              name="asset_code"
              required
              value={formData.asset_code}
              onChange={handleChange}
              placeholder="e.g. BRG-001, TUN-402"
              className="input-field font-mono font-medium text-xs"
            />
          </div>

          {/* Name */}
          <div>
            <label className="block text-xs font-bold uppercase tracking-wider text-slate-700 mb-1.5">
              Asset Structure Name *
            </label>
            <input
              type="text"
              name="name"
              required
              value={formData.name}
              onChange={handleChange}
              placeholder="e.g. Golden Gate Overpass Viaduct"
              className="input-field text-xs"
            />
          </div>

          {/* Type */}
          <div>
            <label className="block text-xs font-bold uppercase tracking-wider text-slate-700 mb-1.5">
              Structure Type *
            </label>
            <select
              name="type"
              value={formData.type}
              onChange={handleChange}
              className="input-field bg-white text-xs"
            >
              {ASSET_TYPES.map((t) => (
                <option key={t} value={t}>
                  {t}
                </option>
              ))}
            </select>
          </div>

          {/* Construction Year */}
          <div>
            <label className="block text-xs font-bold uppercase tracking-wider text-slate-700 mb-1.5">
              Construction Year (1800 - 2100)
            </label>
            <input
              type="number"
              name="construction_year"
              min="1800"
              max="2100"
              value={formData.construction_year}
              onChange={handleChange}
              placeholder="e.g. 1985"
              className="input-field text-xs"
            />
          </div>

          {/* Latitude */}
          <div>
            <label className="block text-xs font-bold uppercase tracking-wider text-slate-700 mb-1.5">
              Latitude (-90° to 90°)
            </label>
            <input
              type="number"
              step="any"
              name="latitude"
              min="-90"
              max="90"
              value={formData.latitude}
              onChange={handleChange}
              placeholder="e.g. 37.8199"
              className="input-field font-mono text-xs"
            />
          </div>

          {/* Longitude */}
          <div>
            <label className="block text-xs font-bold uppercase tracking-wider text-slate-700 mb-1.5">
              Longitude (-180° to 180°)
            </label>
            <input
              type="number"
              step="any"
              name="longitude"
              min="-180"
              max="180"
              value={formData.longitude}
              onChange={handleChange}
              placeholder="e.g. -122.4783"
              className="input-field font-mono text-xs"
            />
          </div>

          {/* Material Type */}
          <div>
            <label className="block text-xs font-bold uppercase tracking-wider text-slate-700 mb-1.5">
              Material Composition
            </label>
            <input
              type="text"
              name="material_type"
              value={formData.material_type}
              onChange={handleChange}
              placeholder="e.g. Prestressed Reinforced Concrete, Steel"
              className="input-field text-xs"
            />
          </div>

          {/* Responsible Department */}
          <div>
            <label className="block text-xs font-bold uppercase tracking-wider text-slate-700 mb-1.5">
              Responsible Department
            </label>
            <input
              type="text"
              name="responsible_department"
              value={formData.responsible_department}
              onChange={handleChange}
              placeholder="e.g. DOT Bridge Maintenance Division"
              className="input-field text-xs"
            />
          </div>

          {/* Inspection Frequency Days */}
          <div>
            <label className="block text-xs font-bold uppercase tracking-wider text-slate-700 mb-1.5">
              Inspection Frequency (Days)
            </label>
            <input
              type="number"
              name="inspection_frequency_days"
              min="1"
              value={formData.inspection_frequency_days}
              onChange={handleChange}
              placeholder="e.g. 180 (Every 6 months)"
              className="input-field text-xs"
            />
          </div>

          {/* Location Text */}
          <div className="md:col-span-2">
            <label className="block text-xs font-bold uppercase tracking-wider text-slate-700 mb-1.5">
              Physical Location & Address Description
            </label>
            <input
              type="text"
              name="location_text"
              value={formData.location_text}
              onChange={handleChange}
              placeholder="e.g. Interstate 80, Mile Marker 42, North Bay"
              className="input-field text-xs"
            />
          </div>

          {/* Maintenance History */}
          <div className="md:col-span-2">
            <label className="block text-xs font-bold uppercase tracking-wider text-slate-700 mb-1.5">
              Maintenance History / Engineering Logs
            </label>
            <textarea
              name="maintenance_history"
              rows={4}
              value={formData.maintenance_history}
              onChange={handleChange}
              placeholder="Record previous retrofits, joint sealings, or structural repairs..."
              className="input-field font-sans text-xs"
            />
          </div>
        </div>

        <div className="flex justify-end gap-3 pt-5 border-t border-slate-100">
          <Link to="/assets" className="btn-secondary text-xs py-2 px-4">
            Cancel
          </Link>
          <button type="submit" disabled={loading} className="btn-primary text-xs py-2 px-4 flex items-center gap-2">
            <Save className="w-4 h-4" />
            <span>{loading ? 'Saving Asset...' : 'Save Asset Record'}</span>
          </button>
        </div>
      </form>
    </div>
  );
};
