import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import SeverityBadge from '../components/SeverityBadge';
import PriorityBadge from '../components/PriorityBadge';
import { 
  ShieldCheck, 
  Upload, 
  FileText, 
  Clock, 
  AlertTriangle, 
  CheckCircle2, 
  Download, 
  User, 
  Settings, 
  Eye, 
  Layers,
  Sparkles
} from 'lucide-react';

export default function UserDashboard() {
  const { user, authFetch, updateProfile } = useAuth();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [showProfileModal, setShowProfileModal] = useState(false);
  const [profileName, setProfileName] = useState(user?.full_name || '');
  const [profileEmail, setProfileEmail] = useState(user?.email || '');
  const [currentPassword, setCurrentPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [profileMsg, setProfileMsg] = useState({ text: '', type: '' });
  const [profileLoading, setProfileLoading] = useState(false);
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

  useEffect(() => {
    authFetch('/api/dashboard/user-stats')
      .then(res => res.json())
      .then(json => {
        setData(json);
        setLoading(false);
      })
      .catch(err => {
        console.error(err);
        setLoading(false);
      });
  }, []);

  const handleUpdateProfile = async (e) => {
    e.preventDefault();
    setProfileLoading(true);
    setProfileMsg({ text: '', type: '' });

    try {
      const res = await authFetch('/api/auth/profile', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          full_name: profileName,
          email: profileEmail,
          current_password: currentPassword || undefined,
          new_password: newPassword || undefined
        })
      });

      const updated = await res.json();
      if (!res.ok) {
        throw new Error(updated.detail || 'Profile update failed');
      }

      updateProfile(updated);
      setProfileMsg({ text: 'Profile updated successfully!', type: 'success' });
      setCurrentPassword('');
      setNewPassword('');
    } catch (err) {
      setProfileMsg({ text: err.message || 'Error updating profile', type: 'error' });
    } finally {
      setProfileLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <div className="w-10 h-10 border-4 border-blue-500 border-t-transparent rounded-full animate-spin"></div>
      </div>
    );
  }

  const stats = data?.stats || { total_inspections: 0, cracked_count: 0, critical_count: 0, sound_count: 0 };
  const recentInspections = data?.recent_inspections || [];

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8">
      {/* Welcome Section Banner */}
      <div className="glass-card p-6 rounded-2xl flex flex-col md:flex-row items-start md:items-center justify-between gap-6 border-l-4 border-l-blue-500 shadow-xl">
        <div className="flex items-center gap-4">
          <div className="w-14 h-14 rounded-2xl bg-gradient-to-tr from-blue-600 to-indigo-500 flex items-center justify-center text-white shadow-lg shadow-blue-500/20 font-black text-xl">
            {user?.full_name ? user.full_name[0].toUpperCase() : 'U'}
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-2xl font-black text-white tracking-tight">
                Welcome, {user?.full_name || user?.username}!
              </h1>
              <span className="px-2.5 py-0.5 rounded-full text-[11px] font-bold bg-blue-500/20 text-blue-400 border border-blue-500/30">
                Registered Inspector
              </span>
            </div>
            <p className="text-xs text-slate-400 mt-1 flex items-center gap-3">
              <span>Inspector Account: <strong>{user?.username}</strong></span>
              <span>&bull;</span>
              <span>{user?.email}</span>
            </p>
          </div>
        </div>

        <div className="flex items-center gap-3 w-full md:w-auto">
          <button
            onClick={() => setShowProfileModal(true)}
            className="flex-1 md:flex-none px-4 py-2.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-xs font-semibold text-slate-200 border border-slate-700 transition flex items-center justify-center gap-2"
          >
            <Settings className="w-4 h-4 text-slate-400" />
            Profile Settings
          </button>
          <Link
            to="/new-inspection"
            className="flex-1 md:flex-none px-5 py-2.5 rounded-xl bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 text-xs font-bold text-white shadow-lg shadow-blue-500/25 transition flex items-center justify-center gap-2"
          >
            <Upload className="w-4 h-4" />
            New Inspection
          </Link>
        </div>
      </div>

      {/* Inspection Summary Stats Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">
        <div className="glass-card p-5 rounded-2xl border border-slate-800">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">My Total Inspections</span>
            <div className="p-2 rounded-xl bg-blue-500/10 text-blue-400">
              <FileText className="w-5 h-5" />
            </div>
          </div>
          <div className="text-3xl font-black text-white mt-3 font-mono">{stats.total_inspections}</div>
          <span className="text-[11px] text-slate-500 mt-1 block">Inspections authored by your account</span>
        </div>

        <div className="glass-card p-5 rounded-2xl border border-slate-800">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Damaged Surfaces</span>
            <div className="p-2 rounded-xl bg-amber-500/10 text-amber-400">
              <AlertTriangle className="w-5 h-5" />
            </div>
          </div>
          <div className="text-3xl font-black text-amber-400 mt-3 font-mono">{stats.cracked_count}</div>
          <span className="text-[11px] text-slate-500 mt-1 block">Surfaces with detected crack defects</span>
        </div>

        <div className="glass-card p-5 rounded-2xl border border-slate-800">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Critical Reviews</span>
            <div className="p-2 rounded-xl bg-rose-500/10 text-rose-400">
              <ShieldCheck className="w-5 h-5" />
            </div>
          </div>
          <div className="text-3xl font-black text-rose-400 mt-3 font-mono">{stats.critical_count}</div>
          <span className="text-[11px] text-slate-500 mt-1 block">Require urgent engineering review</span>
        </div>

        <div className="glass-card p-5 rounded-2xl border border-slate-800">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Sound Surfaces</span>
            <div className="p-2 rounded-xl bg-emerald-500/10 text-emerald-400">
              <CheckCircle2 className="w-5 h-5" />
            </div>
          </div>
          <div className="text-3xl font-black text-emerald-400 mt-3 font-mono">{stats.sound_count}</div>
          <span className="text-[11px] text-slate-500 mt-1 block">No visible structural damage</span>
        </div>
      </div>

      {/* Model Status Card */}
      <div className="glass-card p-5 rounded-2xl border border-indigo-500/20 bg-indigo-950/20 flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <div className="p-2.5 rounded-xl bg-indigo-500/20 text-indigo-400">
            <Sparkles className="w-5 h-5" />
          </div>
          <div>
            <h3 className="text-sm font-bold text-white flex items-center gap-2">
              Active YOLO11s Detection Engine
              <span className="text-[10px] px-2 py-0.5 rounded-full bg-emerald-500/20 text-emerald-300 font-semibold border border-emerald-500/30">
                CRACK500 Trained
              </span>
            </h3>
            <p className="text-xs text-slate-400 mt-0.5">
              Improved P3–P5 architecture (imgsz=640) with morphological closing and proximity merging.
            </p>
          </div>
        </div>
        <Link
          to="/models"
          className="text-xs font-semibold text-indigo-300 hover:text-white px-3 py-1.5 rounded-lg bg-indigo-900/40 border border-indigo-700/50 transition shrink-0"
        >
          View Model Evaluation &rarr;
        </Link>
      </div>

      {/* My Recent Inspections Table */}
      <div className="glass-card rounded-2xl border border-slate-800 overflow-hidden">
        <div className="p-5 border-b border-slate-800 flex items-center justify-between">
          <div>
            <h2 className="text-base font-bold text-white flex items-center gap-2">
              <Clock className="w-4 h-4 text-blue-400" />
              My Recent Inspections
            </h2>
            <p className="text-xs text-slate-400 mt-0.5">
              Private inspection logs associated with your account.
            </p>
          </div>
          <Link
            to="/inspections"
            className="text-xs font-semibold text-blue-400 hover:text-blue-300 transition"
          >
            View All ({stats.total_inspections}) &rarr;
          </Link>
        </div>

        {recentInspections.length === 0 ? (
          <div className="p-12 text-center text-slate-400">
            <Layers className="w-10 h-10 text-slate-600 mx-auto mb-3" />
            <p className="text-sm font-semibold text-slate-300">No inspections performed yet</p>
            <p className="text-xs text-slate-500 mt-1">Upload your first concrete damage image to get started.</p>
            <Link
              to="/new-inspection"
              className="inline-flex items-center gap-2 mt-4 px-4 py-2 rounded-xl bg-blue-600 hover:bg-blue-500 text-xs font-bold text-white transition"
            >
              <Upload className="w-3.5 h-3.5" />
              Upload Inspection Image
            </Link>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-slate-900/60 text-slate-400 uppercase tracking-wider font-semibold border-b border-slate-800">
                <tr>
                  <th className="py-3 px-4">ID</th>
                  <th className="py-3 px-4">Asset</th>
                  <th className="py-3 px-4">Date</th>
                  <th className="py-3 px-4">Defects</th>
                  <th className="py-3 px-4">Severity</th>
                  <th className="py-3 px-4">Priority</th>
                  <th className="py-3 px-4 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60 text-slate-300">
                {recentInspections.map((insp) => (
                  <tr key={insp.id} className="hover:bg-slate-800/40 transition">
                    <td className="py-3 px-4 font-mono font-bold text-white">#{insp.id}</td>
                    <td className="py-3 px-4">
                      <div className="font-semibold text-white">{insp.asset_name}</div>
                      <div className="text-[10px] text-slate-500 truncate max-w-[150px]">{insp.notes || 'No notes'}</div>
                    </td>
                    <td className="py-3 px-4 text-slate-400 whitespace-nowrap">
                      {insp.timestamp ? new Date(insp.timestamp).toLocaleDateString() : 'N/A'}
                    </td>
                    <td className="py-3 px-4">
                      {insp.result?.crack_detected ? (
                        <span className="font-bold text-amber-400">
                          {insp.result.defect_count} crack zone(s)
                        </span>
                      ) : (
                        <span className="text-emerald-400 font-semibold">Sound Surface</span>
                      )}
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
                        Details
                      </Link>
                      <button
                        onClick={() => handleDownloadReport(insp.id)}
                        disabled={downloadingId === insp.id}
                        className="inline-flex items-center gap-1 px-2.5 py-1.5 rounded-lg bg-blue-600/20 hover:bg-blue-600/30 text-[11px] font-semibold text-blue-300 border border-blue-500/30 transition disabled:opacity-50"
                      >
                        <Download className="w-3 h-3" />
                        {downloadingId === insp.id ? '...' : 'Report'}
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Profile Settings Modal */}
      {showProfileModal && (
        <div className="fixed inset-0 z-50 bg-black/70 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="glass-card max-w-md w-full p-6 rounded-2xl border border-slate-700 shadow-2xl relative">
            <h2 className="text-lg font-bold text-white mb-4 flex items-center gap-2">
              <User className="w-5 h-5 text-blue-400" />
              Inspector Profile Settings
            </h2>

            {profileMsg.text && (
              <div
                className={`p-3 rounded-xl text-xs mb-4 flex items-center gap-2 ${
                  profileMsg.type === 'success'
                    ? 'bg-emerald-500/10 text-emerald-300 border border-emerald-500/30'
                    : 'bg-rose-500/10 text-rose-300 border border-rose-500/30'
                }`}
              >
                <span>{profileMsg.text}</span>
              </div>
            )}

            <form onSubmit={handleUpdateProfile} className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-slate-400 mb-1">Full Name</label>
                <input
                  type="text"
                  value={profileName}
                  onChange={(e) => setProfileName(e.target.value)}
                  className="w-full bg-slate-900 border border-slate-700 rounded-xl px-3 py-2 text-sm text-white focus:outline-none focus:border-blue-500"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-400 mb-1">Email Address</label>
                <input
                  type="email"
                  value={profileEmail}
                  onChange={(e) => setProfileEmail(e.target.value)}
                  className="w-full bg-slate-900 border border-slate-700 rounded-xl px-3 py-2 text-sm text-white focus:outline-none focus:border-blue-500"
                />
              </div>

              <div className="pt-2 border-t border-slate-800">
                <span className="text-xs font-semibold text-slate-400 block mb-2">Change Password (optional)</span>
                <div className="space-y-2">
                  <input
                    type="password"
                    placeholder="Current Password"
                    value={currentPassword}
                    onChange={(e) => setCurrentPassword(e.target.value)}
                    className="w-full bg-slate-900 border border-slate-700 rounded-xl px-3 py-2 text-sm text-white focus:outline-none focus:border-blue-500"
                  />
                  <input
                    type="password"
                    placeholder="New Password (min 6 chars)"
                    value={newPassword}
                    onChange={(e) => setNewPassword(e.target.value)}
                    className="w-full bg-slate-900 border border-slate-700 rounded-xl px-3 py-2 text-sm text-white focus:outline-none focus:border-blue-500"
                  />
                </div>
              </div>

              <div className="flex items-center justify-end gap-3 pt-3">
                <button
                  type="button"
                  onClick={() => setShowProfileModal(false)}
                  className="px-4 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-xs font-semibold text-slate-300 transition"
                >
                  Close
                </button>
                <button
                  type="submit"
                  disabled={profileLoading}
                  className="px-4 py-2 rounded-xl bg-blue-600 hover:bg-blue-500 text-xs font-bold text-white transition disabled:opacity-50"
                >
                  {profileLoading ? 'Saving...' : 'Save Changes'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
