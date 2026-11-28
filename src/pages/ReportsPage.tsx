import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { FileText, Download, Eye, Plus } from 'lucide-react'
import { reportService } from '@/services/reportService'
import { MOCK_INSPECTIONS } from '@/data/mockData'
import { SeverityBadge } from '@/components/ui/SeverityBadge'
import { StatusBadge } from '@/components/ui/StatusBadge'
import { Modal } from '@/components/ui/Modal'
import type { InspectionReport } from '@/types'

export function ReportsPage() {
  const queryClient = useQueryClient()
  const { data: reports = [] } = useQuery({
    queryKey: ['reports'],
    queryFn: reportService.getAll,
  })
  const [preview, setPreview] = useState<InspectionReport | null>(null)

  const generateMutation = useMutation({
    mutationFn: () => {
      const insp = MOCK_INSPECTIONS[0]
      return reportService.generate(insp.id, insp.assetId, insp.assetName)
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['reports'] }),
  })

  const exportCsv = () => {
    const header = 'Report ID,Title,Asset,Generated At,Review Status,Max Severity\n'
    const rows = reports
      .map((r) => `"${r.id}","${r.title}","${r.assetName}","${r.generatedAt}","${r.engineerReviewStatus}","${r.maxSeverity}"`)
      .join('\n')
    const blob = new Blob([header + rows], { type: 'text/csv;charset=utf-8;' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = 'infrascan-inspection-reports.csv'
    a.click()
    URL.revokeObjectURL(url)
  }

  return (
    <div className="space-y-5">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-semibold text-slate-900">Inspection Reports</h1>
          <p className="text-xs text-slate-500 mt-0.5">
            Engineering-grade inspection summaries, AI findings, and exportable documentation
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={exportCsv}
            className="inline-flex items-center gap-1.5 px-3.5 py-2 rounded-md bg-white border border-slate-200 hover:bg-slate-50 text-slate-700 text-xs font-medium"
          >
            <Download className="w-3.5 h-3.5" /> Export CSV
          </button>
          <button
            onClick={() => generateMutation.mutate()}
            className="inline-flex items-center gap-1.5 px-3.5 py-2 rounded-md bg-[#0F2942] hover:bg-[#163859] text-white text-xs font-medium"
          >
            <Plus className="w-3.5 h-3.5" /> Generate Report
          </button>
        </div>
      </div>

      <div className="bg-white rounded-lg border border-slate-200 overflow-hidden shadow-xs">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="bg-slate-50 text-slate-500 border-b border-slate-200">
              <tr>
                <th className="px-4 py-3 font-medium">Report ID</th>
                <th className="px-4 py-3 font-medium">Title</th>
                <th className="px-4 py-3 font-medium">Generated</th>
                <th className="px-4 py-3 font-medium">Review Status</th>
                <th className="px-4 py-3 font-medium">Max Severity</th>
                <th className="px-4 py-3 font-medium text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {reports.map((rpt) => (
                <tr key={rpt.id} className="hover:bg-slate-50">
                  <td className="px-4 py-3 font-mono font-medium text-slate-800">{rpt.id}</td>
                  <td className="px-4 py-3">
                    <p className="font-medium text-slate-900">{rpt.title}</p>
                    <p className="text-[11px] text-slate-500">{rpt.assetName}</p>
                  </td>
                  <td className="px-4 py-3 text-slate-600">{rpt.generatedAt}</td>
                  <td className="px-4 py-3">
                    <StatusBadge status={rpt.engineerReviewStatus} />
                  </td>
                  <td className="px-4 py-3">
                    <SeverityBadge severity={rpt.maxSeverity} />
                  </td>
                  <td className="px-4 py-3 text-right">
                    <button
                      onClick={() => setPreview(rpt)}
                      className="inline-flex items-center gap-1 px-2.5 py-1 rounded border border-slate-200 hover:bg-slate-100 text-slate-700"
                    >
                      <Eye className="w-3.5 h-3.5" /> Preview
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      <Modal open={!!preview} onClose={() => setPreview(null)} title={preview?.title || ''} subtitle={preview?.id}>
        {preview && (
          <div className="space-y-4 text-xs">
            <div className="p-4 rounded-md bg-slate-50 border border-slate-200 space-y-2">
              <div className="flex items-center gap-2 font-semibold text-slate-900">
                <FileText className="w-4 h-4 text-cyan-700" /> Executive Summary
              </div>
              <p className="text-slate-700">{preview.findingsSummary}</p>
            </div>
            <div className="flex justify-end gap-2">
              <button
                onClick={() => window.print()}
                className="inline-flex items-center gap-1.5 px-4 py-2 bg-[#0F2942] text-white rounded-md font-medium"
              >
                <Download className="w-3.5 h-3.5" /> Print / Save PDF
              </button>
            </div>
          </div>
        )}
      </Modal>
    </div>
  )
}

