import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import api from '../api/client';
import { Building2, ClipboardList, Camera, Activity } from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { DashboardStats, ModelStatus } from '../types';

export const Dashboard: React.FC = () => {
  const { user } = useAuth();
  const [stats, setStats] = useState<DashboardStats>({
    assets: 0,
    inspections: 0,
    images: 0,
    analyses: 0,
  });
  const [models, setModels] = useState<ModelStatus | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchStats = async () => {
      try {
        const [statsRes, modelRes] = await Promise.all([
          api.get<DashboardStats>('/stats'),
          api.get<ModelStatus>('/models/status'),
        ]);
        setStats(statsRes.data);
        setModels(modelRes.data);
      } catch (err) {
        console.error('Failed to fetch dashboard stats', err);
      } finally {
        setLoading(false);
      }
    };

    fetchStats();
  }, []);

  return (
    <div className="space-y-8 max-w-7xl mx-auto">
      {/* Welcome Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 bg-white p-6 rounded-2xl shadow-sm border border-gray-100">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">
            Welcome back, {user?.full_name} 👋
          </h1>
          <p className="text-sm text-gray-500 mt-1">
            Logged in as <span className="font-semibold text-blue-600">{user?.role?.name}</span> • Infrastructure Health Monitoring System
          </p>
        </div>
        <div className="flex items-center gap-3">
          <Link to="/assets" className="btn-primary flex items-center gap-2 text-sm">
            <Building2 className="w-4 h-4" />
            <span>View All Assets</span>
          </Link>
        </div>
      </div>

      {/* Overview Stat Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div className="card flex items-center gap-5 hover:shadow-md transition-shadow">
          <div className="h-14 w-14 rounded-2xl bg-blue-50 text-blue-600 flex items-center justify-center">
            <Building2 className="w-7 h-7" />
          </div>
          <div>
            <p className="text-xs font-semibold uppercase tracking-wider text-gray-400">Total Assets</p>
            <p className="text-3xl font-extrabold text-gray-900 mt-1">
              {loading ? '...' : stats.assets}
            </p>
            <p className="text-xs text-gray-500 mt-0.5">Bridges, Tunnels, Dams, Roads</p>
          </div>
        </div>

        <div className="card flex items-center gap-5 hover:shadow-md transition-shadow">
          <div className="h-14 w-14 rounded-2xl bg-emerald-50 text-emerald-600 flex items-center justify-center">
            <ClipboardList className="w-7 h-7" />
          </div>
          <div>
            <p className="text-xs font-semibold uppercase tracking-wider text-gray-400">Inspections</p>
            <p className="text-3xl font-extrabold text-gray-900 mt-1">
              {loading ? '...' : stats.inspections}
            </p>
            <p className="text-xs text-gray-500 mt-0.5">Recorded site evaluations</p>
          </div>
        </div>

        <div className="card flex items-center gap-5 hover:shadow-md transition-shadow">
          <div className="h-14 w-14 rounded-2xl bg-purple-50 text-purple-600 flex items-center justify-center">
            <Camera className="w-7 h-7" />
          </div>
          <div>
            <p className="text-xs font-semibold uppercase tracking-wider text-gray-400">Validated Images</p>
            <p className="text-3xl font-extrabold text-gray-900 mt-1">
              {loading ? '...' : stats.images}
            </p>
            <p className="text-xs text-gray-500 mt-0.5">
              {loading ? 'Quality checked uploads' : `${stats.analyses} analyzed`}
            </p>
          </div>
        </div>
      </div>

      {/* AI Placeholder Card */}
      <div className="bg-gradient-to-r from-slate-900 to-indigo-950 text-white p-8 rounded-2xl shadow-md border border-slate-800">
        <div className="flex items-start justify-between gap-6">
          <div className="space-y-3 max-w-2xl">
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full text-xs font-semibold bg-indigo-500/20 text-indigo-300 border border-indigo-500/30">
              <Activity className="w-3.5 h-3.5" />
              <span>Milestone 2 model status</span>
            </div>
            <h2 className="text-xl font-bold text-white">
              Crack classification, detection, and segmentation
            </h2>
            <p className="text-sm text-slate-300 leading-relaxed">
              Open an inspection, upload a photo, and run analysis. Each model reports completed, failed, or weights-not-on-disk. The dashboard does not invent scores.
            </p>
            <ul className="space-y-1 text-xs text-slate-200">
              <li>Classifier ({models?.classifier.name || 'SmallCNN'}): {loading ? '...' : models?.classifier.available ? 'weights found' : 'weights missing'}</li>
              <li>Segmentation ({models?.segmentation.name || 'UNet'}): {loading ? '...' : models?.segmentation.available ? 'weights found' : 'weights missing'}</li>
              <li>Detection ({models?.detection.name || 'YOLOv8n'}): {loading ? '...' : models?.detection.available ? 'weights found' : 'weights missing'}</li>
            </ul>
          </div>
        </div>
      </div>
    </div>
  );
};
