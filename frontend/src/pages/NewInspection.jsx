import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import SeverityBadge from '../components/SeverityBadge';
import PriorityBadge from '../components/PriorityBadge';

export default function NewInspection() {
  const navigate = useNavigate();
  const { user, token } = useAuth();
  const [assets, setAssets] = useState([]);
  const [selectedAsset, setSelectedAsset] = useState('');
  const [inspectorName, setInspectorName] = useState(user?.full_name || user?.username || 'Civil Engineer Inspector');
  const [notes, setNotes] = useState('');
  const [manualLat, setManualLat] = useState('');
  const [manualLon, setManualLon] = useState('');
  const [imageFile, setImageFile] = useState(null);
  const [imagePreview, setImagePreview] = useState(null);
  const [analyzing, setAnalyzing] = useState(false);
  const [analysisStep, setAnalysisStep] = useState('');
  const [result, setResult] = useState(null);
  const [activeTab, setActiveTab] = useState('overlay');

  useEffect(() => {
    fetch('/api/assets')
      .then(r => r.json())
      .then(data => setAssets(data))
      .catch(console.error);
  }, []);

  const handleImageChange = (e) => {
    const file = e.target.files[0];
    if (file) {
      setImageFile(file);
      setImagePreview(URL.createObjectURL(file));
      setResult(null);
    }
  };

  const handleAnalyze = async (e) => {
    e.preventDefault();
    if (!imageFile) {
      alert('Please select an infrastructure surface image.');
      return;
    }

    setAnalyzing(true);
    setAnalysisStep('Uploading & assessing image quality...');

    const formData = new FormData();
    formData.append('image', imageFile);
    if (selectedAsset) formData.append('asset_id', selectedAsset);
    formData.append('inspector_name', inspectorName);
    if (notes) formData.append('notes', notes);
    if (manualLat) formData.append('manual_latitude', manualLat);
    if (manualLon) formData.append('manual_longitude', manualLon);

    try {
      setTimeout(() => setAnalysisStep('Running Crack Classification & Surface Identification...'), 500);
      setTimeout(() => setAnalysisStep('Running U-Net Semantic Crack Segmentation...'), 1200);
      setTimeout(() => setAnalysisStep('Extracting Crack Geometry & Measurements...'), 2000);
      setTimeout(() => setAnalysisStep('Evaluating Preliminary Damage Severity & Maintenance Priority...'), 2800);
      setTimeout(() => setAnalysisStep('Computing Grad-CAM Explainable AI Heatmap...'), 3500);

      const headers = {};
      if (token) {
        headers['Authorization'] = `Bearer ${token}`;
      }

      const res = await fetch('/api/inspections/analyze', {
        method: 'POST',
        headers,
        body: formData
      });

      if (!res.ok) {
        throw new Error('Analysis failed on server.');
      }

      const data = await res.json();
      setResult(data);
    } catch (err) {
      alert('Inspection analysis error: ' + err.message);
    } finally {
      setAnalyzing(false);
      setAnalysisStep('');
    }
  };

  const r = result?.result;

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8">
      <div>
        <h1 className="text-2xl font-black text-white tracking-tight">AI Infrastructure Surface Inspection</h1>
        <p className="text-sm text-slate-400 mt-1">
          Upload surface imagery of bridges, pavements, tunnels, or concrete structures for automated multi-model crack assessment.
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
        {/* Upload Form */}
        <div className="lg:col-span-5 space-y-6">
          <form onSubmit={handleAnalyze} className="glass-card p-6 rounded-2xl border border-slate-800 space-y-5">
            <h2 className="text-base font-bold text-white">Inspection Inputs</h2>

            {/* Image Drop Zone */}
            <div className="space-y-2">
              <label className="text-xs font-semibold text-slate-300">Surface Image <span className="text-rose-400">*</span></label>
              <div className="border-2 border-dashed border-slate-700 hover:border-blue-500 rounded-xl p-4 text-center cursor-pointer transition bg-slate-900/50">
                <input
                  type="file"
                  accept="image/*"
                  onChange={handleImageChange}
                  className="hidden"
                  id="image-upload-input"
                />
                <label htmlFor="image-upload-input" className="cursor-pointer block">
                  {imagePreview ? (
                    <div className="relative group">
                      <img src={imagePreview} alt="Preview" className="w-full h-48 object-cover rounded-lg border border-slate-700" />
                      <div className="absolute inset-0 bg-slate-950/60 opacity-0 group-hover:opacity-100 flex items-center justify-center rounded-lg transition text-xs font-semibold text-white">
                        Click to change image
                      </div>
                    </div>
                  ) : (
                    <div className="py-8 space-y-2">
                      <div className="w-12 h-12 rounded-full bg-blue-500/10 text-blue-400 mx-auto flex items-center justify-center">
                        <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
                        </svg>
                      </div>
                      <div className="text-xs font-medium text-slate-300">
                        <span className="text-blue-400 font-bold">Click to upload</span> or drag and drop
                      </div>
                      <div className="text-[11px] text-slate-500">JPG, PNG, TIFF up to 25MB</div>
                    </div>
                  )}
                </label>
              </div>
            </div>

            {/* Asset Selection */}
            <div className="space-y-1.5">
              <label className="text-xs font-semibold text-slate-300">Target Infrastructure Asset</label>
              <select
                value={selectedAsset}
                onChange={e => setSelectedAsset(e.target.value)}
                className="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-xs text-white focus:outline-none focus:border-blue-500"
              >
                <option value="">Unassigned (Standalone Image)</option>
                {assets.map(a => (
                  <option key={a.id} value={a.id}>{a.name} ({a.type})</option>
                ))}
              </select>
            </div>

            {/* Inspector Name */}
            <div className="space-y-1.5">
              <label className="text-xs font-semibold text-slate-300">Inspector Name</label>
              <input
                type="text"
                value={inspectorName}
                onChange={e => setInspectorName(e.target.value)}
                className="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-xs text-white focus:outline-none focus:border-blue-500"
              />
            </div>

            {/* Location (Manual entry or EXIF auto) */}
            <div className="space-y-1.5">
              <div className="flex justify-between items-center">
                <label className="text-xs font-semibold text-slate-300">GPS Coordinates</label>
                <span className="text-[10px] text-slate-500">Auto-extracted from EXIF if present</span>
              </div>
              <div className="grid grid-cols-2 gap-2">
                <input
                  type="number"
                  step="0.0001"
                  placeholder="Latitude (e.g. 28.5355)"
                  value={manualLat}
                  onChange={e => setManualLat(e.target.value)}
                  className="bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-xs text-white focus:outline-none focus:border-blue-500"
                />
                <input
                  type="number"
                  step="0.0001"
                  placeholder="Longitude (e.g. 77.3910)"
                  value={manualLon}
                  onChange={e => setManualLon(e.target.value)}
                  className="bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-xs text-white focus:outline-none focus:border-blue-500"
                />
              </div>
            </div>

            {/* Notes */}
            <div className="space-y-1.5">
              <label className="text-xs font-semibold text-slate-300">Field Notes / Structural Observations</label>
              <textarea
                rows={3}
                placeholder="Observed flexural crack pattern, moisture, spalling, or environmental factors..."
                value={notes}
                onChange={e => setNotes(e.target.value)}
                className="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-xs text-white focus:outline-none focus:border-blue-500"
              />
            </div>

            {/* Submit Button */}
            <button
              type="submit"
              disabled={analyzing || !imageFile}
              className="w-full py-3 rounded-xl bg-blue-600 hover:bg-blue-500 disabled:opacity-50 text-white font-bold text-sm shadow-lg shadow-blue-600/30 transition flex items-center justify-center gap-2"
            >
              {analyzing ? (
                <>
                  <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
                  Analyzing Surface...
                </>
              ) : (
                'Run AI Inspection'
              )}
            </button>

            {analyzing && (
              <div className="p-3 rounded-lg bg-blue-950/40 border border-blue-800/40 text-xs text-blue-300 flex items-center gap-2">
                <span className="w-2 h-2 rounded-full bg-blue-400 animate-ping"></span>
                <span>{analysisStep}</span>
              </div>
            )}
          </form>
        </div>

        {/* Results Panel */}
        <div className="lg:col-span-7">
          {r ? (
            <div className="space-y-6">
              {/* Header Badges */}
              <div className="glass-card p-6 rounded-2xl border border-slate-800 space-y-4">
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <div>
                    <h2 className="text-xl font-black text-white">Inspection #{result.id} Assessment</h2>
                    <div className="text-xs text-slate-400 mt-0.5">Surface Type: <strong className="text-slate-200">{r.surface_type}</strong></div>
                  </div>
                  <div className="flex items-center gap-2">
                    <SeverityBadge level={r.severity_level} score={r.severity_score} />
                    <PriorityBadge level={r.priority_level} />
                  </div>
                </div>

                {/* Tabbed Visualizer */}
                <div className="space-y-3">
                  <div className="flex items-center gap-2 border-b border-slate-800 pb-2">
                    {['overlay', 'gradcam', 'mask', 'original'].map(tab => (
                      <button
                        key={tab}
                        type="button"
                        onClick={() => setActiveTab(tab)}
                        className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition ${
                          activeTab === tab
                            ? 'bg-blue-600 text-white shadow-sm'
                            : 'text-slate-400 hover:text-white hover:bg-slate-800'
                        }`}
                      >
                        {tab === 'overlay' && 'Segmentation Overlay'}
                        {tab === 'gradcam' && 'Grad-CAM Explainable AI'}
                        {tab === 'mask' && 'Binary Crack Mask'}
                        {tab === 'original' && 'Original Surface'}
                      </button>
                    ))}
                  </div>

                  <div className="relative rounded-xl overflow-hidden bg-slate-950 border border-slate-800 h-80 flex items-center justify-center">
                    {activeTab === 'overlay' && r.overlay_url && (
                      <img src={r.overlay_url} alt="Overlay" className="max-h-full max-w-full object-contain" />
                    )}
                    {activeTab === 'gradcam' && r.gradcam_url && (
                      <img src={r.gradcam_url} alt="Grad-CAM" className="max-h-full max-w-full object-contain" />
                    )}
                    {activeTab === 'mask' && r.mask_url && (
                      <img src={r.mask_url} alt="Mask" className="max-h-full max-w-full object-contain bg-black" />
                    )}
                    {activeTab === 'original' && r.original_url && (
                      <img src={r.original_url} alt="Original" className="max-h-full max-w-full object-contain" />
                    )}
                  </div>
                  {activeTab === 'gradcam' && (
                    <p className="text-[11px] text-slate-400 italic">
                      Grad-CAM activation highlights spatial regions that most influenced the CNN classification. Does not imply physical causation.
                    </p>
                  )}
                </div>

                {/* Geometry Table */}
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 pt-2">
                  <div className="p-3 rounded-lg bg-slate-900/60 border border-slate-800">
                    <span className="text-[11px] text-slate-400">Crack Area</span>
                    <div className="text-base font-bold font-mono text-white mt-0.5">{r.crack_area_px} px</div>
                    <div className="text-[10px] text-slate-500">{(r.crack_area_ratio * 100).toFixed(2)}% of surface</div>
                  </div>
                  <div className="p-3 rounded-lg bg-slate-900/60 border border-slate-800">
                    <span className="text-[11px] text-slate-400">Skeleton Length</span>
                    <div className="text-base font-bold font-mono text-indigo-400 mt-0.5">{r.skeleton_length_px} px</div>
                    <div className="text-[10px] text-slate-500">Trajectory axis</div>
                  </div>
                  <div className="p-3 rounded-lg bg-slate-900/60 border border-slate-800">
                    <span className="text-[11px] text-slate-400">Mean Aperture</span>
                    <div className="text-base font-bold font-mono text-purple-400 mt-0.5">{r.mean_width_px} px</div>
                    <div className="text-[10px] text-slate-500">Max: {r.max_width_px} px</div>
                  </div>
                  <div className="p-3 rounded-lg bg-slate-900/60 border border-slate-800">
                    <span className="text-[11px] text-slate-400">Orientation</span>
                    <div className="text-base font-bold font-mono text-blue-400 mt-0.5">{r.orientation_angle}&deg;</div>
                    <div className="text-[10px] text-slate-500">{r.num_branches} branch points</div>
                  </div>
                </div>

                {/* Severity Reasons & Recommendations */}
                <div className="space-y-2 pt-2 border-t border-slate-800">
                  <h3 className="text-xs font-bold text-slate-200 uppercase tracking-wider">Severity Rationale</h3>
                  <ul className="space-y-1 text-xs text-slate-300">
                    {r.severity_reasons.map((reason, idx) => (
                      <li key={idx} className="flex items-start gap-1.5">
                        <span className="text-blue-400 font-bold">&bull;</span>
                        <span>{reason}</span>
                      </li>
                    ))}
                  </ul>
                  <div className="mt-3 p-3 rounded-lg bg-slate-900/80 border border-slate-800 text-xs text-slate-300 space-y-1">
                    <strong className="text-white">Recommended Maintenance Action:</strong>
                    <p>{r.recommended_action}</p>
                  </div>
                </div>

                {/* Legal / Engineering Disclaimer */}
                <div className="p-3 rounded-lg bg-amber-950/20 border border-amber-800/30 text-[11px] text-amber-300/80">
                  <strong>Engineering Notice:</strong> Automated preliminary assessment based on visual machine learning models. Does not substitute for certified structural engineering on-site evaluation.
                </div>
              </div>
            </div>
          ) : (
            <div className="glass-card p-12 rounded-2xl border border-slate-800 text-center flex flex-col items-center justify-center min-h-[500px]">
              <div className="w-16 h-16 rounded-2xl bg-slate-800/80 border border-slate-700/80 flex items-center justify-center text-slate-400 mb-4">
                <svg className="w-8 h-8" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                </svg>
              </div>
              <h3 className="text-lg font-bold text-white">No Inspection Processed Yet</h3>
              <p className="text-xs text-slate-400 max-w-sm mt-1">
                Select an infrastructure surface photo on the left and click "Run AI Inspection" to view crack classification, U-Net masks, and geometry metrics.
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
