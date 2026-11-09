import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import api from '../api/client';
import { Building2, ClipboardList, Camera, ArrowRight, Activity, Sparkles, MapPin } from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { AssetMap } from '../components/AssetMap';
import { InfrastructureAsset } from '../types';

export const Dashboard: React.FC = () => {
  const { user } = useAuth();
  const [stats, setStats] = useState({
    totalAssets: 0,
    totalInspections: 0,
    totalImages: 0,
  });
  const [assets, setAssets] = useState<InfrastructureAsset[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchStats = async () => {
      try {
        const [assetsRes, inspRes] = await Promise.all([
          api.get('/assets/?page=1&size=50'),
          api.get('/inspections/'),
        ]);

        const inspections = inspRes.data || [];
        const assetList = assetsRes.data.items || [];
        setAssets(assetList);
        setStats({
          totalAssets: assetsRes.data.total || assetList.length,
          totalInspections: inspections.length,
          totalImages: 0,
        });
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
            <span>Manage Assets</span>
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
              {loading ? '...' : stats.totalAssets}
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
              {loading ? '...' : stats.totalInspections}
            </p>
            <p className="text-xs text-gray-500 mt-0.5">Recorded site evaluations</p>
          </div>
        </div>

        <div className="card flex items-center gap-5 hover:shadow-md transition-shadow">
          <div className="h-14 w-14 rounded-2xl bg-purple-50 text-purple-600 flex items-center justify-center">
            <Sparkles className="w-7 h-7 text-purple-600" />
          </div>
          <div>
            <p className="text-xs font-semibold uppercase tracking-wider text-gray-400">AI Assessment</p>
            <p className="text-3xl font-extrabold text-purple-900 mt-1">
              Live ONNX
            </p>
            <p className="text-xs text-gray-500 mt-0.5">Grad-CAM + MobileNetV3</p>
          </div>
        </div>
      </div>

      {/* Interactive GIS Asset Map */}
      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-bold text-gray-900 flex items-center gap-2">
            <MapPin className="w-5 h-5 text-blue-600" />
            <span>Civil Infrastructure Geographic Overview</span>
          </h2>
          <span className="text-xs text-gray-500">Live GPS Coordinates</span>
        </div>
        <AssetMap assets={assets} height="380px" />
      </div>

      {/* AI Inference Banner */}
      <div className="bg-gradient-to-r from-slate-900 via-indigo-950 to-slate-900 text-white p-8 rounded-2xl shadow-md border border-slate-800">
        <div className="flex items-start justify-between gap-6">
          <div className="space-y-3 max-w-2xl">
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full text-xs font-semibold bg-emerald-500/20 text-emerald-300 border border-emerald-500/30">
              <Activity className="w-3.5 h-3.5 text-emerald-400" />
              <span>AI Damage Assessment & Grad-CAM Active</span>
            </div>
            <h2 className="text-xl font-bold text-white">
              AI Decision Support: Defect Classification & Explainable Heatmaps
            </h2>
            <p className="text-sm text-slate-300 leading-relaxed">
              InfraScan utilizes an optimized MobileNetV3 neural network running on ONNX Runtime for sub-second concrete crack detection. Inspectors can toggle CLAHE contrast enhancement, inspect Grad-CAM activation heatmaps, and export formal engineering PDF inspection reports.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};
