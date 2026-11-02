import React, { useEffect, useState } from 'react';
import api from '../api/client';
import { ImageAnalysis } from '../types';

function statusLabel(status: string): string {
  if (status === 'completed') return 'Completed';
  if (status === 'unavailable') return 'Weights not on disk';
  if (status === 'failed') return 'Failed';
  if (status === 'unreliable') return 'Not reliable';
  return status;
}

function StatusPill({ status }: { status: string }) {
  const tone =
    status === 'completed'
      ? 'bg-green-100 text-green-800'
      : status === 'failed'
        ? 'bg-red-100 text-red-800'
        : 'bg-amber-100 text-amber-800';
  return <span className={`inline-flex rounded-full px-2 py-0.5 text-[11px] font-semibold ${tone}`}>{statusLabel(status)}</span>;
}

export const AnalysisPanel: React.FC<{ analysis: ImageAnalysis; onClose: () => void }> = ({ analysis, onClose }) => {
  const detectionReliable = analysis.detection.reliable === true;
  const boxes = detectionReliable ? analysis.detection.detections || [] : [];
  const detectionPill =
    analysis.detection_status === 'completed' && !detectionReliable
      ? 'unreliable'
      : analysis.detection_status;
  const geometry = analysis.geometry.measurements;
  const [overlaySrc, setOverlaySrc] = useState('');
  const [maskSrc, setMaskSrc] = useState('');

  useEffect(() => {
    let overlayObject = '';
    let maskObject = '';
    let cancelled = false;

    const load = async () => {
      if (analysis.overlay_url) {
        const response = await api.get(analysis.overlay_url, { responseType: 'blob' });
        overlayObject = URL.createObjectURL(response.data);
        if (!cancelled) setOverlaySrc(overlayObject);
      }
      if (analysis.mask_url) {
        const response = await api.get(analysis.mask_url, { responseType: 'blob' });
        maskObject = URL.createObjectURL(response.data);
        if (!cancelled) setMaskSrc(maskObject);
      }
    };
    load().catch(() => {
      if (!cancelled) {
        setOverlaySrc('');
        setMaskSrc('');
      }
    });

    return () => {
      cancelled = true;
      if (overlayObject) URL.revokeObjectURL(overlayObject);
      if (maskObject) URL.revokeObjectURL(maskObject);
    };
  }, [analysis]);

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 p-4 backdrop-blur-sm">
      <div className="max-h-[92vh] w-full max-w-5xl overflow-y-auto rounded-2xl bg-white p-6 shadow-2xl">
        <div className="flex items-start justify-between gap-4 border-b pb-3">
          <div>
            <h3 className="text-lg font-bold text-gray-900">Damage analysis</h3>
            <p className="text-xs text-gray-500">
              Results come from the API. A task marked “Weights not on disk” did not produce a prediction.
            </p>
          </div>
          <button onClick={onClose} className="btn-secondary px-3 py-1 text-xs">
            Close
          </button>
        </div>

        <div className="mt-4 grid gap-4 lg:grid-cols-2">
          <div className="space-y-2">
            <p className="text-xs font-semibold uppercase text-gray-500">Original with mask and boxes</p>
            {overlaySrc ? (
              <img src={overlaySrc} alt="Analysis overlay" className="max-h-80 w-full rounded-xl bg-slate-950 object-contain" />
            ) : (
              <p className="text-sm text-gray-500">No overlay was saved.</p>
            )}
          </div>
          <div className="space-y-2">
            <p className="text-xs font-semibold uppercase text-gray-500">Segmentation mask</p>
            {maskSrc ? (
              <img src={maskSrc} alt="Predicted crack mask" className="max-h-80 w-full rounded-xl bg-slate-950 object-contain" />
            ) : (
              <p className="rounded-xl bg-gray-50 p-6 text-sm text-gray-500">{analysis.segmentation.detail || 'No mask was produced.'}</p>
            )}
            {analysis.segmentation.detail && (
              <p className="text-[11px] text-gray-500">{analysis.segmentation.detail}</p>
            )}
          </div>
        </div>

        <div className="mt-5 grid gap-3 md:grid-cols-2">
          <section className="rounded-xl border border-gray-100 p-4">
            <div className="mb-2 flex items-center justify-between">
              <h4 className="text-sm font-bold text-gray-900">Image quality</h4>
              <StatusPill status={analysis.quality.valid ? analysis.quality.status : 'failed'} />
            </div>
            <ul className="space-y-1 text-xs text-gray-600">
              <li>Size: {analysis.quality.width} × {analysis.quality.height} px</li>
              <li>Blur score: {analysis.quality.blur_score ?? 'n/a'}</li>
              <li>Brightness: {analysis.quality.brightness ?? 'n/a'}</li>
              <li>Contrast: {analysis.quality.contrast ?? 'n/a'}</li>
              <li>Flags: {analysis.quality.flags.length ? analysis.quality.flags.join(', ') : 'none'}</li>
            </ul>
          </section>

          <section className="rounded-xl border border-gray-100 p-4">
            <div className="mb-2 flex items-center justify-between">
              <h4 className="text-sm font-bold text-gray-900">Crack classification</h4>
              <StatusPill status={analysis.classification_status} />
            </div>
            {analysis.classification_status === 'completed' ? (
              <ul className="space-y-1 text-xs text-gray-600">
                <li>Label: {analysis.classification_label}</li>
                <li>Confidence: {analysis.classification_confidence}</li>
                <li>Crack-patch fraction: {analysis.classification.crack_patch_fraction ?? 'n/a'}</li>
                <li className="pt-1 text-[11px] text-gray-500">{analysis.classification.detail}</li>
              </ul>
            ) : (
              <p className="text-xs text-gray-600">{analysis.classification.detail}</p>
            )}
          </section>

          <section className="rounded-xl border border-gray-100 p-4">
            <div className="mb-2 flex items-center justify-between">
              <h4 className="text-sm font-bold text-gray-900">YOLO detection</h4>
              <StatusPill status={detectionPill} />
            </div>
            {boxes.length === 0 ? (
              <p className="text-xs text-gray-600">
                {analysis.detection.detail ||
                  'Detection model requires further training and validation. No reliable bounding boxes generated.'}
              </p>
            ) : (
              <ul className="space-y-1 text-xs text-gray-600">
                {boxes.map((box, index) => (
                  <li key={`${box.class_name}-${index}`}>
                    {box.class_name} ({box.confidence}) — {Math.round(box.xmin)},{Math.round(box.ymin)} to {Math.round(box.xmax)},{Math.round(box.ymax)}
                  </li>
                ))}
              </ul>
            )}
          </section>

          <section className="rounded-xl border border-gray-100 p-4">
            <div className="mb-2 flex items-center justify-between">
              <h4 className="text-sm font-bold text-gray-900">Crack geometry</h4>
              <StatusPill status={analysis.geometry.status === 'completed' ? 'completed' : 'unavailable'} />
            </div>
            {geometry ? (
              <ul className="space-y-1 text-xs text-gray-600">
                <li>Area: {geometry.crack_pixel_area} px</li>
                <li>Length estimate: {geometry.crack_length_px} px</li>
                <li>Mean width estimate: {geometry.crack_width_px_mean} px</li>
                <li>Bounding size: {geometry.bbox_width_px} × {geometry.bbox_height_px} px</li>
                <li>Coverage: {geometry.coverage_percent}%</li>
                <li className="pt-1 text-[11px] text-amber-700">{geometry.physical_scale_note}</li>
              </ul>
            ) : (
              <p className="text-xs text-gray-600">{analysis.geometry.detail}</p>
            )}
          </section>
        </div>

        {analysis.error_message && (
          <p className="mt-4 rounded-lg bg-red-50 p-3 text-xs text-red-700">{analysis.error_message}</p>
        )}
      </div>
    </div>
  );
};
