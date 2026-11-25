import React, { useState } from 'react'
import { Navbar } from '../components/Navbar'

export const Help: React.FC = () => {
  const [activeTab, setActiveTab] = useState<'inspector' | 'civil_engineer' | 'maintenance' | 'manager' | 'admin'>('inspector')

  return (
    <div className="min-h-screen bg-slate-50 flex flex-col">
      <Navbar />
      <div className="container mx-auto px-4 py-8 max-w-6xl flex-1">
        <div className="mb-6">
          <h1 className="text-3xl font-extrabold text-gray-900">User Guides &amp; Role Manuals</h1>
          <p className="text-sm text-gray-500 mt-1">
            Standard operating procedures and interactive workflow walkthroughs per user role.
          </p>
        </div>

        {/* Role Tabs */}
        <div className="flex border-b border-gray-200 mb-6 space-x-2 overflow-x-auto">
          {[
            { id: 'inspector', label: 'Field Inspector' },
            { id: 'civil_engineer', label: 'Civil Engineer' },
            { id: 'maintenance', label: 'Maintenance Engineer' },
            { id: 'manager', label: 'Operations Manager' },
            { id: 'admin', label: 'System Admin' },
          ].map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id as any)}
              className={`px-4 py-2.5 text-sm font-semibold border-b-2 transition whitespace-nowrap ${
                activeTab === tab.id
                  ? 'border-indigo-600 text-indigo-600 bg-white rounded-t'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>

        {/* Tab Contents */}
        <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-8">
          {activeTab === 'inspector' && (
            <div className="space-y-6">
              <div className="flex items-center gap-3">
                <span className="w-8 h-8 rounded-full bg-blue-100 text-blue-700 font-bold flex items-center justify-center text-sm">
                  1
                </span>
                <h2 className="text-xl font-bold text-gray-900">Field Inspector Standard Operating Procedure</h2>
              </div>
              <p className="text-sm text-gray-600">
                Inspectors capture high-resolution imagery in the field, run immediate blur and illumination validation,
                and queue batch uploads to the central inspection database.
              </p>

              <div className="bg-slate-50 p-5 rounded-lg border border-slate-200 space-y-3 font-mono text-xs">
                <div className="font-bold text-gray-800">[Inspector Mobile Workflow Wireframe]</div>
                <div>+-------------------------------------------------------+</div>
                <div>| 1. Select Assigned Asset &amp; Start Inspection         |</div>
                <div>| 2. Open Camera &rarr; Live Quality Evaluation             |</div>
                <div>|    - Blur Metric (Laplacian variance &gt; 100)           |</div>
                <div>|    - Brightness Check (Mean intensity 50..220)          |</div>
                <div>| 3. Add Reference Scale (Coin / R-Checker target)       |</div>
                <div>| 4. Batch Queue &rarr; Auto-Sync when Wi-Fi/LTE Connected   |</div>
                <div>+-------------------------------------------------------+</div>
              </div>

              <div className="space-y-2 text-sm text-gray-700">
                <h3 className="font-bold text-gray-900">Key Guidelines:</h3>
                <ul className="list-disc pl-5 space-y-1">
                  <li>Ensure inspection photos are perpendicular to structural surfaces.</li>
                  <li>Avoid direct glare or dark shadows when capturing crack candidates.</li>
                  <li>Always include a calibration ruler or standard reference marker in at least one baseline photo per structural zone.</li>
                </ul>
              </div>
            </div>
          )}

          {activeTab === 'civil_engineer' && (
            <div className="space-y-6">
              <div className="flex items-center gap-3">
                <span className="w-8 h-8 rounded-full bg-emerald-100 text-emerald-700 font-bold flex items-center justify-center text-sm">
                  2
                </span>
                <h2 className="text-xl font-bold text-gray-900">Civil Engineer Review &amp; Analysis Workflow</h2>
              </div>
              <p className="text-sm text-gray-600">
                Civil Engineers inspect AI model detections, verify semantic crack segmentation masks, interact with Grad-CAM heatmaps,
                and confirm or override provisional severity ratings.
              </p>

              <div className="bg-slate-50 p-5 rounded-lg border border-slate-200 space-y-3 font-mono text-xs">
                <div className="font-bold text-gray-800">[Inspection Viewer Controls]</div>
                <div>+-------------------------------------------------------+</div>
                <div>| [Pan / Zoom]  [Layer Toggles: Image | Mask | Heatmap]  |</div>
                <div>| [Confidence Threshold Slider]  [Crack Width Profiler]  |</div>
                <div>|                                                       |</div>
                <div>| Actions:                                              |</div>
                <div>| - Confirm Severity (Provisional &rarr; Final)               |</div>
                <div>| - Interactive Scale Calibration (Draw reference line) |</div>
                <div>| - Reject false-positive detection                     |</div>
                <div>+-------------------------------------------------------+</div>
              </div>

              <div className="p-4 bg-amber-50 border-l-4 border-amber-400 rounded-r text-xs text-amber-900">
                <strong>Safety Protocol:</strong> "AI result for engineer review, not a final structural safety verdict."
                Severity ratings remain provisional until an engineer explicitly reviews and signs off on the inspection report.
              </div>
            </div>
          )}

          {activeTab === 'maintenance' && (
            <div className="space-y-6">
              <div className="flex items-center gap-3">
                <span className="w-8 h-8 rounded-full bg-amber-100 text-amber-700 font-bold flex items-center justify-center text-sm">
                  3
                </span>
                <h2 className="text-xl font-bold text-gray-900">Maintenance Engineer Workflow</h2>
              </div>
              <p className="text-sm text-gray-600">
                Maintenance Engineers receive automated notifications for approaching deadlines and critical defect alerts,
                prioritizing work orders according to composite criticality formulas.
              </p>

              <div className="space-y-3 text-sm text-gray-700">
                <h3 className="font-bold text-gray-900">Automated Notification Rules:</h3>
                <ul className="list-disc pl-5 space-y-1">
                  <li><strong>Critical Defect Alert</strong>: Triggered when severity assessment yields high/critical score.</li>
                  <li><strong>Maintenance Deadline Sweep</strong>: Scheduled check notifies engineers 48 hours prior to work order due date.</li>
                  <li><strong>Overdue Inspection Alerts</strong>: Identifies assets exceeding mandatory inspection cycles.</li>
                </ul>
              </div>
            </div>
          )}

          {activeTab === 'manager' && (
            <div className="space-y-6">
              <div className="flex items-center gap-3">
                <span className="w-8 h-8 rounded-full bg-purple-100 text-purple-700 font-bold flex items-center justify-center text-sm">
                  4
                </span>
                <h2 className="text-xl font-bold text-gray-900">Operations Manager &amp; Portfolio Analytics</h2>
              </div>
              <p className="text-sm text-gray-600">
                Managers oversee the entire infrastructure asset network, track geospatial distress clusters on the Damage Map,
                and export formal audit reports in multi-format packages.
              </p>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="p-4 bg-slate-50 rounded border text-xs">
                  <div className="font-bold text-gray-800 mb-1">Geospatial Hotspots &amp; Routing</div>
                  <p className="text-gray-600">
                    Clustering algorithms group distress points within a 200m radius, identifying critical structural corridors and optimal repair routes.
                  </p>
                </div>
                <div className="p-4 bg-slate-50 rounded border text-xs">
                  <div className="font-bold text-gray-800 mb-1">Multi-Tab Excel &amp; PDF Exports</div>
                  <p className="text-gray-600">
                    Generate ReportLab two-pass PDFs with "Page X of Y", draft watermarks, and openpyxl 8-sheet Excel workbooks sanitized against formula injection.
                  </p>
                </div>
              </div>
            </div>
          )}

          {activeTab === 'admin' && (
            <div className="space-y-6">
              <div className="flex items-center gap-3">
                <span className="w-8 h-8 rounded-full bg-red-100 text-red-700 font-bold flex items-center justify-center text-sm">
                  5
                </span>
                <h2 className="text-xl font-bold text-gray-900">System Administrator Guide</h2>
              </div>
              <p className="text-sm text-gray-600">
                Administrators manage user roles, audit trails, brute-force security lockouts, and deep learning model activations with smoke test verification.
              </p>

              <div className="space-y-3 text-sm text-gray-700">
                <h3 className="font-bold text-gray-900">Admin Controls:</h3>
                <ul className="list-disc pl-5 space-y-1">
                  <li><strong>Model Smoke Testing</strong>: Activating a model executes an automated dummy tensor forward pass; corrupted weights are automatically blocked.</li>
                  <li><strong>Session Revocation</strong>: Global session termination across devices or per-user.</li>
                  <li><strong>Account Lockout</strong>: 5 consecutive failed logins trigger a 15-minute freeze.</li>
                </ul>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
export default Help
