import React, { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import api from '../api/client';
import { 
  Building2, 
  ArrowLeft, 
  Plus, 
  Calendar, 
  User as UserIcon, 
  MapPin, 
  Clock, 
  ClipboardCheck, 
  AlertCircle,
  ExternalLink
} from 'lucide-react';
import { InfrastructureAsset, Inspection, User } from '../types';
import { useAuth } from '../context/AuthContext';

export const AssetDetail: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const { user } = useAuth();
  const [asset, setAsset] = useState<InfrastructureAsset | null>(null);
  const [inspections, setInspections] = useState<Inspection[]>([]);
  const [inspectors, setInspectors] = useState<User[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  // New Inspection Modal State
  const [showModal, setShowModal] = useState(false);
  const [inspDate, setInspDate] = useState(new Date().toISOString().split('T')[0]);
  const [inspectorId, setInspectorId] = useState<number | ''>('');
  const [notes, setNotes] = useState('');
  const [submitting, setSubmitting] = useState(false);

  const canCreateInspection = ['Administrator', 'Infrastructure Manager', 'Infrastructure Inspector'].includes(
    user?.role?.name || ''
  );

  const fetchData = async () => {
    setLoading(true);
    try {
      const [assetRes, inspRes, inspListRes] = await Promise.all([
        api.get<InfrastructureAsset>(`/assets/${id}`),
        api.get<Inspection[]>(`/inspections/?asset_id=${id}`),
        api.get<User[]>('/users/inspectors'),
      ]);
      setAsset(assetRes.data);
      setInspections(inspRes.data);
      setInspectors(inspListRes.data);

      if (user?.role?.name === 'Infrastructure Inspector') {
        setInspectorId(user.id);
      } else if (inspListRes.data.length > 0) {
        setInspectorId(inspListRes.data[0].id);
      }
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to load asset details');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, [id]);

  const handleCreateInspection = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!inspectorId) return;
    setSubmitting(true);
    try {
      await api.post('/inspections/', {
        asset_id: Number(id),
        inspector_id: Number(inspectorId),
        inspection_date: inspDate,
        notes: notes || null,
      });
      setShowModal(false);
      setNotes('');
      fetchData();
    } catch (err: any) {
      alert(err.response?.data?.detail || 'Failed to schedule inspection');
    } finally {
      setSubmitting(false);
    }
  };

  if (loading) {
    return (
      <div className="py-20 text-center text-gray-500">
        <div className="w-8 h-8 border-4 border-blue-600 border-t-transparent rounded-full animate-spin mx-auto mb-3"></div>
        Loading asset information...
      </div>
    );
  }

  if (!asset) {
    return (
      <div className="card p-8 text-center text-gray-600">
        <p>Asset not found or failed to load.</p>
        <Link to="/assets" className="btn-secondary mt-4 inline-block">
          Return to Asset List
        </Link>
      </div>
    );
  }

  return (
    <div className="space-y-8 max-w-7xl mx-auto">
      {/* Top Bar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <Link to="/assets" className="btn-secondary py-1.5 px-3 text-xs flex items-center gap-1.5">
            <ArrowLeft className="w-4 h-4" /> Assets
          </Link>
          <span className="font-mono text-xs font-bold bg-blue-100 text-blue-800 px-2 py-0.5 rounded">
            {asset.asset_code}
          </span>
          <h1 className="text-2xl font-bold text-gray-900">{asset.name}</h1>
        </div>

        {canCreateInspection && (
          <button
            onClick={() => setShowModal(true)}
            className="btn-primary flex items-center gap-2 text-sm self-start sm:self-auto"
          >
            <Plus className="w-4 h-4" />
            <span>Schedule New Inspection</span>
          </button>
        )}
      </div>

      {error && (
        <div className="p-4 rounded-lg bg-red-50 border border-red-200 text-red-700 text-sm flex items-center gap-2">
          <AlertCircle className="w-5 h-5 flex-shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {/* Asset Metadata Grid */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div className="card p-6 md:col-span-2 space-y-4">
          <h2 className="text-base font-bold text-gray-900 border-b pb-3">Engineering Specifications</h2>
          <div className="grid grid-cols-2 gap-4 text-sm">
            <div>
              <p className="text-xs text-gray-500 font-semibold uppercase">Structure Type</p>
              <p className="font-medium text-gray-900 mt-0.5">{asset.type}</p>
            </div>
            <div>
              <p className="text-xs text-gray-500 font-semibold uppercase">Construction Year</p>
              <p className="font-medium text-gray-900 mt-0.5">{asset.construction_year || 'Not specified'}</p>
            </div>
            <div>
              <p className="text-xs text-gray-500 font-semibold uppercase">Material Composition</p>
              <p className="font-medium text-gray-900 mt-0.5">{asset.material_type || 'Reinforced Concrete'}</p>
            </div>
            <div>
              <p className="text-xs text-gray-500 font-semibold uppercase">Inspection Interval</p>
              <p className="font-medium text-gray-900 mt-0.5">{asset.inspection_frequency_days} Days</p>
            </div>
            <div className="col-span-2">
              <p className="text-xs text-gray-500 font-semibold uppercase">Responsible Department</p>
              <p className="font-medium text-gray-900 mt-0.5">{asset.responsible_department || 'Department of Transportation'}</p>
            </div>
            <div className="col-span-2">
              <p className="text-xs text-gray-500 font-semibold uppercase">Maintenance History</p>
              <p className="text-gray-700 mt-0.5 whitespace-pre-wrap text-xs bg-gray-50 p-3 rounded-lg border border-gray-100">
                {asset.maintenance_history || 'No prior maintenance logged.'}
              </p>
            </div>
          </div>
        </div>

        {/* Location & Map Placeholder */}
        <div className="card p-6 space-y-4 flex flex-col justify-between">
          <div>
            <h2 className="text-base font-bold text-gray-900 border-b pb-3">Geographic Coordinates</h2>
            <div className="space-y-3 mt-4 text-sm">
              <div className="flex items-start gap-2 text-gray-700">
                <MapPin className="w-4 h-4 text-blue-600 flex-shrink-0 mt-0.5" />
                <span>{asset.location_text || 'GPS benchmark coordinates only'}</span>
              </div>
              <div className="bg-gray-50 p-3 rounded-lg border border-gray-100 text-xs font-mono space-y-1">
                <p>Latitude: <strong>{asset.latitude ?? 'N/A'}</strong></p>
                <p>Longitude: <strong>{asset.longitude ?? 'N/A'}</strong></p>
              </div>
            </div>
          </div>

          <div className="p-4 bg-blue-50 border border-blue-200 rounded-xl text-center text-xs text-blue-800">
            <p className="font-semibold">Milestone 2 Map View Placeholder</p>
            <p className="text-[11px] mt-0.5 text-blue-600">Interactive PostGIS GIS Map integration</p>
          </div>
        </div>
      </div>

      {/* Inspection History */}
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-bold text-gray-900 flex items-center gap-2">
            <ClipboardCheck className="w-5 h-5 text-blue-600" />
            <span>Inspection History & Damage Assessments ({inspections.length})</span>
          </h2>
        </div>

        {inspections.length === 0 ? (
          <div className="card p-8 text-center text-gray-500">
            <p className="text-sm">No inspections have been logged for this asset yet.</p>
            {canCreateInspection && (
              <button onClick={() => setShowModal(true)} className="btn-primary mt-4 text-xs">
                Schedule First Inspection
              </button>
            )}
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {inspections.map((insp) => (
              <div key={insp.id} className="card p-5 hover:shadow-md transition-shadow flex flex-col justify-between">
                <div className="space-y-3">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-semibold uppercase text-gray-400 flex items-center gap-1.5">
                      <Calendar className="w-3.5 h-3.5" />
                      {insp.inspection_date}
                    </span>
                    <span
                      className={`px-2.5 py-0.5 rounded-full text-xs font-semibold ${
                        insp.status === 'completed'
                          ? 'bg-green-100 text-green-800'
                          : insp.status === 'in_progress'
                          ? 'bg-blue-100 text-blue-800'
                          : 'bg-yellow-100 text-yellow-800'
                      }`}
                    >
                      {insp.status.replace('_', ' ')}
                    </span>
                  </div>

                  <p className="text-sm font-semibold text-gray-800 flex items-center gap-1.5">
                    <UserIcon className="w-4 h-4 text-gray-400" />
                    Inspector: {insp.inspector?.full_name || 'Assigned Staff'}
                  </p>

                  <p className="text-xs text-gray-600 line-clamp-2">
                    {insp.notes || 'No notes entered for this site visit.'}
                  </p>
                </div>

                <div className="pt-4 mt-4 border-t border-gray-100 flex justify-end">
                  <Link
                    to={`/inspections/${insp.id}`}
                    className="btn-primary text-xs flex items-center gap-1.5 py-1.5 px-3"
                  >
                    <span>Inspect Images & Upload</span>
                    <ExternalLink className="w-3 h-3" />
                  </Link>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Schedule Inspection Modal */}
      {showModal && (
        <div className="fixed inset-0 bg-black/50 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl shadow-xl max-w-lg w-full p-6 space-y-5">
            <h3 className="text-lg font-bold text-gray-900">Schedule Site Inspection</h3>

            <form onSubmit={handleCreateInspection} className="space-y-4">
              <div>
                <label className="block text-xs font-semibold uppercase text-gray-700 mb-1">
                  Inspection Date
                </label>
                <input
                  type="date"
                  required
                  value={inspDate}
                  onChange={(e) => setInspDate(e.target.value)}
                  className="input-field"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold uppercase text-gray-700 mb-1">
                  Assigned Inspector
                </label>
                {user?.role?.name === 'Infrastructure Inspector' ? (
                  <input
                    type="text"
                    disabled
                    value={`${user.full_name} (Self)`}
                    className="input-field bg-gray-100 text-gray-600"
                  />
                ) : (
                  <select
                    value={inspectorId}
                    onChange={(e) => setInspectorId(Number(e.target.value))}
                    className="input-field bg-white"
                  >
                    {inspectors.map((ins) => (
                      <option key={ins.id} value={ins.id}>
                        {ins.full_name} ({ins.email})
                      </option>
                    ))}
                  </select>
                )}
              </div>

              <div>
                <label className="block text-xs font-semibold uppercase text-gray-700 mb-1">
                  Inspection Instructions / Field Notes
                </label>
                <textarea
                  rows={3}
                  value={notes}
                  onChange={(e) => setNotes(e.target.value)}
                  placeholder="Focus areas: Abutment 2 spalling, pier water line scour..."
                  className="input-field"
                />
              </div>

              <div className="flex justify-end gap-3 pt-3 border-t">
                <button
                  type="button"
                  onClick={() => setShowModal(false)}
                  className="btn-secondary"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={submitting}
                  className="btn-primary"
                >
                  {submitting ? 'Scheduling...' : 'Create Inspection'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
