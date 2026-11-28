import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import api from '../api/client';
import { MaintenanceQueueItem, WorkOrder } from '../types';
import {
  Wrench,
  AlertTriangle,
  ShieldAlert,
  Clock,
  ArrowRight,
  Filter,
  CheckCircle2,
  AlertCircle,
  RefreshCw,
  Search,
  ExternalLink,
  ChevronRight,
  SlidersHorizontal,
  Plus,
  Check,
  X,
  FileText,
  DollarSign,
  Calendar,
  Layers
} from 'lucide-react';
import { useAuth } from '../context/AuthContext';

const PRIORITY_BADGES: Record<string, { bg: string; text: string; border: string; icon: any }> = {
  'Urgent Engineering Review': { bg: 'bg-rose-50', text: 'text-rose-700', border: 'border-rose-200', icon: ShieldAlert },
  Critical: { bg: 'bg-rose-50', text: 'text-rose-700', border: 'border-rose-200', icon: ShieldAlert },
  'High Priority': { bg: 'bg-red-50', text: 'text-red-700', border: 'border-red-200', icon: AlertTriangle },
  High: { bg: 'bg-red-50', text: 'text-red-700', border: 'border-red-200', icon: AlertTriangle },
  'Medium Priority': { bg: 'bg-amber-50', text: 'text-amber-700', border: 'border-amber-200', icon: AlertCircle },
  Medium: { bg: 'bg-amber-50', text: 'text-amber-700', border: 'border-amber-200', icon: AlertCircle },
  'Low Priority': { bg: 'bg-emerald-50', text: 'text-emerald-700', border: 'border-emerald-200', icon: CheckCircle2 },
  Low: { bg: 'bg-emerald-50', text: 'text-emerald-700', border: 'border-emerald-200', icon: CheckCircle2 },
  'Routine Monitoring': { bg: 'bg-slate-50', text: 'text-slate-600', border: 'border-slate-200', icon: Clock },
  Minimal: { bg: 'bg-slate-50', text: 'text-slate-600', border: 'border-slate-200', icon: Clock },
};

