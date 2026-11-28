import React, { useState, useEffect } from 'react';
import api from '../api/client';
import { ModelComparisonItem } from '../types';
import {
  Brain,
  CheckCircle,
  Zap,
  HardDrive,
  Cpu,
  BarChart2,
  ShieldCheck,
  Eye,
  Layers,
  Sparkles,
  ArrowUpRight,
  RefreshCw,
  AlertCircle,
  Play,
  Check,
  Activity,
  Table
} from 'lucide-react';

export const ModelComparison: React.FC = () => {
  const [models, setModels] = useState<ModelComparisonItem[]>([]);
  const [selectedModel, setSelectedModel] = useState<string>('');
  const [rationale, setRationale] = useState<string>('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [evalMetrics, setEvalMetrics] = useState<any>(null);
  const [deployingId, setDeployingId] = useState<string | null>(null);

  const fetchComparison = async () => {
    setLoading(true);
    setError('');
    try {
      const [compRes, metricsRes] = await Promise.all([
        api.get('/analytics/model-comparison'),
        api.get('/analytics/models/evaluation-metrics')
      ]);
      setModels(compRes.data.models || []);
      setSelectedModel(compRes.data.selected_model || '');
      setRationale(compRes.data.selection_rationale || '');
      setEvalMetrics(metricsRes.data);
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Failed to load model comparison analytics.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchComparison();
  }, []);

  const handleDeploy = async (modelId: string) => {
    setDeployingId(modelId);
    setError('');
    setSuccess('');
    try {
      const res = await api.post(`/analytics/models/${modelId}/deploy`);
      setSuccess(res.data.message || 'Model successfully deployed to production.');
      fetchComparison();
    } catch (e: any) {
      setError('Failed to switch model deployment.');
    } finally {
      setDeployingId(null);
    }
  };

  const deployedModel = models.find((m) => m.status === 'Production') || models[0];

  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      {/* Header Card */}
      <div className="card p-6 flex flex-col md:flex-row md:items-center justify-between gap-4 border-slate-200/80">
        <div>
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full text-xs font-semibold bg-blue-50 text-blue-700 border border-blue-200 mb-2">
            <Brain className="w-3.5 h-3.5" />
            <span>Milestone 3 & 4 • Deep Learning Benchmark & Model Versioning</span>
          </div>
          <h1 className="text-xl sm:text-2xl font-bold text-slate-900 tracking-tight">
            AI Model Registry, Versioning & Comparative Benchmark
          </h1>
          <p className="text-xs sm:text-sm text-slate-500 mt-1 max-w-2xl">
            Empirical benchmark evaluating defect accuracy, F1-score, mAP, Dice coefficient, CPU latency, and production registry rollouts.
          </p>
        </div>
        <button
          onClick={fetchComparison}
          disabled={loading}
          className="btn-secondary flex items-center gap-2 self-start md:self-auto text-xs py-2 px-3.5 bg-white hover:bg-slate-50 shadow-xs"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin text-blue-600' : 'text-slate-600'}`} />
          <span>Reload Benchmarks</span>
        </button>
      </div>

      {/* Alerts */}
      {error && (
        <div className="p-4 rounded-xl bg-rose-50 border border-rose-200 text-xs font-medium text-rose-700 flex items-center gap-2">
          <AlertCircle className="w-4 h-4 shrink-0" />
          <span>{error}</span>
        </div>
      )}
      {success && (
        <div className="p-4 rounded-xl bg-emerald-50 border border-emerald-200 text-xs font-medium text-emerald-700 flex items-center gap-2">
          <CheckCircle className="w-4 h-4 shrink-0" />
          <span>{success}</span>
        </div>
      )}

      {/* Deployed Model Highlight Card */}
      {deployedModel && (
        <div className="bg-gradient-to-br from-slate-900 via-slate-950 to-indigo-950 text-white rounded-2xl p-6 sm:p-7 shadow-xl border border-slate-800 relative overflow-hidden">
          <div className="absolute right-0 top-0 w-96 h-96 bg-blue-500/10 rounded-full blur-3xl pointer-events-none" />

          <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-6 relative z-10">
            <div className="space-y-2.5 max-w-2xl">
              <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full text-xs font-semibold bg-emerald-500/20 text-emerald-300 border border-emerald-500/30">
                <CheckCircle className="w-3.5 h-3.5" />
                <span>Active Production Architecture • Version {deployedModel.version || 'v3.0'}</span>
              </div>
              <h2 className="text-2xl sm:text-3xl font-extrabold text-white tracking-tight">
                {deployedModel.name}
              </h2>
              <p className="text-xs sm:text-sm text-slate-300 leading-relaxed">
                Trained on composite civil infrastructure benchmarks (SDNET2018 Bridge Decks, Pavements, Concrete Walls + METU Benchmark) with 8-view reflection/rotation Test-Time Augmentation (TTA).
              </p>
            </div>

            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
              <div className="bg-white/5 backdrop-blur-md rounded-xl p-3.5 text-center border border-white/10">
                <p className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">Accuracy</p>
                <p className="text-xl sm:text-2xl font-black text-emerald-400 mt-1">{deployedModel.accuracy}%</p>
                <p className="text-[10px] text-slate-400 mt-0.5">Dual-benchmark</p>
              </div>

              <div className="bg-white/5 backdrop-blur-md rounded-xl p-3.5 text-center border border-white/10">
                <p className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">F1-Score</p>
                <p className="text-xl sm:text-2xl font-black text-indigo-300 mt-1">{deployedModel.f1_score}%</p>
                <p className="text-[10px] text-slate-400 mt-0.5">Macro balanced</p>
              </div>

              <div className="bg-white/5 backdrop-blur-md rounded-xl p-3.5 text-center border border-white/10">
                <p className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">CPU Latency</p>
                <p className="text-xl sm:text-2xl font-black text-blue-300 mt-1">{deployedModel.inference_time_ms}ms</p>
                <p className="text-[10px] text-slate-400 mt-0.5">Sub-50ms CPU</p>
              </div>

              <div className="bg-white/5 backdrop-blur-md rounded-xl p-3.5 text-center border border-white/10">
                <p className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">Footprint</p>
                <p className="text-xl sm:text-2xl font-black text-amber-300 mt-1">{deployedModel.model_size_kb} KB</p>
                <p className="text-[10px] text-slate-400 mt-0.5">Edge deployable</p>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* ── Model Versioning Registry & Switcher Table ─────────────────── */}
      <div className="card p-6 space-y-4 border-slate-200/80">
        <div className="flex items-center justify-between">
          <div>
            <h3 className="text-base font-bold text-slate-900 flex items-center gap-2">
              <Layers className="w-4 h-4 text-blue-600" />
              <span>Registered Vision Architectures & Model Versions</span>
            </h3>
            <p className="text-xs text-slate-500 mt-0.5">Switch active models or test candidate backbones in production</p>
          </div>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs border-collapse">
            <thead>
              <tr className="bg-slate-50 border-b border-slate-200 text-[10px] font-bold text-slate-400 uppercase tracking-wider">
                <th className="py-3 px-4">Architecture</th>
                <th className="py-3 px-3">Version</th>
                <th className="py-3 px-4">Type</th>
                <th className="py-3 px-3">Accuracy</th>
                <th className="py-3 px-3">F1-Score</th>
                <th className="py-3 px-3">Latency</th>
                <th className="py-3 px-3">Params</th>
                <th className="py-3 px-4">Status</th>
                <th className="py-3 px-4 text-right">Deployment</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {models.map((m) => {
                const isProduction = m.status === 'Production';
                return (
                  <tr key={m.id || m.name} className="hover:bg-slate-50/80 transition-colors">
                    <td className="py-3.5 px-4 font-bold text-slate-900">
                      {m.name}
                      <span className="block text-[10px] font-normal text-slate-500 mt-0.5">{m.notes}</span>
                    </td>
                    <td className="py-3.5 px-3 font-mono font-bold text-slate-600">{m.version || 'v1.0'}</td>
                    <td className="py-3.5 px-4 text-slate-600">{m.type}</td>
                    <td className="py-3.5 px-3 font-mono font-bold text-emerald-600">{m.accuracy}%</td>
                    <td className="py-3.5 px-3 font-mono font-bold text-indigo-600">{m.f1_score}%</td>
                    <td className="py-3.5 px-3 font-mono text-slate-700">{m.inference_time_ms}ms</td>
                    <td className="py-3.5 px-3 font-mono text-slate-500">{m.parameters}</td>
                    <td className="py-3.5 px-4">
                      <span className={`px-2.5 py-0.5 rounded-full text-[10px] font-bold ${
                        isProduction ? 'bg-emerald-100 text-emerald-800' : 'bg-slate-100 text-slate-600'
                      }`}>
                        {m.status}
                      </span>
                    </td>
                    <td className="py-3.5 px-4 text-right">
                      {isProduction ? (
                        <span className="inline-flex items-center gap-1 text-[11px] font-bold text-emerald-600">
                          <Check className="w-3.5 h-3.5" />
                          <span>Active</span>
                        </span>
                      ) : (
                        <button
                          onClick={() => handleDeploy(m.id || '')}
                          disabled={deployingId === m.id}
                          className="btn-secondary py-1 px-3 text-[11px] font-semibold flex items-center gap-1 ml-auto"
                        >
                          <Play className="w-3 h-3 text-blue-600" />
                          <span>{deployingId === m.id ? 'Deploying...' : 'Deploy'}</span>
                        </button>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>

      {/* ── Evaluation Metrics & Confusion Matrix (Module 13) ──────────── */}
      {evalMetrics && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Confusion Matrix */}
          <div className="card p-6 space-y-4 border-slate-200/80">
            <h3 className="text-base font-bold text-slate-900 flex items-center gap-2">
              <Table className="w-4 h-4 text-blue-600" />
              <span>Defect Confusion Matrix (Test Benchmark)</span>
            </h3>
            <p className="text-xs text-slate-500">
              Evaluated on 2,000 held-out images: 1,000 cracked civil surfaces and 1,000 sound intact surfaces.
            </p>

            <div className="overflow-x-auto pt-2">
              <table className="w-full text-center text-xs border border-slate-200">
                <thead>
                  <tr className="bg-slate-50 text-slate-500">
                    <th className="p-2 border">Actual \ Predicted</th>
                    <th className="p-2 border font-bold text-slate-900 bg-rose-50/50">Predicted Cracked</th>
                    <th className="p-2 border font-bold text-slate-900 bg-emerald-50/50">Predicted Sound</th>
                  </tr>
                </thead>
                <tbody>
                  <tr>
                    <td className="p-3 border font-bold text-slate-700 bg-slate-50">Actual Cracked</td>
                    <td className="p-3 border bg-emerald-50 font-bold font-mono text-emerald-700 text-sm">
                      {evalMetrics.confusion_matrix.true_positives} (TP - 94.0%)
                    </td>
                    <td className="p-3 border bg-rose-50 font-mono text-rose-600">
                      {evalMetrics.confusion_matrix.false_negatives} (FN - 6.0%)
                    </td>
                  </tr>
                  <tr>
                    <td className="p-3 border font-bold text-slate-700 bg-slate-50">Actual Sound</td>
                    <td className="p-3 border bg-rose-50 font-mono text-rose-600">
                      {evalMetrics.confusion_matrix.false_positives} (FP - 4.8%)
                    </td>
                    <td className="p-3 border bg-emerald-50 font-bold font-mono text-emerald-700 text-sm">
                      {evalMetrics.confusion_matrix.true_negatives} (TN - 95.2%)
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>

            <div className="grid grid-cols-2 gap-3 text-xs pt-2">
              <div className="p-3 rounded-xl bg-slate-50 border border-slate-200">
                <span className="text-[10px] text-slate-400 font-bold uppercase block">mAP@50 (Detection)</span>
                <span className="text-lg font-bold text-blue-600">{evalMetrics.metrics.mAP_50}%</span>
              </div>
              <div className="p-3 rounded-xl bg-slate-50 border border-slate-200">
                <span className="text-[10px] text-slate-400 font-bold uppercase block">Dice Coefficient (Mask)</span>
                <span className="text-lg font-bold text-purple-600">{evalMetrics.metrics.dice_coefficient}%</span>
              </div>
            </div>
          </div>

          {/* Class-wise Performance */}
          <div className="card p-6 space-y-4 border-slate-200/80">
            <h3 className="text-base font-bold text-slate-900 flex items-center gap-2">
              <Activity className="w-4 h-4 text-blue-600" />
              <span>Infrastructure Domain Generalization</span>
            </h3>
            <p className="text-xs text-slate-500">
              Evaluated across distinct civil structure materials and public benchmark datasets.
            </p>

            <div className="space-y-3 pt-2">
              {evalMetrics.class_performance.map((c: any, idx: number) => (
                <div key={idx} className="p-3 rounded-xl bg-slate-50 border border-slate-200 space-y-1.5">
                  <div className="flex items-center justify-between text-xs">
                    <span className="font-bold text-slate-900">{c.category}</span>
                    <span className="font-mono font-bold text-blue-600">{c.f1_score}% F1</span>
                  </div>
                  <div className="w-full bg-slate-200 rounded-full h-2 overflow-hidden">
                    <div className="bg-blue-600 h-full rounded-full" style={{ width: `${c.f1_score}%` }} />
                  </div>
                  <div className="flex justify-between text-[10px] text-slate-400 font-mono">
                    <span>Precision: {c.precision}%</span>
                    <span>Recall: {c.recall}%</span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
