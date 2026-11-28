import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import api from '../api/client';
import {
  Building2,
  ClipboardList,
  Camera,
  ArrowRight,
  Activity,
  Sparkles,
  MapPin,
  AlertTriangle,
  Wrench,
  BarChart2,
  TrendingUp,
  CheckCircle2,
  Clock,
  ShieldCheck,
  ChevronRight,
  RefreshCw,
  ExternalLink,
  Users,
  HardHat,
  ShieldAlert,
  Sliders,
  Check,
  FileText
} from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { AssetMap } from '../components/AssetMap';
import { InfrastructureAsset, DashboardAnalytics } from '../types';

const SEVERITY_CONFIG: Record<string, { label: string; barColor: string; textColor: string; bg: string }> = {
  Critical: { label: 'Critical Risk', barColor: 'bg-rose-500', textColor: 'text-rose-700', bg: 'bg-rose-50' },
  High: { label: 'High Priority', barColor: 'bg-orange-500', textColor: 'text-orange-700', bg: 'bg-orange-50' },
  Medium: { label: 'Medium Risk', barColor: 'bg-amber-500', textColor: 'text-amber-700', bg: 'bg-amber-50' },
  Low: { label: 'Low / Faint', barColor: 'bg-blue-500', textColor: 'text-blue-700', bg: 'bg-blue-50' },
  None: { label: 'Sound / Healthy', barColor: 'bg-emerald-500', textColor: 'text-emerald-700', bg: 'bg-emerald-50' },
};

const STATUS_CONFIG: Record<string, { label: string; bg: string; text: string; dot: string }> = {
  completed: { label: 'Completed', bg: 'bg-emerald-50', text: 'text-emerald-700', dot: 'bg-emerald-500' },
  in_progress: { label: 'In Progress', bg: 'bg-blue-50', text: 'text-blue-700', dot: 'bg-blue-500' },
  pending: { label: 'Pending Review', bg: 'bg-amber-50', text: 'text-amber-700', dot: 'bg-amber-500' },
};

