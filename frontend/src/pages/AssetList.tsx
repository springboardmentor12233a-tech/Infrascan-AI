import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import api from '../api/client';
import { 
  Building2, 
  Search, 
  Filter, 
  Plus, 
  MapPin, 
  Calendar, 
  Eye, 
  Edit3, 
  Trash2,
  ChevronLeft,
  ChevronRight,
  AlertCircle,
  ExternalLink,
  RefreshCw
} from 'lucide-react';
import { InfrastructureAsset, AssetType, AssetListResponse } from '../types';
import { useAuth } from '../context/AuthContext';

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

const ASSET_TYPE_COLORS: Record<string, string> = {
  Bridge: 'bg-blue-50 text-blue-700 border-blue-200',
  Tunnel: 'bg-purple-50 text-purple-700 border-purple-200',
  Dam: 'bg-cyan-50 text-cyan-700 border-cyan-200',
  Road: 'bg-amber-50 text-amber-700 border-amber-200',
  Building: 'bg-emerald-50 text-emerald-700 border-emerald-200',
  'Retaining Wall': 'bg-slate-100 text-slate-700 border-slate-200',
  'Concrete Structure': 'bg-indigo-50 text-indigo-700 border-indigo-200',
  'Industrial Structure': 'bg-orange-50 text-orange-700 border-orange-200',
};

