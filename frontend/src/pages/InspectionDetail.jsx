import React, { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import SeverityBadge from '../components/SeverityBadge';
import PriorityBadge from '../components/PriorityBadge';
import { Download } from 'lucide-react';

export default function InspectionDetail() {
  const { id } = useParams();
  const { authFetch } = useAuth();
  const [inspection, setInspection] = useState(null);
  const [history, setHistory] = useState(null);
  const [activeTab, setActiveTab] = useState('overlay');
  const [loading, setLoading] = useState(true);
  const [downloading, setDownloading] = useState(false);
  const [downloadingPdf, setDownloadingPdf] = useState(false);

  const handleDownloadReport = async (inspId, format = 'csv') => {
    if (format === 'pdf') setDownloadingPdf(true);
    else setDownloading(true);

    try {
      const res = await authFetch(`/api/inspections/${inspId}/report?format=${format}`);
      if (!res.ok) throw new Error(`${format.toUpperCase()} report download failed`);
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `infrascan_report_${inspId}.${format}`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    } catch (err) {
      alert(`Failed to download ${format.toUpperCase()} report: ` + err.message);
    } finally {
      if (format === 'pdf') setDownloadingPdf(false);
      else setDownloading(false);
    }
  };

  useEffect(() => {
    authFetch(`/api/inspections/${id}`)
      .then(r => {
        if (!r.ok) throw new Error('Inspection not found or access denied');
        return r.json();
      })
      .then(data => {
        setInspection(data);
        setLoading(false);
        if (data.asset_id) {
          authFetch(`/api/analytics/historical/${data.asset_id}`)
            .then(res => res.json())
            .then(hist => setHistory(hist))
            .catch(console.error);
        }
      })
      .catch(err => {
        console.error(err);
        setLoading(false);
      });
  }, [id]);

  if (loading || !inspection) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <div className="w-10 h-10 border-4 border-blue-500 border-t-transparent rounded-full animate-spin"></div>
      </div>
    );
  }

  const r = inspection.result;

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8">
      {/* Breadcrumb & Navigation */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2 text-xs text-slate-400">
          <Link to="/" className="hover:text-white transition">Dashboard</Link>
          <span>/</span>
          <Link to="/inspections" className="hover:text-white transition">Inspections</Link>
          <span>/</span>
          <span className="text-white font-mono font-bold">#{inspection.id}</span>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => handleDownloadReport(inspection.id, 'pdf')}
            disabled={downloadingPdf}
            className="px-3.5 py-1.5 rounded-lg bg-emerald-600/20 hover:bg-emerald-600/30 text-xs font-semibold text-emerald-300 border border-emerald-500/30 transition flex items-center gap-1.5 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <Download className="w-4 h-4" />
            {downloadingPdf ? 'Exporting PDF...' : 'Download PDF Report'}
          </button>
          <button
            onClick={() => handleDownloadReport(inspection.id, 'csv')}
            disabled={downloading}
            className="px-3.5 py-1.5 rounded-lg bg-blue-600/20 hover:bg-blue-600/30 text-xs font-semibold text-blue-300 border border-blue-500/30 transition flex items-center gap-1.5 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <Download className="w-4 h-4" />
            {downloading ? 'Exporting CSV...' : 'CSV Data'}
          </button>
          <button
            onClick={() => window.print()}
            className="px-3.5 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-xs font-semibold text-slate-200 border border-slate-700 transition flex items-center gap-1.5"
          >
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 17h2a2 2 0 002-2v-4a2 2 0 00-2-2H5a2 2 0 00-2 2v4a2 2 0 002 2h2m2 4h6a2 2 0 002-2v-4a2 2 0 00-2-2H9a2 2 0 00-2 2v4a2 2 0 002 2zm8-12V5a2 2 0 00-2-2H9a2 2 0 00-2 2v4h10z" />
            </svg>
            Print
          </button>
        </div>
      </div>

      {/* Main Title Card */}
      <div className="glass-card p-6 rounded-2xl border border-slate-800 flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="text-2xl font-black text-white">Inspection #{inspection.id} Report</h1>
            <SeverityBadge level={r?.severity_level} score={r?.severity_score} />
            <PriorityBadge level={r?.priority_level} />
          </div>
          <div className="text-xs text-slate-400 mt-1 flex flex-wrap items-center gap-3">
            <span>Asset: <strong className="text-white">{inspection.asset_name}</strong></span>
            <span>&bull;</span>
            <span>Inspector: <strong className="text-white">{inspection.inspector_name}</strong></span>
            <span>&bull;</span>
            <span className="font-mono">{new Date(inspection.timestamp).toLocaleString()}</span>
          </div>
        </div>
        {inspection.latitude && inspection.longitude && (
          <div className="text-xs font-mono bg-slate-900/80 px-3 py-1.5 rounded-lg border border-slate-700 text-slate-300">
            GPS: {inspection.latitude}, {inspection.longitude} ({inspection.location_source})
          </div>
        )}
      </div>

      {/* Image Visualization Suite */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
        <div className="lg:col-span-8 space-y-4">
          <div className="glass-card p-6 rounded-2xl border border-slate-800 space-y-4">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <h2 className="text-base font-bold text-white">Multi-Model AI Visualizations</h2>
              <div className="flex items-center gap-2">
                {['overlay', 'gradcam', 'mask', 'original'].map(tab => (
                  <button
                    key={tab}
                    onClick={() => setActiveTab(tab)}
                    className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition ${
                      activeTab === tab
                        ? 'bg-blue-600 text-white shadow-sm'
                        : 'text-slate-400 hover:text-white hover:bg-slate-800'
                    }`}
                  >
                    {tab === 'overlay' && 'Segmentation Overlay'}
                    {tab === 'gradcam' && 'Grad-CAM Saliency'}
                    {tab === 'mask' && 'Binary Mask'}
                    {tab === 'original' && 'Raw Image'}
                  </button>
                ))}
              </div>
            </div>

            <div className="bg-slate-950 rounded-xl overflow-hidden border border-slate-800 h-96 flex items-center justify-center">
              {activeTab === 'overlay' && r?.overlay_url && (
                <img src={r.overlay_url} alt="Overlay" className="max-h-full max-w-full object-contain" />
              )}
              {activeTab === 'gradcam' && r?.gradcam_url && (
                <img src={r.gradcam_url} alt="Grad-CAM" className="max-h-full max-w-full object-contain" />
              )}
              {activeTab === 'mask' && r?.mask_url && (
                <img src={r.mask_url} alt="Mask" className="max-h-full max-w-full object-contain bg-black" />
              )}
              {activeTab === 'original' && r?.original_url && (
                <img src={r.original_url} alt="Original" className="max-h-full max-w-full object-contain" />
              )}
            </div>

            <div className="text-xs text-slate-400 p-3 rounded-lg bg-slate-900/60 border border-slate-800 flex items-center justify-between">
              <div>
                <strong>Active View:</strong> {activeTab.toUpperCase()} &mdash;{' '}
                {activeTab === 'overlay' && 'U-Net segmentation with boundary contours and crack highlighting.'}
                {activeTab === 'gradcam' && 'Class activation heatmap indicating CNN focus areas.'}
                {activeTab === 'mask' && 'Clean binary defect mask used for skeletonization.'}
                {activeTab === 'original' && 'Original resolution surface photograph.'}
              </div>
              <span className="text-[11px] font-mono text-slate-500">{r?.image_width} &times; {r?.image_height} px</span>
            </div>
          </div>

          {/* Crack Geometry Metrics */}
          <div className="glass-card p-6 rounded-2xl border border-slate-800 space-y-4">
            <h2 className="text-base font-bold text-white">Crack Geometry & Quantitative Extraction</h2>
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
              <div className="p-3.5 rounded-xl bg-slate-900/80 border border-slate-800">
                <span className="text-xs text-slate-400">Total Defect Area</span>
                <div className="text-xl font-bold font-mono text-white mt-1">{r?.crack_area_px} px</div>
                <div className="text-[11px] text-slate-500">{(r?.crack_area_ratio * 100).toFixed(3)}% coverage</div>
              </div>
              <div className="p-3.5 rounded-xl bg-slate-900/80 border border-slate-800">
                <span className="text-xs text-slate-400">Skeleton Axis Length</span>
                <div className="text-xl font-bold font-mono text-indigo-400 mt-1">{r?.skeleton_length_px} px</div>
                <div className="text-[11px] text-slate-500">Thinned centerline</div>
              </div>
              <div className="p-3.5 rounded-xl bg-slate-900/80 border border-slate-800">
                <span className="text-xs text-slate-400">Mean Crack Aperture</span>
                <div className="text-xl font-bold font-mono text-purple-400 mt-1">{r?.mean_width_px} px</div>
                <div className="text-[11px] text-slate-500">Max aperture: {r?.max_width_px} px</div>
              </div>
              <div className="p-3.5 rounded-xl bg-slate-900/80 border border-slate-800">
                <span className="text-xs text-slate-400">Orientation & Topology</span>
                <div className="text-xl font-bold font-mono text-blue-400 mt-1">{r?.orientation_angle}&deg;</div>
                <div className="text-[11px] text-slate-500">{r?.num_branches} branches, {r?.num_components} segments</div>
              </div>
            </div>

            <div className="text-[11px] text-slate-500 italic">
              Note: Without on-site metric scale calibration (e.g. calibration target or known focal length), measurements are reported strictly in pixels to avoid misleading real-world claims.
            </div>
          </div>
        </div>

        {/* Right Sidebar: Quality, Severity, Priority, History */}
        <div className="lg:col-span-4 space-y-6">
          {/* Severity & Maintenance Card */}
          <div className="glass-card p-5 rounded-2xl border border-slate-800 space-y-4">
            <h3 className="text-sm font-bold text-white">Severity & Maintenance Evaluation</h3>
            <div className="space-y-2 text-xs">
              <div className="p-3 rounded-lg bg-slate-900/80 border border-slate-800 space-y-1">
                <span className="text-slate-400">Severity Assessment:</span>
                <div className="flex items-center gap-2">
                  <span className="font-bold text-white text-sm">{r?.severity_level}</span>
                  <span className="font-mono text-xs text-slate-400">(Score: {r?.severity_score}/100)</span>
                </div>
              </div>

              <div className="p-3 rounded-lg bg-slate-900/80 border border-slate-800 space-y-1">
                <span className="text-slate-400">Maintenance Priority:</span>
                <div className="font-bold text-white text-sm">{r?.priority_level}</div>
                <p className="text-[11px] text-slate-400 mt-1">{r?.priority_rationale}</p>
              </div>

              <div className="p-3 rounded-lg bg-blue-950/30 border border-blue-800/40 space-y-1">
                <strong className="text-blue-300">Action Plan:</strong>
                <p className="text-slate-300 text-xs">{r?.recommended_action}</p>
              </div>
            </div>
          </div>

          {/* Image Quality Audit */}
          <div className="glass-card p-5 rounded-2xl border border-slate-800 space-y-3">
            <h3 className="text-sm font-bold text-white">Image Quality Audit</h3>
            <div className="grid grid-cols-2 gap-2 text-xs">
              <div className="p-2.5 rounded-lg bg-slate-900/60 border border-slate-800">
                <span className="text-slate-400">Blur Score (Laplacian)</span>
                <div className="font-mono font-bold text-white mt-0.5">{r?.blur_score}</div>
                <div className="text-[10px] text-slate-500">{r?.is_blurry ? 'Blurry' : 'Sharp / Adequate'}</div>
              </div>
              <div className="p-2.5 rounded-lg bg-slate-900/60 border border-slate-800">
                <span className="text-slate-400">Illumination (Mean)</span>
                <div className="font-mono font-bold text-white mt-0.5">{r?.brightness_mean}</div>
                <div className="text-[10px] text-slate-500">{r?.is_low_light ? 'Low light' : 'Good exposure'}</div>
              </div>
            </div>
          </div>

          {/* Historical Progression */}
          {history && history.timeline && history.timeline.length > 1 && (
            <div className="glass-card p-5 rounded-2xl border border-slate-800 space-y-3">
              <h3 className="text-sm font-bold text-white">Historical Defect Progression</h3>
              <p className="text-xs text-slate-400">Previous inspections recorded for this asset:</p>
              <div className="space-y-2">
                {history.timeline.map((item, idx) => (
                  <div key={idx} className="p-2.5 rounded-lg bg-slate-900/80 border border-slate-800 flex items-center justify-between text-xs">
                    <div>
                      <div className="font-mono text-slate-300">{item.timestamp}</div>
                      <div className="text-[11px] text-slate-400">Area: {item.crack_area_px} px</div>
                    </div>
                    <SeverityBadge level={item.severity_level} />
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
