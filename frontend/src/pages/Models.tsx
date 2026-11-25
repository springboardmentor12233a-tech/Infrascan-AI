import React, { useState, useEffect } from 'react'
import { Navbar } from '../components/Navbar'
import {
  modelsApi,
  type ModelVersionItem,
  type DatasetVersionItem,
  type ModelEventItem,
  type ClassifyCropResponse,
} from '../api/client'

export const Models: React.FC = () => {
  const [models, setModels] = useState<ModelVersionItem[]>([])
  const [datasets, setDatasets] = useState<DatasetVersionItem[]>([])
  const [selectedModel, setSelectedModel] = useState<ModelVersionItem | null>(null)
  const [events, setEvents] = useState<ModelEventItem[]>([])
  const [loading, setLoading] = useState(true)
  const [actionLoading, setActionLoading] = useState(false)
  const [feedback, setFeedback] = useState<{ type: 'success' | 'error'; msg: string } | null>(null)

  // Crop tester state
  const [cropFile, setCropFile] = useState<File | null>(null)
  const [cropPreview, setCropPreview] = useState<string | null>(null)
  const [cropResult, setCropResult] = useState<ClassifyCropResponse | null>(null)
  const [cropLoading, setCropLoading] = useState(false)
  const [cropError, setCropError] = useState<string | null>(null)

  const loadData = async () => {
    try {
      setLoading(true)
      const [mList, dList] = await Promise.all([modelsApi.list(), modelsApi.datasets()])
      setModels(mList)
      setDatasets(dList)
    } catch (err: any) {
      setFeedback({ type: 'error', msg: err.response?.data?.detail || 'Failed to load model registry data.' })
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadData()
  }, [])

  const handleActivate = async (modelId: string) => {
    try {
      setActionLoading(true)
      setFeedback(null)
      await modelsApi.activate(modelId)
      setFeedback({ type: 'success', msg: `Model ${modelId} smoke tested and activated successfully.` })
      await loadData()
      if (selectedModel?.model_id === modelId) {
        viewEvents(modelId)
      }
    } catch (err: any) {
      setFeedback({ type: 'error', msg: err.response?.data?.detail || `Failed to activate model ${modelId}.` })
    } finally {
      setActionLoading(false)
    }
  }

  const handleRollback = async (modelId: string) => {
    try {
      setActionLoading(true)
      setFeedback(null)
      await modelsApi.rollback(modelId)
      setFeedback({ type: 'success', msg: `Model ${modelId} rolled back successfully.` })
      await loadData()
      if (selectedModel?.model_id === modelId) {
        viewEvents(modelId)
      }
    } catch (err: any) {
      setFeedback({ type: 'error', msg: err.response?.data?.detail || `Failed to rollback model ${modelId}.` })
    } finally {
      setActionLoading(false)
    }
  }

  const viewEvents = async (modelId: string) => {
    try {
      const evs = await modelsApi.events(modelId)
      setEvents(evs)
    } catch (err) {
      setEvents([])
    }
  }

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      const file = e.target.files[0]
      setCropFile(file)
      setCropPreview(URL.createObjectURL(file))
      setCropResult(null)
      setCropError(null)
    }
  }

  const handleClassifyCrop = async () => {
    if (!cropFile) return
    try {
      setCropLoading(true)
      setCropError(null)
      setCropResult(null)
      const fd = new FormData()
      fd.append('file', cropFile)
      fd.append('threshold', '0.5')
      const res = await modelsApi.classifyCrop(fd)
      setCropResult(res)
    } catch (err: any) {
      setCropError(err.response?.data?.detail || 'Crop classification failed.')
    } finally {
      setCropLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <Navbar />
      <div className="container mx-auto px-4 py-8 max-w-7xl">
      {/* Header */}
      <div className="mb-6 flex flex-col md:flex-row md:items-center md:justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">AI Model Registry & Diagnostics</h1>
          <p className="text-sm text-gray-500 mt-1">
            Dynamic model management, operational metrics, validation benchmarks, and live crop screening.
          </p>
        </div>
        <button
          onClick={loadData}
          className="px-4 py-2 bg-gray-100 hover:bg-gray-200 text-gray-700 text-sm font-medium rounded shadow-sm self-start"
        >
          Refresh Registry
        </button>
      </div>

      {/* Mandatory AI Safety Disclaimer Banner */}
      <div className="bg-amber-50 border-l-4 border-amber-400 p-4 mb-6 rounded-r">
        <p className="text-sm text-amber-800 font-medium">
          <strong>Mandatory Notice:</strong> AI result for engineer review, not a final structural safety verdict.
        </p>
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

      {/* Grid: Models Table & Datasets */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-8">
        {/* Models list (2 cols) */}
        <div className="lg:col-span-2 bg-white rounded-lg shadow border border-gray-200 overflow-hidden">
          <div className="px-6 py-4 border-b border-gray-200 bg-gray-50">
            <h2 className="text-lg font-semibold text-gray-800">Registered AI Models</h2>
          </div>
          {loading ? (
            <div className="p-8 text-center text-gray-500">Loading model registry...</div>
          ) : models.length === 0 ? (
            <div className="p-8 text-center text-gray-500">No models registered.</div>
          ) : (
            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-gray-200">
                <thead className="bg-gray-50 text-xs font-semibold text-gray-600 uppercase">
                  <tr>
                    <th className="px-4 py-3 text-left">Model / Task</th>
                    <th className="px-4 py-3 text-left">Version</th>
                    <th className="px-4 py-3 text-left">Status</th>
                    <th className="px-4 py-3 text-right">Inferences</th>
                    <th className="px-4 py-3 text-right">Avg Latency</th>
                    <th className="px-4 py-3 text-right">Errors</th>
                    <th className="px-4 py-3 text-center">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-200 text-sm">
                  {models.map((m) => (
                    <tr
                      key={m.model_id}
                      className={`hover:bg-gray-50 cursor-pointer ${
                        selectedModel?.model_id === m.model_id ? 'bg-blue-50' : ''
                      }`}
                      onClick={() => {
                        setSelectedModel(m)
                        viewEvents(m.model_id)
                      }}
                    >
                      <td className="px-4 py-3">
                        <div className="font-semibold text-gray-900">{m.model_name}</div>
                        <div className="text-xs text-gray-500 font-mono">{m.model_id} &bull; {m.task}</div>
                      </td>
                      <td className="px-4 py-3 text-gray-600 font-mono text-xs">{m.version}</td>
                      <td className="px-4 py-3">
                        {m.is_active ? (
                          <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-green-100 text-green-800">
                            Active
                          </span>
                        ) : (
                          <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-gray-100 text-gray-600">
                            Inactive
                          </span>
                        )}
                      </td>
                      <td className="px-4 py-3 text-right font-medium text-gray-900">{m.inferences_count}</td>
                      <td className="px-4 py-3 text-right font-mono text-xs text-gray-600">
                        {m.mean_inference_time_ms > 0 ? `${m.mean_inference_time_ms} ms` : '—'}
                      </td>
                      <td className="px-4 py-3 text-right font-medium text-red-600">{m.error_count}</td>
                      <td className="px-4 py-3 text-center">
                        <div className="inline-flex items-center gap-1" onClick={(e) => e.stopPropagation()}>
                          {!m.is_active ? (
                            <button
                              onClick={() => handleActivate(m.model_id)}
                              disabled={actionLoading}
                              className="px-2 py-1 bg-blue-600 hover:bg-blue-700 text-white text-xs font-medium rounded shadow-sm disabled:opacity-50"
                            >
                              Activate
                            </button>
                          ) : (
                            <button
                              onClick={() => handleRollback(m.model_id)}
                              disabled={actionLoading}
                              className="px-2 py-1 bg-amber-600 hover:bg-amber-700 text-white text-xs font-medium rounded shadow-sm disabled:opacity-50"
                            >
                              Rollback
                            </button>
                          )}
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>

        {/* Datasets & Model Details (1 col) */}
        <div className="space-y-6">
          {/* Datasets list */}
          <div className="bg-white rounded-lg shadow border border-gray-200 p-5">
            <h3 className="text-base font-semibold text-gray-800 mb-3">Dataset Versions</h3>
            <div className="space-y-3">
              {datasets.map((d) => (
                <div key={d.id} className="p-3 bg-gray-50 rounded border border-gray-100 text-xs">
                  <div className="font-semibold text-gray-900 flex justify-between">
                    <span>{d.name} v{d.version}</span>
                    <span className="capitalize text-gray-500">{d.task}</span>
                  </div>
                  {d.split_stats && (
                    <div className="mt-1 text-gray-600 flex gap-2 font-mono">
                      <span>Train: {d.split_stats.train?.toLocaleString()}</span>
                      <span>Val: {d.split_stats.val?.toLocaleString()}</span>
                      <span>Test: {d.split_stats.test?.toLocaleString()}</span>
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>

          {/* Model Event Audit */}
          {selectedModel && (
            <div className="bg-white rounded-lg shadow border border-gray-200 p-5">
              <h3 className="text-base font-semibold text-gray-800 mb-1">
                Audit Trail: {selectedModel.model_id}
              </h3>
              <p className="text-xs text-gray-500 mb-3">Lifecycle changes and smoke test records.</p>
              {events.length === 0 ? (
                <div className="text-xs text-gray-400">No events logged for this model yet.</div>
              ) : (
                <div className="space-y-2 max-h-48 overflow-y-auto pr-1">
                  {events.map((ev) => (
                    <div key={ev.id} className="p-2 bg-gray-50 rounded border border-gray-100 text-xs">
                      <div className="font-semibold text-gray-800 capitalize flex justify-between">
                        <span>{ev.event_type.replace('_', ' ')}</span>
                        <span className="text-gray-400 text-[10px]">
                          {new Date(ev.created_at).toLocaleDateString()}
                        </span>
                      </div>
                      {ev.details && (
                        <div className="text-gray-600 text-[11px] font-mono mt-0.5">
                          {JSON.stringify(ev.details)}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>
      </div>

      {/* Interactive Crop Classification Section */}
      <div className="bg-white rounded-lg shadow border border-gray-200 p-6">
        <div className="mb-4">
          <h2 className="text-xl font-bold text-gray-900">Crack Crop Screening Tester (SDNET2018 ResNet-50)</h2>
          <p className="text-sm text-gray-600 mt-1">
            Test localized candidate crops directly. Dimensions must be &le; 600&times;600 px. Preprocessed with CLAHE &amp; ImageNet normalization.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div>
            <div className="mb-4">
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Select Crop Image (PNG/JPEG &le; 600px):
              </label>
              <input
                type="file"
                accept="image/*"
                onChange={handleFileChange}
                className="block w-full text-sm text-gray-500 file:mr-4 file:py-2 file:px-4 file:rounded file:border-0 file:text-sm file:font-semibold file:bg-blue-50 file:text-blue-700 hover:file:bg-blue-100"
              />
            </div>

            {cropPreview && (
              <div className="mt-4 p-2 border rounded bg-gray-50 inline-block">
                <img
                  src={cropPreview}
                  alt="Crop preview"
                  className="max-h-56 max-w-full object-contain rounded"
                />
              </div>
            )}

            <div className="mt-4">
              <button
                onClick={handleClassifyCrop}
                disabled={!cropFile || cropLoading}
                className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white text-sm font-medium rounded shadow disabled:opacity-50"
              >
                {cropLoading ? 'Evaluating Model...' : 'Classify Crop'}
              </button>
            </div>

            {cropError && (
              <div className="mt-4 p-3 bg-red-50 text-red-800 text-sm border border-red-200 rounded">
                {cropError}
              </div>
            )}
          </div>

          <div>
            {cropResult && (
              <div className="p-5 bg-gray-50 border border-gray-200 rounded-lg space-y-4">
                <h3 className="text-base font-semibold text-gray-800">Inference Screening Results</h3>

                <div className="grid grid-cols-2 gap-3 text-sm">
                  <div className="p-3 bg-white rounded border">
                    <div className="text-xs text-gray-500">Classification Label</div>
                    <div className={`text-lg font-bold ${cropResult.is_cracked ? 'text-red-600' : 'text-green-600'}`}>
                      {cropResult.label.toUpperCase()}
                    </div>
                  </div>
                  <div className="p-3 bg-white rounded border">
                    <div className="text-xs text-gray-500">Crack Probability</div>
                    <div className="text-lg font-bold text-gray-900">
                      {(cropResult.crack_probability * 100).toFixed(1)}%
                    </div>
                  </div>
                  <div className="p-3 bg-white rounded border">
                    <div className="text-xs text-gray-500">Crop Resolution</div>
                    <div className="text-sm font-semibold font-mono text-gray-800">
                      {cropResult.crop_dimensions.width} &times; {cropResult.crop_dimensions.height} px
                    </div>
                  </div>
                  <div className="p-3 bg-white rounded border">
                    <div className="text-xs text-gray-500">Inference Latency</div>
                    <div className="text-sm font-semibold font-mono text-gray-800">
                      {cropResult.latency_ms} ms
                    </div>
                  </div>
                </div>

                <div className="p-3 bg-amber-50 border-l-4 border-amber-400 rounded-r text-xs text-amber-900">
                  {cropResult.screening_disclaimer}
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  </div>
  )
}
export default Models
