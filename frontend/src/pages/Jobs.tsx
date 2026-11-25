import React, { useState, useEffect } from 'react'
import { Navbar } from '../components/Navbar'
import { jobsApi, type JobItem } from '../api/client'

export const Jobs: React.FC = () => {
  const [jobs, setJobs] = useState<JobItem[]>([])
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(true)
  const [statusFilter, setStatusFilter] = useState<string>('')
  const [typeFilter, setTypeFilter] = useState<string>('')
  const [autoRefresh, setAutoRefresh] = useState(true)
  const [actionLoading, setActionLoading] = useState(false)
  const [feedback, setFeedback] = useState<{ type: 'success' | 'error'; msg: string } | null>(null)

  const loadJobs = async () => {
    try {
      const res = await jobsApi.list({
        status: statusFilter || undefined,
        job_type: typeFilter || undefined,
        page: 1,
        page_size: 50,
      })
      setJobs(res.jobs)
      setTotal(res.total)
    } catch (err: any) {
      console.error('Failed to load background jobs:', err)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadJobs()
  }, [statusFilter, typeFilter])

  useEffect(() => {
    if (!autoRefresh) return
    const interval = setInterval(() => {
      loadJobs()
    }, 3000)
    return () => clearInterval(interval)
  }, [autoRefresh, statusFilter, typeFilter])

  const handleCancel = async (jobId: number) => {
    try {
      setActionLoading(true)
      await jobsApi.cancel(jobId)
      setFeedback({ type: 'success', msg: `Job #${jobId} cancelled successfully.` })
      await loadJobs()
    } catch (err: any) {
      setFeedback({ type: 'error', msg: err.response?.data?.detail || `Failed to cancel job #${jobId}.` })
    } finally {
      setActionLoading(false)
    }
  }

  const handleEnqueueTest = async () => {
    try {
      setActionLoading(true)
      await jobsApi.enqueue({
        job_type: 'batch_import',
        payload: {
          items: ['img_test_01.jpg', 'img_test_02.jpg', 'img_test_03.jpg', 'img_test_04.jpg'],
          source: 'manual_test_dispatch',
        },
      })
      setFeedback({ type: 'success', msg: 'Test batch job enqueued successfully.' })
      await loadJobs()
    } catch (err: any) {
      setFeedback({ type: 'error', msg: err.response?.data?.detail || 'Failed to enqueue test job.' })
    } finally {
      setActionLoading(false)
    }
  }

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'completed':
        return <span className="px-2 py-0.5 rounded text-xs font-medium bg-green-100 text-green-800">Completed</span>
      case 'running':
        return <span className="px-2 py-0.5 rounded text-xs font-medium bg-blue-100 text-blue-800 animate-pulse">Running</span>
      case 'pending':
        return <span className="px-2 py-0.5 rounded text-xs font-medium bg-amber-100 text-amber-800">Pending</span>
      case 'failed':
        return <span className="px-2 py-0.5 rounded text-xs font-medium bg-red-100 text-red-800">Failed</span>
      case 'cancelled':
        return <span className="px-2 py-0.5 rounded text-xs font-medium bg-gray-100 text-gray-700">Cancelled</span>
      default:
        return <span className="px-2 py-0.5 rounded text-xs font-medium bg-gray-100 text-gray-700">{status}</span>
    }
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <Navbar />
      <div className="container mx-auto px-4 py-8 max-w-7xl">
      <div className="mb-6 flex flex-col md:flex-row md:items-center md:justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Background Job Queue</h1>
          <p className="text-sm text-gray-500 mt-1">
            Database-backed queue for asynchronous AI inference, report compilation, and batch tasks.
          </p>
        </div>
        <div className="flex items-center gap-3">
          <label className="flex items-center text-xs text-gray-600 gap-1.5 cursor-pointer">
            <input
              type="checkbox"
              checked={autoRefresh}
              onChange={(e) => setAutoRefresh(e.target.checked)}
              className="rounded text-blue-600"
            />
            Live Polling (3s)
          </label>
          <button
            onClick={handleEnqueueTest}
            disabled={actionLoading}
            className="px-3 py-1.5 bg-blue-600 hover:bg-blue-700 text-white text-xs font-medium rounded shadow-sm disabled:opacity-50"
          >
            + Enqueue Test Batch
          </button>
          <button
            onClick={loadJobs}
            className="px-3 py-1.5 bg-gray-100 hover:bg-gray-200 text-gray-700 text-xs font-medium rounded shadow-sm"
          >
            Refresh
          </button>
        </div>
      </div>

      {feedback && (
        <div
          className={`p-4 mb-6 rounded ${
            feedback.type === 'success' ? 'bg-green-50 text-green-800 border border-green-200' : 'bg-red-50 text-red-800 border border-red-200'
          }`}
        >
          {feedback.msg}
        </div>
      )}

      {/* Filters bar */}
      <div className="bg-white p-4 rounded-lg shadow-sm border border-gray-200 mb-6 flex flex-wrap gap-4 items-center">
        <div>
          <label className="block text-xs font-medium text-gray-500 mb-1">Status</label>
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="text-xs border rounded px-3 py-1.5 text-gray-700 bg-white"
          >
            <option value="">All Statuses</option>
            <option value="pending">Pending</option>
            <option value="running">Running</option>
            <option value="completed">Completed</option>
            <option value="failed">Failed</option>
            <option value="cancelled">Cancelled</option>
          </select>
        </div>

        <div>
          <label className="block text-xs font-medium text-gray-500 mb-1">Job Type</label>
          <select
            value={typeFilter}
            onChange={(e) => setTypeFilter(e.target.value)}
            className="text-xs border rounded px-3 py-1.5 text-gray-700 bg-white"
          >
            <option value="">All Types</option>
            <option value="analysis_run">Analysis Run</option>
            <option value="report_generation">Report Generation</option>
            <option value="batch_import">Batch Import</option>
          </select>
        </div>

        <div className="ml-auto text-xs text-gray-500 self-end pb-1.5">
          Total: <span className="font-semibold text-gray-800">{total}</span> jobs
        </div>
      </div>

      {/* Jobs Table */}
      <div className="bg-white rounded-lg shadow border border-gray-200 overflow-hidden">
        {loading ? (
          <div className="p-8 text-center text-gray-500">Loading jobs...</div>
        ) : jobs.length === 0 ? (
          <div className="p-8 text-center text-gray-500">No background jobs found.</div>
        ) : (
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200 text-sm">
              <thead className="bg-gray-50 text-xs font-semibold text-gray-600 uppercase">
                <tr>
                  <th className="px-4 py-3 text-left">ID</th>
                  <th className="px-4 py-3 text-left">Job Type</th>
                  <th className="px-4 py-3 text-left">Status</th>
                  <th className="px-4 py-3 text-left">Progress</th>
                  <th className="px-4 py-3 text-center">Retries</th>
                  <th className="px-4 py-3 text-left">Created At</th>
                  <th className="px-4 py-3 text-left">Result / Error</th>
                  <th className="px-4 py-3 text-center">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200">
                {jobs.map((job) => (
                  <tr key={job.id} className="hover:bg-gray-50">
                    <td className="px-4 py-3 font-mono text-xs font-bold text-gray-700">#{job.id}</td>
                    <td className="px-4 py-3 font-medium text-gray-900 capitalize">
                      {job.job_type.replace('_', ' ')}
                    </td>
                    <td className="px-4 py-3">{getStatusBadge(job.status)}</td>
                    <td className="px-4 py-3 w-40">
                      <div className="flex items-center gap-2">
                        <div className="w-full bg-gray-200 rounded-full h-2">
                          <div
                            className={`h-2 rounded-full ${
                              job.status === 'completed'
                                ? 'bg-green-600'
                                : job.status === 'failed'
                                ? 'bg-red-500'
                                : 'bg-blue-600'
                            }`}
                            style={{ width: `${job.progress}%` }}
                          />
                        </div>
                        <span className="text-xs font-mono text-gray-500">{job.progress}%</span>
                      </div>
                    </td>
                    <td className="px-4 py-3 text-center text-xs font-mono text-gray-600">
                      {job.retries} / {job.max_retries}
                    </td>
                    <td className="px-4 py-3 text-xs text-gray-500">
                      {new Date(job.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })}
                    </td>
                    <td className="px-4 py-3 text-xs max-w-xs truncate">
                      {job.error_message ? (
                        <span className="text-red-600 font-medium" title={job.error_message}>
                          {job.error_message}
                        </span>
                      ) : job.result ? (
                        <span className="text-gray-600 font-mono" title={JSON.stringify(job.result)}>
                          {JSON.stringify(job.result)}
                        </span>
                      ) : (
                        <span className="text-gray-400">—</span>
                      )}
                    </td>
                    <td className="px-4 py-3 text-center">
                      {(job.status === 'pending' || job.status === 'running') && (
                        <button
                          onClick={() => handleCancel(job.id)}
                          disabled={actionLoading}
                          className="px-2 py-1 text-xs text-red-600 hover:text-red-800 hover:bg-red-50 rounded border border-red-200"
                        >
                          Cancel
                        </button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  </div>
  )
}
export default Jobs
