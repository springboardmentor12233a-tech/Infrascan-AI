import React, { useState, useEffect } from 'react';
import { useNavigate, useParams, Link } from 'react-router-dom';
import api from '../api/client';
import { Building2, ArrowLeft, Save, AlertCircle } from 'lucide-react';
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
      <div className="flex items-center gap-4">
        <Link to="/assets" className="btn-secondary py-1.5 px-3 text-xs flex items-center gap-1.5">
          <ArrowLeft className="w-4 h-4" /> Back to Assets
        </Link>
        <h1 className="text-2xl font-bold text-gray-900">
          {isEdit ? 'Edit Infrastructure Asset' : 'Register New Infrastructure Asset'}
        </h1>
      </div>

      {error && (
        <div className="p-4 rounded-lg bg-red-50 border border-red-200 text-red-700 text-sm flex items-center gap-2">
          <AlertCircle className="w-5 h-5 flex-shrink-0" />
          <span>{error}</span>
        </div>
      )}

      <form onSubmit={handleSubmit} className="card p-8 space-y-6 shadow-sm">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {/* Asset Code */}
          <div>
            <label className="block text-xs font-semibold uppercase tracking-wider text-gray-700 mb-1">
              Asset Code *
            </label>
            <input
              type="text"
              name="asset_code"
              required
              value={formData.asset_code}
              onChange={handleChange}
              placeholder="e.g. BRG-001, TUN-402"
              className="input-field font-mono font-medium"
            />
          </div>

          {/* Name */}
          <div>
            <label className="block text-xs font-semibold uppercase tracking-wider text-gray-700 mb-1">
              Asset Structure Name *
            </label>
            <input
              type="text"
              name="name"
              required
              value={formData.name}
              onChange={handleChange}
              placeholder="e.g. Golden Gate Overpass Viaduct"
              className="input-field"
            />
          </div>

          {/* Type */}
          <div>
            <label className="block text-xs font-semibold uppercase tracking-wider text-gray-700 mb-1">
              Structure Type *
            </label>
            <select
              name="type"
              value={formData.type}
              onChange={handleChange}
              className="input-field bg-white"
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
            <label className="block text-xs font-semibold uppercase tracking-wider text-gray-700 mb-1">
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
              className="input-field"
            />
          </div>

          {/* Latitude */}
          <div>
            <label className="block text-xs font-semibold uppercase tracking-wider text-gray-700 mb-1">
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
              className="input-field"
            />
          </div>

          {/* Longitude */}
          <div>
            <label className="block text-xs font-semibold uppercase tracking-wider text-gray-700 mb-1">
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
              className="input-field"
            />
          </div>

          {/* Material Type */}
          <div>
            <label className="block text-xs font-semibold uppercase tracking-wider text-gray-700 mb-1">
              Material Composition
            </label>
            <input
              type="text"
              name="material_type"
              value={formData.material_type}
              onChange={handleChange}
              placeholder="e.g. Prestressed Reinforced Concrete, Steel"
              className="input-field"
            />
          </div>

          {/* Responsible Department */}
          <div>
            <label className="block text-xs font-semibold uppercase tracking-wider text-gray-700 mb-1">
              Responsible Department
            </label>
            <input
              type="text"
              name="responsible_department"
              value={formData.responsible_department}
              onChange={handleChange}
              placeholder="e.g. DOT Bridge Maintenance Division"
              className="input-field"
            />
          </div>

          {/* Inspection Frequency Days */}
          <div>
            <label className="block text-xs font-semibold uppercase tracking-wider text-gray-700 mb-1">
              Inspection Frequency (Days)
            </label>
            <input
              type="number"
              name="inspection_frequency_days"
              min="1"
              value={formData.inspection_frequency_days}
              onChange={handleChange}
              placeholder="e.g. 180 (Every 6 months)"
              className="input-field"
            />
          </div>

          {/* Location Text */}
          <div className="md:col-span-2">
            <label className="block text-xs font-semibold uppercase tracking-wider text-gray-700 mb-1">
              Physical Location & Address Description
            </label>
            <input
              type="text"
              name="location_text"
              value={formData.location_text}
              onChange={handleChange}
              placeholder="e.g. Interstate 80, Mile Marker 42, North Bay"
              className="input-field"
            />
          </div>

          {/* Maintenance History */}
          <div className="md:col-span-2">
            <label className="block text-xs font-semibold uppercase tracking-wider text-gray-700 mb-1">
              Maintenance History / Engineering Logs
            </label>
            <textarea
              name="maintenance_history"
              rows={4}
              value={formData.maintenance_history}
              onChange={handleChange}
              placeholder="Record previous retrofits, joint sealings, or structural repairs..."
              className="input-field font-sans"
            />
          </div>
        </div>

        <div className="flex justify-end gap-3 pt-4 border-t border-gray-100">
          <Link to="/assets" className="btn-secondary">
            Cancel
          </Link>
          <button type="submit" disabled={loading} className="btn-primary flex items-center gap-2">
            <Save className="w-4 h-4" />
            <span>{loading ? 'Saving...' : 'Save Asset'}</span>
          </button>
        </div>
      </form>
    </div>
  );
};
