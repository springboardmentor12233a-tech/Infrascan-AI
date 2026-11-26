import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import SeverityBadge from '../components/SeverityBadge';
import PriorityBadge from '../components/PriorityBadge';
import { Download, Eye } from 'lucide-react';

export default function InspectionsList() {
  const { authFetch, isAdmin } = useAuth();
  const [inspections, setInspections] = useState([]);
  const [filterSeverity, setFilterSeverity] = useState('all');
  const [searchTerm, setSearchTerm] = useState('');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    authFetch('/api/inspections')
      .then(r => r.json())
      .then(data => {
        setInspections(Array.isArray(data) ? data : []);
        setLoading(false);
      })
      .catch(err => {
        console.error(err);
        setLoading(false);
      });
  }, []);

  const filtered = inspections.filter(insp => {
    const res = insp.result;
    const matchesSev = filterSeverity === 'all' || (res && res.severity_level.toLowerCase().includes(filterSeverity.toLowerCase()));
    const matchesSearch = !searchTerm || (
      (insp.asset_name && insp.asset_name.toLowerCase().includes(searchTerm.toLowerCase())) ||
      (insp.inspector_name && insp.inspector_name.toLowerCase().includes(searchTerm.toLowerCase())) ||
      (res && res.surface_type && res.surface_type.toLowerCase().includes(searchTerm.toLowerCase()))
    );
    return matchesSev && matchesSearch;
  });

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-6">
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-black text-white tracking-tight">Inspection Records</h1>
          <p className="text-sm text-slate-400 mt-1">History of all structural inspections and automated AI damage assessments.</p>
        </div>
        <Link
          to="/new-inspection"
          className="px-4 py-2 rounded-lg bg-blue-600 hover:bg-blue-500 text-xs font-semibold text-white shadow-md shadow-blue-500/20 transition"
        >
          + Perform New Inspection
        </Link>
      </div>

      {/* Filter and Search Bar */}
      <div className="glass-card p-4 rounded-xl border border-slate-800 flex flex-col sm:flex-row items-center justify-between gap-3">
        <input
          type="text"
          placeholder="Search by asset, inspector, surface type..."
          value={searchTerm}
          onChange={e => setSearchTerm(e.target.value)}
          className="w-full sm:w-80 bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-xs text-white focus:outline-none focus:border-blue-500"
        />

        <div className="flex items-center gap-2 w-full sm:w-auto">
          <span className="text-xs text-slate-400">Severity:</span>
          <select
            value={filterSeverity}
            onChange={e => setFilterSeverity(e.target.value)}
            className="bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-xs text-white focus:outline-none focus:border-blue-500"
          >
            <option value="all">All Severities</option>
            <option value="no visible">No Visible Damage</option>
            <option value="minor">Minor Damage</option>
            <option value="moderate">Moderate Damage</option>
            <option value="severe">Severe Damage</option>
            <option value="critical">Critical Review Required</option>
          </select>
        </div>
      </div>

      {/* Table */}
      <div className="glass-card rounded-2xl border border-slate-800 overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm text-slate-300">
            <thead className="bg-slate-800/60 text-xs font-semibold text-slate-400 uppercase tracking-wider border-b border-slate-700/60">
              <tr>
                <th className="py-3 px-4">Image</th>
                <th className="py-3 px-4">Inspection ID</th>
                <th className="py-3 px-4">Asset Name</th>
                <th className="py-3 px-4">Timestamp</th>
                <th className="py-3 px-4">Classification</th>
                <th className="py-3 px-4">Crack Area</th>
                <th className="py-3 px-4">Severity</th>
                <th className="py-3 px-4">Maintenance Priority</th>
                <th className="py-3 px-4 text-right">Details</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/80">
              {filtered.map(insp => {
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
                    <td className="py-3 px-4 font-mono font-bold text-slate-200">#{insp.id}</td>
                    <td className="py-3 px-4">
                      <div className="font-semibold text-white">{insp.asset_name}</div>
                      <div className="text-xs text-slate-400">{insp.inspector_name}</div>
                    </td>
                    <td className="py-3 px-4 text-xs font-mono text-slate-400">
                      {new Date(insp.timestamp).toLocaleString()}
                    </td>
                    <td className="py-3 px-4">
                      {res?.crack_detected ? (
                        <span className="text-xs font-medium text-rose-400">Crack Detected</span>
                      ) : (
                        <span className="text-xs font-medium text-emerald-400">Normal Surface</span>
                      )}
                      <div className="text-[11px] text-slate-500">{res?.surface_type}</div>
                    </td>
                    <td className="py-3 px-4 font-mono text-xs text-slate-300">
                      {res ? `${res.crack_area_px} px` : 'N/A'}
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
                        className="px-3 py-1.5 rounded-md bg-blue-600/10 hover:bg-blue-600 text-xs font-semibold text-blue-400 hover:text-white border border-blue-500/20 transition"
                      >
                        View &rarr;
                      </Link>
                    </td>
                  </tr>
                );
              })}
              {filtered.length === 0 && !loading && (
                <tr>
                  <td colSpan="9" className="py-8 text-center text-xs text-slate-500">
                    No inspections matching filter criteria.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
