import React, { useState, useEffect } from 'react';
import api from '../api/client';
import { Users, Shield, Check, X, AlertCircle } from 'lucide-react';
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
      <div>
        <h1 className="text-2xl font-bold text-gray-900">User & Role Management</h1>
        <p className="text-sm text-gray-500 mt-0.5">
          Administrator console: manage staff access, assign engineering roles, and toggle accounts
        </p>
      </div>

      {error && (
        <div className="p-4 rounded-lg bg-red-50 border border-red-200 text-red-700 text-sm flex items-center gap-2">
          <AlertCircle className="w-5 h-5 flex-shrink-0" />
          <span>{error}</span>
        </div>
      )}

      <div className="card p-0 overflow-hidden shadow-sm">
        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse text-sm">
            <thead className="bg-gray-50 border-b border-gray-200 text-gray-500 uppercase text-xs font-semibold">
              <tr>
                <th className="px-6 py-3.5">ID</th>
                <th className="px-6 py-3.5">Full Name</th>
                <th className="px-6 py-3.5">Email</th>
                <th className="px-6 py-3.5">Assigned Role</th>
                <th className="px-6 py-3.5">Status</th>
                <th className="px-6 py-3.5 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {loading ? (
                <tr>
                  <td colSpan={6} className="px-6 py-12 text-center text-gray-400">
                    <div className="w-6 h-6 border-2 border-blue-600 border-t-transparent rounded-full animate-spin mx-auto mb-2"></div>
                    Loading staff directory...
                  </td>
                </tr>
              ) : (
                users.map((u) => (
                  <tr key={u.id} className="hover:bg-gray-50/80 transition-colors">
                    <td className="px-6 py-4 font-mono text-gray-400 text-xs">#{u.id}</td>
                    <td className="px-6 py-4 font-semibold text-gray-900">{u.full_name}</td>
                    <td className="px-6 py-4 text-gray-600 font-mono text-xs">{u.email}</td>
                    <td className="px-6 py-4">
                      <select
                        value={u.role_id}
                        disabled={updatingId === u.id}
                        onChange={(e) => handleRoleChange(u.id, Number(e.target.value))}
                        className="input-field py-1 text-xs bg-white rounded-md max-w-xs"
                      >
                        {roles.map((r) => (
                          <option key={r.id} value={r.id}>
                            {r.name}
                          </option>
                        ))}
                      </select>
                    </td>
                    <td className="px-6 py-4">
                      <span
                        className={`inline-block px-2.5 py-0.5 rounded-full text-xs font-medium ${
                          u.is_active
                            ? 'bg-green-100 text-green-800'
                            : 'bg-red-100 text-red-800'
                        }`}
                      >
                        {u.is_active ? 'Active' : 'Inactive'}
                      </span>
                    </td>
                    <td className="px-6 py-4 text-right">
                      <button
                        onClick={() => handleToggleActive(u.id, u.is_active, u.role_id)}
                        disabled={updatingId === u.id}
                        className={`btn-secondary text-xs py-1 px-3 ${
                          u.is_active ? 'hover:text-red-600' : 'hover:text-green-600'
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
