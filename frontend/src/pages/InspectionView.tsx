import React, { useState, useEffect, useRef } from 'react';
import { useParams, Link } from 'react-router-dom';
import api from '../api/client';
import { 
  ArrowLeft, 
  Upload, 
  Camera, 
  CheckCircle, 
  AlertTriangle, 
  Sun, 
  Sliders, 
  Calendar, 
  User as UserIcon,
  RefreshCw,
  Eye,
  Building2,
  FileText,
  Sparkles,
  ShieldAlert,
  Layers,
  Box,
  Ruler,
  Maximize2,
  X,
  Activity,
  CheckCircle2,
  Clock,
  Download,
  RotateCw,
  GitCompare,
  FileSpreadsheet,
  FileCode,
  SlidersHorizontal,
  ChevronRight
} from 'lucide-react';
import { Inspection, InspectionImage, QualityStatus, InspectionComparisonData } from '../types';
import { useAuth } from '../context/AuthContext';

export const InspectionView: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const { user } = useAuth();
  const [inspection, setInspection] = useState<Inspection | null>(null);
  const [images, setImages] = useState<InspectionImage[]>([]);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [analyzing, setAnalyzing] = useState(false);
  const [dragActive, setDragActive] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Status update
  const [status, setStatus] = useState<string>('pending');
  const [updatingStatus, setUpdatingStatus] = useState(false);

  // Preview Modal for Original vs Enhanced CLAHE vs AI Grad-CAM vs Mask vs Boxes
  const [previewImage, setPreviewImage] = useState<InspectionImage | null>(null);
  type PreviewMode = 
    | 'original' | 'enhanced' | 'sharpen' | 'shadow_reduction' | 'edge' | 'texture' | 'roi'
    | 'gradcam' | 'gradcam_plus' | 'saliency' | 'mask' | 'skeleton' | 'boxes';
  const [previewMode, setPreviewMode] = useState<PreviewMode>('original');
  const [calibrationMm, setCalibrationMm] = useState<number>(0.2);
  const [calibrating, setCalibrating] = useState(false);

  // Reports
  const [downloadingFormat, setDownloadingFormat] = useState<string | null>(null);

  // Camera Capture Modal
  const [showCameraModal, setShowCameraModal] = useState(false);
  const [cameraStream, setCameraStream] = useState<MediaStream | null>(null);
  const [capturedBlob, setCapturedBlob] = useState<Blob | null>(null);
  const [capturedDataUrl, setCapturedDataUrl] = useState<string | null>(null);
  const [rotationAngle, setRotationAngle] = useState(0);
  const videoRef = useRef<HTMLVideoElement>(null);

  // Comparison with Previous Inspection
  const [priorInspections, setPriorInspections] = useState<Inspection[]>([]);
  const [selectedPriorId, setSelectedPriorId] = useState<number | null>(null);
  const [comparisonData, setComparisonData] = useState<InspectionComparisonData | null>(null);
  const [showComparisonModal, setShowComparisonModal] = useState(false);
  const [loadingComparison, setLoadingComparison] = useState(false);

  const fetchInspectionData = async () => {
    setLoading(true);
    try {
      const [inspRes, imgsRes] = await Promise.all([
        api.get<Inspection>(`/inspections/${id}`),
        api.get<InspectionImage[]>(`/inspections/${id}/images`),
      ]);
      setInspection(inspRes.data);
      setStatus(inspRes.data.status);
      setImages(imgsRes.data);

      // Fetch other inspections of same asset for historical comparison
      if (inspRes.data.asset_id) {
        const othersRes = await api.get<Inspection[]>(`/inspections/?asset_id=${inspRes.data.asset_id}`);
        const others = othersRes.data.filter((i) => i.id !== Number(id));
        setPriorInspections(others);
        if (others.length > 0) {
          setSelectedPriorId(others[0].id);
        }
      }
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to load inspection');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchInspectionData();
  }, [id]);

  // Report downloads
  const handleDownload = async (format: 'pdf' | 'csv' | 'excel' | 'json') => {
    if (!id) return;
    try {
      setDownloadingFormat(format);
      setError('');
      if (format === 'json') {
        const res = await api.get(`/inspections/${id}/report/json`);
        const blob = new Blob([JSON.stringify(res.data, null, 2)], { type: 'application/json' });
        const link = document.createElement('a');
        link.href = window.URL.createObjectURL(blob);
        link.download = `InfraScan_Inspection_${id}_Data.json`;
        link.click();
      } else {
        const ext = format === 'pdf' ? 'pdf' : format === 'csv' ? 'csv' : 'xlsx';
        const res = await api.get(`/inspections/${id}/report/${format}`, { responseType: 'blob' });
        const link = document.createElement('a');
        link.href = window.URL.createObjectURL(new Blob([res.data]));
        link.download = `InfraScan_Inspection_${id}_Report.${ext}`;
        link.click();
      }
      setSuccess(`Report exported in ${format.toUpperCase()} format.`);
    } catch (e: any) {
      setError(`Failed to generate ${format.toUpperCase()} report.`);
    } finally {
      setDownloadingFormat(null);
    }
  };

  // Status update
  const handleStatusChange = async (newStatus: string) => {
    setUpdatingStatus(true);
    try {
      await api.put(`/inspections/${id}`, { status: newStatus });
      setStatus(newStatus);
      setSuccess('Inspection status updated successfully.');
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to update inspection status');
    } finally {
      setUpdatingStatus(false);
    }
  };

  // Analyze all images
  const handleRunFullAnalysis = async () => {
    setAnalyzing(true);
    setError('');
    setSuccess('');
    try {
      const res = await api.post(`/inspections/${id}/analyze`);
      setImages(res.data.images || []);
      setSuccess(`AI analysis completed: ${res.data.cracked_count} cracked surfaces identified.`);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'AI analysis failed');
    } finally {
      setAnalyzing(false);
    }
  };

  // File upload handling
  const handleFiles = async (filesList: FileList | null) => {
    if (!filesList || filesList.length === 0) return;
    setUploading(true);
    setError('');
    setSuccess('');

    const formData = new FormData();
    for (let i = 0; i < filesList.length; i++) {
      formData.append('files', filesList[i]);
    }

    try {
      const res = await api.post<InspectionImage[]>(`/inspections/${id}/images`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });
      setImages((prev) => [...res.data, ...prev]);
      setSuccess(`Successfully uploaded and analyzed ${res.data.length} inspection image(s).`);
      if (fileInputRef.current) fileInputRef.current.value = '';
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Image validation / upload failed');
    } finally {
      setUploading(false);
    }
  };

  // Live Camera handlers
  const startCamera = async () => {
    setShowCameraModal(true);
    setCapturedBlob(null);
    setCapturedDataUrl(null);
    setRotationAngle(0);
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: { facingMode: 'environment', width: { ideal: 1280 }, height: { ideal: 720 } }
      });
      setCameraStream(stream);
      if (videoRef.current) {
        videoRef.current.srcObject = stream;
      }
    } catch (e) {
      setError('Camera access denied or unavailable on this device.');
      setShowCameraModal(false);
    }
  };

  const stopCamera = () => {
    if (cameraStream) {
      cameraStream.getTracks().forEach((track) => track.stop());
      setCameraStream(null);
    }
    setShowCameraModal(false);
  };

  const capturePhoto = () => {
    if (!videoRef.current) return;
    const canvas = document.createElement('canvas');
    canvas.width = videoRef.current.videoWidth || 1280;
    canvas.height = videoRef.current.videoHeight || 720;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    if (rotationAngle !== 0) {
      ctx.translate(canvas.width / 2, canvas.height / 2);
      ctx.rotate((rotationAngle * Math.PI) / 180);
      ctx.drawImage(videoRef.current, -canvas.width / 2, -canvas.height / 2);
    } else {
      ctx.drawImage(videoRef.current, 0, 0);
    }

    canvas.toBlob((blob) => {
      if (blob) {
        setCapturedBlob(blob);
        setCapturedDataUrl(canvas.toDataURL('image/jpeg'));
      }
    }, 'image/jpeg', 0.95);
  };

  const uploadCapturedPhoto = async () => {
    if (!capturedBlob) return;
    setUploading(true);
    setError('');
    const file = new File([capturedBlob], `camera_${Date.now()}.jpg`, { type: 'image/jpeg' });
    const formData = new FormData();
    formData.append('files', file);

    try {
      const res = await api.post<InspectionImage[]>(`/inspections/${id}/images`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });
      setImages((prev) => [...res.data, ...prev]);
      setSuccess('Camera photo captured, validated, and analyzed successfully.');
      stopCamera();
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to upload captured photo');
    } finally {
      setUploading(false);
    }
  };

  // Scale calibration update
  const handleUpdateCalibration = async () => {
    if (!previewImage) return;
    setCalibrating(true);
    try {
      const res = await api.put<InspectionImage>(`/images/${previewImage.id}/calibration?calibration_mm_per_px=${calibrationMm}`);
      setPreviewImage(res.data);
      setImages(images.map((img) => (img.id === res.data.id ? res.data : img)));
      setSuccess(`Calibrated scale updated to ${calibrationMm} mm/px.`);
    } catch (e: any) {
      setError('Failed to update scale calibration.');
    } finally {
      setCalibrating(false);
    }
  };

  // Compare with historical inspection
  const handleRunComparison = async () => {
    if (!selectedPriorId) return;
    setLoadingComparison(true);
    try {
      const res = await api.get<InspectionComparisonData>(`/inspections/${id}/compare/${selectedPriorId}`);
      setComparisonData(res.data);
      setShowComparisonModal(true);
    } catch (e: any) {
      setError('Failed to perform historical inspection comparison.');
    } finally {
      setLoadingComparison(false);
    }
  };

  const getQualityBadge = (status: QualityStatus, blur?: number, bright?: number) => {
    if (status === 'ok') {
      return (
        <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[11px] font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200">
          <CheckCircle className="w-3 h-3" />
          <span>Optimal Quality</span>
        </span>
      );
    }
    if (status === 'blurry') {
      return (
        <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[11px] font-semibold bg-amber-50 text-amber-700 border border-amber-200">
          <AlertTriangle className="w-3 h-3" />
          <span>Blurry ({blur} LVar)</span>
        </span>
      );
    }
    return (
      <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[11px] font-semibold bg-orange-50 text-orange-700 border border-orange-200">
        <Sun className="w-3 h-3" />
        <span>Low Light ({bright} Br)</span>
      </span>
    );
  };

  const getDamageBadge = (hasCrack?: boolean, conf?: number, sev?: string) => {
    if (hasCrack === true) {
      return (
        <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[11px] font-bold bg-rose-50 text-rose-700 border border-rose-200">
          <ShieldAlert className="w-3.5 h-3.5" />
          <span>Crack ({conf ? `${(conf * 100).toFixed(1)}%` : ''}) • {sev}</span>
        </span>
      );
    }
    if (hasCrack === false) {
      return (
        <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[11px] font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200">
          <CheckCircle2 className="w-3 h-3" />
          <span>Sound / Intact</span>
        </span>
      );
    }
    return (
      <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[11px] font-semibold bg-slate-100 text-slate-600">
        <Clock className="w-3 h-3" />
        <span>Pending AI Analysis</span>
      </span>
    );
  };

  if (loading) {
    return (
      <div className="py-24 text-center text-slate-500">
        <div className="w-10 h-10 border-4 border-blue-600 border-t-transparent rounded-full animate-spin mx-auto mb-3"></div>
        <p className="text-sm font-medium">Loading inspection imagery and deep learning diagnostics...</p>
      </div>
    );
  }

  if (!inspection) {
    return (
      <div className="py-24 text-center text-slate-500">
        <p className="text-base font-semibold text-slate-800">Inspection record not found.</p>
        <Link to="/assets" className="btn-primary mt-4 inline-flex items-center gap-2">
          <ArrowLeft className="w-4 h-4" />
          <span>Return to Assets</span>
        </Link>
      </div>
    );
  }

  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      {/* ── Breadcrumb & Back ────────────────────────────────────────────── */}
      <div className="flex items-center gap-2 text-xs text-slate-500">
        <Link to="/assets" className="hover:text-blue-600 flex items-center gap-1">
          <ArrowLeft className="w-3.5 h-3.5" />
          <span>Assets</span>
        </Link>
        <span>/</span>
        <Link to={`/assets/${inspection.asset_id}`} className="hover:text-blue-600 font-medium">
          {inspection.asset?.name || `Asset #${inspection.asset_id}`}
        </Link>
        <span>/</span>
        <span className="text-slate-900 font-semibold">Inspection #{inspection.id}</span>
      </div>

      {/* ── Header Card ─────────────────────────────────────────────────── */}
      <div className="card p-6 border-slate-200/80 space-y-4">
        <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4">
          <div className="space-y-1.5">
            <div className="flex items-center gap-2">
              <span className="font-mono text-xs font-bold text-slate-400 bg-slate-100 px-2 py-0.5 rounded">
                INSP-{String(inspection.id).padStart(4, '0')}
              </span>
              <span className={`px-2.5 py-0.5 rounded-full text-xs font-bold ${
                status === 'completed' ? 'bg-emerald-50 text-emerald-700 border border-emerald-200' :
                status === 'in_progress' ? 'bg-blue-50 text-blue-700 border border-blue-200' :
                'bg-amber-50 text-amber-700 border border-amber-200'
              }`}>
                {status.toUpperCase()}
              </span>
            </div>
            <h1 className="text-2xl font-bold text-slate-900 tracking-tight">
              {inspection.asset?.name || `Asset #${inspection.asset_id}`}
            </h1>
            <p className="text-xs sm:text-sm text-slate-500 flex items-center gap-4 flex-wrap">
              <span className="flex items-center gap-1">
                <Calendar className="w-4 h-4 text-slate-400" />
                <span>Date: {inspection.inspection_date || 'N/A'}</span>
              </span>
              <span className="flex items-center gap-1">
                <UserIcon className="w-4 h-4 text-slate-400" />
                <span>Inspector: {inspection.inspector?.full_name || 'Unassigned'}</span>
              </span>
            </p>
          </div>

          {/* Action Buttons: Camera Capture, AI Analysis, Export Reports */}
          <div className="flex items-center gap-2 flex-wrap">
            <button
              onClick={startCamera}
              className="btn-secondary text-xs py-2 px-3 flex items-center gap-1.5 bg-white border-slate-300 hover:bg-slate-50"
            >
              <Camera className="w-3.5 h-3.5 text-blue-600" />
              <span>Camera Capture</span>
            </button>

            <button
              onClick={handleRunFullAnalysis}
              disabled={analyzing || images.length === 0}
              className="btn-secondary text-xs py-2 px-3 flex items-center gap-1.5 bg-white border-slate-300 hover:bg-slate-50"
            >
              <Sparkles className={`w-3.5 h-3.5 text-blue-600 ${analyzing ? 'animate-spin' : ''}`} />
              <span>{analyzing ? 'Analyzing...' : 'Re-Run AI Engine'}</span>
            </button>

            {priorInspections.length > 0 && (
              <button
                onClick={handleRunComparison}
                disabled={loadingComparison}
                className="btn-secondary text-xs py-2 px-3 flex items-center gap-1.5 bg-white border-slate-300 hover:bg-slate-50"
              >
                <GitCompare className="w-3.5 h-3.5 text-indigo-600" />
                <span>Compare Historical</span>
              </button>
            )}

            {/* Export Dropdown / Buttons */}
            <div className="flex items-center gap-1 bg-slate-100 p-1 rounded-xl">
              <button
                onClick={() => handleDownload('pdf')}
                disabled={downloadingFormat === 'pdf'}
                className="px-2.5 py-1.5 text-xs font-bold rounded-lg bg-white text-slate-700 shadow-xs hover:text-blue-600 flex items-center gap-1"
                title="Download Structural Assessment PDF"
              >
                <Download className="w-3 h-3 text-blue-600" />
                <span>PDF</span>
              </button>
              <button
                onClick={() => handleDownload('csv')}
                disabled={downloadingFormat === 'csv'}
                className="px-2 py-1.5 text-xs font-bold rounded-lg hover:bg-white text-slate-600 hover:text-blue-600"
                title="Download CSV Table"
              >
                CSV
              </button>
              <button
                onClick={() => handleDownload('excel')}
                disabled={downloadingFormat === 'excel'}
                className="px-2 py-1.5 text-xs font-bold rounded-lg hover:bg-white text-slate-600 hover:text-emerald-600 flex items-center gap-0.5"
                title="Download Excel Workbook (.xlsx)"
              >
                <FileSpreadsheet className="w-3 h-3 text-emerald-600" />
                <span>Excel</span>
              </button>
              <button
                onClick={() => handleDownload('json')}
                disabled={downloadingFormat === 'json'}
                className="px-2 py-1.5 text-xs font-bold rounded-lg hover:bg-white text-slate-600 hover:text-indigo-600 flex items-center gap-0.5"
                title="Download Full JSON Data"
              >
                <FileCode className="w-3 h-3 text-indigo-600" />
                <span>JSON</span>
              </button>
            </div>
          </div>
        </div>

        {/* Status Changer Bar */}
        <div className="pt-3 border-t border-slate-100 flex items-center justify-between gap-4 flex-wrap text-xs">
          <div className="flex items-center gap-2">
            <span className="font-semibold text-slate-700">Workflow State:</span>
            {['pending', 'in_progress', 'completed'].map((st) => (
              <button
                key={st}
                onClick={() => handleStatusChange(st)}
                disabled={updatingStatus}
                className={`px-3 py-1 rounded-lg font-bold capitalize transition-all ${
                  status === st
                    ? 'bg-slate-900 text-white shadow-xs'
                    : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
                }`}
              >
                {st.replace('_', ' ')}
              </button>
            ))}
          </div>
          <span className="text-slate-400">
            {images.length} Image{images.length !== 1 ? 's' : ''} Uploaded • {images.filter(i => i.has_crack).length} Cracks Detected
          </span>
        </div>
      </div>

      {/* Alerts */}
      {error && (
        <div className="p-4 rounded-xl bg-rose-50 border border-rose-200 text-xs font-medium text-rose-700 flex items-center gap-2">
          <AlertTriangle className="w-4 h-4 shrink-0" />
          <span>{error}</span>
        </div>
      )}
      {success && (
        <div className="p-4 rounded-xl bg-emerald-50 border border-emerald-200 text-xs font-medium text-emerald-700 flex items-center gap-2">
          <CheckCircle2 className="w-4 h-4 shrink-0" />
          <span>{success}</span>
        </div>
      )}

      {/* ── Drag & Drop Upload Zone (Module 3) ───────────────────────────── */}
      <div
        onDragOver={(e) => { e.preventDefault(); setDragActive(true); }}
        onDragLeave={() => setDragActive(false)}
        onDrop={(e) => {
          e.preventDefault();
          setDragActive(false);
          handleFiles(e.dataTransfer.files);
        }}
        className={`card p-8 border-2 border-dashed transition-all text-center ${
          dragActive ? 'border-blue-500 bg-blue-50/50 scale-[1.005]' : 'border-slate-300 hover:border-slate-400'
        }`}
      >
        <div className="max-w-md mx-auto space-y-3">
          <div className="h-12 w-12 rounded-2xl bg-blue-50 text-blue-600 flex items-center justify-center mx-auto shadow-inner">
            <Upload className="w-6 h-6" />
          </div>
          <div>
            <p className="text-sm font-bold text-slate-900">
              Drag and drop inspection imagery here, or browse files
            </p>
            <p className="text-xs text-slate-500 mt-1">
              Supports JPG, JPEG, PNG from mobile cameras, digital DSLRs, and aerial drone captures.
            </p>
          </div>
          <div className="pt-2 flex justify-center gap-3">
            <input
              ref={fileInputRef}
              type="file"
              multiple
              accept=".jpg,.jpeg,.png"
              onChange={(e) => handleFiles(e.target.files)}
              className="hidden"
              id="file-upload"
            />
            <label
              htmlFor="file-upload"
              className="btn-primary text-xs py-2 px-4 cursor-pointer inline-flex items-center gap-2"
            >
              <Upload className="w-4 h-4" />
              <span>{uploading ? 'Validating & Uploading...' : 'Select Images'}</span>
            </label>
            <button
              onClick={startCamera}
              className="btn-secondary text-xs py-2 px-3.5 inline-flex items-center gap-2"
            >
              <Camera className="w-4 h-4 text-blue-600" />
              <span>Use Camera</span>
            </button>
          </div>
        </div>
      </div>

      {/* ── Image Gallery & Defect Records (Modules 5, 6, 8, 9) ─────────── */}
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="text-base font-bold text-slate-900 flex items-center gap-2">
            <Layers className="w-4 h-4 text-blue-600" />
            <span>Inspection Images & AI Diagnostics ({images.length})</span>
          </h2>
        </div>

        {images.length === 0 ? (
          <div className="card p-12 text-center text-slate-400 text-xs">
            <Camera className="w-10 h-10 mx-auto mb-2 text-slate-300" />
            <p className="font-semibold text-slate-700">No inspection imagery uploaded yet.</p>
            <p className="mt-1">Capture photos from the mobile camera or upload image files above.</p>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
            {images.map((img) => (
              <div key={img.id} className="card p-4 space-y-3 hover:shadow-card-hover transition-all">
                {/* Thumbnail with overlay view button */}
                <div className="relative aspect-4/3 bg-slate-950 rounded-xl overflow-hidden group">
                  <img
                    src={`http://localhost:8000/uploads/${img.file_path}`}
                    alt={img.original_filename}
                    className="w-full h-full object-cover"
                  />
                  <div className="absolute inset-0 bg-slate-900/60 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center gap-2">
                    <button
                      onClick={() => {
                        setPreviewImage(img);
                        setPreviewMode('original');
                        setCalibrationMm(img.calibration_mm_per_px || 0.2);
                      }}
                      className="btn-primary text-xs py-1.5 px-3 flex items-center gap-1.5 shadow-lg"
                    >
                      <Eye className="w-3.5 h-3.5" />
                      <span>Diagnostics & XAI</span>
                    </button>
                  </div>

                  <div className="absolute top-2 left-2 flex gap-1">
                    {getQualityBadge(img.quality_status, img.blur_score, img.brightness)}
                  </div>
                </div>

                {/* Status Badges */}
                <div className="space-y-2 pt-1">
                  <div>{getDamageBadge(img.has_crack, img.confidence_score, img.severity_level)}</div>

                  {/* Multi-Class Damage Badges */}
                  {img.damage_types && (() => {
                    try {
                      const dtypes = JSON.parse(img.damage_types);
                      if (dtypes && dtypes.length > 0) {
                        return (
                          <div className="flex flex-wrap gap-1">
                            {dtypes.map((d: any, dIdx: number) => (
                              <span
                                key={dIdx}
                                className={`px-1.5 py-0.5 text-[10px] font-semibold rounded border ${
                                  d.severity === 'Critical'
                                    ? 'bg-rose-50 text-rose-700 border-rose-200'
                                    : d.severity === 'High'
                                    ? 'bg-red-50 text-red-700 border-red-200'
                                    : d.severity === 'Medium'
                                    ? 'bg-amber-50 text-amber-700 border-amber-200'
                                    : 'bg-blue-50 text-blue-700 border-blue-200'
                                }`}
                              >
                                {d.damage_type}
                              </span>
                            ))}
                          </div>
                        );
                      }
                    } catch (e) {
                      return null;
                    }
                    return null;
                  })()}

                  {/* Crack Geometry Breakdown (Module 9) */}
                  {img.has_crack && (
                    <div className="bg-slate-50 border border-slate-200 rounded-lg p-2.5 space-y-1.5 text-xs text-slate-700">
                      <div className="font-bold text-slate-900 truncate flex items-center justify-between">
                        <span>{img.crack_type || 'Crack Defect'}</span>
                        <span className="text-[10px] text-slate-400 font-mono">
                          {img.orientation_deg !== undefined ? `${img.orientation_deg}°` : ''}
                        </span>
                      </div>
                      <div className="grid grid-cols-2 gap-1 text-[11px] text-slate-600 font-mono">
                        <div>Length: <strong className="text-slate-900">{img.crack_length_mm ? `${img.crack_length_mm}mm` : `${img.crack_length_px}px`}</strong></div>
                        <div>Max Width: <strong className="text-slate-900">{img.max_crack_width_mm ? `${img.max_crack_width_mm}mm` : `${img.max_crack_width_px}px`}</strong></div>
                        <div>Density: <strong className="text-slate-900">{img.crack_density_pct || 0}%</strong></div>
                        <div>Junctions: <strong className="text-slate-900">{img.branching_points || 0}</strong></div>
                      </div>
                    </div>
                  )}

                  <p className="text-xs font-semibold text-slate-800 truncate pt-1" title={img.original_filename}>
                    {img.original_filename}
                  </p>
                </div>

                <div className="pt-2 border-t border-slate-100 text-[10px] text-slate-400 flex items-center justify-between font-mono">
                  <span>{img.width}x{img.height} px</span>
                  <span>{img.file_size_kb} KB</span>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* ── Live Mobile Camera Capture Modal (Module 3) ──────────────────── */}
      {showCameraModal && (
        <div className="fixed inset-0 bg-slate-950/85 backdrop-blur-md z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl max-w-2xl w-full p-5 space-y-4 shadow-2xl border border-slate-200">
            <div className="flex items-center justify-between border-b border-slate-200 pb-3">
              <h3 className="text-base font-bold text-slate-900 flex items-center gap-2">
                <Camera className="w-5 h-5 text-blue-600" />
                <span>Live Infrastructure Camera Viewfinder</span>
              </h3>
              <button onClick={stopCamera} className="p-1 rounded-lg text-slate-400 hover:text-slate-700">
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="relative aspect-4/3 bg-black rounded-xl overflow-hidden flex items-center justify-center">
              {!capturedDataUrl ? (
                <video ref={videoRef} autoPlay playsInline className="w-full h-full object-cover" />
              ) : (
                <img src={capturedDataUrl} alt="Captured" className="w-full h-full object-contain" />
              )}
            </div>

            <div className="flex items-center justify-between gap-3 pt-2">
              <button
                onClick={() => setRotationAngle((prev) => (prev + 90) % 360)}
                className="btn-secondary text-xs py-2 px-3 flex items-center gap-1.5"
              >
                <RotateCw className="w-4 h-4" />
                <span>Rotate 90° ({rotationAngle}°)</span>
              </button>

              {!capturedDataUrl ? (
                <button onClick={capturePhoto} className="btn-primary text-xs py-2 px-6 flex items-center gap-2">
                  <Camera className="w-4 h-4" />
                  <span>Capture Snapshot</span>
                </button>
              ) : (
                <div className="flex items-center gap-2">
                  <button
                    onClick={() => { setCapturedBlob(null); setCapturedDataUrl(null); }}
                    className="btn-secondary text-xs py-2 px-4"
                  >
                    Retake
                  </button>
                  <button
                    onClick={uploadCapturedPhoto}
                    disabled={uploading}
                    className="btn-primary text-xs py-2 px-5 flex items-center gap-1.5"
                  >
                    <Upload className="w-4 h-4" />
                    <span>{uploading ? 'Analyzing...' : 'Confirm & Upload'}</span>
                  </button>
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* ── Multi-Modal Diagnostics & Explainability Modal (Modules 4, 12, 18) ── */}
      {previewImage && (
        <div className="fixed inset-0 bg-slate-950/85 backdrop-blur-md z-50 flex items-center justify-center p-3 sm:p-5">
          <div className="bg-white rounded-2xl max-w-5xl w-full p-5 sm:p-6 space-y-4 shadow-2xl border border-slate-200 overflow-hidden flex flex-col max-h-[92vh]">
            <div className="flex items-center justify-between border-b border-slate-200 pb-3">
              <div>
                <h3 className="text-base font-bold text-slate-900 flex items-center gap-2">
                  <span>AI Diagnostics, Preprocessing & Explainability (XAI)</span>
                  <span className="text-xs font-mono px-2 py-0.5 rounded bg-slate-100 text-slate-700">
                    ID #{previewImage.id}
                  </span>
                </h3>
                <p className="text-xs text-slate-500 mt-0.5">
                  Multi-modal vision engine: CLAHE, Sharpening, U-Net Crack Mask, Skeleton, Grad-CAM, Grad-CAM++, Saliency & Bounding Boxes.
                </p>
              </div>
              <button
                onClick={() => setPreviewImage(null)}
                className="p-1.5 rounded-lg text-slate-400 hover:text-slate-700 hover:bg-slate-100 transition-colors"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Mode Selector Tabs (Preprocessing & XAI) */}
            <div className="space-y-2">
              <div className="flex items-center gap-1.5 flex-wrap text-xs font-bold">
                <span className="text-slate-400 uppercase text-[10px] tracking-wider pr-1">Preprocessing:</span>
                {[
                  { id: 'original', label: '1. Original' },
                  { id: 'enhanced', label: '2. CLAHE Contrast' },
                  { id: 'sharpen', label: '3. Sharpening' },
                  { id: 'shadow_reduction', label: '4. Shadow Reduction' },
                  { id: 'edge', label: '5. Canny Edges' },
                  { id: 'texture', label: '6. Texture' },
                  { id: 'roi', label: '7. Surface ROI' },
                ].map((m) => (
                  <button
                    key={m.id}
                    onClick={() => setPreviewMode(m.id as PreviewMode)}
                    className={`px-2.5 py-1 rounded-lg transition-all ${
                      previewMode === m.id
                        ? 'bg-blue-600 text-white shadow-xs'
                        : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
                    }`}
                  >
                    {m.label}
                  </button>
                ))}
              </div>

              <div className="flex items-center gap-1.5 flex-wrap text-xs font-bold pt-1">
                <span className="text-slate-400 uppercase text-[10px] tracking-wider pr-1">AI & Explainability:</span>
                {[
                  { id: 'mask', label: 'U-Net Segmentation Mask' },
                  { id: 'skeleton', label: 'Medial Axis Skeleton' },
                  { id: 'boxes', label: 'Defect Bounding Boxes' },
                  { id: 'gradcam', label: 'Grad-CAM Heatmap' },
                  { id: 'gradcam_plus', label: 'Grad-CAM++ (Multi-Defect)' },
                  { id: 'saliency', label: 'Pixel Saliency Map' },
                ].map((m) => (
                  <button
                    key={m.id}
                    onClick={() => setPreviewMode(m.id as PreviewMode)}
                    className={`px-2.5 py-1 rounded-lg transition-all ${
                      previewMode === m.id
                        ? 'bg-purple-600 text-white shadow-xs'
                        : 'bg-purple-50 text-purple-700 hover:bg-purple-100 border border-purple-200'
                    }`}
                  >
                    {m.label}
                  </button>
                ))}
              </div>
            </div>

            {/* Display Viewport */}
            <div className="relative aspect-16/10 bg-slate-950 rounded-xl overflow-hidden flex items-center justify-center border border-slate-800">
              <img
                src={`http://localhost:8000/images/${previewImage.id}/preview?mode=${previewMode}`}
                alt="Preview"
                className="max-h-full max-w-full object-contain"
              />
              <div className="absolute bottom-3 left-3 bg-slate-900/80 backdrop-blur-md px-3 py-1 rounded-md text-xs text-white font-mono border border-slate-700/50">
                Active Layer: <strong className="text-blue-400">{previewMode.toUpperCase()}</strong>
              </div>
            </div>

            {/* Interactive Scale Calibration Bar (Module 9) */}
            <div className="p-3 bg-slate-50 border border-slate-200 rounded-xl flex items-center justify-between gap-4 flex-wrap text-xs">
              <div className="flex items-center gap-2">
                <Ruler className="w-4 h-4 text-blue-600" />
                <span className="font-bold text-slate-800">Pixel-to-Real-World Scale Conversion:</span>
                <input
                  type="number"
                  step="0.05"
                  min="0.01"
                  max="5.0"
                  value={calibrationMm}
                  onChange={(e) => setCalibrationMm(parseFloat(e.target.value) || 0.2)}
                  className="w-20 px-2 py-1 rounded border border-slate-300 font-mono text-xs text-center"
                />
                <span className="text-slate-500">mm / pixel</span>
                <button
                  onClick={handleUpdateCalibration}
                  disabled={calibrating}
                  className="btn-primary text-xs py-1 px-3 ml-2"
                >
                  {calibrating ? 'Updating...' : 'Calibrate Measurements'}
                </button>
              </div>

              <div className="flex items-center gap-4 text-xs font-mono text-slate-600">
                <span>Length: <strong className="text-slate-900">{previewImage.crack_length_mm || 0} mm</strong></span>
                <span>Max Width: <strong className="text-slate-900">{previewImage.max_crack_width_mm || 0} mm</strong></span>
                <span>Area: <strong className="text-slate-900">{previewImage.crack_area_mm2 || 0} mm²</strong></span>
              </div>
            </div>

            {/* Footer */}
            <div className="flex items-center justify-between text-xs text-slate-500 pt-2 border-t border-slate-200">
              <span className="font-mono">Dimensions: {previewImage.width}x{previewImage.height} px</span>
              <button onClick={() => setPreviewImage(null)} className="btn-secondary py-1.5 px-4 text-xs">
                Close Diagnostics
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ── Historical Inspection Comparison Modal (Module 15) ─────────────── */}
      {showComparisonModal && comparisonData && (
        <div className="fixed inset-0 bg-slate-950/85 backdrop-blur-md z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl max-w-3xl w-full p-6 space-y-5 shadow-2xl border border-slate-200 max-h-[90vh] overflow-y-auto">
            <div className="flex items-center justify-between border-b border-slate-200 pb-3">
              <div className="flex items-center gap-2">
                <GitCompare className="w-5 h-5 text-indigo-600" />
                <h3 className="font-bold text-slate-900 text-base">Historical Damage Progression Analysis</h3>
              </div>
              <button onClick={() => setShowComparisonModal(false)} className="p-1 rounded text-slate-400 hover:text-slate-700">
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Comparison Delta Summary */}
            <div className={`p-4 rounded-xl border flex items-center justify-between ${
              comparisonData.deltas.overall_progression_trend.includes('Accelerated') ? 'bg-rose-50 border-rose-200 text-rose-800' :
              comparisonData.deltas.overall_progression_trend.includes('Active') ? 'bg-amber-50 border-amber-200 text-amber-800' :
              'bg-emerald-50 border-emerald-200 text-emerald-800'
            }`}>
              <div>
                <span className="text-[11px] font-bold uppercase tracking-wider">Overall Progression Trend</span>
                <p className="text-lg font-extrabold mt-0.5">{comparisonData.deltas.overall_progression_trend}</p>
              </div>
              <span className="px-3 py-1 rounded-full text-xs font-bold bg-white shadow-xs">
                Alert: {comparisonData.deltas.alert_level}
              </span>
            </div>

            {/* Metrics Side-by-Side Comparison */}
            <div className="grid grid-cols-2 gap-4">
              <div className="p-4 bg-slate-50 border border-slate-200 rounded-xl space-y-2">
                <span className="text-xs font-bold text-slate-500 uppercase">Baseline / Prior Inspection</span>
                <p className="text-xs font-semibold text-slate-800">Date: {comparisonData.previous_inspection.date || 'N/A'}</p>
                <div className="text-xs font-mono space-y-1 pt-1 text-slate-600">
                  <div>Crack Length: <strong>{comparisonData.previous_inspection.summary.total_length_mm} mm</strong></div>
                  <div>Max Width: <strong>{comparisonData.previous_inspection.summary.max_width_mm} mm</strong></div>
                  <div>Cracked Images: <strong>{comparisonData.previous_inspection.summary.cracked_count}</strong></div>
                </div>
              </div>

              <div className="p-4 bg-blue-50/50 border border-blue-200 rounded-xl space-y-2">
                <span className="text-xs font-bold text-blue-600 uppercase">Current Inspection</span>
                <p className="text-xs font-semibold text-slate-800">Date: {comparisonData.current_inspection.date || 'N/A'}</p>
                <div className="text-xs font-mono space-y-1 pt-1 text-slate-600">
                  <div>Crack Length: <strong>{comparisonData.current_inspection.summary.total_length_mm} mm</strong></div>
                  <div>Max Width: <strong>{comparisonData.current_inspection.summary.max_width_mm} mm</strong></div>
                  <div>Cracked Images: <strong>{comparisonData.current_inspection.summary.cracked_count}</strong></div>
                </div>
              </div>
            </div>

            {/* Growth Deltas */}
            <div className="p-4 bg-slate-100 rounded-xl space-y-2 text-xs">
              <h4 className="font-bold text-slate-800">Quantified Growth & Defect Emergence:</h4>
              <div className="grid grid-cols-3 gap-3 font-mono pt-1">
                <div className="p-2.5 bg-white rounded-lg border border-slate-200">
                  <span className="text-[10px] text-slate-400 block">Length Growth</span>
                  <strong className={comparisonData.deltas.crack_length_mm_change > 0 ? 'text-rose-600' : 'text-emerald-600'}>
                    {comparisonData.deltas.crack_length_mm_change > 0 ? '+' : ''}{comparisonData.deltas.crack_length_mm_change} mm
                  </strong>
                </div>
                <div className="p-2.5 bg-white rounded-lg border border-slate-200">
                  <span className="text-[10px] text-slate-400 block">Width Expansion</span>
                  <strong className={comparisonData.deltas.max_width_mm_change > 0 ? 'text-rose-600' : 'text-emerald-600'}>
                    {comparisonData.deltas.max_width_mm_change > 0 ? '+' : ''}{comparisonData.deltas.max_width_mm_change} mm
                  </strong>
                </div>
                <div className="p-2.5 bg-white rounded-lg border border-slate-200">
                  <span className="text-[10px] text-slate-400 block">New Defect Images</span>
                  <strong className="text-slate-800">
                    {comparisonData.deltas.cracked_images_change > 0 ? `+${comparisonData.deltas.cracked_images_change}` : comparisonData.deltas.cracked_images_change}
                  </strong>
                </div>
              </div>
            </div>

            <div className="text-right pt-2 border-t border-slate-200">
              <button onClick={() => setShowComparisonModal(false)} className="btn-secondary text-xs py-2 px-5">
                Close Comparison
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
