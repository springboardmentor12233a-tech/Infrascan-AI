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
  FileText
} from 'lucide-react';
import { Inspection, InspectionImage, QualityStatus } from '../types';
import { useAuth } from '../context/AuthContext';

export const InspectionView: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const { user } = useAuth();
  const [inspection, setInspection] = useState<Inspection | null>(null);
  const [images, setImages] = useState<InspectionImage[]>([]);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [dragActive, setDragActive] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Status update
  const [status, setStatus] = useState<string>('pending');
  const [updatingStatus, setUpdatingStatus] = useState(false);

  // Preview Modal for Original vs Enhanced CLAHE
  const [previewImage, setPreviewImage] = useState<InspectionImage | null>(null);
  const [previewMode, setPreviewMode] = useState<'original' | 'enhanced'>('original');

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
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to load inspection');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchInspectionData();
  }, [id]);

  const handleStatusChange = async (newStatus: string) => {
    setUpdatingStatus(true);
    try {
      await api.put(`/inspections/${id}`, { status: newStatus });
      setStatus(newStatus);
    } catch (err: any) {
      alert(err.response?.data?.detail || 'Failed to update inspection status');
    } finally {
      setUpdatingStatus(false);
    }
  };

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
      setSuccess(`Successfully uploaded and validated ${res.data.length} image(s)!`);
      if (fileInputRef.current) fileInputRef.current.value = '';
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Image validation / upload failed');
    } finally {
      setUploading(false);
    }
  };

  const handleDrag = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === 'dragenter' || e.type === 'dragover') {
      setDragActive(true);
    } else if (e.type === 'dragleave') {
      setDragActive(false);
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      handleFiles(e.dataTransfer.files);
    }
  };

  const getQualityBadge = (status: QualityStatus, blur?: number, bright?: number) => {
    switch (status) {
      case 'ok':
        return (
          <span className="badge-ok flex items-center gap-1">
            <CheckCircle className="w-3 h-3 text-green-600" />
            <span>Optimal Quality</span>
          </span>
        );
      case 'blurry':
        return (
          <span className="badge-blurry flex items-center gap-1" title={`Blur score: ${blur} (Threshold: 100)`}>
            <AlertTriangle className="w-3 h-3 text-yellow-600" />
            <span>Blurry (Score: {blur})</span>
          </span>
        );
      case 'low_light':
        return (
          <span className="badge-low-light flex items-center gap-1" title={`Brightness: ${bright} (Threshold: 50)`}>
            <Sun className="w-3 h-3 text-red-600" />
            <span>Low Light (Bright: {bright})</span>
          </span>
        );
      default:
        return null;
    }
  };

  if (loading) {
    return (
      <div className="py-20 text-center text-gray-500">
        <div className="w-8 h-8 border-4 border-blue-600 border-t-transparent rounded-full animate-spin mx-auto mb-3"></div>
        Loading inspection workspace...
      </div>
    );
  }

  if (!inspection) {
    return (
      <div className="card p-8 text-center text-gray-600">
        <p>Inspection session not found.</p>
        <Link to="/assets" className="btn-secondary mt-4 inline-block">
          Return to Assets
        </Link>
      </div>
    );
  }

  return (
    <div className="space-y-8 max-w-7xl mx-auto">
      {/* Top Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <Link
            to={`/assets/${inspection.asset_id}`}
            className="btn-secondary py-1.5 px-3 text-xs flex items-center gap-1.5"
          >
            <ArrowLeft className="w-4 h-4" /> Asset Overview
          </Link>
          <h1 className="text-2xl font-bold text-gray-900">
            Inspection #{inspection.id}
          </h1>
          <span className="text-xs text-gray-500">
            ({inspection.inspection_date})
          </span>
        </div>

        {/* Status Dropdown */}
        <div className="flex items-center gap-2">
          <span className="text-xs font-semibold uppercase text-gray-500">Status:</span>
          <select
            value={status}
            disabled={updatingStatus}
            onChange={(e) => handleStatusChange(e.target.value)}
            className="input-field py-1 text-xs font-semibold bg-white rounded-md"
          >
            <option value="pending">Pending</option>
            <option value="in_progress">In Progress</option>
            <option value="completed">Completed</option>
          </select>
        </div>
      </div>

      {/* Info Card */}
      <div className="card p-6 grid grid-cols-1 md:grid-cols-3 gap-6 bg-slate-900 text-white border-0 shadow-md">
        <div>
          <p className="text-xs text-slate-400 uppercase font-semibold">Inspected Asset</p>
          <p className="text-base font-bold text-white mt-1">
            {inspection.asset?.name || `Asset #${inspection.asset_id}`}
          </p>
          <p className="text-xs text-blue-400 font-mono mt-0.5">
            {inspection.asset?.asset_code}
          </p>
        </div>
        <div>
          <p className="text-xs text-slate-400 uppercase font-semibold">Assigned Inspector</p>
          <p className="text-base font-semibold text-white mt-1 flex items-center gap-1.5">
            <UserIcon className="w-4 h-4 text-blue-400" />
            {inspection.inspector?.full_name}
          </p>
          <p className="text-xs text-slate-400 mt-0.5">{inspection.inspector?.email}</p>
        </div>
        <div>
          <p className="text-xs text-slate-400 uppercase font-semibold">Field Instructions</p>
          <p className="text-xs text-slate-300 mt-1 line-clamp-2">
            {inspection.notes || 'Routine structural condition survey.'}
          </p>
        </div>
      </div>

      {/* Alerts */}
      {error && (
        <div className="p-4 rounded-lg bg-red-50 border border-red-200 text-red-700 text-sm flex items-center gap-2">
          <AlertTriangle className="w-5 h-5 flex-shrink-0" />
          <span>{error}</span>
        </div>
      )}
      {success && (
        <div className="p-4 rounded-lg bg-green-50 border border-green-200 text-green-700 text-sm flex items-center gap-2">
          <CheckCircle className="w-5 h-5 flex-shrink-0" />
          <span>{success}</span>
        </div>
      )}

      {/* Drag & Drop Upload Zone */}
      <div
        onDragEnter={handleDrag}
        onDragLeave={handleDrag}
        onDragOver={handleDrag}
        onDrop={handleDrop}
        className={`border-2 border-dashed rounded-2xl p-8 text-center transition-all ${
          dragActive
            ? 'border-blue-600 bg-blue-50/50 scale-[1.01]'
            : 'border-gray-300 hover:border-gray-400 bg-white'
        }`}
      >
        <input
          ref={fileInputRef}
          type="file"
          multiple
          accept=".jpg,.jpeg,.png"
          onChange={(e) => handleFiles(e.target.files)}
          className="hidden"
          id="file-upload"
        />
        <div className="max-w-md mx-auto space-y-3">
          <div className="h-12 w-12 rounded-full bg-blue-100 text-blue-600 flex items-center justify-center mx-auto">
            <Upload className="w-6 h-6" />
          </div>
          <div>
            <label
              htmlFor="file-upload"
              className="text-blue-600 font-semibold cursor-pointer hover:underline text-sm"
            >
              Click to select inspection photos
            </label>{' '}
            <span className="text-sm text-gray-500">or drag and drop files here</span>
          </div>
          <p className="text-xs text-gray-400">
            Supports JPG, JPEG, PNG • Max 20MB per photo • Automatic blur & low-light validation
          </p>
          {uploading && (
            <div className="pt-2 flex items-center justify-center gap-2 text-xs text-blue-600 font-medium">
              <RefreshCw className="w-4 h-4 animate-spin" />
              <span>Running quality checks & duplicate MD5 validation...</span>
            </div>
          )}
        </div>
      </div>

      {/* Uploaded Images Gallery */}
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-bold text-gray-900 flex items-center gap-2">
            <Camera className="w-5 h-5 text-blue-600" />
            <span>Inspection Images & Quality Validation ({images.length})</span>
          </h2>
        </div>

        {images.length === 0 ? (
          <div className="card p-12 text-center text-gray-400">
            <Camera className="w-10 h-10 mx-auto mb-2 text-gray-300" />
            <p className="text-sm">No images uploaded for this inspection yet.</p>
            <p className="text-xs text-gray-400 mt-1">Upload images to test blur assessment and CLAHE preprocessing.</p>
          </div>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-6">
            {images.map((img) => (
              <div key={img.id} className="card p-3 flex flex-col justify-between hover:shadow-md transition-shadow">
                <div className="space-y-2">
                  {/* Image container */}
                  <div className="relative aspect-video bg-gray-100 rounded-lg overflow-hidden group">
                    <img
                      src={`http://localhost:8000/uploads/${img.file_path}`}
                      alt={img.original_filename}
                      className="w-full h-full object-cover"
                    />
                    <div className="absolute inset-0 bg-black/40 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center gap-2">
                      <button
                        onClick={() => {
                          setPreviewImage(img);
                          setPreviewMode('original');
                        }}
                        className="bg-white/90 text-gray-800 p-2 rounded-full hover:bg-white text-xs font-semibold flex items-center gap-1 shadow"
                        title="Compare Original vs CLAHE Enhanced"
                      >
                        <Sliders className="w-4 h-4 text-blue-600" />
                      </button>
                    </div>
                  </div>

                  {/* Quality Badge */}
                  <div>
                    {getQualityBadge(img.quality_status, img.blur_score, img.brightness)}
                  </div>

                  <p className="text-xs font-medium text-gray-800 truncate" title={img.original_filename}>
                    {img.original_filename}
                  </p>
                </div>

                <div className="pt-2 mt-2 border-t text-[11px] text-gray-400 flex items-center justify-between">
                  <span>{img.width}x{img.height} px</span>
                  <span>{img.file_size_kb} KB</span>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Comparison Modal: Original vs CLAHE Enhanced */}
      {previewImage && (
        <div className="fixed inset-0 bg-black/80 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl max-w-4xl w-full p-6 space-y-4 shadow-2xl">
            <div className="flex items-center justify-between border-b pb-3">
              <div>
                <h3 className="text-base font-bold text-gray-900">
                  Image Preprocessing & Enhancement Preview
                </h3>
                <p className="text-xs text-gray-500">
                  Gaussian Denoising + CLAHE (Contrast Limited Adaptive Histogram Equalization)
                </p>
              </div>

              {/* Mode Toggle */}
              <div className="flex items-center bg-gray-100 p-1 rounded-lg">
                <button
                  onClick={() => setPreviewMode('original')}
                  className={`px-3 py-1 text-xs font-semibold rounded-md transition-colors ${
                    previewMode === 'original'
                      ? 'bg-white text-blue-600 shadow-sm'
                      : 'text-gray-600 hover:text-gray-900'
                  }`}
                >
                  Original Image
                </button>
                <button
                  onClick={() => setPreviewMode('enhanced')}
                  className={`px-3 py-1 text-xs font-semibold rounded-md transition-colors ${
                    previewMode === 'enhanced'
                      ? 'bg-blue-600 text-white shadow-sm'
                      : 'text-gray-600 hover:text-gray-900'
                  }`}
                >
                  Enhanced (CLAHE)
                </button>
              </div>
            </div>

            {/* Display */}
            <div className="relative aspect-video bg-slate-950 rounded-xl overflow-hidden flex items-center justify-center">
              <img
                src={`http://localhost:8000/images/${previewImage.id}/preview?mode=${previewMode}`}
                alt="Preview"
                className="max-h-full max-w-full object-contain"
              />
              <div className="absolute bottom-3 left-3 bg-black/70 backdrop-blur-md px-3 py-1 rounded text-xs text-white font-mono">
                Mode: {previewMode.toUpperCase()}
              </div>
            </div>

            <div className="flex items-center justify-between text-xs text-gray-500 pt-2 border-t">
              <p>MD5: <code className="font-mono">{previewImage.md5_hash}</code></p>
              <button
                onClick={() => setPreviewImage(null)}
                className="btn-secondary py-1 px-4 text-xs"
              >
                Close Preview
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
