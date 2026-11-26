import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import SeverityBadge from '../components/SeverityBadge';
import PriorityBadge from '../components/PriorityBadge';
import {
  Users,
  Shield,
  FileText,
  Activity,
  AlertTriangle,
  CheckCircle,
  XCircle,
  Search,
  UserPlus,
  BarChart3,
  Download,
  Eye,
  RefreshCw,
  Cpu,
  Layers,
  Settings
} from 'lucide-react';

export default function AdminDashboard() {
  const { authFetch } = useAuth();
  const [activeTab, setActiveTab] = useState('overview'); // 'overview' | 'users' | 'inspections' | 'analytics'
  const [overview, setOverview] = useState(null);
  const [users, setUsers] = useState([]);
  const [inspections, setInspections] = useState([]);
  const [analytics, setAnalytics] = useState(null);
  const [loading, setLoading] = useState(true);

  // User search/filter state
  const [userSearch, setUserSearch] = useState('');
  const [userRoleFilter, setUserRoleFilter] = useState('all');
  const [userStatusFilter, setUserStatusFilter] = useState('all');

  // Inspection search/filter state
  const [inspSearch, setInspSearch] = useState('');
  const [inspSeverityFilter, setInspSeverityFilter] = useState('all');

  // Create admin modal state
  const [showCreateAdmin, setShowCreateAdmin] = useState(false);
  const [adminUsername, setAdminUsername] = useState('');
  const [adminEmail, setAdminEmail] = useState('');
  const [adminFullName, setAdminFullName] = useState('');
  const [adminPassword, setAdminPassword] = useState('');
  const [adminCreateMsg, setAdminCreateMsg] = useState({ text: '', type: '' });
  const [adminCreateLoading, setAdminCreateLoading] = useState(false);
  const [downloadingId, setDownloadingId] = useState(null);

  const handleDownloadReport = async (inspId) => {
    setDownloadingId(inspId);
    try {
      const res = await authFetch(`/api/inspections/${inspId}/report`);
      if (!res.ok) throw new Error('Report download failed');
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `infrascan_report_${inspId}.csv`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    } catch (err) {
      alert('Failed to download report: ' + err.message);
    } finally {
      setDownloadingId(null);
    }
  };

  const fetchOverview = async () => {
    try {
      const res = await authFetch('/api/admin/overview');
      if (res.ok) {
        const json = await res.json();
        setOverview(json);
      }
    } catch (e) {
      console.error(e);
    }
  };

  const fetchUsers = async () => {
    try {
      const url = `/api/admin/users?search=${encodeURIComponent(userSearch)}&role=${userRoleFilter}&status=${userStatusFilter}`;
      const res = await authFetch(url);
      if (res.ok) {
        const json = await res.json();
        setUsers(json);
      }
    } catch (e) {
      console.error(e);
    }
  };

  const fetchInspections = async () => {
    try {
      const url = `/api/admin/inspections?search=${encodeURIComponent(inspSearch)}&severity=${inspSeverityFilter}`;
      const res = await authFetch(url);
      if (res.ok) {
        const json = await res.json();
        setInspections(json);
      }
    } catch (e) {
      console.error(e);
    }
  };

  const fetchAnalytics = async () => {
    try {
      const res = await authFetch('/api/admin/analytics');
      if (res.ok) {
        const json = await res.json();
        setAnalytics(json);
      }
    } catch (e) {
      console.error(e);
    }
  };

  useEffect(() => {
    setLoading(true);
    Promise.all([fetchOverview(), fetchUsers(), fetchInspections(), fetchAnalytics()])
      .finally(() => setLoading(false));
  }, []);

  const handleToggleUserStatus = async (userId, currentStatus) => {
    const nextStatus = currentStatus === 'active' ? 'inactive' : 'active';
    if (!window.confirm(`Are you sure you want to mark this user as ${nextStatus}?`)) {
      return;
    }

    try {
      const res = await authFetch(`/api/admin/users/${userId}/status`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ status: nextStatus })
      });
      if (res.ok) {
        fetchUsers();
        fetchOverview();
      } else {
        const err = await res.json();
        alert(err.detail || 'Failed to update status');
      }
    } catch (e) {
      console.error(e);
    }
  };

  const handleCreateAdminSubmit = async (e) => {
    e.preventDefault();
    setAdminCreateLoading(true);
    setAdminCreateMsg({ text: '', type: '' });

    try {
      const res = await authFetch('/api/admin/users/create-admin', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          username: adminUsername,
          email: adminEmail,
          password: adminPassword,
          full_name: adminFullName
        })
      });

      const data = await res.json();
      if (!res.ok) {
        throw new Error(data.detail || 'Failed to create admin');
      }

      setAdminCreateMsg({ text: 'New Administrator created successfully!', type: 'success' });
      setAdminUsername('');
      setAdminEmail('');
      setAdminFullName('');
      setAdminPassword('');
      fetchUsers();
      fetchOverview();
    } catch (err) {
      setAdminCreateMsg({ text: err.message, type: 'error' });
    } finally {
      setAdminCreateLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <div className="w-10 h-10 border-4 border-amber-500 border-t-transparent rounded-full animate-spin"></div>
      </div>
    );
  }

  const userStats = overview?.user_statistics || { total_users: 0, active_users: 0, inactive_users: 0, admin_count: 0 };
  const inspStats = overview?.inspection_statistics || { total_inspections: 0, cracked_inspections: 0, critical_inspections: 0, total_assets: 0 };

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8">
      {/* Header Banner */}
      <div className="glass-card p-6 rounded-2xl border-l-4 border-l-amber-500 shadow-xl flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <span className="px-2.5 py-0.5 rounded-full text-[11px] font-black uppercase tracking-wider bg-amber-500/20 text-amber-300 border border-amber-500/30">
              Admin Control Center
            </span>
            <span className="text-xs text-slate-400">System Management & Governance</span>
          </div>
          <h1 className="text-2xl font-black text-white tracking-tight mt-1">
            InfraScan Enterprise Administration
          </h1>
          <p className="text-xs text-slate-400 mt-1">
            Authorized oversight of civil inspectors, structural inspection assets, AI models, and damage intelligence.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={() => {
              setLoading(true);
              Promise.all([fetchOverview(), fetchUsers(), fetchInspections(), fetchAnalytics()]).finally(() => setLoading(false));
            }}
            className="px-3.5 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-xs font-semibold text-slate-200 border border-slate-700 transition flex items-center gap-1.5"
          >
            <RefreshCw className="w-3.5 h-3.5" />
            Refresh Data
          </button>
          <button
            onClick={() => setShowCreateAdmin(true)}
            className="px-4 py-2 rounded-xl bg-gradient-to-r from-amber-600 to-orange-600 hover:from-amber-500 hover:to-orange-500 text-xs font-bold text-white shadow-lg shadow-amber-600/20 transition flex items-center gap-1.5"
          >
            <UserPlus className="w-4 h-4" />
            Add Administrator
          </button>
        </div>
      </div>

      {/* Navigation Tabs */}
      <div className="flex items-center gap-2 border-b border-slate-800 pb-2 overflow-x-auto">
        {[
          { id: 'overview', label: 'System Overview', icon: Activity },
          { id: 'users', label: `User Management (${userStats.total_users})`, icon: Users },
          { id: 'inspections', label: `All Inspections (${inspStats.total_inspections})`, icon: FileText },
          { id: 'analytics', label: 'System Analytics', icon: BarChart3 }
        ].map(tab => {
          const Icon = tab.icon;
          const isActive = activeTab === tab.id;
          return (
            <button
              key={tab.id}
              onClick={() => {
                setActiveTab(tab.id);
                if (tab.id === 'users') fetchUsers();
                if (tab.id === 'inspections') fetchInspections();
                if (tab.id === 'analytics') fetchAnalytics();
              }}
              className={`px-4 py-2.5 rounded-xl text-xs font-bold transition flex items-center gap-2 whitespace-nowrap ${
                isActive
                  ? 'bg-amber-500/15 text-amber-300 border border-amber-500/30 shadow-sm'
                  : 'text-slate-400 hover:text-white hover:bg-slate-800/60'
              }`}
            >
              <Icon className="w-4 h-4" />
              {tab.label}
            </button>
          );
        })}
      </div>

      {/* TAB 1: SYSTEM OVERVIEW */}
      {activeTab === 'overview' && (
        <div className="space-y-8">
          {/* Top Metric Cards */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">
            <div className="glass-card p-5 rounded-2xl border border-slate-800">
              <div className="flex items-center justify-between">
                <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Registered Users</span>
                <div className="p-2 rounded-xl bg-blue-500/10 text-blue-400">
                  <Users className="w-5 h-5" />
                </div>
              </div>
              <div className="text-3xl font-black text-white mt-3 font-mono">{userStats.total_users}</div>
              <div className="text-[11px] text-slate-400 mt-1 flex items-center gap-2">
                <span className="text-emerald-400 font-bold">{userStats.active_users} active</span>
                <span>&bull;</span>
                <span className="text-slate-500">{userStats.inactive_users} inactive</span>
              </div>
            </div>

            <div className="glass-card p-5 rounded-2xl border border-slate-800">
              <div className="flex items-center justify-between">
                <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">System Inspections</span>
                <div className="p-2 rounded-xl bg-indigo-500/10 text-indigo-400">
                  <FileText className="w-5 h-5" />
                </div>
              </div>
              <div className="text-3xl font-black text-white mt-3 font-mono">{inspStats.total_inspections}</div>
              <span className="text-[11px] text-slate-500 mt-1 block">Total civil inspections recorded</span>
            </div>

            <div className="glass-card p-5 rounded-2xl border border-slate-800">
              <div className="flex items-center justify-between">
                <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Cracked Surfaces</span>
                <div className="p-2 rounded-xl bg-amber-500/10 text-amber-400">
                  <AlertTriangle className="w-5 h-5" />
                </div>
              </div>
              <div className="text-3xl font-black text-amber-400 mt-3 font-mono">{inspStats.cracked_inspections}</div>
              <span className="text-[11px] text-slate-500 mt-1 block">Positive structural damage findings</span>
            </div>

            <div className="glass-card p-5 rounded-2xl border border-slate-800">
              <div className="flex items-center justify-between">
                <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Critical Reviews</span>
                <div className="p-2 rounded-xl bg-rose-500/10 text-rose-400">
                  <Shield className="w-5 h-5" />
                </div>
              </div>
              <div className="text-3xl font-black text-rose-400 mt-3 font-mono">{inspStats.critical_inspections}</div>
              <span className="text-[11px] text-slate-500 mt-1 block">Urgent engineering attention required</span>
            </div>
          </div>

          {/* Model Status Card */}
          <div className="glass-card p-5 rounded-2xl border border-slate-800 bg-slate-900/40">
            <h2 className="text-sm font-bold text-white mb-3 flex items-center gap-2">
              <Cpu className="w-4 h-4 text-emerald-400" />
              Active AI Model Architecture & Status
            </h2>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-xs">
              <div className="p-4 rounded-xl bg-slate-900 border border-slate-800">
                <span className="text-slate-400 block font-semibold mb-1">Object Detection Head:</span>
                <div className="font-bold text-emerald-400 flex items-center gap-1.5">
                  <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse"></span>
                  YOLO11s (P3–P5 Architecture)
                </div>
                <span className="text-[11px] text-slate-500 block mt-1">Checkpoint: models/yolo_best.pt (640x640)</span>
              </div>

              <div className="p-4 rounded-xl bg-slate-900 border border-slate-800">
                <span className="text-slate-400 block font-semibold mb-1">Semantic Segmentation:</span>
                <div className="font-bold text-blue-400 flex items-center gap-1.5">
                  <span className="w-2 h-2 rounded-full bg-blue-400"></span>
                  U-Net Multi-Scale Skip Connections
                </div>
                <span className="text-[11px] text-slate-500 block mt-1">Morphological thin-fracture segmentation</span>
              </div>

              <div className="p-4 rounded-xl bg-slate-900 border border-slate-800">
                <span className="text-slate-400 block font-semibold mb-1">Binary Classification:</span>
                <div className="font-bold text-purple-400 flex items-center gap-1.5">
                  <span className="w-2 h-2 rounded-full bg-purple-400"></span>
                  Deep CNN Concrete Classifier
                </div>
                <span className="text-[11px] text-slate-500 block mt-1">Conv2D &rarr; BatchNorm &rarr; MaxPooling</span>
              </div>
            </div>
          </div>

          {/* Recent System Activity Table */}
          <div className="glass-card rounded-2xl border border-slate-800 overflow-hidden">
            <div className="p-5 border-b border-slate-800 flex items-center justify-between">
              <h2 className="text-sm font-bold text-white flex items-center gap-2">
                <Activity className="w-4 h-4 text-amber-400" />
                Recent System-Wide Inspection Activity
              </h2>
              <span className="text-xs text-slate-400">Latest submissions</span>
            </div>

            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead className="bg-slate-900/60 text-slate-400 uppercase tracking-wider font-semibold border-b border-slate-800">
                  <tr>
                    <th className="py-3 px-4">Insp ID</th>
                    <th className="py-3 px-4">Asset</th>
                    <th className="py-3 px-4">Inspector / User</th>
                    <th className="py-3 px-4">Date</th>
                    <th className="py-3 px-4">Severity</th>
                    <th className="py-3 px-4">Priority</th>
                    <th className="py-3 px-4 text-right">Action</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800/60 text-slate-300">
                  {(overview?.recent_activity || []).map(item => (
                    <tr key={item.id} className="hover:bg-slate-800/40 transition">
                      <td className="py-3 px-4 font-mono font-bold text-white">#{item.id}</td>
                      <td className="py-3 px-4 font-semibold text-white">{item.asset_name}</td>
                      <td className="py-3 px-4">
                        <div className="font-semibold text-slate-200">{item.inspector_name}</div>
                        <div className="text-[10px] text-slate-500">@{item.username}</div>
                      </td>
                      <td className="py-3 px-4 text-slate-400 whitespace-nowrap">
                        {item.timestamp ? new Date(item.timestamp).toLocaleString() : 'N/A'}
                      </td>
                      <td className="py-3 px-4">
                        <SeverityBadge severity={item.severity_level} />
                      </td>
                      <td className="py-3 px-4">
                        <PriorityBadge priority={item.priority_level} />
                      </td>
                      <td className="py-3 px-4 text-right">
                        <Link
                          to={`/inspections/${item.id}`}
                          className="inline-flex items-center gap-1 px-2.5 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-[11px] font-semibold text-slate-200 border border-slate-700 transition"
                        >
                          <Eye className="w-3 h-3 text-blue-400" />
                          View
                        </Link>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {/* TAB 2: USER MANAGEMENT */}
      {activeTab === 'users' && (
        <div className="space-y-6">
          {/* User Filters */}
          <div className="glass-card p-4 rounded-xl border border-slate-800 flex flex-col sm:flex-row items-center justify-between gap-3">
            <div className="relative w-full sm:w-80">
              <input
                type="text"
                placeholder="Search username, email, full name..."
                value={userSearch}
                onChange={e => setUserSearch(e.target.value)}
                onKeyDown={e => e.key === 'Enter' && fetchUsers()}
                className="w-full bg-slate-900 border border-slate-700 rounded-lg pl-9 pr-3 py-2 text-xs text-white focus:outline-none focus:border-amber-500"
              />
              <Search className="w-4 h-4 text-slate-500 absolute left-3 top-2.5 pointer-events-none" />
            </div>

            <div className="flex items-center gap-3 w-full sm:w-auto">
              <select
                value={userRoleFilter}
                onChange={e => setUserRoleFilter(e.target.value)}
                className="bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-xs text-white focus:outline-none"
              >
                <option value="all">All Roles</option>
                <option value="user">Registered User</option>
                <option value="admin">Administrator</option>
              </select>

              <select
                value={userStatusFilter}
                onChange={e => setUserStatusFilter(e.target.value)}
                className="bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-xs text-white focus:outline-none"
              >
                <option value="all">All Statuses</option>
                <option value="active">Active Only</option>
                <option value="inactive">Inactive Only</option>
              </select>

              <button
                onClick={fetchUsers}
                className="px-3 py-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-xs font-semibold text-slate-200 border border-slate-700 transition"
              >
                Filter
              </button>
            </div>
          </div>

          {/* User Table */}
          <div className="glass-card rounded-2xl border border-slate-800 overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead className="bg-slate-900/60 text-slate-400 uppercase tracking-wider font-semibold border-b border-slate-800">
                  <tr>
                    <th className="py-3 px-4">User ID</th>
                    <th className="py-3 px-4">Inspector / Account</th>
                    <th className="py-3 px-4">Email</th>
                    <th className="py-3 px-4">Role</th>
                    <th className="py-3 px-4">Status</th>
                    <th className="py-3 px-4">Inspections</th>
                    <th className="py-3 px-4">Last Login</th>
                    <th className="py-3 px-4 text-right">Access Management</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800/60 text-slate-300">
                  {users.map(u => (
                    <tr key={u.id} className="hover:bg-slate-800/40 transition">
                      <td className="py-3 px-4 font-mono font-bold text-white">#{u.id}</td>
                      <td className="py-3 px-4">
                        <div className="font-bold text-white">{u.full_name || u.username}</div>
                        <div className="text-[10px] text-slate-500 font-mono">@{u.username}</div>
                      </td>
                      <td className="py-3 px-4 text-slate-400">{u.email}</td>
                      <td className="py-3 px-4">
                        <span
                          className={`px-2.5 py-1 rounded-full text-[10px] font-bold ${
                            u.role === 'admin'
                              ? 'bg-amber-500/20 text-amber-300 border border-amber-500/30'
                              : 'bg-blue-500/20 text-blue-300 border border-blue-500/30'
                          }`}
                        >
                          {u.role.toUpperCase()}
                        </span>
                      </td>
                      <td className="py-3 px-4">
                        <span
                          className={`px-2.5 py-1 rounded-full text-[10px] font-bold flex items-center gap-1 w-fit ${
                            u.status === 'active'
                              ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/30'
                              : 'bg-rose-500/20 text-rose-300 border border-rose-500/30'
                          }`}
                        >
                          {u.status === 'active' ? (
                            <>
                              <span className="w-1.5 h-1.5 rounded-full bg-emerald-400"></span>
                              Active
                            </>
                          ) : (
                            <>
                              <span className="w-1.5 h-1.5 rounded-full bg-rose-400"></span>
                              Inactive
                            </>
                          )}
                        </span>
                      </td>
                      <td className="py-3 px-4 font-mono font-bold text-white">
                        {u.inspection_count}
                      </td>
                      <td className="py-3 px-4 text-slate-500 whitespace-nowrap">
                        {u.last_login ? new Date(u.last_login).toLocaleDateString() : 'Never'}
                      </td>
                      <td className="py-3 px-4 text-right">
                        <button
                          onClick={() => handleToggleUserStatus(u.id, u.status)}
                          className={`px-3 py-1.5 rounded-lg text-xs font-bold transition ${
                            u.status === 'active'
                              ? 'bg-rose-500/10 hover:bg-rose-500/20 text-rose-400 border border-rose-500/30'
                              : 'bg-emerald-500/10 hover:bg-emerald-500/20 text-emerald-400 border border-emerald-500/30'
                          }`}
                        >
                          {u.status === 'active' ? 'Deactivate' : 'Reactivate'}
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {/* TAB 3: ALL INSPECTIONS */}
      {activeTab === 'inspections' && (
        <div className="space-y-6">
          <div className="glass-card p-4 rounded-xl border border-slate-800 flex flex-col sm:flex-row items-center justify-between gap-3">
            <div className="relative w-full sm:w-80">
              <input
                type="text"
                placeholder="Search asset, inspector, notes..."
                value={inspSearch}
                onChange={e => setInspSearch(e.target.value)}
                onKeyDown={e => e.key === 'Enter' && fetchInspections()}
                className="w-full bg-slate-900 border border-slate-700 rounded-lg pl-9 pr-3 py-2 text-xs text-white focus:outline-none focus:border-amber-500"
              />
              <Search className="w-4 h-4 text-slate-500 absolute left-3 top-2.5 pointer-events-none" />
            </div>

            <div className="flex items-center gap-3 w-full sm:w-auto">
              <select
                value={inspSeverityFilter}
                onChange={e => setInspSeverityFilter(e.target.value)}
                className="bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-xs text-white focus:outline-none"
              >
                <option value="all">All Severities</option>
                <option value="Minor">Minor</option>
                <option value="Moderate">Moderate</option>
                <option value="Severe">Severe</option>
                <option value="Critical">Critical</option>
              </select>

              <button
                onClick={fetchInspections}
                className="px-3 py-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-xs font-semibold text-slate-200 border border-slate-700 transition"
              >
                Filter
              </button>
            </div>
          </div>

          <div className="glass-card rounded-2xl border border-slate-800 overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead className="bg-slate-900/60 text-slate-400 uppercase tracking-wider font-semibold border-b border-slate-800">
                  <tr>
                    <th className="py-3 px-4">ID</th>
                    <th className="py-3 px-4">Asset</th>
                    <th className="py-3 px-4">Author Account</th>
                    <th className="py-3 px-4">Date</th>
                    <th className="py-3 px-4">Crack Area</th>
                    <th className="py-3 px-4">Severity</th>
                    <th className="py-3 px-4">Priority</th>
                    <th className="py-3 px-4 text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800/60 text-slate-300">
                  {inspections.map(insp => (
                    <tr key={insp.id} className="hover:bg-slate-800/40 transition">
                      <td className="py-3 px-4 font-mono font-bold text-white">#{insp.id}</td>
                      <td className="py-3 px-4 font-semibold text-white">{insp.asset_name}</td>
                      <td className="py-3 px-4">
                        <div className="font-semibold text-slate-200">{insp.inspector_name}</div>
                        <div className="text-[10px] text-slate-500">@{insp.user_username}</div>
                      </td>
                      <td className="py-3 px-4 text-slate-400 whitespace-nowrap">
                        {insp.timestamp ? new Date(insp.timestamp).toLocaleDateString() : 'N/A'}
                      </td>
                      <td className="py-3 px-4 font-mono text-slate-300">
                        {insp.result?.crack_area_px ? `${insp.result.crack_area_px.toLocaleString()} px` : '0 px'}
                      </td>
                      <td className="py-3 px-4">
                        <SeverityBadge severity={insp.result?.severity_level} />
                      </td>
                      <td className="py-3 px-4">
                        <PriorityBadge priority={insp.result?.priority_level} />
                      </td>
                      <td className="py-3 px-4 text-right space-x-2 whitespace-nowrap">
                        <Link
                          to={`/inspections/${insp.id}`}
                          className="inline-flex items-center gap-1 px-2.5 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-[11px] font-semibold text-slate-200 border border-slate-700 transition"
                        >
                          <Eye className="w-3 h-3 text-blue-400" />
                          View
                        </Link>
                        <button
                          onClick={() => handleDownloadReport(insp.id)}
                          disabled={downloadingId === insp.id}
                          className="inline-flex items-center gap-1 px-2.5 py-1.5 rounded-lg bg-blue-600/20 hover:bg-blue-600/30 text-[11px] font-semibold text-blue-300 border border-blue-500/30 transition disabled:opacity-50"
                        >
                          <Download className="w-3 h-3" />
                          {downloadingId === insp.id ? '...' : 'CSV'}
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {/* TAB 4: SYSTEM ANALYTICS */}
      {activeTab === 'analytics' && (
        <div className="space-y-6">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {/* Severity Distribution */}
            <div className="glass-card p-6 rounded-2xl border border-slate-800">
              <h3 className="text-sm font-bold text-white mb-4 flex items-center gap-2">
                <AlertTriangle className="w-4 h-4 text-amber-400" />
                Damage Severity Distribution (Real DB Records)
              </h3>
              <div className="space-y-3">
                {Object.entries(analytics?.severity_distribution || {}).map(([level, count]) => (
                  <div key={level} className="flex items-center justify-between text-xs">
                    <span className="text-slate-300 font-semibold">{level}</span>
                    <div className="flex items-center gap-3">
                      <span className="font-mono font-bold text-white">{count}</span>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Maintenance Priority Distribution */}
            <div className="glass-card p-6 rounded-2xl border border-slate-800">
              <h3 className="text-sm font-bold text-white mb-4 flex items-center gap-2">
                <Shield className="w-4 h-4 text-blue-400" />
                Maintenance Priority Schedule
              </h3>
              <div className="space-y-3">
                {Object.entries(analytics?.priority_distribution || {}).map(([level, count]) => (
                  <div key={level} className="flex items-center justify-between text-xs">
                    <span className="text-slate-300 font-semibold">{level}</span>
                    <span className="font-mono font-bold text-white">{count}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>

          {/* Top Active Inspectors */}
          <div className="glass-card p-6 rounded-2xl border border-slate-800">
            <h3 className="text-sm font-bold text-white mb-4 flex items-center gap-2">
              <Users className="w-4 h-4 text-purple-400" />
              Inspector Activity Rankings
            </h3>
            <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-4">
              {(analytics?.top_inspectors || []).map((insp, idx) => (
                <div key={idx} className="p-4 rounded-xl bg-slate-900 border border-slate-800 flex items-center justify-between">
                  <div>
                    <span className="text-[11px] text-slate-500 font-bold block">RANK #{idx + 1}</span>
                    <span className="text-xs font-bold text-white">{insp.name}</span>
                  </div>
                  <span className="text-base font-black font-mono text-purple-400">{insp.count}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Create Admin Account Modal */}
      {showCreateAdmin && (
        <div className="fixed inset-0 z-50 bg-black/70 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="glass-card max-w-md w-full p-6 rounded-2xl border border-amber-500/40 shadow-2xl relative">
            <h2 className="text-lg font-bold text-white mb-2 flex items-center gap-2">
              <UserPlus className="w-5 h-5 text-amber-400" />
              Authorize New Administrator
            </h2>
            <p className="text-xs text-slate-400 mb-4">
              Create an additional administrator account with system-wide management privileges.
            </p>

            {adminCreateMsg.text && (
              <div
                className={`p-3 rounded-xl text-xs mb-4 ${
                  adminCreateMsg.type === 'success'
                    ? 'bg-emerald-500/10 text-emerald-300 border border-emerald-500/30'
                    : 'bg-rose-500/10 text-rose-300 border border-rose-500/30'
                }`}
              >
                {adminCreateMsg.text}
              </div>
            )}

            <form onSubmit={handleCreateAdminSubmit} className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-slate-400 mb-1">Full Name</label>
                <input
                  type="text"
                  required
                  placeholder="e.g. Chief Structural Engineer"
                  value={adminFullName}
                  onChange={e => setAdminFullName(e.target.value)}
                  className="w-full bg-slate-900 border border-slate-700 rounded-xl px-3 py-2 text-sm text-white focus:outline-none focus:border-amber-500"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-400 mb-1">Admin Username</label>
                <input
                  type="text"
                  required
                  placeholder="admin_username"
                  value={adminUsername}
                  onChange={e => setAdminUsername(e.target.value)}
                  className="w-full bg-slate-900 border border-slate-700 rounded-xl px-3 py-2 text-sm text-white focus:outline-none focus:border-amber-500"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-400 mb-1">Email Address</label>
                <input
                  type="email"
                  required
                  placeholder="admin@infrascan.ai"
                  value={adminEmail}
                  onChange={e => setAdminEmail(e.target.value)}
                  className="w-full bg-slate-900 border border-slate-700 rounded-xl px-3 py-2 text-sm text-white focus:outline-none focus:border-amber-500"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-400 mb-1">Admin Password</label>
                <input
                  type="password"
                  required
                  placeholder="Min 6 characters"
                  value={adminPassword}
                  onChange={e => setAdminPassword(e.target.value)}
                  className="w-full bg-slate-900 border border-slate-700 rounded-xl px-3 py-2 text-sm text-white focus:outline-none focus:border-amber-500"
                />
              </div>

              <div className="flex items-center justify-end gap-3 pt-3">
                <button
                  type="button"
                  onClick={() => setShowCreateAdmin(false)}
                  className="px-4 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-xs font-semibold text-slate-300 transition"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={adminCreateLoading}
                  className="px-4 py-2 rounded-xl bg-gradient-to-r from-amber-600 to-orange-600 hover:from-amber-500 hover:to-orange-500 text-xs font-bold text-white shadow-md transition disabled:opacity-50"
                >
                  {adminCreateLoading ? 'Creating...' : 'Create Administrator'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
