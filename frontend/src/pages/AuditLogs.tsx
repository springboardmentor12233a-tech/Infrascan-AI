import React, { useState, useEffect } from 'react'
import { Navbar } from '../components/Navbar'
import { usersApi, type AuditLogEntry } from '../api/client'

export const AuditLogs: React.FC = () => {
  const [logs, setLogs] = useState<AuditLogEntry[]>([])
  const [loading, setLoading] = useState<boolean>(true)
  const [error, setError] = useState<string | null>(null)

  // Filters
  const [userIdFilter, setUserIdFilter] = useState<string>('')
  const [actionFilter, setActionFilter] = useState<string>('')
  const [entityFilter, setEntityFilter] = useState<string>('')
  const [page, setPage] = useState<number>(1)
  const [pageSize] = useState<number>(25)
  const [total, setTotal] = useState<number>(0)

  const fetchLogs = async () => {
    setLoading(true)
    setError(null)
    try {
      const data = await usersApi.listAuditLogs({
        user_id: userIdFilter ? parseInt(userIdFilter, 10) : undefined,
        action: actionFilter.trim() || undefined,
        entity_type: entityFilter.trim() || undefined,
        page,
        page_size: pageSize,
      })
      setLogs(data.items)
      setTotal(data.total)
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to load audit logs.')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchLogs()
  }, [page, actionFilter, entityFilter])

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault()
    setPage(1)
    fetchLogs()
  }

  const handleExportCsv = () => {
    const url = usersApi.exportAuditLogsUrl({
      user_id: userIdFilter ? parseInt(userIdFilter, 10) : undefined,
      action: actionFilter.trim() || undefined,
      entity_type: entityFilter.trim() || undefined,
    })
    window.open(url, '_blank')
  }

  const totalPages = Math.ceil(total / pageSize) || 1

  return (
    <div className="min-h-screen bg-slate-50 flex flex-col">
      <Navbar />

      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 mb-6">
          <div>
            <h1 className="text-2xl font-bold text-slate-900 tracking-tight">System Audit Log</h1>
            <p className="text-xs text-slate-500 mt-1">
              Tamper-evident chronological audit entries for all authentication and security events.
            </p>
          </div>
          <button
            onClick={handleExportCsv}
            className="inline-flex items-center gap-2 px-4 py-2 bg-white border border-slate-300 rounded-lg text-xs font-semibold text-slate-700 hover:bg-slate-50 shadow-sm transition"
          >
            <svg className="w-4 h-4 text-slate-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
            </svg>
            Export Audit CSV
          </button>
        </div>

        {/* Filter bar */}
        <form onSubmit={handleSearch} className="bg-white p-4 rounded-xl border border-slate-200 shadow-sm mb-6 flex flex-wrap gap-3 items-end">
          <div>
            <label className="block text-xs font-semibold text-slate-700 mb-1">User ID</label>
            <input
              type="number"
              placeholder="e.g. 1"
              value={userIdFilter}
              onChange={(e) => setUserIdFilter(e.target.value)}
              className="w-24 px-3 py-1.5 border border-slate-300 rounded-lg text-xs text-slate-800 focus:outline-none focus:ring-2 focus:ring-indigo-500"
            />
          </div>
          <div>
            <label className="block text-xs font-semibold text-slate-700 mb-1">Action</label>
            <input
              type="text"
              placeholder="e.g. login_success, role_change"
              value={actionFilter}
              onChange={(e) => setActionFilter(e.target.value)}
              className="w-48 px-3 py-1.5 border border-slate-300 rounded-lg text-xs text-slate-800 focus:outline-none focus:ring-2 focus:ring-indigo-500"
            />
          </div>
          <div>
            <label className="block text-xs font-semibold text-slate-700 mb-1">Entity Type</label>
            <input
              type="text"
              placeholder="e.g. user, auth, session"
              value={entityFilter}
              onChange={(e) => setEntityFilter(e.target.value)}
              className="w-40 px-3 py-1.5 border border-slate-300 rounded-lg text-xs text-slate-800 focus:outline-none focus:ring-2 focus:ring-indigo-500"
            />
          </div>
          <button
            type="submit"
            className="px-4 py-1.5 bg-indigo-600 hover:bg-indigo-700 text-white rounded-lg text-xs font-semibold shadow-sm transition"
          >
            Filter
          </button>
          {(userIdFilter || actionFilter || entityFilter) && (
            <button
              type="button"
              onClick={() => {
                setUserIdFilter('')
                setActionFilter('')
                setEntityFilter('')
                setPage(1)
              }}
              className="px-3 py-1.5 bg-slate-100 hover:bg-slate-200 text-slate-600 rounded-lg text-xs font-medium transition"
            >
              Reset
            </button>
          )}
        </form>

        {error && (
          <div className="p-4 mb-6 bg-rose-50 border border-rose-200 text-rose-700 rounded-xl text-xs font-medium">
            {error}
          </div>
        )}

        {/* Logs Table */}
        <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-slate-200 text-xs">
              <thead className="bg-slate-50 text-slate-500 font-semibold uppercase tracking-wider">
                <tr>
                  <th className="px-4 py-3 text-left">ID</th>
                  <th className="px-4 py-3 text-left">Timestamp</th>
                  <th className="px-4 py-3 text-left">Action</th>
                  <th className="px-4 py-3 text-left">User ID</th>
                  <th className="px-4 py-3 text-left">Entity</th>
                  <th className="px-4 py-3 text-left">Details</th>
                  <th className="px-4 py-3 text-left">IP Address</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 text-slate-700">
                {loading ? (
                  <tr>
                    <td colSpan={7} className="px-4 py-8 text-center text-slate-400">
                      Loading audit entries...
                    </td>
                  </tr>
                ) : logs.length === 0 ? (
                  <tr>
                    <td colSpan={7} className="px-4 py-8 text-center text-slate-400">
                      No audit records match the current filters.
                    </td>
                  </tr>
                ) : (
                  logs.map((log) => (
                    <tr key={log.log_id} className="hover:bg-slate-50/70 transition-colors">
                      <td className="px-4 py-2.5 font-mono text-slate-500">#{log.log_id}</td>
                      <td className="px-4 py-2.5 whitespace-nowrap text-slate-600">
                        {new Date(log.created_at).toLocaleString()}
                      </td>
                      <td className="px-4 py-2.5">
                        <span className={`inline-flex items-center px-2 py-0.5 rounded font-mono font-medium text-[11px] ${
                          log.action.includes('failure') || log.action.includes('locked')
                            ? 'bg-rose-50 text-rose-700 border border-rose-200'
                            : log.action.includes('success')
                            ? 'bg-emerald-50 text-emerald-700 border border-emerald-200'
                            : 'bg-indigo-50 text-indigo-700 border border-indigo-200'
                        }`}>
                          {log.action}
                        </span>
                      </td>
                      <td className="px-4 py-2.5 font-medium text-slate-800">
                        {log.user_id ? `User #${log.user_id}` : '—'}
                      </td>
                      <td className="px-4 py-2.5 text-slate-500 font-mono text-[11px]">
                        {log.entity_type || '—'}
                      </td>
                      <td className="px-4 py-2.5 text-slate-600 max-w-xs truncate" title={log.entity_id || ''}>
                        {log.entity_id || '—'}
                      </td>
                      <td className="px-4 py-2.5 font-mono text-slate-500 text-[11px]">
                        {log.ip_address || '—'}
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>

          {/* Pagination */}
          <div className="px-4 py-3 bg-slate-50 border-t border-slate-200 flex items-center justify-between">
            <span className="text-xs text-slate-500">
              Showing page {page} of {totalPages} ({total} total records)
            </span>
            <div className="flex gap-2">
              <button
                disabled={page <= 1}
                onClick={() => setPage((p) => Math.max(1, p - 1))}
                className="px-3 py-1 bg-white border border-slate-300 rounded text-xs font-medium text-slate-700 disabled:opacity-40 hover:bg-slate-50"
              >
                Previous
              </button>
              <button
                disabled={page >= totalPages}
                onClick={() => setPage((p) => p + 1)}
                className="px-3 py-1 bg-white border border-slate-300 rounded text-xs font-medium text-slate-700 disabled:opacity-40 hover:bg-slate-50"
              >
                Next
              </button>
            </div>
          </div>
        </div>
      </main>
    </div>
  )
}

export default AuditLogs