export const AssetList: React.FC = () => {
  const { user } = useAuth();
  const [assets, setAssets] = useState<InfrastructureAsset[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState('');
  const [selectedType, setSelectedType] = useState<string>('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const canManage = ['Administrator', 'Infrastructure Manager'].includes(user?.role?.name || '');

  const fetchAssets = async () => {
    setLoading(true);
    setError('');
    try {
      const params = new URLSearchParams();
      params.append('page', page.toString());
      params.append('size', '10');
      if (search.trim()) params.append('search', search.trim());
      if (selectedType) params.append('asset_type', selectedType);

      const res = await api.get<AssetListResponse>(`/assets/?${params.toString()}`);
      setAssets(res.data.items);
      setTotal(res.data.total);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to load assets');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchAssets();
  }, [page, selectedType]);

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setPage(1);
    fetchAssets();
  };

  const handleDelete = async (id: number, code: string) => {
    if (!window.confirm(`Are you sure you want to delete asset ${code}?`)) return;
    try {
      await api.delete(`/assets/${id}`);
      fetchAssets();
    } catch (err: any) {
      alert(err.response?.data?.detail || 'Failed to delete asset');
    }
  };

  const totalPages = Math.ceil(total / 10) || 1;

  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 bg-white p-6 rounded-2xl shadow-card border border-slate-100">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 tracking-tight">Civil Infrastructure Assets</h1>
          <p className="text-xs text-slate-500 mt-0.5">
            Registered civil structures, engineering records, construction specs, and inspection archives
          </p>
        </div>
        {canManage && (
          <Link to="/assets/new" className="btn-primary text-xs py-2 px-4 self-start sm:self-auto shadow-sm">
            <Plus className="w-4 h-4" />
            <span>Register New Asset</span>
          </Link>
        )}
      </div>

      {/* Filter and Search Bar */}
      <div className="card p-4 flex flex-col md:flex-row items-center gap-3">
        <form onSubmit={handleSearchSubmit} className="flex-1 flex items-center gap-2 w-full">
          <div className="relative flex-1">
            <Search className="w-4 h-4 text-slate-400 absolute left-3.5 top-3" />
            <input
              type="text"
              placeholder="Search by asset code, name, location..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="input-field pl-10"
            />
          </div>
          <button type="submit" className="btn-secondary text-xs py-2.5 px-4 shrink-0">
            Search
          </button>
        </form>

        <div className="flex items-center gap-2 w-full md:w-auto">
          <Filter className="w-4 h-4 text-slate-400 shrink-0" />
          <select
            value={selectedType}
            onChange={(e) => {
              setSelectedType(e.target.value);
              setPage(1);
            }}
            className="input-field py-2 text-xs bg-white shrink-0"
          >
            <option value="">All Categories</option>
            {ASSET_TYPES.map((t) => (
              <option key={t} value={t}>
                {t}
              </option>
            ))}
          </select>
        </div>
      </div>

      {error && (
        <div className="p-4 rounded-xl bg-rose-50 border border-rose-200 text-rose-700 text-xs flex items-center gap-2.5">
          <AlertCircle className="w-4 h-4 shrink-0 text-rose-600" />
          <span className="font-medium">{error}</span>
        </div>
      )}

      {/* Main Table */}
      <div className="card p-0 overflow-hidden shadow-card">
        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse text-sm">
            <thead className="bg-slate-50/80 border-b border-slate-100 text-[11px] font-bold text-slate-400 uppercase tracking-wider">
              <tr>
                <th className="px-6 py-3.5">Asset Code</th>
                <th className="px-6 py-3.5">Structure Name</th>
                <th className="px-6 py-3.5">Category</th>
                <th className="px-6 py-3.5">Physical Location</th>
                <th className="px-6 py-3.5">Year Built</th>
                <th className="px-6 py-3.5 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 text-xs">
              {loading ? (
                <tr>
                  <td colSpan={6} className="px-6 py-16 text-center text-slate-400">
                    <RefreshCw className="w-6 h-6 animate-spin text-brand-600 mx-auto mb-2" />
                    <span>Loading registered civil assets...</span>
                  </td>
                </tr>
              ) : assets.length === 0 ? (
                <tr>
                  <td colSpan={6} className="px-6 py-16 text-center text-slate-400">
                    <Building2 className="w-8 h-8 text-slate-300 mx-auto mb-2" />
                    <p className="font-semibold text-slate-600">No infrastructure assets found</p>
                    <p className="text-[11px] text-slate-400 mt-0.5">Try adjusting your search criteria or category filter</p>
                  </td>
                </tr>
              ) : (
                assets.map((asset) => {
                  const typeColor = ASSET_TYPE_COLORS[asset.type] || 'bg-slate-100 text-slate-700 border-slate-200';
                  return (
                    <tr key={asset.id} className="hover:bg-slate-50/70 transition-colors">
                      <td className="px-6 py-4 font-mono font-bold text-brand-600">
                        {asset.asset_code}
                      </td>
                      <td className="px-6 py-4 font-bold text-slate-900">
                        <Link
                          to={`/assets/${asset.id}`}
                          className="hover:text-brand-600 transition-colors flex items-center gap-1.5"
                        >
                          <span>{asset.name}</span>
                          <ExternalLink className="w-3.5 h-3.5 text-slate-400" />
                        </Link>
                      </td>
                      <td className="px-6 py-4">
                        <span className={`inline-block px-2.5 py-0.5 rounded-full text-[11px] font-semibold border ${typeColor}`}>
                          {asset.type}
                        </span>
                      </td>
                      <td className="px-6 py-4 text-slate-600 max-w-xs truncate" title={asset.location_text}>
                        {asset.location_text || '—'}
                      </td>
                      <td className="px-6 py-4 text-slate-600 font-medium">
                        {asset.construction_year || '—'}
                      </td>
                      <td className="px-6 py-4 text-right space-x-1.5 whitespace-nowrap">
                        <Link
                          to={`/assets/${asset.id}`}
                          className="inline-flex items-center gap-1 text-xs font-semibold text-brand-700 bg-brand-50 hover:bg-brand-100 px-2.5 py-1.5 rounded-lg transition-colors"
                        >
                          <Eye className="w-3.5 h-3.5" />
                          <span>View</span>
                        </Link>
                        {canManage && (
                          <>
                            <Link
                              to={`/assets/${asset.id}/edit`}
                              className="inline-flex items-center gap-1 text-xs font-semibold text-slate-700 bg-slate-100 hover:bg-slate-200 px-2.5 py-1.5 rounded-lg transition-colors"
                            >
                              <Edit3 className="w-3.5 h-3.5" />
                              <span>Edit</span>
                            </Link>
                            <button
                              onClick={() => handleDelete(asset.id, asset.asset_code)}
                              className="inline-flex items-center gap-1 text-xs font-semibold text-rose-700 bg-rose-50 hover:bg-rose-100 px-2.5 py-1.5 rounded-lg transition-colors"
                            >
                              <Trash2 className="w-3.5 h-3.5" />
                            </button>
                          </>
                        )}
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>

        {/* Pagination Bar */}
        {totalPages > 1 && (
          <div className="p-4 border-t border-slate-100 flex items-center justify-between text-xs text-slate-500">
            <span>
              Showing Page <strong className="text-slate-900">{page}</strong> of <strong className="text-slate-900">{totalPages}</strong> ({total} total assets)
            </span>
            <div className="flex items-center gap-1">
              <button
                onClick={() => setPage((p) => Math.max(1, p - 1))}
                disabled={page <= 1}
                className="btn-secondary py-1 px-2.5 text-xs disabled:opacity-40"
              >
                <ChevronLeft className="w-3.5 h-3.5" />
              </button>
              <button
                onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                disabled={page >= totalPages}
                className="btn-secondary py-1 px-2.5 text-xs disabled:opacity-40"
              >
                <ChevronRight className="w-3.5 h-3.5" />
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
