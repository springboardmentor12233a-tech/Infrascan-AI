import React, { useState, useEffect } from 'react';
import api from '../api/client';
import { Users, Shield, Check, X, AlertCircle, RefreshCw, UserCheck, UserX } from 'lucide-react';
import { User, Role } from '../types';

export const UserManagement: React.FC = () => {
  const [users, setUsers] = useState<User[]>([]);
  const [roles, setRoles] = useState<Role[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [updatingId, setUpdatingId] = useState<number | null>(null);

  const fetchData = async () => {
    setLoading(true);
    try {
      const [usersRes, rolesRes] = await Promise.all([
        api.get<User[]>('/users/'),
        api.get<Role[]>('/auth/roles'),
      ]);
      setUsers(usersRes.data);
      setRoles(rolesRes.data);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to fetch users');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  const handleRoleChange = async (userId: number, newRoleId: number) => {
    setUpdatingId(userId);
    try {
      const res = await api.put<User>(`/users/${userId}`, { role_id: newRoleId });
      setUsers((prev) => prev.map((u) => (u.id === userId ? res.data : u)));
    } catch (err: any) {
      alert(err.response?.data?.detail || 'Failed to update user role');
    } finally {
      setUpdatingId(null);
    }
  };

  const handleToggleActive = async (userId: number, currentActive: boolean, roleId: number) => {
    setUpdatingId(userId);
    try {
      const res = await api.put<User>(`/users/${userId}`, {
        role_id: roleId,
        is_active: !currentActive,
      });
      setUsers((prev) => prev.map((u) => (u.id === userId ? res.data : u)));
    } catch (err: any) {
      alert(err.response?.data?.detail || 'Failed to change active status');
    } finally {
      setUpdatingId(null);
    }
  };

  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      {/* Header Card */}
      <div className="card p-6 flex flex-col md:flex-row md:items-center justify-between gap-4 border-slate-200/80 bg-white">
        <div>
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full text-xs font-semibold bg-blue-50 text-blue-700 border border-blue-200 mb-2">
            <Shield className="w-3.5 h-3.5" />
            <span>Role-Based Access Control (RBAC)</span>
          </div>
          <h1 className="text-xl sm:text-2xl font-bold text-slate-900 tracking-tight">
            User & Role Management Console
          </h1>
          <p className="text-xs sm:text-sm text-slate-500 mt-1 max-w-2xl">
            Administrator console: manage staff access, assign engineering roles, and govern active accounts.
          </p>
        </div>
        <button
          onClick={fetchData}
          disabled={loading}
          className="btn-secondary flex items-center gap-2 self-start md:self-auto text-xs py-2 px-3.5 bg-white hover:bg-slate-50 shadow-xs"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin text-blue-600' : 'text-slate-600'}`} />
          <span>Refresh Directory</span>
        </button>
      </div>

      {error && (
        <div className="p-4 rounded-xl bg-rose-50 border border-rose-200 text-rose-700 text-xs flex items-center gap-2.5">
          <AlertCircle className="w-4 h-4 flex-shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {/* Users Table */}
      <div className="card border-slate-200/80 overflow-hidden bg-white shadow-xs">
        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse text-xs">
            <thead>
              <tr className="bg-slate-50/80 border-b border-slate-200 text-[11px] font-bold text-slate-500 uppercase tracking-wider">
                <th className="py-3.5 px-4">Staff ID</th>
                <th className="py-3.5 px-4">Full Name</th>
                <th className="py-3.5 px-4">Email Address</th>
                <th className="py-3.5 px-4">Assigned Role</th>
                <th className="py-3.5 px-4">Account Status</th>
                <th className="py-3.5 px-4 text-right">Access Controls</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {loading ? (
                <tr>
                  <td colSpan={6} className="py-20 text-center text-slate-400">
                    <RefreshCw className="w-7 h-7 border-2 border-blue-600 border-t-transparent rounded-full animate-spin mx-auto mb-2 text-blue-600" />
                    <p className="text-xs font-medium text-slate-600">Loading personnel directory...</p>
                  </td>
                </tr>
              ) : (
                users.map((u) => (
                  <tr key={u.id} className="hover:bg-slate-50/80 transition-colors">
                    <td className="py-3.5 px-4 font-mono font-bold text-slate-400">#{u.id}</td>
                    <td className="py-3.5 px-4 font-bold text-slate-900">{u.full_name}</td>
                    <td className="py-3.5 px-4 text-slate-600 font-mono text-xs">{u.email}</td>
                    <td className="py-3.5 px-4">
                      <select
                        value={u.role_id}
                        disabled={updatingId === u.id}
                        onChange={(e) => handleRoleChange(u.id, Number(e.target.value))}
                        className="text-xs font-semibold bg-white border border-slate-200 rounded-lg py-1.5 px-2.5 text-slate-800 focus:outline-hidden focus:ring-2 focus:ring-blue-500 max-w-xs"
                      >
                        {roles.map((r) => (
                          <option key={r.id} value={r.id}>
                            {r.name}
                          </option>
                        ))}
                      </select>
                    </td>
                    <td className="py-3.5 px-4">
                      <span
                        className={`inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[10px] font-bold border ${
                          u.is_active
                            ? 'bg-emerald-50 text-emerald-700 border-emerald-200'
                            : 'bg-rose-50 text-rose-700 border-rose-200'
                        }`}
                      >
                        {u.is_active ? <UserCheck className="w-3 h-3 text-emerald-600" /> : <UserX className="w-3 h-3 text-rose-600" />}
                        <span>{u.is_active ? 'Active' : 'Disabled'}</span>
                      </span>
                    </td>
                    <td className="py-3.5 px-4 text-right">
                      <button
                        onClick={() => handleToggleActive(u.id, u.is_active, u.role_id)}
                        disabled={updatingId === u.id}
                        className={`btn-secondary text-[11px] py-1 px-3 ${
                          u.is_active ? 'hover:text-rose-600 hover:border-rose-300' : 'hover:text-emerald-600 hover:border-emerald-300'
                        }`}
                      >
                        {u.is_active ? 'Deactivate' : 'Activate'}
                      </button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
