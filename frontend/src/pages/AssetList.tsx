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
  AlertCircle
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
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Infrastructure Assets</h1>
          <p className="text-sm text-gray-500 mt-0.5">
            Registered civil structures, engineering records, and inspection logs
          </p>
        </div>
        {canManage && (
          <Link to="/assets/new" className="btn-primary flex items-center gap-2 text-sm self-start sm:self-auto">
            <Plus className="w-4 h-4" />
            <span>Register New Asset</span>
          </Link>
        )}
      </div>

      {/* Filter and Search Bar */}
      <div className="card p-4 flex flex-col md:flex-row items-center gap-4">
        <form onSubmit={handleSearchSubmit} className="flex-1 flex items-center gap-2 w-full">
          <div className="relative flex-1">
            <Search className="w-4 h-4 text-gray-400 absolute left-3 top-3" />
            <input
              type="text"
              placeholder="Search by asset code or name..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="input-field pl-9"
            />
          </div>
          <button type="submit" className="btn-secondary text-sm">
            Search
          </button>
        </form>

        <div className="flex items-center gap-2 w-full md:w-auto">
          <Filter className="w-4 h-4 text-gray-500" />
          <select
            value={selectedType}
            onChange={(e) => {
              setSelectedType(e.target.value);
              setPage(1);
            }}
            className="input-field py-2 text-sm bg-white"
          >
            <option value="">All Asset Types</option>
            {ASSET_TYPES.map((t) => (
              <option key={t} value={t}>
                {t}
              </option>
            ))}
          </select>
        </div>
      </div>

      {error && (
        <div className="p-4 rounded-lg bg-red-50 border border-red-200 text-red-700 text-sm flex items-center gap-2">
          <AlertCircle className="w-5 h-5 flex-shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {/* Table */}
      <div className="card p-0 overflow-hidden shadow-sm">
        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse text-sm">
            <thead className="bg-gray-50 border-b border-gray-200 text-gray-500 uppercase text-xs font-semibold">
              <tr>
                <th className="px-6 py-3.5">Code</th>
                <th className="px-6 py-3.5">Name</th>
                <th className="px-6 py-3.5">Type</th>
                <th className="px-6 py-3.5">Location</th>
                <th className="px-6 py-3.5">Built</th>
                <th className="px-6 py-3.5 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {loading ? (
                <tr>
                  <td colSpan={6} className="px-6 py-12 text-center text-gray-400">
                    <div className="w-6 h-6 border-2 border-blue-600 border-t-transparent rounded-full animate-spin mx-auto mb-2"></div>
                    Loading infrastructure assets...
                  </td>
                </tr>
              ) : assets.length === 0 ? (
                <tr>
                  <td colSpan={6} className="px-6 py-12 text-center text-gray-500">
                    No infrastructure assets found matching your criteria.
                  </td>
                </tr>
              ) : (
                assets.map((asset) => (
                  <tr key={asset.id} className="hover:bg-gray-50/80 transition-colors">
                    <td className="px-6 py-4 font-mono font-bold text-blue-600">
                      {asset.asset_code}
                    </td>
                    <td className="px-6 py-4 font-semibold text-gray-900">
                      {asset.name}
                    </td>
                    <td className="px-6 py-4">
                      <span className="inline-block px-2.5 py-0.5 rounded-full text-xs font-medium bg-gray-100 text-gray-700 border border-gray-200">
                        {asset.type}
                      </span>
                    </td>
                    <td className="px-6 py-4 text-gray-600 max-w-xs truncate">
                      {asset.location_text || '—'}
                    </td>
                    <td className="px-6 py-4 text-gray-600">
                      {asset.construction_year || '—'}
                    </td>
                    <td className="px-6 py-4 text-right space-x-2">
                      <Link
                        to={`/assets/${asset.id}`}
                        className="inline-flex items-center gap-1 text-xs font-medium text-blue-600 hover:text-blue-800 bg-blue-50 px-2.5 py-1 rounded-md"
                      >
                        <Eye className="w-3.5 h-3.5" />
                        <span>Inspect</span>
                      </Link>
                      {canManage && (
                        <>
                          <Link
                            to={`/assets/${asset.id}/edit`}
                            className="inline-flex items-center text-xs font-medium text-gray-600 hover:text-gray-900 bg-gray-100 px-2 py-1 rounded-md"
                          >
                            <Edit3 className="w-3.5 h-3.5" />
                          </Link>
                          <button
                            onClick={() => handleDelete(asset.id, asset.asset_code)}
                            className="inline-flex items-center text-xs font-medium text-red-600 hover:text-red-800 bg-red-50 px-2 py-1 rounded-md"
                          >
                            <Trash2 className="w-3.5 h-3.5" />
                          </button>
                        </>
                      )}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>

        {/* Pagination */}
        <div className="px-6 py-4 border-t border-gray-100 flex items-center justify-between text-xs text-gray-500">
          <div>
            Showing page <strong>{page}</strong> of <strong>{totalPages}</strong> ({total} total assets)
          </div>
          <div className="flex items-center gap-2">
            <button
              disabled={page <= 1}
              onClick={() => setPage((p) => Math.max(1, p - 1))}
              className="btn-secondary py-1 px-2.5 text-xs flex items-center gap-1 disabled:opacity-40"
            >
              <ChevronLeft className="w-3.5 h-3.5" /> Previous
            </button>
            <button
              disabled={page >= totalPages}
              onClick={() => setPage((p) => p + 1)}
              className="btn-secondary py-1 px-2.5 text-xs flex items-center gap-1 disabled:opacity-40"
            >
              Next <ChevronRight className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
