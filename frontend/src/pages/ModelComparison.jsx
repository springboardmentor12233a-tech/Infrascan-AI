import React from 'react';

export default function ModelComparison() {
  const benchmarks = [
    {
      model: 'CNN Crack Classifier',
      task: 'Binary Crack Classification',
      dataset: 'Concrete Crack Classification (SDNET/Maguire)',
      primaryMetric: 'Test Accuracy: 0.9969',
      badgeColor: 'bg-emerald-500/20 text-emerald-400 border-emerald-500/30',
      details: [
        'Precision (Crack): 0.9993',
        'Recall (Crack): 0.9970',
        'F1-score: 0.9982',
        'Test instances: 3,554 images (554 neg, 3000 pos)',
        'Confusion Matrix: TN=552, FP=2, FN=9, TP=2991'
      ],
      role: 'First-stage triage: rapidly flags cracked concrete surfaces with near-zero false negatives.'
    },
    {
      model: 'YOLO11s Checkpoint Audit & Baseline',
      task: 'Object Detection (Infrastructure Damage Status)',
      dataset: 'Currently Deployed: MS COCO (80 Classes) | Historical Research: CRACK500 (Colab)',
      primaryMetric: 'Deployed: COCO Baseline (Not fine-tuned) | Research Target mAP@50: 0.8064',
      badgeColor: 'bg-amber-500/20 text-amber-400 border-amber-500/30',
      details: [
        'Deployed Checkpoint: models/yolo_best.pt (80 classes, standard COCO weights)',
        'Operational Notice: COCO predictions are strictly isolated and NOT used for crack damage severity or prioritization',
        'Historical Colab Evaluation (Held-out CRACK500 test set, 1,124 images):',
        '  - Precision: 0.8447 | Recall: 0.7478',
        '  - mAP@50: 0.8064 | mAP@50-95: 0.5175',
        '  - Latency: 5.67 ms/image',
        'Note: Custom CRACK500 weights reside in Colab runtime (/content/crack500_work/); local deployment currently loads COCO base.'
      ],
      role: 'Architecture verified for P3-P5 bounding-box localization; awaits CRACK500 weight placement.'
    },
    {
      model: 'U-Net Semantic Segmentor',
      task: 'Pixel-Level Crack Segmentation',
      dataset: 'CRACK500 (Pixel Ground Truth)',
      primaryMetric: 'IoU: 0.5408, Dice: 0.7020',
      badgeColor: 'bg-indigo-500/20 text-indigo-400 border-indigo-500/30',
      details: [
        'Pixel Accuracy: 0.9674',
        'Precision: 0.7172',
        'Recall: 0.6874',
        'Evaluated on 1,124 held-out test predictions',
        'Preserves thin linear fracture trajectories for geometry extraction'
      ],
      role: 'Enables pixel-accurate crack skeletonization, length, and aperture width estimation.'
    }
  ];

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8">
      <div>
        <h1 className="text-2xl font-black text-white tracking-tight">AI Model Evaluation & Accuracy Optimization</h1>
        <p className="text-sm text-slate-400 mt-1">
          Empirical evaluation results verified from the Milestone 2 training runs, with YOLO detection accuracy optimizations.
        </p>
      </div>

      {/* Model Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {benchmarks.map((m, idx) => (
          <div key={idx} className="glass-card p-6 rounded-2xl border border-slate-800 space-y-4 flex flex-col justify-between">
            <div className="space-y-3">
              <span className={`text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded border ${m.badgeColor}`}>
                {m.task}
              </span>
              <h2 className="text-lg font-bold text-white">{m.model}</h2>
              <div className="p-3 rounded-lg bg-slate-900 border border-slate-800 text-sm font-bold text-emerald-400 font-mono">
                {m.primaryMetric}
              </div>
              <div className="text-xs text-slate-400">
                <strong>Dataset:</strong> {m.dataset}
              </div>
              <ul className="space-y-1.5 text-xs text-slate-300 pt-1">
                {m.details.map((d, i) => (
                  <li key={i} className="flex items-start gap-1.5">
                    <span className="text-blue-400 mt-0.5">&bull;</span>
                    <span>{d}</span>
                  </li>
                ))}
              </ul>
            </div>
            <div className="pt-3 border-t border-slate-800 text-xs text-slate-400">
              {m.role}
            </div>
          </div>
        ))}
      </div>

      {/* YOLO Optimization Deep-Dive Card */}
      <div className="glass-card p-6 rounded-2xl border border-blue-500/30 bg-blue-950/10 space-y-4">
        <div className="flex items-center gap-2">
          <span className="px-2.5 py-1 rounded-full text-xs font-bold bg-blue-500/20 text-blue-400 border border-blue-500/30">
            YOLO Accuracy Improvement Deep Dive
          </span>
          <h2 className="text-base font-bold text-white">Why Baseline YOLO11n mAP Was 0.400 & How It Is Solved</h2>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs text-slate-300">
          <div className="p-4 rounded-xl bg-slate-900/80 border border-slate-800 space-y-2">
            <h3 className="font-bold text-rose-400 flex items-center gap-1.5">
              <span>&#9888;</span> Root Causes of Low Baseline (mAP50: 0.400, Recall: 0.380)
            </h3>
            <ul className="space-y-1.5 list-disc list-inside text-slate-300">
              <li><strong>Annotation Fragmentation:</strong> Raw connected components with <code>min_area=20</code> split single continuous cracks into 30–100 tiny micro-boxes per image.</li>
              <li><strong>IoU Metric Penalty:</strong> At IoU=0.50, a 2-pixel shift on a 10×10px box drops IoU below 0.50, counting as both a False Negative and a False Positive.</li>
              <li><strong>Model Scale:</strong> YOLO11n (2.6M params) at 640×384 downsampled scale loses fine crack aperture textures.</li>
            </ul>
          </div>

          <div className="p-4 rounded-xl bg-slate-900/80 border border-slate-800 space-y-2">
            <h3 className="font-bold text-emerald-400 flex items-center gap-1.5">
              <span>&#10003;</span> Four Implemented Solutions
            </h3>
            <ul className="space-y-1.5 list-disc list-inside text-slate-300">
              <li><strong>Morphological Closing (11×11):</strong> Bridges disconnected crack fractures into continuous structural entities.</li>
              <li><strong>Proximity Box Merging:</strong> Clusters bounding boxes within 30px so entire crack trajectories form unified damage zones.</li>
              <li><strong>YOLO11s (9.4M params) @ imgsz=960:</strong> Triples feature capacity and doubles input resolution for fine linear cracks.</li>
              <li><strong>Loss Rebalancing:</strong> Increased box regression weight (<code>box=8.5</code>, <code>dfl=2.0</code>) with crack-optimized augmentations.</li>
            </ul>
          </div>
        </div>

        <div className="p-3 rounded-lg bg-slate-900/90 border border-slate-800 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 text-xs">
          <span className="text-slate-300">
            Training script &amp; Colab notebook are available in: <code className="text-blue-400 font-mono">InfraScan/notebooks/InfraScan_YOLO_Accuracy_Improvement.ipynb</code>
          </span>
        </div>
      </div>

      {/* Comparative Evaluation Matrix Table */}
      <div className="glass-card p-6 rounded-2xl border border-slate-800 space-y-4">
        <h2 className="text-base font-bold text-white">Comparative Evaluation Matrix</h2>
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs text-slate-300">
            <thead className="bg-slate-800/60 uppercase text-slate-400 font-semibold border-b border-slate-700">
              <tr>
                <th className="p-3">Model Architecture</th>
                <th className="p-3">Target Objective</th>
                <th className="p-3">Evaluation Metric</th>
                <th className="p-3">Empirical Value</th>
                <th className="p-3">Analytical Role in InfraScan</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800">
              <tr>
                <td className="p-3 font-bold text-white">CNN Baseline</td>
                <td className="p-3">Binary Crack Presence</td>
                <td className="p-3">Classification Accuracy</td>
                <td className="p-3 font-mono font-bold text-emerald-400">0.9969 (99.69%)</td>
                <td className="p-3">High-speed triage of intact vs defective structural elements</td>
              </tr>
              <tr>
                <td className="p-3 font-bold text-white">YOLO11n Baseline</td>
                <td className="p-3">Multi-Crack Bounding Boxes</td>
                <td className="p-3">mAP@50 / mAP@50-95</td>
                <td className="p-3 font-mono font-bold text-amber-400">0.400 / 0.221</td>
                <td className="p-3">Baseline localization on raw micro-fragmented pseudo-boxes</td>
              </tr>
              <tr>
                <td className="p-3 font-bold text-white">YOLO11s (Deployed)</td>
                <td className="p-3">Object Detection Baseline</td>
                <td className="p-3">COCO 80-Class Detection</td>
                <td className="p-3 font-mono font-bold text-amber-400">Deployed Base COCO</td>
                <td className="p-3">Pretrained baseline; predictions isolated from damage severity logic</td>
              </tr>
              <tr>
                <td className="p-3 font-bold text-white">YOLO11s (Colab Research)</td>
                <td className="p-3">Cohesive Crack Damage Zones</td>
                <td className="p-3">mAP@50: 0.8064 / Precision: 0.8447</td>
                <td className="p-3 font-mono font-bold text-blue-400">Recall: 0.7478 (mAP50-95: 0.5175)</td>
                <td className="p-3">Evaluated in Colab on 1,124 CRACK500 test images (weights pending transfer)</td>
              </tr>
              <tr>
                <td className="p-3 font-bold text-white">U-Net Segmentor</td>
                <td className="p-3">Pixel Crack Mask</td>
                <td className="p-3">IoU / Dice Coefficient</td>
                <td className="p-3 font-mono font-bold text-indigo-400">0.5408 / 0.7020</td>
                <td className="p-3">Crack geometry extraction (length, aperture width, branching)</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