export const Dashboard: React.FC = () => {
  const { user } = useAuth();
  const [analytics, setAnalytics] = useState<DashboardAnalytics | null>(null);
  const [assets, setAssets] = useState<InfrastructureAsset[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  // Module 17: Role-specific dashboard perspectives
  type DashboardRoleView = 'all' | 'inspector' | 'engineer' | 'manager' | 'admin';
  const initialView: DashboardRoleView = 
    user?.role?.name === 'Infrastructure Inspector' ? 'inspector' :
    user?.role?.name === 'Civil Engineer' ? 'engineer' :
    user?.role?.name === 'Infrastructure Manager' ? 'manager' :
    user?.role?.name === 'Administrator' ? 'admin' : 'all';

  const [activeView, setActiveView] = useState<DashboardRoleView>(initialView);

  const fetchDashboardData = async () => {
    try {
      const [analyticsRes, assetsRes] = await Promise.all([
        api.get<DashboardAnalytics>('/analytics/dashboard'),
        api.get('/assets/?page=1&size=100'),
      ]);
      setAnalytics(analyticsRes.data);
      setAssets(assetsRes.data.items || []);
    } catch (err) {
      console.error('Failed to load dashboard analytics', err);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  useEffect(() => {
    fetchDashboardData();
  }, []);

  const handleRefresh = () => {
    setRefreshing(true);
    fetchDashboardData();
  };

  const totalSeverity = analytics
    ? Object.values(analytics.severity_distribution).reduce((a, b) => a + b, 0) || 1
    : 1;

  return (
    <div className="space-y-8 max-w-7xl mx-auto">
      {/* ── Welcome & Top Actions Header ─────────────────────────────────── */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 bg-white p-5 sm:p-6 rounded-2xl border border-slate-200/80 shadow-xs">
        <div className="space-y-1">
          <div className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-blue-50 text-blue-700 border border-blue-200">
            <Sparkles className="w-3.5 h-3.5" />
            <span>InfraScan AI v3.0 • Civil Structural Assessment</span>
          </div>
          <h1 className="text-xl sm:text-2xl font-bold text-slate-900 tracking-tight">
            Welcome back, {user?.full_name}
          </h1>
          <p className="text-xs sm:text-sm text-slate-500">
            Real-time infrastructure health monitoring, crack localization, and autonomous risk scoring.
          </p>
        </div>

        <div className="flex items-center gap-2.5">
          <button
            onClick={handleRefresh}
            disabled={refreshing}
            className="btn-secondary text-xs py-2 px-3.5"
            title="Refresh metrics"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${refreshing ? 'animate-spin' : ''}`} />
            <span>Sync Live Data</span>
          </button>
          <Link to="/assets" className="btn-primary text-xs py-2 px-4">
            <Building2 className="w-4 h-4" />
            <span>Manage Assets</span>
          </Link>
        </div>
      </div>

      {/* ── Module 17: Role-Specific Dashboard Perspective Selector ─────── */}
      <div className="bg-slate-100/80 p-1.5 rounded-2xl border border-slate-200 flex flex-wrap items-center gap-1">
        <span className="text-[11px] font-bold text-slate-400 uppercase tracking-wider px-2.5 hidden sm:inline">
          Console:
        </span>
        {[
          { id: 'all', label: 'Executive Overview', icon: Activity },
          { id: 'inspector', label: 'Field Inspector', icon: HardHat },
          { id: 'engineer', label: 'Civil Engineer', icon: ShieldCheck },
          { id: 'manager', label: 'Asset Manager', icon: Building2 },
          { id: 'admin', label: 'Administrator', icon: Users },
        ].map((v) => {
          const Icon = v.icon;
          const isActive = activeView === v.id;
          return (
            <button
              key={v.id}
              onClick={() => setActiveView(v.id as DashboardRoleView)}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-medium transition-all duration-150 ${
                isActive
                  ? 'bg-white text-slate-900 font-semibold shadow-xs'
                  : 'text-slate-600 hover:text-slate-900 hover:bg-slate-200/60'
              }`}
            >
              <Icon className="w-3.5 h-3.5" />
              <span>{v.label}</span>
            </button>
          );
        })}
      </div>

      {/* ── 4 Primary KPI Stat Cards ─────────────────────────────────────── */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Card 1: Assets */}
        <div className="card p-5 border-slate-200/80 flex flex-col justify-between">
          <div className="flex items-start justify-between">
            <div className="space-y-1">
              <p className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider">
                Total Assets
              </p>
              <p className="text-2xl sm:text-3xl font-extrabold text-slate-900 tracking-tight">
                {loading ? '...' : analytics?.total_assets || assets.length}
              </p>
              <p className="text-[11px] text-slate-500">Bridges, Tunnels, Walls, Dams</p>
            </div>
            <div className="h-10 w-10 rounded-xl bg-blue-50 text-blue-600 flex items-center justify-center shrink-0 border border-blue-100">
              <Building2 className="w-5 h-5" />
            </div>
          </div>
          <div className="mt-4 pt-3 border-t border-slate-100 flex items-center justify-between text-xs text-slate-500">
            <span>Inventory catalog</span>
            <Link to="/assets" className="text-blue-600 font-semibold hover:underline flex items-center gap-1">
              <span>View all</span>
              <ChevronRight className="w-3.5 h-3.5" />
            </Link>
          </div>
        </div>

        {/* Card 2: Inspections */}
        <div className="card p-5 border-slate-200/80 flex flex-col justify-between">
          <div className="flex items-start justify-between">
            <div className="space-y-1">
              <p className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider">
                Inspections
              </p>
              <p className="text-2xl sm:text-3xl font-extrabold text-slate-900 tracking-tight">
                {loading ? '...' : analytics?.total_inspections || 0}
              </p>
              <p className="text-[11px] text-slate-500">Field evaluations recorded</p>
            </div>
            <div className="h-10 w-10 rounded-xl bg-indigo-50 text-indigo-600 flex items-center justify-center shrink-0 border border-indigo-100">
              <ClipboardList className="w-5 h-5" />
            </div>
          </div>
          <div className="mt-4 pt-3 border-t border-slate-100 flex items-center justify-between text-xs text-slate-500">
            <span>Audit trail active</span>
            <span className="font-semibold text-emerald-600 flex items-center gap-1">
              <CheckCircle2 className="w-3 h-3" />
              <span>Compliant</span>
            </span>
          </div>
        </div>

        {/* Card 3: Images & Crack Detection Rate */}
        <div className="card p-5 border-slate-200/80 flex flex-col justify-between">
          <div className="flex items-start justify-between">
            <div className="space-y-1">
              <p className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider">
                Defect Rate
              </p>
              <div className="flex items-baseline gap-2">
                <p className="text-2xl sm:text-3xl font-extrabold text-slate-900 tracking-tight">
                  {loading ? '...' : `${analytics?.crack_rate_pct || 0}%`}
                </p>
                <span className="text-[11px] font-semibold text-rose-700 bg-rose-50 px-1.5 py-0.2 rounded border border-rose-200">
                  {analytics?.cracked_images || 0} Defective
                </span>
              </div>
              <p className="text-[11px] text-slate-500">
                {analytics?.total_images || 0} total photos analyzed
              </p>
            </div>
            <div className="h-10 w-10 rounded-xl bg-rose-50 text-rose-600 flex items-center justify-center shrink-0 border border-rose-100">
              <Camera className="w-5 h-5" />
            </div>
          </div>
          <div className="mt-4 pt-3 border-t border-slate-100 flex items-center justify-between text-xs text-slate-500">
            <span>AI Precision</span>
            <span className="font-semibold text-blue-600">95.14% Precision</span>
          </div>
        </div>

        {/* Card 4: AI Model Performance */}
        <div className="card p-5 border-slate-200/80 flex flex-col justify-between bg-slate-900 text-white">
          <div className="flex items-start justify-between">
            <div className="space-y-1">
              <p className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider">
                Production AI
              </p>
              <p className="text-2xl sm:text-3xl font-extrabold text-white tracking-tight">
                94.6%
              </p>
              <p className="text-[11px] text-slate-300">MobileNetV3 + TTA (ONNX)</p>
            </div>
            <div className="h-10 w-10 rounded-xl bg-slate-800 text-emerald-400 flex items-center justify-center shrink-0 border border-slate-700">
              <ShieldCheck className="w-5 h-5" />
            </div>
          </div>
          <div className="mt-4 pt-3 border-t border-slate-800 flex items-center justify-between text-xs text-slate-400">
            <span>Latency: ~48ms</span>
            <Link to="/model-comparison" className="text-emerald-400 font-semibold hover:underline flex items-center gap-1">
              <span>Benchmark</span>
              <ChevronRight className="w-3.5 h-3.5" />
            </Link>
          </div>
        </div>
      </div>

      {/* ── Perspective 1: Inspector Specific Panel ───────────────────────── */}
      {activeView === 'inspector' && (
        <div className="card p-5 border-slate-200/80 space-y-4">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-slate-100 pb-3">
            <div className="flex items-center gap-2.5">
              <div className="p-2 bg-indigo-50 text-indigo-700 border border-indigo-100 rounded-xl">
                <HardHat className="w-5 h-5" />
              </div>
              <div>
                <h3 className="font-bold text-slate-900 text-sm">Inspector Field Console</h3>
                <p className="text-xs text-slate-500">Assigned inspections, field upload pipeline, and real-time image validation</p>
              </div>
            </div>
            <Link to="/assets" className="btn-primary text-xs py-2 px-3 self-start sm:self-auto">
              <span>+ Select Asset for Inspection</span>
            </Link>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
            <div className="p-3.5 rounded-xl bg-slate-50 border border-slate-100">
              <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">Pending Review</span>
              <p className="text-2xl font-extrabold text-amber-600 mt-0.5">{analytics?.inspection_status?.pending || 0}</p>
              <span className="text-xs text-slate-500">Awaiting engineer review</span>
            </div>
            <div className="p-3.5 rounded-xl bg-slate-50 border border-slate-100">
              <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">In Progress</span>
              <p className="text-2xl font-extrabold text-blue-600 mt-0.5">{analytics?.inspection_status?.in_progress || 0}</p>
              <span className="text-xs text-slate-500">Field imagery uploaded</span>
            </div>
            <div className="p-3.5 rounded-xl bg-slate-50 border border-slate-100">
              <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">Completed</span>
              <p className="text-2xl font-extrabold text-emerald-600 mt-0.5">{analytics?.inspection_status?.completed || 0}</p>
              <span className="text-xs text-slate-500">Signed off with PDF report</span>
            </div>
          </div>
        </div>
      )}

      {/* ── Perspective 2: Civil Engineer Panel ───────────────────────────── */}
      {activeView === 'engineer' && (
        <div className="card p-5 border-slate-200/80 space-y-4">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-slate-100 pb-3">
            <div className="flex items-center gap-2.5">
              <div className="p-2 bg-amber-50 text-amber-700 border border-amber-100 rounded-xl">
                <ShieldAlert className="w-5 h-5" />
              </div>
              <div>
                <h3 className="font-bold text-slate-900 text-sm">Civil Engineer Review Console</h3>
                <p className="text-xs text-slate-500">Damage quantification, crack morphology analysis, and official sign-off</p>
              </div>
            </div>
            <Link to="/maintenance" className="btn-secondary text-xs py-2 px-3 self-start sm:self-auto">
              <span>View Prioritization Queue</span>
            </Link>
          </div>

          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            <div className="p-3.5 rounded-xl bg-slate-50 border border-slate-100">
              <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">Critical Risks</span>
              <p className="text-2xl font-extrabold text-rose-600 mt-0.5">{analytics?.severity_distribution?.Critical || 0}</p>
              <span className="text-xs text-slate-500">Urgent review</span>
            </div>
            <div className="p-3.5 rounded-xl bg-slate-50 border border-slate-100">
              <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">High Severity</span>
              <p className="text-2xl font-extrabold text-orange-600 mt-0.5">{analytics?.severity_distribution?.High || 0}</p>
              <span className="text-xs text-slate-500">Repair &lt;30 days</span>
            </div>
            <div className="p-3.5 rounded-xl bg-slate-50 border border-slate-100">
              <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">Medium Severity</span>
              <p className="text-2xl font-extrabold text-amber-600 mt-0.5">{analytics?.severity_distribution?.Medium || 0}</p>
              <span className="text-xs text-slate-500">Preventive coating</span>
            </div>
            <div className="p-3.5 rounded-xl bg-slate-50 border border-slate-100">
              <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">Sound Concrete</span>
              <p className="text-2xl font-extrabold text-emerald-600 mt-0.5">{analytics?.severity_distribution?.None || 0}</p>
              <span className="text-xs text-slate-500">Healthy surfaces</span>
            </div>
          </div>
        </div>
      )}

      {/* ── Perspective 3: Administrator Panel ────────────────────────────── */}
      {activeView === 'admin' && (
        <div className="card p-5 border-slate-200/80 space-y-4">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-slate-100 pb-3">
            <div className="flex items-center gap-2.5">
              <div className="p-2 bg-purple-50 text-purple-700 border border-purple-100 rounded-xl">
                <Users className="w-5 h-5" />
              </div>
              <div>
                <h3 className="font-bold text-slate-900 text-sm">Platform Administration Console</h3>
                <p className="text-xs text-slate-500">System health, RBAC security, active AI model registry & audit trails</p>
              </div>
            </div>
            <Link to="/admin/users" className="btn-secondary text-xs py-2 px-3 self-start sm:self-auto">
              <span>Manage User Roles</span>
            </Link>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
            <div className="p-3.5 rounded-xl bg-slate-50 border border-slate-100">
              <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">System Health</span>
              <p className="text-base font-bold text-emerald-600 mt-0.5 flex items-center gap-1.5">
                <Check className="w-4 h-4" />
                <span>100% Operational</span>
              </p>
              <span className="text-xs text-slate-500">FastAPI + ONNX Runtime CPU</span>
            </div>
            <div className="p-3.5 rounded-xl bg-slate-50 border border-slate-100">
              <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">Active Vision Backbone</span>
              <p className="text-base font-bold text-slate-900 mt-0.5">MobileNetV3-TTA</p>
              <span className="text-xs text-slate-500">Version 3.0 Deployed</span>
            </div>
            <div className="p-3.5 rounded-xl bg-slate-50 border border-slate-100">
              <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">Security Standard</span>
              <p className="text-base font-bold text-blue-600 mt-0.5">JWT + PBKDF2</p>
              <span className="text-xs text-slate-500">5-Tier Role-Based Access</span>
            </div>
          </div>
        </div>
      )}

      {/* ── Structural Health & Severity Analytics ───────────────────────── */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Severity Breakdown Bar Chart */}
        <div className="card lg:col-span-2 space-y-5">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-base font-bold text-slate-900 flex items-center gap-2">
                <Activity className="w-4 h-4 text-blue-600" />
                <span>Structural Defect Severity Distribution</span>
              </h2>
              <p className="text-xs text-slate-500 mt-0.5">
                Classification breakdown across all analyzed concrete inspection photographs
              </p>
            </div>
            <Link to="/maintenance" className="text-xs font-semibold text-blue-600 hover:underline flex items-center gap-1">
              <span>Maintenance Queue</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </Link>
          </div>

          {/* Stacked Progress Bar */}
          <div className="space-y-2">
            <div className="w-full bg-slate-100 rounded-full h-3 overflow-hidden flex">
              {Object.entries(analytics?.severity_distribution || { None: 1 }).map(([sev, count]) => {
                const pct = Math.max(0, (count / totalSeverity) * 100);
                const cfg = SEVERITY_CONFIG[sev] || SEVERITY_CONFIG.None;
                if (count === 0) return null;
                return (
                  <div
                    key={sev}
                    className={`h-full ${cfg.barColor} transition-all duration-500 first:rounded-l-full last:rounded-r-full`}
                    style={{ width: `${pct}%` }}
                    title={`${cfg.label}: ${count} (${pct.toFixed(1)}%)`}
                  />
                );
              })}
            </div>

            {/* Severity Legend */}
            <div className="grid grid-cols-2 sm:grid-cols-5 gap-3 pt-2">
              {['Critical', 'High', 'Medium', 'Low', 'None'].map((sev) => {
                const count = analytics?.severity_distribution?.[sev] || 0;
                const cfg = SEVERITY_CONFIG[sev];
                return (
                  <div key={sev} className={`p-3 rounded-xl border border-slate-100 ${cfg.bg}`}>
                    <div className="flex items-center gap-1.5 mb-1">
                      <span className={`h-2 w-2 rounded-full ${cfg.barColor}`} />
                      <span className="text-[11px] font-bold text-slate-700">{cfg.label}</span>
                    </div>
                    <p className={`text-xl font-extrabold ${cfg.textColor}`}>{count}</p>
                    <p className="text-[10px] text-slate-400 mt-0.5">
                      {((count / totalSeverity) * 100).toFixed(0)}% of total
                    </p>
                  </div>
                );
              })}
            </div>
          </div>
        </div>

        {/* Inspection Lifecycle Status Card */}
        <div className="card space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-base font-bold text-slate-900 flex items-center gap-2">
              <Clock className="w-4 h-4 text-indigo-600" />
              <span>Inspection Status</span>
            </h2>
            <span className="text-xs text-slate-400">Current Cycle</span>
          </div>

          <div className="space-y-3 pt-1">
            {['completed', 'in_progress', 'pending'].map((st) => {
              const count = analytics?.inspection_status?.[st] || 0;
              const cfg = STATUS_CONFIG[st] || STATUS_CONFIG.pending;
              return (
                <div
                  key={st}
                  className="flex items-center justify-between p-3 rounded-xl bg-slate-50 border border-slate-100 hover:border-slate-200 transition-colors"
                >
                  <div className="flex items-center gap-2.5">
                    <span className={`h-2.5 w-2.5 rounded-full ${cfg.dot}`} />
                    <span className="text-xs font-semibold text-slate-800">{cfg.label}</span>
                  </div>
                  <span className={`px-2.5 py-0.5 rounded-full text-xs font-extrabold ${cfg.bg} ${cfg.text}`}>
                    {count}
                  </span>
                </div>
              );
            })}
          </div>

          <div className="pt-2">
            <Link
              to="/maintenance"
              className="w-full btn-secondary text-xs py-2.5 flex items-center justify-center gap-2"
            >
              <Wrench className="w-3.5 h-3.5 text-amber-600" />
              <span>Open Maintenance Prioritization</span>
            </Link>
          </div>
        </div>
      </div>

      {/* ── Interactive GIS Asset Map ────────────────────────────────────── */}
      <div className="card space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
          <div>
            <h2 className="text-base font-bold text-slate-900 flex items-center gap-2">
              <MapPin className="w-4 h-4 text-blue-600" />
              <span>Geospatial Infrastructure Asset Overview</span>
            </h2>
            <p className="text-xs text-slate-500 mt-0.5">
              Live GIS coordinates with automated structural damage status indicators
            </p>
          </div>
          <div className="flex items-center gap-2 text-xs text-slate-500">
            <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded bg-emerald-50 text-emerald-700 font-semibold border border-emerald-200">
              <span className="h-1.5 w-1.5 rounded-full bg-emerald-500"></span>
              <span>Active Assets ({assets.length})</span>
            </span>
          </div>
        </div>

        <div className="rounded-xl overflow-hidden border border-slate-200/90 shadow-inner">
          <AssetMap assets={assets} height="420px" />
        </div>
      </div>

      {/* ── Recent Inspections Table ─────────────────────────────────────── */}
      <div className="card space-y-4 overflow-hidden">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-base font-bold text-slate-900 flex items-center gap-2">
              <ClipboardList className="w-4 h-4 text-blue-600" />
              <span>Recent Site Inspections & Assessments</span>
            </h2>
            <p className="text-xs text-slate-500 mt-0.5">Latest civil asset physical evaluations logged in system</p>
          </div>
          <Link to="/assets" className="text-xs font-semibold text-blue-600 hover:underline flex items-center gap-1">
            <span>View all inspections</span>
            <ArrowRight className="w-3.5 h-3.5" />
          </Link>
        </div>

        {analytics?.recent_inspections && analytics.recent_inspections.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse text-sm">
              <thead>
                <tr className="bg-slate-50/80 border-b border-slate-100 text-[11px] font-bold text-slate-400 uppercase tracking-wider">
                  <th className="py-3 px-4">Inspection Date</th>
                  <th className="py-3 px-4">Asset Name</th>
                  <th className="py-3 px-4">Assigned Inspector</th>
                  <th className="py-3 px-4">Status</th>
                  <th className="py-3 px-4 text-right">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 text-xs">
                {analytics.recent_inspections.map((insp) => {
                  const statusCfg = STATUS_CONFIG[insp.status] || STATUS_CONFIG.pending;
                  return (
                    <tr key={insp.id} className="hover:bg-slate-50/80 transition-colors">
                      <td className="py-3.5 px-4 font-mono font-medium text-slate-600">
                        {insp.inspection_date || 'N/A'}
                      </td>
                      <td className="py-3.5 px-4 font-semibold text-slate-900">
                        <Link
                          to={`/inspections/${insp.id}`}
                          className="hover:text-blue-600 transition-colors flex items-center gap-1.5"
                        >
                          <span>{insp.asset_name}</span>
                          <ExternalLink className="w-3 h-3 text-slate-400" />
                        </Link>
                      </td>
                      <td className="py-3.5 px-4 text-slate-600 font-medium">
                        {insp.inspector_name}
                      </td>
                      <td className="py-3.5 px-4">
                        <span className={`inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full font-semibold text-[11px] ${statusCfg.bg} ${statusCfg.text}`}>
                          <span className={`h-1.5 w-1.5 rounded-full ${statusCfg.dot}`} />
                          <span>{statusCfg.label}</span>
                        </span>
                      </td>
                      <td className="py-3.5 px-4 text-right">
                        <Link
                          to={`/inspections/${insp.id}`}
                          className="inline-flex items-center gap-1 px-3 py-1.5 rounded-lg text-xs font-semibold bg-blue-50 text-blue-700 hover:bg-blue-100 transition-colors"
                        >
                          <span>Open View</span>
                          <ArrowRight className="w-3 h-3" />
                        </Link>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="py-12 text-center text-slate-400 text-xs">
            <ClipboardList className="w-8 h-8 mx-auto mb-2 text-slate-300" />
            <p>No recent inspection records found.</p>
          </div>
        )}
      </div>
    </div>
  );
};
