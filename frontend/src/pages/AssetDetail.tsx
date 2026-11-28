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
  ExternalLink,
  Shield,
  Layers,
  FileText,
  X,
  TrendingUp,
  Activity,
  AlertTriangle,
  CheckCircle2,
  BarChart3,
  ArrowUpRight
} from 'lucide-react';
import { InfrastructureAsset, Inspection, User, AssetProgressionData } from '../types';
import { useAuth } from '../context/AuthContext';
import { AssetMap } from '../components/AssetMap';

export const AssetDetail: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const { user } = useAuth();
  const [asset, setAsset] = useState<InfrastructureAsset | null>(null);
  const [inspections, setInspections] = useState<Inspection[]>([]);
  const [inspectors, setInspectors] = useState<User[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const [activeTab, setActiveTab] = useState<'inspections' | 'progression'>('inspections');
  const [progressionData, setProgressionData] = useState<AssetProgressionData | null>(null);
  const [progressionLoading, setProgressionLoading] = useState(false);

  // New Inspection Modal State
  const [showModal, setShowModal] = useState(false);
  const [inspDate, setInspDate] = useState(new Date().toISOString().split('T')[0]);
  const [inspectorId, setInspectorId] = useState<number | ''>('');
  const [notes, setNotes] = useState('');
  const [submitting, setSubmitting] = useState(false);

  const canCreateInspection = ['Administrator', 'Infrastructure Manager', 'Infrastructure Inspector'].includes(
    user?.role?.name || ''
  );

  const fetchProgression = async () => {
    setProgressionLoading(true);
    try {
      const res = await api.get<AssetProgressionData>(`/inspections/asset/${id}/progression`);
      setProgressionData(res.data);
    } catch (err: any) {
      console.error('Failed to load progression data:', err);
    } finally {
      setProgressionLoading(false);
    }
  };

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
      
      // Also trigger progression fetch
      fetchProgression();
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
      <div className="py-24 text-center text-slate-500">
        <div className="w-10 h-10 border-4 border-blue-600 border-t-transparent rounded-full animate-spin mx-auto mb-3"></div>
        <p className="text-sm font-medium">Loading asset specifications and inspection history...</p>
      </div>
    );
  }

  if (!asset) {
    return (
      <div className="card p-10 text-center text-slate-600 max-w-md mx-auto">
        <AlertCircle className="w-10 h-10 text-amber-500 mx-auto mb-3" />
        <h3 className="text-base font-bold text-slate-900">Asset Not Found</h3>
        <p className="text-xs text-slate-500 mt-1">The requested infrastructure asset does not exist.</p>
        <Link to="/assets" className="btn-secondary mt-5 inline-block text-xs">
          Return to Asset List
        </Link>
      </div>
    );
  }

  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      {/* Top Header Card */}
      <div className="card p-5 sm:p-6 flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-slate-200/80">
        <div className="flex items-center gap-3">
          <Link 
            to="/assets" 
            className="p-2 rounded-xl border border-slate-200 bg-white hover:bg-slate-50 text-slate-600 transition-colors shadow-xs"
            title="Return to Asset Inventory"
          >
            <ArrowLeft className="w-5 h-5" />
          </Link>
          <div>
            <div className="flex items-center gap-2">
              <span className="font-mono text-xs font-bold bg-blue-50 text-blue-700 border border-blue-200 px-2.5 py-0.5 rounded-md">
                {asset.asset_code}
              </span>
              <span className="text-xs px-2.5 py-0.5 rounded-md font-semibold bg-slate-100 text-slate-700 border border-slate-200">
                {asset.type}
              </span>
            </div>
            <h1 className="text-xl sm:text-2xl font-bold text-slate-900 tracking-tight mt-1">
              {asset.name}
            </h1>
          </div>
        </div>

        {canCreateInspection && (
          <button
            onClick={() => setShowModal(true)}
            className="btn-primary flex items-center gap-2 text-xs py-2 px-4 shadow-sm"
          >
            <Plus className="w-4 h-4" />
            <span>Schedule Site Inspection</span>
          </button>
        )}
      </div>

      {error && (
        <div className="p-4 rounded-xl bg-rose-50 border border-rose-200 text-rose-700 text-xs flex items-center gap-2.5">
          <AlertCircle className="w-4 h-4 flex-shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {/* Asset Specifications & Map Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Specifications */}
        <div className="card p-6 lg:col-span-2 space-y-5 border-slate-200/80">
          <div className="flex items-center justify-between border-b border-slate-100 pb-3">
            <h2 className="text-sm font-bold text-slate-900 uppercase tracking-wider flex items-center gap-2">
              <Building2 className="w-4 h-4 text-blue-600" />
              <span>Engineering Specifications</span>
            </h2>
            <span className="text-xs text-slate-400 font-mono">ID #{asset.id}</span>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-xs">
            <div className="p-3 rounded-xl bg-slate-50 border border-slate-100">
              <p className="text-[11px] text-slate-400 font-semibold uppercase tracking-wider">Structure Type</p>
              <p className="font-bold text-slate-900 mt-1 text-sm">{asset.type}</p>
            </div>
            <div className="p-3 rounded-xl bg-slate-50 border border-slate-100">
              <p className="text-[11px] text-slate-400 font-semibold uppercase tracking-wider">Construction Year</p>
              <p className="font-bold text-slate-900 mt-1 text-sm">{asset.construction_year || 'Not specified'}</p>
            </div>
            <div className="p-3 rounded-xl bg-slate-50 border border-slate-100">
              <p className="text-[11px] text-slate-400 font-semibold uppercase tracking-wider">Material Composition</p>
              <p className="font-bold text-slate-900 mt-1 text-sm">{asset.material_type || 'Reinforced Concrete'}</p>
            </div>
            <div className="p-3 rounded-xl bg-slate-50 border border-slate-100">
              <p className="text-[11px] text-slate-400 font-semibold uppercase tracking-wider">Inspection Frequency</p>
              <p className="font-bold text-slate-900 mt-1 text-sm">{asset.inspection_frequency_days} Days</p>
            </div>
            <div className="p-3 rounded-xl bg-slate-50 border border-slate-100 sm:col-span-2">
              <p className="text-[11px] text-slate-400 font-semibold uppercase tracking-wider">Responsible Department</p>
              <p className="font-bold text-slate-900 mt-1 text-sm">{asset.responsible_department || 'Department of Transportation & Infrastructure'}</p>
            </div>
            <div className="sm:col-span-2">
              <p className="text-[11px] text-slate-400 font-semibold uppercase tracking-wider mb-1.5">Maintenance History & Field Notes</p>
              <p className="text-slate-700 whitespace-pre-wrap text-xs bg-slate-50 p-3.5 rounded-xl border border-slate-200/80 leading-relaxed font-sans">
                {asset.maintenance_history || 'No prior structural rehabilitation or maintenance logged for this asset.'}
              </p>
            </div>
          </div>
        </div>

        {/* Geographic Coordinates & GIS Map Card */}
        <div className="card p-6 space-y-4 flex flex-col justify-between border-slate-200/80">
          <div>
            <div className="flex items-center justify-between border-b border-slate-100 pb-3">
              <h2 className="text-sm font-bold text-slate-900 uppercase tracking-wider flex items-center gap-2">
                <MapPin className="w-4 h-4 text-blue-600" />
                <span>Geographic Location</span>
              </h2>
            </div>
            
            <div className="space-y-3 mt-4 text-xs">
              <div className="flex items-start gap-2 text-slate-700">
                <MapPin className="w-4 h-4 text-blue-600 flex-shrink-0 mt-0.5" />
                <span className="font-medium">{asset.location_text || 'Standard GPS benchmark coordinates'}</span>
              </div>
              <div className="bg-slate-50 p-3 rounded-xl border border-slate-100 text-xs font-mono space-y-1">
                <p className="flex justify-between">
                  <span className="text-slate-500">Latitude:</span>
                  <strong className="text-slate-800">{asset.latitude ?? 'N/A'}</strong>
                </p>
                <p className="flex justify-between">
                  <span className="text-slate-500">Longitude:</span>
                  <strong className="text-slate-800">{asset.longitude ?? 'N/A'}</strong>
                </p>
              </div>
            </div>
          </div>

          <div className="overflow-hidden rounded-xl border border-slate-200 shadow-xs">
            {asset.latitude && asset.longitude ? (
              <AssetMap assets={[asset]} height="200px" selectedAssetId={asset.id} />
            ) : (
              <div className="p-6 bg-slate-50 text-center text-xs text-slate-400">
                <MapPin className="w-6 h-6 mx-auto text-slate-300 mb-1" />
                <p>Coordinates not available for GIS map rendering</p>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Tabs Switcher: Inspections vs Damage Progression */}
      <div className="border-b border-slate-200">
        <div className="flex gap-6">
          <button
            onClick={() => setActiveTab('inspections')}
            className={`pb-3 text-sm font-bold flex items-center gap-2 border-b-2 transition-colors ${
              activeTab === 'inspections'
                ? 'border-blue-600 text-blue-600'
                : 'border-transparent text-slate-500 hover:text-slate-800'
            }`}
          >
            <ClipboardCheck className="w-4 h-4" />
            <span>Inspection History</span>
            <span className="text-xs px-2 py-0.5 rounded-full bg-slate-100 text-slate-600">
              {inspections.length}
            </span>
          </button>

          <button
            onClick={() => {
              setActiveTab('progression');
              if (!progressionData) fetchProgression();
            }}
            className={`pb-3 text-sm font-bold flex items-center gap-2 border-b-2 transition-colors ${
              activeTab === 'progression'
                ? 'border-blue-600 text-blue-600'
                : 'border-transparent text-slate-500 hover:text-slate-800'
            }`}
          >
            <TrendingUp className="w-4 h-4" />
            <span>Damage Progression & Tracking</span>
            {progressionData && (
              <span className="text-xs px-2 py-0.5 rounded-full bg-purple-50 text-purple-700 font-semibold border border-purple-200">
                {progressionData.timeline.length} Milestones
              </span>
            )}
          </button>
        </div>
      </div>

      {/* Tab Content: Inspection History */}
      {activeTab === 'inspections' && (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-base font-bold text-slate-900 flex items-center gap-2">
                <ClipboardCheck className="w-5 h-5 text-blue-600" />
                <span>Inspection Records & Field Evaluations</span>
              </h2>
              <p className="text-xs text-slate-500 mt-0.5">
                Review completed and ongoing AI damage evaluations for this asset.
              </p>
            </div>
          </div>

          {inspections.length === 0 ? (
            <div className="card p-10 text-center text-slate-400 border-slate-200/80">
              <ClipboardCheck className="w-10 h-10 mx-auto mb-2 text-slate-300" />
              <h4 className="text-sm font-bold text-slate-700">No inspections logged yet</h4>
              <p className="text-xs text-slate-400 mt-1 max-w-sm mx-auto">
                Schedule the first structural site inspection to begin uploading imagery and defect diagnostics.
              </p>
              {canCreateInspection && (
                <button 
                  onClick={() => setShowModal(true)} 
                  className="btn-primary mt-4 text-xs py-1.5 px-3"
                >
                  Schedule Inspection
                </button>
              )}
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {inspections.map((insp) => (
                <div key={insp.id} className="card p-5 hover:shadow-md transition-all border-slate-200/80 flex flex-col justify-between bg-white">
                  <div className="space-y-3">
                    <div className="flex items-center justify-between">
                      <span className="text-xs font-semibold text-slate-500 flex items-center gap-1.5">
                        <Calendar className="w-3.5 h-3.5 text-slate-400" />
                        {insp.inspection_date}
                      </span>
                      <span
                        className={`px-2.5 py-0.5 rounded-full text-[11px] font-semibold capitalize border ${
                          insp.status === 'completed'
                            ? 'bg-emerald-50 text-emerald-700 border-emerald-200'
                            : insp.status === 'in_progress'
                            ? 'bg-blue-50 text-blue-700 border-blue-200'
                            : 'bg-amber-50 text-amber-700 border-amber-200'
                        }`}
                      >
                        {insp.status.replace('_', ' ')}
                      </span>
                    </div>

                    <p className="text-xs font-bold text-slate-800 flex items-center gap-1.5">
                      <UserIcon className="w-3.5 h-3.5 text-slate-400" />
                      Inspector: {insp.inspector?.full_name || 'Assigned Staff'}
                    </p>

                    <p className="text-xs text-slate-600 line-clamp-2 leading-relaxed bg-slate-50 p-2.5 rounded-lg border border-slate-100">
                      {insp.notes || 'No field notes logged for this session.'}
                    </p>
                  </div>

                  <div className="pt-3.5 mt-3.5 border-t border-slate-100 flex items-center justify-between">
                    <span className="text-[11px] font-mono text-slate-400">Session #{insp.id}</span>
                    <Link
                      to={`/inspections/${insp.id}`}
                      className="btn-primary text-xs flex items-center gap-1.5 py-1.5 px-3"
                    >
                      <span>View Inspection Workspace</span>
                      <ExternalLink className="w-3 h-3" />
                    </Link>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Tab Content: Damage Progression Timeline */}
      {activeTab === 'progression' && (
        <div className="space-y-6">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-slate-100 pb-3">
            <div>
              <h2 className="text-base font-bold text-slate-900 flex items-center gap-2">
                <TrendingUp className="w-5 h-5 text-purple-600" />
                <span>Damage Progression & Degradation Analytics</span>
              </h2>
              <p className="text-xs text-slate-500 mt-0.5">
                Module 15: Automated time-series analysis comparing crack length, aperture expansion, and defect emergence across inspections.
              </p>
            </div>
            <button
              onClick={fetchProgression}
              disabled={progressionLoading}
              className="btn-secondary text-xs py-1.5 px-3 self-start sm:self-auto flex items-center gap-1.5"
            >
              <Activity className="w-3.5 h-3.5" />
              <span>{progressionLoading ? 'Refreshing...' : 'Refresh Timeline'}</span>
            </button>
          </div>

          {progressionLoading ? (
            <div className="py-16 text-center text-slate-400">
              <div className="w-8 h-8 border-4 border-purple-600 border-t-transparent rounded-full animate-spin mx-auto mb-2"></div>
              <p className="text-xs">Computing time-series crack growth metrics...</p>
            </div>
          ) : !progressionData || progressionData.timeline.length === 0 ? (
            <div className="card p-10 text-center text-slate-400 border-slate-200/80">
              <Activity className="w-10 h-10 mx-auto mb-2 text-slate-300" />
              <h4 className="text-sm font-bold text-slate-700">No Progression Data Available</h4>
              <p className="text-xs text-slate-400 mt-1 max-w-sm mx-auto">
                At least one completed inspection with analyzed imagery is required to track structural damage progression over time.
              </p>
            </div>
          ) : (
            <div className="space-y-6">
              {/* Summary KPIs */}
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
                <div className="card p-4 border-slate-200/80 bg-white">
                  <p className="text-[11px] font-bold uppercase tracking-wider text-slate-400">Total Inspections</p>
                  <p className="text-2xl font-black text-slate-900 mt-1">{progressionData.timeline.length}</p>
                  <p className="text-[11px] text-slate-500 mt-0.5">Historical data points</p>
                </div>

                <div className="card p-4 border-slate-200/80 bg-white">
                  <p className="text-[11px] font-bold uppercase tracking-wider text-slate-400">Latest Crack Length</p>
                  <p className="text-2xl font-black text-slate-900 mt-1">
                    {progressionData.timeline[progressionData.timeline.length - 1].total_crack_length_mm > 0
                      ? `${progressionData.timeline[progressionData.timeline.length - 1].total_crack_length_mm.toFixed(1)} mm`
                      : `${progressionData.timeline[progressionData.timeline.length - 1].total_crack_length_px.toFixed(0)} px`}
                  </p>
                  <p className="text-[11px] text-slate-500 mt-0.5">Latest inspected state</p>
                </div>

                <div className="card p-4 border-slate-200/80 bg-white">
                  <p className="text-[11px] font-bold uppercase tracking-wider text-slate-400">Peak Crack Width</p>
                  <p className="text-2xl font-black text-slate-900 mt-1">
                    {progressionData.timeline[progressionData.timeline.length - 1].max_crack_width_mm > 0
                      ? `${progressionData.timeline[progressionData.timeline.length - 1].max_crack_width_mm.toFixed(2)} mm`
                      : `${progressionData.timeline[progressionData.timeline.length - 1].max_crack_width_px.toFixed(1)} px`}
                  </p>
                  <p className="text-[11px] text-slate-500 mt-0.5">Critical aperture size</p>
                </div>

                <div className="card p-4 border-slate-200/80 bg-white">
                  <p className="text-[11px] font-bold uppercase tracking-wider text-slate-400">Current Health Trend</p>
                  <p className="text-sm font-black mt-2">
                    <span
                      className={`px-2.5 py-1 rounded-full text-xs font-bold inline-block border ${
                        progressionData.timeline[progressionData.timeline.length - 1].progression_status === 'Accelerated Deterioration'
                          ? 'bg-rose-50 text-rose-700 border-rose-200'
                          : progressionData.timeline[progressionData.timeline.length - 1].progression_status === 'Active Progression'
                          ? 'bg-amber-50 text-amber-700 border-amber-200'
                          : progressionData.timeline[progressionData.timeline.length - 1].progression_status === 'Repaired'
                          ? 'bg-blue-50 text-blue-700 border-blue-200'
                          : 'bg-emerald-50 text-emerald-700 border-emerald-200'
                      }`}
                    >
                      {progressionData.timeline[progressionData.timeline.length - 1].progression_status}
                    </span>
                  </p>
                </div>
              </div>

              {/* Chronological Timeline Cards */}
              <div className="space-y-4">
                <h3 className="text-xs font-bold text-slate-600 uppercase tracking-wider">
                  Chronological Degradation Milestones
                </h3>

                <div className="relative border-l-2 border-slate-200 ml-4 pl-6 space-y-6">
                  {progressionData.timeline.map((point, index) => {
                    const isAccelerating = point.progression_status === 'Accelerated Deterioration';
                    const isProgressing = point.progression_status === 'Active Progression';
                    const isRepaired = point.progression_status === 'Repaired';

                    return (
                      <div key={point.inspection_id} className="relative">
                        {/* Timeline node icon */}
                        <div
                          className={`absolute -left-[35px] top-1.5 w-6 h-6 rounded-full border-2 flex items-center justify-center bg-white shadow-xs ${
                            isAccelerating
                              ? 'border-rose-500 text-rose-600'
                              : isProgressing
                              ? 'border-amber-500 text-amber-600'
                              : isRepaired
                              ? 'border-blue-500 text-blue-600'
                              : 'border-emerald-500 text-emerald-600'
                          }`}
                        >
                          <div className={`w-2 h-2 rounded-full ${
                            isAccelerating ? 'bg-rose-500' : isProgressing ? 'bg-amber-500' : isRepaired ? 'bg-blue-500' : 'bg-emerald-500'
                          }`} />
                        </div>

                        {/* Card */}
                        <div className="card p-5 border-slate-200/80 bg-white space-y-3">
                          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-slate-100 pb-3">
                            <div>
                              <div className="flex items-center gap-2">
                                <span className="font-bold text-sm text-slate-900">
                                  Inspection #{point.inspection_id}
                                </span>
                                <span className="text-xs text-slate-500">
                                  ({point.inspection_date || 'Undated'})
                                </span>
                                <span className="text-[11px] font-semibold px-2 py-0.5 rounded bg-slate-100 text-slate-700">
                                  {point.inspector_name}
                                </span>
                              </div>
                            </div>

                            <div className="flex items-center gap-2">
                              {index > 0 && point.growth_rate_pct !== 0 && (
                                <span
                                  className={`text-xs font-mono font-bold px-2 py-0.5 rounded flex items-center gap-0.5 border ${
                                    point.growth_rate_pct > 0
                                      ? 'bg-rose-50 text-rose-700 border-rose-200'
                                      : 'bg-emerald-50 text-emerald-700 border-emerald-200'
                                  }`}
                                >
                                  {point.growth_rate_pct > 0 ? '+' : ''}{point.growth_rate_pct.toFixed(1)}% length delta
                                </span>
                              )}
                              <span
                                className={`text-xs font-semibold px-2.5 py-0.5 rounded-full border ${
                                  isAccelerating
                                    ? 'bg-rose-50 text-rose-700 border-rose-200'
                                    : isProgressing
                                    ? 'bg-amber-50 text-amber-700 border-amber-200'
                                    : isRepaired
                                    ? 'bg-blue-50 text-blue-700 border-blue-200'
                                    : 'bg-emerald-50 text-emerald-700 border-emerald-200'
                                }`}
                              >
                                {point.progression_status}
                              </span>
                            </div>
                          </div>

                          {/* Metric stats row */}
                          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs">
                            <div className="p-2.5 rounded-lg bg-slate-50 border border-slate-100">
                              <span className="text-slate-400 block text-[10px] font-bold uppercase">Crack Images</span>
                              <span className="font-bold text-slate-800 text-sm">
                                {point.cracked_images} / {point.total_images}
                              </span>
                            </div>

                            <div className="p-2.5 rounded-lg bg-slate-50 border border-slate-100">
                              <span className="text-slate-400 block text-[10px] font-bold uppercase">Total Crack Length</span>
                              <span className="font-bold text-slate-800 text-sm">
                                {point.total_crack_length_mm > 0
                                  ? `${point.total_crack_length_mm.toFixed(1)} mm`
                                  : `${point.total_crack_length_px.toFixed(0)} px`}
                              </span>
                            </div>

                            <div className="p-2.5 rounded-lg bg-slate-50 border border-slate-100">
                              <span className="text-slate-400 block text-[10px] font-bold uppercase">Max Width Aperture</span>
                              <span className="font-bold text-slate-800 text-sm">
                                {point.max_crack_width_mm > 0
                                  ? `${point.max_crack_width_mm.toFixed(2)} mm`
                                  : `${point.max_crack_width_px.toFixed(1)} px`}
                              </span>
                            </div>

                            <div className="p-2.5 rounded-lg bg-slate-50 border border-slate-100">
                              <span className="text-slate-400 block text-[10px] font-bold uppercase">Surface Crack Density</span>
                              <span className="font-bold text-slate-800 text-sm">
                                {point.mean_crack_density_pct.toFixed(2)}%
                              </span>
                            </div>
                          </div>

                          {/* Damage categories detected */}
                          {point.detected_damage_categories && point.detected_damage_categories.length > 0 && (
                            <div className="pt-2 flex flex-wrap items-center gap-1.5">
                              <span className="text-[10px] font-bold uppercase text-slate-400 mr-1">Observed Defects:</span>
                              {point.detected_damage_categories.map((cat, i) => (
                                <span
                                  key={i}
                                  className="text-[11px] font-medium px-2 py-0.5 rounded-md bg-purple-50 text-purple-700 border border-purple-200"
                                >
                                  {cat}
                                </span>
                              ))}
                            </div>
                          )}

                          <div className="pt-2 flex justify-end">
                            <Link
                              to={`/inspections/${point.inspection_id}`}
                              className="text-xs text-blue-600 hover:text-blue-800 font-semibold flex items-center gap-1"
                            >
                              <span>Open Inspection #{point.inspection_id}</span>
                              <ExternalLink className="w-3 h-3" />
                            </Link>
                          </div>
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Schedule Inspection Modal */}
      {showModal && (
        <div className="fixed inset-0 bg-slate-950/70 backdrop-blur-xs z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl shadow-xl max-w-lg w-full p-6 space-y-5 border border-slate-200">
            <div className="flex items-center justify-between border-b border-slate-100 pb-3">
              <div>
                <h3 className="text-base font-bold text-slate-900">Schedule Site Inspection</h3>
                <p className="text-xs text-slate-500 mt-0.5">Assign an inspector and target date for {asset.name}</p>
              </div>
              <button 
                onClick={() => setShowModal(false)}
                className="text-slate-400 hover:text-slate-600 p-1 rounded-lg"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <form onSubmit={handleCreateInspection} className="space-y-4">
              <div>
                <label className="block text-xs font-bold uppercase text-slate-700 mb-1.5">
                  Inspection Target Date
                </label>
                <input
                  type="date"
                  required
                  value={inspDate}
                  onChange={(e) => setInspDate(e.target.value)}
                  className="input-field text-xs"
                />
              </div>

              <div>
                <label className="block text-xs font-bold uppercase text-slate-700 mb-1.5">
                  Assigned Structural Inspector
                </label>
                {user?.role?.name === 'Infrastructure Inspector' ? (
                  <input
                    type="text"
                    disabled
                    value={`${user.full_name} (Logged In)`}
                    className="input-field bg-slate-100 text-slate-600 text-xs"
                  />
                ) : (
                  <select
                    value={inspectorId}
                    onChange={(e) => setInspectorId(Number(e.target.value))}
                    className="input-field bg-white text-xs"
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
                <label className="block text-xs font-bold uppercase text-slate-700 mb-1.5">
                  Field Scope & Instructions
                </label>
                <textarea
                  rows={3}
                  value={notes}
                  onChange={(e) => setNotes(e.target.value)}
                  placeholder="Focus areas: Abutment 2 spalling, pier water line scour, deck joints..."
                  className="input-field text-xs"
                />
              </div>

              <div className="flex justify-end gap-3 pt-3 border-t border-slate-100">
                <button
                  type="button"
                  onClick={() => setShowModal(false)}
                  className="btn-secondary text-xs py-2 px-3.5"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={submitting}
                  className="btn-primary text-xs py-2 px-4"
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
