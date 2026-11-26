import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import SeverityBadge from '../components/SeverityBadge';
import PriorityBadge from '../components/PriorityBadge';

export default function Dashboard() {
  const [stats, setStats] = useState(null);
  const [analytics, setAnalytics] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([
      fetch('/api/dashboard/stats').then(r => r.json()),
      fetch('/api/analytics/summary').then(r => r.json())
    ]).then(([s, a]) => {
      setStats(s);
      setAnalytics(a);
      setLoading(false);
    }).catch(err => {
      console.error(err);
      setLoading(false);
    });
  }, []);

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <div className="w-10 h-10 border-4 border-blue-500 border-t-transparent rounded-full animate-spin"></div>
      </div>
    );
  }

  const sevCounts = stats?.severity_distribution || {};
  const prioCounts = stats?.priority_distribution || {};
  const defectCats = stats?.defect_categories || {};

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8">
      {/* Top Banner */}
      <div className="glass-card p-6 rounded-2xl flex flex-col md:flex-row items-start md:items-center justify-between gap-4 border-l-4 border-l-blue-500">
        <div>
          <h1 className="text-2xl font-black text-white tracking-tight flex items-center gap-2">
            Infrastructure Damage Intelligence Dashboard
          </h1>
          <p className="text-sm text-slate-400 mt-1">
            Automated crack detection, U-Net semantic segmentation, and rule-based maintenance prioritization.
          </p>
        </div>
        <div className="flex items-center gap-3">
          <Link to="/models" className="px-3.5 py-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-xs font-semibold text-slate-200 border border-slate-700 transition">
            View Model Benchmarks
          </Link>
          <Link to="/new-inspection" className="px-4 py-2 rounded-lg bg-blue-600 hover:bg-blue-500 text-xs font-semibold text-white shadow-md shadow-blue-500/20 transition">
            + New Inspection
          </Link>
        </div>
      </div>

      {/* Metric Cards Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">
        <div className="glass-card p-5 rounded-xl border border-slate-800">
          <span className="text-xs font-medium text-slate-400 uppercase tracking-wider">Total Inspections</span>
          <div className="mt-2 flex items-baseline gap-2">
            <span className="text-3xl font-extrabold text-white">{stats?.total_inspections || 0}</span>
            <span className="text-xs text-blue-400 font-medium">Logged</span>
          </div>
          <div className="mt-2 text-xs text-slate-400">Recorded across registered assets</div>
        </div>

        <div className="glass-card p-5 rounded-xl border border-slate-800">
          <span className="text-xs font-medium text-slate-400 uppercase tracking-wider">Infrastructure Assets</span>
          <div className="mt-2 flex items-baseline gap-2">
            <span className="text-3xl font-extrabold text-white">{stats?.total_assets || 0}</span>
            <span className="text-xs text-indigo-400 font-medium">Active</span>
          </div>
          <div className="mt-2 text-xs text-slate-400">Bridges, Tunnels, Roads, Walls</div>
        </div>

        <div className="glass-card p-5 rounded-xl border border-slate-800">
          <span className="text-xs font-medium text-slate-400 uppercase tracking-wider">Surface Defects Found</span>
          <div className="mt-2 flex items-baseline gap-2">
            <span className="text-3xl font-extrabold text-amber-400">{stats?.cracked_count || 0}</span>
            <span className="text-xs text-slate-400">/ {stats?.total_inspections || 0}</span>
          </div>
          <div className="mt-2 text-xs text-slate-400">Confirmed crack occurrences</div>
        </div>

        <div className="glass-card p-5 rounded-xl border border-slate-800">
          <span className="text-xs font-medium text-slate-400 uppercase tracking-wider">Urgent Reviews Required</span>
          <div className="mt-2 flex items-baseline gap-2">
            <span className="text-3xl font-extrabold text-rose-400">{analytics?.urgent_review_count || 0}</span>
            <span className="text-xs text-rose-500 font-semibold animate-pulse">Action Required</span>
          </div>
          <div className="mt-2 text-xs text-slate-400">Severity score &gt; 80 or high crack aperture</div>
        </div>
      </div>

      {/* Analytics Rows */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Severity Distribution */}
        <div className="glass-card p-6 rounded-xl border border-slate-800 space-y-4">
          <h2 className="text-base font-bold text-white flex items-center justify-between">
            Damage Severity Breakdown
            <span className="text-xs font-normal text-slate-400">5-Tier Scale</span>
          </h2>
          <div className="space-y-3 pt-2">
            {Object.entries(sevCounts).map(([level, count]) => {
              const total = stats?.total_inspections || 1;
              const pct = Math.round((count / total) * 100);
              let barColor = 'bg-slate-600';
              if (level.includes('No Visible')) barColor = 'bg-emerald-500';
              if (level.includes('Minor')) barColor = 'bg-blue-500';
              if (level.includes('Moderate')) barColor = 'bg-amber-500';
              if (level.includes('Severe')) barColor = 'bg-orange-500';
              if (level.includes('Critical')) barColor = 'bg-rose-500';

              return (
                <div key={level} className="space-y-1">
                  <div className="flex justify-between text-xs">
                    <span className="text-slate-300 font-medium">{level}</span>
                    <span className="text-slate-400 font-mono">{count} ({pct}%)</span>
                  </div>
                  <div className="w-full bg-slate-800 rounded-full h-2 overflow-hidden">
                    <div className={`${barColor} h-2 rounded-full transition-all duration-500`} style={{ width: `${pct}%` }}></div>
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Maintenance Priority */}
        <div className="glass-card p-6 rounded-xl border border-slate-800 space-y-4">
          <h2 className="text-base font-bold text-white flex items-center justify-between">
            Maintenance Priority Distribution
            <span className="text-xs font-normal text-slate-400">Rule-Based</span>
          </h2>
          <div className="space-y-3 pt-2">
            {Object.entries(prioCounts).map(([level, count]) => (
              <div key={level} className="flex items-center justify-between p-2.5 rounded-lg bg-slate-800/50 border border-slate-700/50">
                <span className="text-xs font-medium text-slate-200">{level}</span>
                <span className="text-xs font-mono font-bold text-white px-2 py-0.5 rounded bg-slate-700">{count}</span>
              </div>
            ))}
          </div>
        </div>

        {/* Crack Geometry Overview */}
        <div className="glass-card p-6 rounded-xl border border-slate-800 space-y-4">
          <h2 className="text-base font-bold text-white">Crack Geometry Benchmarks</h2>
          <div className="space-y-3 pt-2">
            <div className="p-3 rounded-lg bg-slate-800/40 border border-slate-700/40">
              <div className="text-xs text-slate-400">Mean Defect Area (Uncalibrated)</div>
              <div className="text-xl font-bold font-mono text-blue-400 mt-1">{analytics?.mean_crack_area_px || 0} px</div>
              <div className="text-[11px] text-slate-500 mt-0.5">Benchmark avg on CRACK500 test: 3,511 px</div>
            </div>

            <div className="p-3 rounded-lg bg-slate-800/40 border border-slate-700/40">
              <div className="text-xs text-slate-400">Mean Skeleton Trajectory Length</div>
              <div className="text-xl font-bold font-mono text-indigo-400 mt-1">{analytics?.mean_skeleton_length_px || 0} px</div>
              <div className="text-[11px] text-slate-500 mt-0.5">Benchmark avg on CRACK500 test: 321.6 px</div>
            </div>

            <div className="p-3 rounded-lg bg-slate-800/40 border border-slate-700/40">
              <div className="text-xs text-slate-400">Mean Estimated Crack Aperture Width</div>
              <div className="text-xl font-bold font-mono text-purple-400 mt-1">{analytics?.mean_crack_width_px || 0} px</div>
              <div className="text-[11px] text-slate-500 mt-0.5">Benchmark avg on CRACK500 test: 10.3 px</div>
            </div>
          </div>
        </div>
      </div>

      {/* Recent Inspections Table */}
      <div className="glass-card rounded-2xl border border-slate-800 overflow-hidden">
        <div className="p-5 border-b border-slate-800 flex items-center justify-between">
          <div>
            <h2 className="text-lg font-bold text-white">Recent Infrastructure Inspections</h2>
            <p className="text-xs text-slate-400 mt-0.5">Latest evaluations analyzed with AI computer vision pipelines</p>
          </div>
          <Link to="/inspections" className="text-xs font-semibold text-blue-400 hover:text-blue-300 transition">
            View All &rarr;
          </Link>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm text-slate-300">
            <thead className="bg-slate-800/60 text-xs font-semibold text-slate-400 uppercase tracking-wider border-b border-slate-700/60">
              <tr>
                <th className="py-3 px-4">Preview</th>
                <th className="py-3 px-4">Asset / Structure</th>
                <th className="py-3 px-4">Inspection Date</th>
                <th className="py-3 px-4">Defect Classification</th>
                <th className="py-3 px-4">Severity Level</th>
                <th className="py-3 px-4">Priority</th>
                <th className="py-3 px-4 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/80">
              {(stats?.recent_inspections || []).map(insp => {
                const res = insp.result;
                return (
                  <tr key={insp.id} className="hover:bg-slate-800/30 transition">
                    <td className="py-3 px-4">
                      {res?.original_url ? (
                        <img src={res.original_url} alt="" className="w-12 h-12 rounded-lg object-cover border border-slate-700" />
                      ) : (
                        <div className="w-12 h-12 rounded-lg bg-slate-800 border border-slate-700 flex items-center justify-center text-xs text-slate-500">N/A</div>
                      )}
                    </td>
                    <td className="py-3 px-4">
                      <div className="font-semibold text-white">{insp.asset_name}</div>
                      <div className="text-xs text-slate-400">{insp.inspector_name}</div>
                    </td>
                    <td className="py-3 px-4 text-xs font-mono text-slate-400">
                      {new Date(insp.timestamp).toLocaleDateString()}
                    </td>
                    <td className="py-3 px-4">
                      {res?.crack_detected ? (
                        <span className="inline-flex items-center gap-1 text-xs font-medium text-rose-400">
                          <span className="w-1.5 h-1.5 rounded-full bg-rose-400"></span>
                          Crack Detected ({(res.crack_probability * 100).toFixed(1)}%)
                        </span>
                      ) : (
                        <span className="inline-flex items-center gap-1 text-xs font-medium text-emerald-400">
                          <span className="w-1.5 h-1.5 rounded-full bg-emerald-400"></span>
                          Normal Surface
                        </span>
                      )}
                      <div className="text-[11px] text-slate-500">{res?.surface_type}</div>
                    </td>
                    <td className="py-3 px-4">
                      <SeverityBadge level={res?.severity_level} score={res?.severity_score} />
                    </td>
                    <td className="py-3 px-4">
                      <PriorityBadge level={res?.priority_level} />
                    </td>
                    <td className="py-3 px-4 text-right">
                      <Link
                        to={`/inspections/${insp.id}`}
                        className="px-3 py-1.5 rounded-md bg-slate-800 hover:bg-slate-700 text-xs font-medium text-blue-400 hover:text-white border border-slate-700 transition"
                      >
                        Inspect &rarr;
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
  );
}
