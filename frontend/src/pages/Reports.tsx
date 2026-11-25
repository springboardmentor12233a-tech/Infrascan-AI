import React, { useEffect, useState } from 'react'
import { Navbar } from '../components/Navbar'
import { reportsApi, inspectionsApi, assetsApi, type ReportItem, type Inspection, type InfrastructureAsset } from '../api/client'

export const Reports: React.FC = () => {
  const [reports, setReports] = useState<ReportItem[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [successMsg, setSuccessMsg] = useState<string | null>(null)

  // Filters & Pagination
  const [statusFilter, setStatusFilter] = useState<string>('')
  const [inspectionFilter, setInspectionFilter] = useState<string>('')
  const [page, setPage] = useState(1)
  const [pageSize] = useState(15)
  const [total, setTotal] = useState(0)

  // Generate Report Modal
  const [isGenerateOpen, setIsGenerateOpen] = useState(false)
  const [selectedInspectionId, setSelectedInspectionId] = useState<number | ''>('')
  const [reportNotes, setReportNotes] = useState('')
  const [isGenerating, setIsGenerating] = useState(false)
  const [inspectionsList, setInspectionsList] = useState<Inspection[]>([])

  // Asset Export Modal
  const [isAssetExportOpen, setIsAssetExportOpen] = useState(false)
  const [selectedAssetId, setSelectedAssetId] = useState<number | ''>('')
  const [assetsList, setAssetsList] = useState<InfrastructureAsset[]>([])
  const [isExporting, setIsExporting] = useState(false)

  // Preview Modal
  const [previewReport, setPreviewReport] = useState<ReportItem | null>(null)
  const [downloadingFormat, setDownloadingFormat] = useState<string | null>(null)

  const loadReports = async () => {
    try {
      setLoading(true)
      const data = await reportsApi.listReports({
        inspection_id: inspectionFilter ? parseInt(inspectionFilter, 10) : undefined,
        status: statusFilter || undefined,
        page,
        page_size: pageSize,
      })
      setReports(data.items)
      setTotal(data.total)
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to load reports')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadReports()
  }, [page, statusFilter, inspectionFilter])

  // Fetch inspections and assets when modals open
  const openGenerateModal = async () => {
    setIsGenerateOpen(true)
    setError(null)
    try {
      const res = await inspectionsApi.list()
      setInspectionsList(res)
      if (res.length > 0) {
        setSelectedInspectionId(res[0].inspection_id)
      }
    } catch (err: any) {
      setError('Could not load inspections list')
    }
  }

  const openAssetExportModal = async () => {
    setIsAssetExportOpen(true)
    setError(null)
    try {
      const res = await assetsApi.list()
      setAssetsList(res.items)
      if (res.items.length > 0) {
        setSelectedAssetId(res.items[0].asset_id)
      }
    } catch (err: any) {
      setError('Could not load assets list')
    }
  }

  const handleGenerateReport = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!selectedInspectionId) return

    try {
      setIsGenerating(true)
      setError(null)
      const newReport = await reportsApi.generateReport(Number(selectedInspectionId), reportNotes.trim() || undefined)
      setSuccessMsg(`Report #${newReport.report_id} (Version ${newReport.version}) generated successfully as ${newReport.status.toUpperCase()}!`)
      setIsGenerateOpen(false)
      setReportNotes('')
      loadReports()
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to generate report')
    } finally {
      setIsGenerating(false)
    }
  }

  const handleDownload = async (reportId: number, format: 'pdf' | 'csv' | 'xlsx' | 'json') => {
    try {
      setDownloadingFormat(`${reportId}-${format}`)
      await reportsApi.downloadReport(reportId, format)
    } catch (err: any) {
      setError(`Failed to download ${format.toUpperCase()}: ${err.response?.data?.detail || 'File not available'}`)
    } finally {
      setDownloadingFormat(null)
    }
  }

  const handlePortfolioExport = async (format: 'csv' | 'xlsx') => {
    try {
      setIsExporting(true)
      await reportsApi.exportPortfolio(format)
      setSuccessMsg(`Portfolio export (${format.toUpperCase()}) downloaded successfully.`)
    } catch (err: any) {
      setError(`Failed to export portfolio: ${err.response?.data?.detail || err.message}`)
    } finally {
      setIsExporting(false)
    }
  }

  const handleAssetExport = async (format: 'csv' | 'xlsx') => {
    if (!selectedAssetId) return
    try {
      setIsExporting(true)
      await reportsApi.exportAsset(Number(selectedAssetId), format)
      setIsAssetExportOpen(false)
      setSuccessMsg(`Asset #${selectedAssetId} summary exported successfully.`)
    } catch (err: any) {
      setError(`Failed to export asset: ${err.response?.data?.detail || err.message}`)
    } finally {
      setIsExporting(false)
    }
  }

  return (
    <div className="min-h-screen bg-slate-50 text-slate-800">
      <Navbar />

      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Mandatory Header Disclaimer Alert */}
        <div className="mb-6 p-4 bg-amber-50 border-l-4 border-amber-500 rounded-r shadow-sm flex items-start gap-3">
          <svg className="w-5 h-5 text-amber-600 mt-0.5 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
            <path fillRule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
          </svg>
          <div>
            <h4 className="text-sm font-semibold text-amber-800">Mandatory Engineering Disclaimer</h4>
            <p className="text-xs text-amber-700 mt-0.5">
              AI result for engineer review, not a final structural safety verdict. Measurements and severity categories are provisional until reviewed and signed off by a qualified civil engineer.
            </p>
          </div>
        </div>

        {/* Action Header */}
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 mb-6">
          <div>
            <h1 className="text-2xl font-bold text-slate-900">Reports & Audit Exports</h1>
            <p className="text-sm text-slate-500 mt-1">
              Version-controlled immutable structural inspection records, multi-format bundles, and compliance snapshots.
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-2">
            <button
              onClick={() => handlePortfolioExport('csv')}
              disabled={isExporting}
              className="px-3 py-2 text-xs font-medium rounded-lg border border-slate-300 bg-white hover:bg-slate-50 text-slate-700 shadow-sm transition disabled:opacity-50"
              title="Download portfolio defect and inspection summary as CSV"
            >
              Export Portfolio (CSV)
            </button>
            <button
              onClick={() => handlePortfolioExport('xlsx')}
              disabled={isExporting}
              className="px-3 py-2 text-xs font-medium rounded-lg border border-slate-300 bg-white hover:bg-slate-50 text-slate-700 shadow-sm transition disabled:opacity-50"
              title="Download portfolio defect and inspection summary as Excel"
            >
              Export Portfolio (Excel)
            </button>
            <button
              onClick={openAssetExportModal}
              className="px-3 py-2 text-xs font-medium rounded-lg border border-slate-300 bg-white hover:bg-slate-50 text-slate-700 shadow-sm transition"
            >
              Export Asset Summary...
            </button>
            <button
              onClick={openGenerateModal}
              className="px-4 py-2 text-xs font-medium rounded-lg bg-indigo-600 hover:bg-indigo-700 text-white shadow transition flex items-center gap-1.5"
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 4v16m8-8H4" />
              </svg>
              Generate Report
            </button>
          </div>
        </div>

        {/* Notifications */}
        {error && (
          <div className="mb-4 p-3 bg-red-50 border border-red-200 text-red-700 rounded-lg text-sm flex justify-between items-center">
            <span>{error}</span>
            <button onClick={() => setError(null)} className="text-red-500 hover:text-red-700 font-bold">&times;</button>
          </div>
        )}
        {successMsg && (
          <div className="mb-4 p-3 bg-green-50 border border-green-200 text-green-700 rounded-lg text-sm flex justify-between items-center">
            <span>{successMsg}</span>
            <button onClick={() => setSuccessMsg(null)} className="text-green-500 hover:text-green-700 font-bold">&times;</button>
          </div>
        )}

        {/* Filters */}
        <div className="bg-white p-4 rounded-xl shadow-sm border border-slate-200 mb-6 flex flex-wrap gap-4 items-center">
          <div className="flex-1 min-w-[200px]">
            <label className="block text-xs font-medium text-slate-500 mb-1">Filter by Inspection ID</label>
            <input
              type="number"
              placeholder="e.g. 101"
              value={inspectionFilter}
              onChange={(e) => {
                setInspectionFilter(e.target.value)
                setPage(1)
              }}
              className="w-full text-xs px-3 py-2 border border-slate-300 rounded-lg focus:ring-1 focus:ring-indigo-500 focus:outline-none"
            />
          </div>

          <div className="w-48">
            <label className="block text-xs font-medium text-slate-500 mb-1">Status</label>
            <select
              value={statusFilter}
              onChange={(e) => {
                setStatusFilter(e.target.value)
                setPage(1)
              }}
              className="w-full text-xs px-3 py-2 border border-slate-300 rounded-lg focus:ring-1 focus:ring-indigo-500 focus:outline-none"
            >
              <option value="">All Statuses</option>
              <option value="draft">Draft (Pending Review)</option>
              <option value="final">Final (Reviewed)</option>
            </select>
          </div>

          <div className="flex items-end pt-5">
            <button
              onClick={() => {
                setInspectionFilter('')
                setStatusFilter('')
                setPage(1)
              }}
              className="px-3 py-2 text-xs text-slate-600 hover:text-slate-900 border border-slate-200 rounded-lg hover:bg-slate-50"
            >
              Clear Filters
            </button>
          </div>
        </div>

        {/* Table of Reports */}
        <div className="bg-white rounded-xl shadow-sm border border-slate-200 overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-slate-50 border-b border-slate-200 text-slate-600 font-semibold uppercase tracking-wider">
                <tr>
                  <th className="py-3 px-4">Report</th>
                  <th className="py-3 px-4">Inspection</th>
                  <th className="py-3 px-4">Status</th>
                  <th className="py-3 px-4">Generated At</th>
                  <th className="py-3 px-4">SHA256 Hash</th>
                  <th className="py-3 px-4 text-center">Available Formats</th>
                  <th className="py-3 px-4 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {loading ? (
                  <tr>
                    <td colSpan={7} className="text-center py-10 text-slate-400">Loading reports...</td>
                  </tr>
                ) : reports.length === 0 ? (
                  <tr>
                    <td colSpan={7} className="text-center py-12">
                      <p className="text-sm text-slate-500 font-medium">No reports generated yet.</p>
                      <p className="text-xs text-slate-400 mt-1">Select an inspection above and click "Generate Report".</p>
                    </td>
                  </tr>
                ) : (
                  reports.map((report) => (
                    <tr key={report.report_id} className="hover:bg-slate-50 transition">
                      <td className="py-3 px-4 font-mono font-medium text-slate-900">
                        #{report.report_id} <span className="text-slate-400 font-sans text-xs">v{report.version}</span>
                      </td>
                      <td className="py-3 px-4">
                        <span className="font-semibold text-indigo-600">Inspection #{report.inspection_id}</span>
                      </td>
                      <td className="py-3 px-4">
                        {report.status === 'final' ? (
                          <span className="inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-semibold bg-emerald-100 text-emerald-800">
                            FINAL
                          </span>
                        ) : (
                          <span className="inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-semibold bg-amber-100 text-amber-800">
                            DRAFT (PENDING REVIEW)
                          </span>
                        )}
                      </td>
                      <td className="py-3 px-4 text-slate-500">
                        {new Date(report.generated_at).toLocaleString()}
                      </td>
                      <td className="py-3 px-4 font-mono text-[11px] text-slate-400" title={report.content_sha256}>
                        {report.content_sha256.slice(0, 10)}...{report.content_sha256.slice(-6)}
                      </td>
                      <td className="py-3 px-4">
                        <div className="flex items-center justify-center gap-1.5">
                          <button
                            onClick={() => handleDownload(report.report_id, 'pdf')}
                            disabled={downloadingFormat === `${report.report_id}-pdf`}
                            className="px-2 py-1 rounded bg-rose-50 text-rose-700 hover:bg-rose-100 font-semibold border border-rose-200 transition text-[10px]"
                            title="Download PDF Inspection Report"
                          >
                            PDF
                          </button>
                          <button
                            onClick={() => handleDownload(report.report_id, 'csv')}
                            disabled={downloadingFormat === `${report.report_id}-csv`}
                            className="px-2 py-1 rounded bg-blue-50 text-blue-700 hover:bg-blue-100 font-semibold border border-blue-200 transition text-[10px]"
                            title="Download CSV ZIP Bundle"
                          >
                            CSV
                          </button>
                          <button
                            onClick={() => handleDownload(report.report_id, 'xlsx')}
                            disabled={downloadingFormat === `${report.report_id}-xlsx`}
                            className="px-2 py-1 rounded bg-emerald-50 text-emerald-700 hover:bg-emerald-100 font-semibold border border-emerald-200 transition text-[10px]"
                            title="Download Excel Workbook (8 sheets)"
                          >
                            XLSX
                          </button>
                          <button
                            onClick={() => handleDownload(report.report_id, 'json')}
                            disabled={downloadingFormat === `${report.report_id}-json`}
                            className="px-2 py-1 rounded bg-slate-100 text-slate-700 hover:bg-slate-200 font-semibold border border-slate-300 transition text-[10px]"
                            title="Download Machine-Readable JSON Snapshot"
                          >
                            JSON
                          </button>
                        </div>
                      </td>
                      <td className="py-3 px-4 text-right">
                        <button
                          onClick={() => setPreviewReport(report)}
                          className="px-2.5 py-1 text-slate-600 hover:text-indigo-600 hover:bg-indigo-50 border border-slate-200 rounded font-medium transition"
                        >
                          View Details
                        </button>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>

          {/* Pagination */}
          {total > pageSize && (
            <div className="p-4 border-t border-slate-100 flex items-center justify-between text-xs text-slate-500">
              <span>Showing {((page - 1) * pageSize) + 1} to {Math.min(page * pageSize, total)} of {total} reports</span>
              <div className="flex gap-2">
                <button
                  disabled={page === 1}
                  onClick={() => setPage(p => p - 1)}
                  className="px-3 py-1 border rounded disabled:opacity-40"
                >
                  Previous
                </button>
                <button
                  disabled={page * pageSize >= total}
                  onClick={() => setPage(p => p + 1)}
                  className="px-3 py-1 border rounded disabled:opacity-40"
                >
                  Next
                </button>
              </div>
            </div>
          )}
        </div>
      </main>

      {/* Generate Report Modal */}
      {isGenerateOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm p-4">
          <div className="bg-white rounded-2xl shadow-xl max-w-lg w-full p-6 border border-slate-100">
            <h3 className="text-lg font-bold text-slate-900 mb-1">Generate Inspection Report</h3>
            <p className="text-xs text-slate-500 mb-4">
              Produces an immutable versioned snapshot in PDF, Excel, CSV Bundle, and JSON formats.
            </p>

            <form onSubmit={handleGenerateReport} className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">Select Inspection</label>
                <select
                  required
                  value={selectedInspectionId}
                  onChange={(e) => setSelectedInspectionId(Number(e.target.value))}
                  className="w-full text-xs px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:outline-none"
                >
                  {inspectionsList.map(insp => (
                    <option key={insp.inspection_id} value={insp.inspection_id}>
                      #{insp.inspection_id} — {insp.asset_name || `Asset #${insp.asset_id}`} ({new Date(insp.inspection_date).toLocaleDateString()}) - {insp.status.toUpperCase()}
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">Engineer Notes (Optional)</label>
                <textarea
                  rows={3}
                  value={reportNotes}
                  onChange={(e) => setReportNotes(e.target.value)}
                  placeholder="e.g. Field inspection conducted post-seismic event; cracks monitored on Pier 2."
                  className="w-full text-xs p-3 border border-slate-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:outline-none"
                />
              </div>

              <div className="p-3 bg-amber-50 rounded-lg border border-amber-200 text-amber-800 text-[11px] leading-relaxed">
                <strong>Note on Report Status:</strong> If any severity assessment is pending review, the report will be branded as <em>DRAFT</em> with watermarks. If all images have confirmed reviews, the report is generated as <em>FINAL</em>.
              </div>

              <div className="flex justify-end gap-3 pt-2">
                <button
                  type="button"
                  onClick={() => setIsGenerateOpen(false)}
                  className="px-4 py-2 text-xs font-medium text-slate-600 hover:bg-slate-100 rounded-lg"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={isGenerating}
                  className="px-5 py-2 text-xs font-medium bg-indigo-600 hover:bg-indigo-700 text-white rounded-lg shadow disabled:opacity-50"
                >
                  {isGenerating ? 'Generating Bundle...' : 'Generate Report'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Asset Export Modal */}
      {isAssetExportOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm p-4">
          <div className="bg-white rounded-2xl shadow-xl max-w-md w-full p-6 border border-slate-100">
            <h3 className="text-lg font-bold text-slate-900 mb-1">Export Asset History</h3>
            <p className="text-xs text-slate-500 mb-4">
              Download historical inspection logs, defect counts, and trends for a specific asset.
            </p>

            <div className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">Select Asset</label>
                <select
                  value={selectedAssetId}
                  onChange={(e) => setSelectedAssetId(Number(e.target.value))}
                  className="w-full text-xs px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:outline-none"
                >
                  {assetsList.map(a => (
                    <option key={a.asset_id} value={a.asset_id}>
                      #{a.asset_id} - {a.name} ({a.asset_type})
                    </option>
                  ))}
                </select>
              </div>

              <div className="flex justify-end gap-2 pt-3">
                <button
                  type="button"
                  onClick={() => setIsAssetExportOpen(false)}
                  className="px-3 py-2 text-xs font-medium text-slate-600 hover:bg-slate-100 rounded-lg"
                >
                  Cancel
                </button>
                <button
                  type="button"
                  onClick={() => handleAssetExport('csv')}
                  disabled={isExporting}
                  className="px-3 py-2 text-xs font-medium border border-slate-300 bg-white hover:bg-slate-50 text-slate-700 rounded-lg"
                >
                  Download CSV
                </button>
                <button
                  type="button"
                  onClick={() => handleAssetExport('xlsx')}
                  disabled={isExporting}
                  className="px-4 py-2 text-xs font-medium bg-indigo-600 hover:bg-indigo-700 text-white rounded-lg"
                >
                  Download Excel
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Report Preview Modal */}
      {previewReport && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm p-4">
          <div className="bg-white rounded-2xl shadow-xl max-w-2xl w-full p-6 border border-slate-100 max-h-[85vh] overflow-y-auto">
            <div className="flex justify-between items-start mb-4 pb-3 border-b border-slate-100">
              <div>
                <h3 className="text-lg font-bold text-slate-900">Report #{previewReport.report_id} Snapshot Details</h3>
                <p className="text-xs text-slate-500">Version {previewReport.version} &bull; Generated {new Date(previewReport.generated_at).toLocaleString()}</p>
              </div>
              <button
                onClick={() => setPreviewReport(null)}
                className="text-slate-400 hover:text-slate-600 text-xl font-bold"
              >
                &times;
              </button>
            </div>

            <div className="space-y-4 text-xs">
              <div className="grid grid-cols-2 gap-3 p-3 bg-slate-50 rounded-lg">
                <div>
                  <span className="font-semibold text-slate-500">Inspection:</span>
                  <p className="font-bold text-slate-800">#{previewReport.inspection_id}</p>
                </div>
                <div>
                  <span className="font-semibold text-slate-500">Status:</span>
                  <p className="font-bold uppercase tracking-wide text-slate-800">{previewReport.status}</p>
                </div>
                <div className="col-span-2">
                  <span className="font-semibold text-slate-500">Content SHA256:</span>
                  <p className="font-mono text-[11px] text-slate-700 break-all">{previewReport.content_sha256}</p>
                </div>
                {previewReport.notes && (
                  <div className="col-span-2">
                    <span className="font-semibold text-slate-500">Notes:</span>
                    <p className="text-slate-700 mt-0.5">{previewReport.notes}</p>
                  </div>
                )}
              </div>

              <div>
                <h4 className="font-semibold text-slate-800 mb-2">Generated Files &amp; Checksums</h4>
                <div className="border border-slate-200 rounded-lg overflow-hidden">
                  <table className="w-full text-left">
                    <thead className="bg-slate-100 text-slate-600 font-semibold">
                      <tr>
                        <th className="p-2">Format</th>
                        <th className="p-2">Size</th>
                        <th className="p-2">SHA256</th>
                        <th className="p-2 text-right">Download</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-100">
                      {previewReport.files.map(f => (
                        <tr key={f.file_id}>
                          <td className="p-2 uppercase font-bold text-indigo-600">{f.format}</td>
                          <td className="p-2 text-slate-500">{(f.size / 1024).toFixed(1)} KB</td>
                          <td className="p-2 font-mono text-[10px] text-slate-400" title={f.sha256}>{f.sha256.slice(0, 16)}...</td>
                          <td className="p-2 text-right">
                            <button
                              onClick={() => handleDownload(previewReport.report_id, f.format as any)}
                              className="px-2 py-0.5 bg-slate-100 hover:bg-slate-200 rounded text-slate-700 font-medium"
                            >
                              Download
                            </button>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>

              <div className="p-3 bg-slate-50 rounded-lg text-slate-600 text-[11px]">
                <strong>Compliance:</strong> Every document includes the mandatory disclaimer:
                <em> "AI result for engineer review, not a final structural safety verdict."</em>
              </div>
            </div>

            <div className="flex justify-end pt-4 border-t border-slate-100 mt-4">
              <button
                onClick={() => setPreviewReport(null)}
                className="px-4 py-2 text-xs font-medium bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-lg"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
export default Reports