export const MaintenancePriority: React.FC = () => {
  const { user } = useAuth();
  const [activeTab, setActiveTab] = useState<'queue' | 'work_orders'>('queue');
  const [queue, setQueue] = useState<MaintenanceQueueItem[]>([]);
  const [workOrders, setWorkOrders] = useState<WorkOrder[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [filterPriority, setFilterPriority] = useState<string>('ALL');
  const [searchQuery, setSearchQuery] = useState<string>('');

  // Work Order Creation Modal
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [modalAssetId, setModalAssetId] = useState<number | ''>('');
  const [modalTitle, setModalTitle] = useState('');
  const [modalDesc, setModalDesc] = useState('');
  const [modalPriority, setModalPriority] = useState('Medium Priority');
  const [modalCost, setModalCost] = useState('');
  const [modalDueDate, setModalDueDate] = useState('');
  const [submittingWO, setSubmittingWO] = useState(false);

  // Resolution Modal
  const [resolvingOrder, setResolvingOrder] = useState<WorkOrder | null>(null);
  const [resolutionNotes, setResolutionNotes] = useState('');

  const fetchData = async () => {
    setLoading(true);
    setError('');
    try {
      const [queueRes, woRes] = await Promise.all([
        api.get('/analytics/maintenance-queue'),
        api.get('/work-orders/')
      ]);
      setQueue(queueRes.data.queue || []);
      setWorkOrders(woRes.data || []);
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Failed to load maintenance prioritization queue.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  const handleCreateWorkOrder = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!modalAssetId || !modalTitle) return;
    setSubmittingWO(true);
    try {
      await api.post('/work-orders/', {
        asset_id: Number(modalAssetId),
        title: modalTitle,
        description: modalDesc,
        priority: modalPriority,
        estimated_cost: modalCost ? parseFloat(modalCost) : null,
        due_date: modalDueDate || null
      });
      setShowCreateModal(false);
      setModalTitle('');
      setModalDesc('');
      setSuccess('Maintenance work order generated and queued successfully.');
      fetchData();
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Failed to create work order.');
    } finally {
      setSubmittingWO(false);
    }
  };

  const handleUpdateStatus = async (woId: number, newStatus: string, notes?: string) => {
    try {
      await api.put(`/work-orders/${woId}`, {
        status: newStatus,
        resolution_notes: notes || undefined
      });
      setSuccess(`Work order updated to '${newStatus}'.`);
      setResolvingOrder(null);
      fetchData();
    } catch (err: any) {
      setError('Failed to update work order status.');
    }
  };

  const openCreateForAsset = (item: MaintenanceQueueItem) => {
    setModalAssetId(item.asset_id);
    setModalTitle(`Structural Repair: ${item.asset_name}`);
    setModalDesc(`Remediate identified ${item.max_severity} defects. Action: ${item.recommended_action}`);
    setModalPriority(item.priority.includes('Critical') ? 'Urgent Engineering Review' : item.priority.includes('High') ? 'High Priority' : 'Medium Priority');
    setShowCreateModal(true);
  };

  const filteredQueue = queue.filter((item) => {
    const matchesPriority =
      filterPriority === 'ALL' || item.priority.toUpperCase().includes(filterPriority.toUpperCase());
    const matchesSearch =
      searchQuery === '' ||
      item.asset_code.toLowerCase().includes(searchQuery.toLowerCase()) ||
      item.asset_name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      item.asset_type.toLowerCase().includes(searchQuery.toLowerCase()) ||
      item.location.toLowerCase().includes(searchQuery.toLowerCase());
    return matchesPriority && matchesSearch;
  });

  const criticalCount = queue.filter((i) => i.priority.includes('Critical') || i.priority.includes('Urgent')).length;
  const highCount = queue.filter((i) => i.priority.includes('High')).length;
  const mediumCount = queue.filter((i) => i.priority.includes('Medium')).length;
  const lowCount = queue.filter((i) => i.priority.includes('Low') || i.priority.includes('Routine') || i.priority.includes('Minimal')).length;

  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      {/* Header Card */}
      <div className="card p-6 flex flex-col md:flex-row md:items-center justify-between gap-4 border-slate-200/80">
        <div>
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full text-xs font-semibold bg-blue-50 text-blue-700 border border-blue-200 mb-2">
            <Wrench className="w-3.5 h-3.5" />
            <span>Autonomous Maintenance Prioritization & Task Management</span>
          </div>
          <h1 className="text-xl sm:text-2xl font-bold text-slate-900 tracking-tight">
            Civil Infrastructure Maintenance & Work Orders
          </h1>
          <p className="text-xs sm:text-sm text-slate-500 mt-1 max-w-2xl">
            Algorithmic ranking weighted by structural defect severity, crack progression metrics, asset age, and repair work order tracking.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => {
              setModalAssetId(queue.length > 0 ? queue[0].asset_id : '');
              setShowCreateModal(true);
            }}
            className="btn-primary flex items-center gap-2 text-xs py-2 px-3.5"
          >
            <Plus className="w-4 h-4" />
            <span>New Work Order</span>
          </button>
          <button
            onClick={fetchData}
            disabled={loading}
            className="btn-secondary flex items-center gap-2 text-xs py-2 px-3.5 bg-white hover:bg-slate-50 shadow-xs"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin text-blue-600' : 'text-slate-600'}`} />
            <span>Refresh</span>
          </button>
        </div>
      </div>

      {/* Tab Switcher */}
      <div className="flex items-center gap-2 bg-slate-100 p-1 rounded-2xl w-fit">
        <button
          onClick={() => setActiveTab('queue')}
          className={`flex items-center gap-2 px-4 py-2 rounded-xl text-xs font-bold transition-all ${
            activeTab === 'queue' ? 'bg-white text-brand-700 shadow-sm' : 'text-slate-600 hover:text-slate-900'
          }`}
        >
          <SlidersHorizontal className="w-3.5 h-3.5" />
          <span>Priority Risk Queue ({queue.length})</span>
        </button>
        <button
          onClick={() => setActiveTab('work_orders')}
          className={`flex items-center gap-2 px-4 py-2 rounded-xl text-xs font-bold transition-all ${
            activeTab === 'work_orders' ? 'bg-white text-brand-700 shadow-sm' : 'text-slate-600 hover:text-slate-900'
          }`}
        >
          <Wrench className="w-3.5 h-3.5" />
          <span>Active Work Orders ({workOrders.length})</span>
        </button>
      </div>

      {/* Alerts */}
      {error && (
        <div className="p-4 rounded-xl bg-rose-50 border border-rose-200 text-xs font-medium text-rose-700 flex items-center gap-2">
          <AlertTriangle className="w-4 h-4 shrink-0" />
          <span>{error}</span>
        </div>
      )}
      {success && (
        <div className="p-4 rounded-xl bg-emerald-50 border border-emerald-200 text-xs font-medium text-emerald-700 flex items-center gap-2">
          <CheckCircle2 className="w-4 h-4 shrink-0" />
          <span>{success}</span>
        </div>
      )}

      {/* TAB 1: PRIORITIZATION QUEUE */}
      {activeTab === 'queue' && (
        <div className="space-y-6">
          {/* Summary KPI Cards */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            <div className="card p-5 border-l-4 border-l-rose-500 border-slate-200/80 flex items-center justify-between bg-white shadow-xs">
              <div>
                <p className="text-[11px] font-bold uppercase tracking-wider text-slate-400">Critical Priority</p>
                <p className="text-2xl font-extrabold text-slate-900 mt-0.5">{criticalCount}</p>
                <p className="text-[11px] text-rose-600 font-medium mt-1">Urgent review required</p>
              </div>
              <div className="h-10 w-10 rounded-xl bg-rose-50 text-rose-600 flex items-center justify-center">
                <ShieldAlert className="w-5 h-5" />
              </div>
            </div>

            <div className="card p-5 border-l-4 border-l-red-500 border-slate-200/80 flex items-center justify-between bg-white shadow-xs">
              <div>
                <p className="text-[11px] font-bold uppercase tracking-wider text-slate-400">High Priority</p>
                <p className="text-2xl font-extrabold text-slate-900 mt-0.5">{highCount}</p>
                <p className="text-[11px] text-red-600 font-medium mt-1">Repair within 30 days</p>
              </div>
              <div className="h-10 w-10 rounded-xl bg-red-50 text-red-600 flex items-center justify-center">
                <AlertTriangle className="w-5 h-5" />
              </div>
            </div>

            <div className="card p-5 border-l-4 border-l-amber-500 border-slate-200/80 flex items-center justify-between bg-white shadow-xs">
              <div>
                <p className="text-[11px] font-bold uppercase tracking-wider text-slate-400">Medium Priority</p>
                <p className="text-2xl font-extrabold text-slate-900 mt-0.5">{mediumCount}</p>
                <p className="text-[11px] text-amber-600 font-medium mt-1">Plan within 90 days</p>
              </div>
              <div className="h-10 w-10 rounded-xl bg-amber-50 text-amber-600 flex items-center justify-center">
                <AlertCircle className="w-5 h-5" />
              </div>
            </div>

            <div className="card p-5 border-l-4 border-l-emerald-500 border-slate-200/80 flex items-center justify-between bg-white shadow-xs">
              <div>
                <p className="text-[11px] font-bold uppercase tracking-wider text-slate-400">Low / Sound</p>
                <p className="text-2xl font-extrabold text-slate-900 mt-0.5">{lowCount}</p>
                <p className="text-[11px] text-emerald-600 font-medium mt-1">Scheduled monitoring</p>
              </div>
              <div className="h-10 w-10 rounded-xl bg-emerald-50 text-emerald-600 flex items-center justify-center">
                <CheckCircle2 className="w-5 h-5" />
              </div>
            </div>
          </div>

          {/* Table Card */}
          <div className="card p-5 space-y-4 border-slate-200/80">
            {/* Filter Bar */}
            <div className="flex flex-col sm:flex-row items-center justify-between gap-3">
              <div className="relative w-full sm:w-72">
                <Search className="w-4 h-4 text-slate-400 absolute left-3 top-2.5" />
                <input
                  type="text"
                  placeholder="Search asset, code, or location..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="w-full pl-9 pr-3 py-1.5 text-xs bg-slate-50 border border-slate-200 rounded-xl focus:bg-white focus:outline-none focus:ring-2 focus:ring-blue-500/20"
                />
              </div>

              <div className="flex items-center gap-1.5 self-end sm:self-auto flex-wrap">
                {['ALL', 'CRITICAL', 'HIGH', 'MEDIUM', 'LOW'].map((p) => (
                  <button
                    key={p}
                    onClick={() => setFilterPriority(p)}
                    className={`px-3 py-1 text-xs font-semibold rounded-lg transition-colors ${
                      filterPriority === p ? 'bg-slate-900 text-white shadow-xs' : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
                    }`}
                  >
                    {p}
                  </button>
                ))}
              </div>
            </div>

            {/* Ranked Table */}
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs border-collapse">
                <thead>
                  <tr className="bg-slate-50 border-b border-slate-200 text-[10px] font-bold text-slate-400 uppercase tracking-wider">
                    <th className="py-3 px-3">Rank</th>
                    <th className="py-3 px-4">Asset Details</th>
                    <th className="py-3 px-4">Type</th>
                    <th className="py-3 px-4">Risk Score</th>
                    <th className="py-3 px-4">Priority Level</th>
                    <th className="py-3 px-4">Flagged Defects</th>
                    <th className="py-3 px-4">Recommended Action</th>
                    <th className="py-3 px-4 text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {filteredQueue.map((item, idx) => {
                    const badgeInfo = PRIORITY_BADGES[item.priority] || PRIORITY_BADGES.Minimal;
                    const BadgeIcon = badgeInfo.icon;
                    return (
                      <tr key={item.asset_id} className="hover:bg-slate-50/80 transition-colors">
                        <td className="py-3.5 px-3 font-mono font-bold text-slate-400">#{idx + 1}</td>
                        <td className="py-3.5 px-4">
                          <Link to={`/assets/${item.asset_id}`} className="font-bold text-slate-900 hover:text-brand-600 flex items-center gap-1.5">
                            <span>{item.asset_name}</span>
                            <ExternalLink className="w-3 h-3 text-slate-400" />
                          </Link>
                          <p className="text-[11px] text-slate-400 font-mono mt-0.5">{item.asset_code}</p>
                        </td>
                        <td className="py-3.5 px-4 text-slate-600 font-medium">{item.asset_type}</td>
                        <td className="py-3.5 px-4">
                          <span className="font-bold font-mono text-xs text-slate-900">{item.risk_score}/100</span>
                        </td>
                        <td className="py-3.5 px-4">
                          <span className={`inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[11px] font-bold border ${badgeInfo.bg} ${badgeInfo.text} ${badgeInfo.border}`}>
                            <BadgeIcon className="w-3 h-3" />
                            <span>{item.priority}</span>
                          </span>
                        </td>
                        <td className="py-3.5 px-4">
                          <div className="flex flex-wrap gap-1 max-w-[180px]">
                            {item.damage_types_found.map((dt, dIdx) => (
                              <span key={dIdx} className="px-1.5 py-0.5 text-[10px] font-medium rounded bg-slate-100 text-slate-700 border border-slate-200">
                                {dt}
                              </span>
                            ))}
                          </div>
                        </td>
                        <td className="py-3.5 px-4 text-slate-700 max-w-[220px] leading-relaxed">
                          {item.recommended_action}
                        </td>
                        <td className="py-3.5 px-4 text-right whitespace-nowrap space-x-1.5">
                          <button
                            onClick={() => openCreateForAsset(item)}
                            className="btn-primary py-1 px-2.5 text-[11px] font-semibold"
                            title="Generate Repair Work Order"
                          >
                            + Work Order
                          </button>
                          <Link
                            to={`/assets/${item.asset_id}`}
                            className="btn-secondary py-1 px-2.5 text-[11px] font-semibold"
                          >
                            View
                          </Link>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {/* TAB 2: ACTIVE WORK ORDERS */}
      {activeTab === 'work_orders' && (
        <div className="card p-5 space-y-4 border-slate-200/80">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-base font-bold text-slate-900 flex items-center gap-2">
                <Wrench className="w-4 h-4 text-brand-600" />
                <span>Structural Repair Tasks & Field Work Orders ({workOrders.length})</span>
              </h2>
              <p className="text-xs text-slate-500 mt-0.5">Track field contractor assignments, epoxy injection sealing, and concrete restoration</p>
            </div>
            <button
              onClick={() => {
                setModalAssetId(queue.length > 0 ? queue[0].asset_id : '');
                setShowCreateModal(true);
              }}
              className="btn-primary text-xs py-1.5 px-3 flex items-center gap-1.5"
            >
              <Plus className="w-3.5 h-3.5" />
              <span>Create Work Order</span>
            </button>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs border-collapse">
              <thead>
                <tr className="bg-slate-50 border-b border-slate-200 text-[10px] font-bold text-slate-400 uppercase tracking-wider">
                  <th className="py-3 px-3">Order ID</th>
                  <th className="py-3 px-4">Task Title</th>
                  <th className="py-3 px-4">Asset</th>
                  <th className="py-3 px-4">Priority</th>
                  <th className="py-3 px-4">Status</th>
                  <th className="py-3 px-4">Due Date</th>
                  <th className="py-3 px-4">Est. Cost</th>
                  <th className="py-3 px-4 text-right">Update Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {workOrders.map((wo) => {
                  const isResolved = wo.status === 'Resolved';
                  return (
                    <tr key={wo.id} className="hover:bg-slate-50/80 transition-colors">
                      <td className="py-3.5 px-3 font-mono font-bold text-slate-500">WO-{String(wo.id).padStart(4, '0')}</td>
                      <td className="py-3.5 px-4">
                        <span className="font-bold text-slate-900 block">{wo.title}</span>
                        <span className="text-[11px] text-slate-500 line-clamp-1">{wo.description}</span>
                      </td>
                      <td className="py-3.5 px-4 font-semibold text-slate-700">
                        {wo.asset_name || `Asset #${wo.asset_id}`}
                      </td>
                      <td className="py-3.5 px-4">
                        <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                          wo.priority.includes('Urgent') ? 'bg-rose-100 text-rose-700' :
                          wo.priority.includes('High') ? 'bg-red-100 text-red-700' :
                          wo.priority.includes('Medium') ? 'bg-amber-100 text-amber-700' : 'bg-slate-100 text-slate-700'
                        }`}>
                          {wo.priority}
                        </span>
                      </td>
                      <td className="py-3.5 px-4">
                        <span className={`px-2.5 py-0.5 rounded-full text-[10px] font-bold ${
                          wo.status === 'Resolved' ? 'bg-emerald-100 text-emerald-800' :
                          wo.status === 'In Progress' ? 'bg-blue-100 text-blue-800' : 'bg-amber-100 text-amber-800'
                        }`}>
                          {wo.status}
                        </span>
                      </td>
                      <td className="py-3.5 px-4 text-slate-600 font-mono">{wo.due_date || 'N/A'}</td>
                      <td className="py-3.5 px-4 text-slate-800 font-mono">
                        {wo.estimated_cost ? `$${wo.estimated_cost.toLocaleString()}` : '—'}
                      </td>
                      <td className="py-3.5 px-4 text-right space-x-1.5">
                        {wo.status === 'Open' && (
                          <button
                            onClick={() => handleUpdateStatus(wo.id, 'In Progress')}
                            className="btn-secondary py-1 px-2.5 text-[11px]"
                          >
                            Start Work
                          </button>
                        )}
                        {wo.status !== 'Resolved' && (
                          <button
                            onClick={() => { setResolvingOrder(wo); setResolutionNotes(''); }}
                            className="btn-primary py-1 px-2.5 text-[11px] bg-emerald-600 hover:bg-emerald-700"
                          >
                            Mark Resolved
                          </button>
                        )}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* CREATE WORK ORDER MODAL */}
      {showCreateModal && (
        <div className="fixed inset-0 bg-slate-950/80 backdrop-blur-md z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl max-w-lg w-full p-6 space-y-4 shadow-2xl border border-slate-200">
            <div className="flex items-center justify-between border-b border-slate-200 pb-3">
              <h3 className="text-base font-bold text-slate-900 flex items-center gap-2">
                <Wrench className="w-4 h-4 text-brand-600" />
                <span>Dispatch Maintenance Work Order</span>
              </h3>
              <button onClick={() => setShowCreateModal(false)} className="p-1 rounded text-slate-400 hover:text-slate-700">
                <X className="w-5 h-5" />
              </button>
            </div>

            <form onSubmit={handleCreateWorkOrder} className="space-y-3.5 text-xs">
              <div>
                <label className="block font-bold text-slate-700 mb-1">Target Infrastructure Asset</label>
                <select
                  value={modalAssetId}
                  onChange={(e) => setModalAssetId(Number(e.target.value))}
                  className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-xl"
                  required
                >
                  <option value="">Select Asset...</option>
                  {queue.map((q) => (
                    <option key={q.asset_id} value={q.asset_id}>
                      {q.asset_code} – {q.asset_name} ({q.priority})
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block font-bold text-slate-700 mb-1">Work Order Title</label>
                <input
                  type="text"
                  value={modalTitle}
                  onChange={(e) => setModalTitle(e.target.value)}
                  placeholder="e.g. Pressure Injection Epoxy Grouting"
                  className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-xl"
                  required
                />
              </div>

              <div>
                <label className="block font-bold text-slate-700 mb-1">Scope of Structural Work</label>
                <textarea
                  value={modalDesc}
                  onChange={(e) => setModalDesc(e.target.value)}
                  rows={3}
                  placeholder="Describe crack preparation, surface grinding, chemical grout injection, or rebar passivation specs..."
                  className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-xl"
                  required
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block font-bold text-slate-700 mb-1">Priority Level</label>
                  <select
                    value={modalPriority}
                    onChange={(e) => setModalPriority(e.target.value)}
                    className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-xl"
                  >
                    <option value="Urgent Engineering Review">Urgent Review</option>
                    <option value="High Priority">High Priority</option>
                    <option value="Medium Priority">Medium Priority</option>
                    <option value="Low Priority">Low Priority</option>
                  </select>
                </div>

                <div>
                  <label className="block font-bold text-slate-700 mb-1">Estimated Cost ($)</label>
                  <input
                    type="number"
                    value={modalCost}
                    onChange={(e) => setModalCost(e.target.value)}
                    placeholder="e.g. 5000"
                    className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-xl"
                  />
                </div>
              </div>

              <div>
                <label className="block font-bold text-slate-700 mb-1">Due Date</label>
                <input
                  type="date"
                  value={modalDueDate}
                  onChange={(e) => setModalDueDate(e.target.value)}
                  className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-xl"
                />
              </div>

              <div className="flex justify-end gap-2 pt-2 border-t border-slate-100">
                <button type="button" onClick={() => setShowCreateModal(false)} className="btn-secondary py-2 px-4">
                  Cancel
                </button>
                <button type="submit" disabled={submittingWO} className="btn-primary py-2 px-5">
                  {submittingWO ? 'Generating...' : 'Issue Work Order'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* RESOLUTION MODAL */}
      {resolvingOrder && (
        <div className="fixed inset-0 bg-slate-950/80 backdrop-blur-md z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl max-w-md w-full p-6 space-y-4 shadow-2xl border border-slate-200">
            <h3 className="text-base font-bold text-slate-900">Mark Work Order Resolved</h3>
            <p className="text-xs text-slate-500">Log repair notes and contractor certification for WO-{resolvingOrder.id}:</p>
            <textarea
              rows={3}
              value={resolutionNotes}
              onChange={(e) => setResolutionNotes(e.target.value)}
              placeholder="e.g. Epoxy injection completed at 4.2 bar pressure, acoustic hammer sounding confirmed solid bond."
              className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-xl text-xs"
            />
            <div className="flex justify-end gap-2 pt-2">
              <button onClick={() => setResolvingOrder(null)} className="btn-secondary py-1.5 px-3 text-xs">
                Cancel
              </button>
              <button
                onClick={() => handleUpdateStatus(resolvingOrder.id, 'Resolved', resolutionNotes)}
                className="btn-primary py-1.5 px-4 text-xs bg-emerald-600 hover:bg-emerald-700"
              >
                Confirm Resolution
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
