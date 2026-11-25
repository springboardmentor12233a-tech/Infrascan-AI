import React, { useEffect, useState } from 'react'
import { Navbar } from '../components/Navbar'
import {
  assetsApi,
  inspectionsApi,
  comparisonsApi,
  type InfrastructureAsset,
  type Inspection,
} from '../api/client'

export const Comparisons: React.FC = () => {
  const [assets, setAssets] = useState<InfrastructureAsset[]>([])
  const [selectedAssetId, setSelectedAssetId] = useState<number>(0)
  const [inspections, setInspections] = useState<Inspection[]>([])
  const [prevInspId, setPrevInspId] = useState<number>(0)
  const [currInspId, setCurrInspId] = useState<number>(0)
  const [comparing, setComparing] = useState(false)
  const [comparisonResult, setComparisonResult] = useState<any | null>(null)
  const [historicalList, setHistoricalList] = useState<any[]>([])
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    assetsApi.list({ page_size: 100 }).then((res) => {
      setAssets(res.items)
      if (res.items.length > 0) {
        setSelectedAssetId(res.items[0].asset_id)
      }
    }).catch(() => {})
  }, [])

  useEffect(() => {
    if (selectedAssetId) {
      inspectionsApi.list({ asset_id: selectedAssetId }).then((res) => {
        setInspections(res)
        if (res.length >= 2) {
          setPrevInspId(res[res.length - 1].inspection_id)
          setCurrInspId(res[0].inspection_id)
        } else if (res.length === 1) {
          setPrevInspId(res[0].inspection_id)
          setCurrInspId(res[0].inspection_id)
        } else {
          setPrevInspId(0)
          setCurrInspId(0)
        }
      }).catch(() => {})
    }
  }, [selectedAssetId])

  useEffect(() => {
    if (currInspId) {
      comparisonsApi.listByInspection(currInspId).then((res) => {
        setHistoricalList(res)
      }).catch(() => {})
    }
  }, [currInspId])

  const handleRunComparison = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!prevInspId || !currInspId) return
    try {
      setComparing(true)
      setError(null)
      const res = await comparisonsApi.compare(prevInspId, currInspId)
      setComparisonResult(res)
      const list = await comparisonsApi.listByInspection(currInspId)
      setHistoricalList(list)
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Failed to compute inspection comparison.')
    } finally {
      setComparing(false)
    }
  }

  return (
    <div className="min-h-screen bg-slate-50 flex flex-col">
      <Navbar />

      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-6 mb-6">
          <h1 className="text-2xl font-bold text-slate-800 tracking-tight">
            Historical Inspection Comparison
          </h1>
          <p className="text-sm text-slate-500 mt-1">
            Compare crack growth, defect evolution, and structural changes across sequential inspection intervals.
          </p>
          <p className="text-xs text-amber-700 mt-2 font-medium bg-amber-50 px-2 py-0.5 rounded inline-block">
            AI result for engineer review, not a final structural safety verdict.
          </p>
        </div>

        {/* Configuration Panel */}
        <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-6 mb-6">
          <form onSubmit={handleRunComparison} className="grid grid-cols-1 md:grid-cols-4 gap-4 items-end">
            <div>
              <label className="block text-xs font-semibold text-slate-600 mb-1">Asset</label>
              <select
                value={selectedAssetId}
                onChange={(e) => setSelectedAssetId(Number(e.target.value))}
                className="w-full text-sm border border-slate-300 rounded-lg p-2 bg-white"
              >
                {assets.map((a) => (
                  <option key={a.asset_id} value={a.asset_id}>
                    {a.name} ({a.asset_type})
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-600 mb-1">Baseline (Previous) Inspection</label>
              <select
                value={prevInspId}
                onChange={(e) => setPrevInspId(Number(e.target.value))}
                className="w-full text-sm border border-slate-300 rounded-lg p-2 bg-white"
                disabled={inspections.length < 2}
              >
                {inspections.map((i) => (
                  <option key={i.inspection_id} value={i.inspection_id}>
                    #{i.inspection_id} ({new Date(i.inspection_date).toLocaleDateString()}) - {i.status}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-600 mb-1">Target (Current) Inspection</label>
              <select
                value={currInspId}
                onChange={(e) => setCurrInspId(Number(e.target.value))}
                className="w-full text-sm border border-slate-300 rounded-lg p-2 bg-white"
                disabled={inspections.length < 2}
              >
                {inspections.map((i) => (
                  <option key={i.inspection_id} value={i.inspection_id}>
                    #{i.inspection_id} ({new Date(i.inspection_date).toLocaleDateString()}) - {i.status}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <button
                type="submit"
                disabled={comparing || inspections.length < 2 || prevInspId === currInspId}
                className="w-full px-4 py-2 text-sm font-semibold rounded-lg bg-indigo-600 text-white hover:bg-indigo-700 disabled:opacity-40 transition"
              >
                {comparing ? 'Analyzing Changes...' : 'Compare Inspections'}
              </button>
            </div>
          </form>

          {inspections.length < 2 && (
            <p className="text-xs text-amber-600 mt-3">
              This asset currently has fewer than two inspections. At least two inspections are required for pairwise comparison.
            </p>
          )}

          {error && (
            <div className="mt-4 p-3 bg-rose-50 border border-rose-200 rounded-lg text-rose-700 text-xs">
              {error}
            </div>
          )}
        </div>

        {/* Comparison Details */}
        {comparisonResult && (
          <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-6 mb-6">
            <h2 className="text-base font-bold text-slate-800 mb-3 flex items-center space-x-2">
              <span>Pairwise Comparison #{comparisonResult.comparison_id}</span>
              <span className="text-xs font-normal text-emerald-600 bg-emerald-50 px-2 py-0.5 rounded">
                Computed Successfully
              </span>
            </h2>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-4">
              <div className="p-4 bg-slate-50 rounded-xl border border-slate-100">
                <span className="text-xs text-slate-400 block">Baseline Interval</span>
                <span className="text-sm font-bold text-slate-700">Inspection #{comparisonResult.prev_inspection_id}</span>
              </div>
              <div className="p-4 bg-slate-50 rounded-xl border border-slate-100">
                <span className="text-xs text-slate-400 block">Comparison Interval</span>
                <span className="text-sm font-bold text-slate-700">Inspection #{comparisonResult.curr_inspection_id}</span>
              </div>
              <div className="p-4 bg-slate-50 rounded-xl border border-slate-100">
                <span className="text-xs text-slate-400 block">Status</span>
                <span className="text-sm font-bold text-indigo-700">Registered</span>
              </div>
            </div>

            <div className="p-4 bg-amber-50/50 rounded-xl border border-amber-200 text-xs text-amber-900 leading-relaxed">
              <strong>Engineering Advisory:</strong> Pairwise crack alignment provides advisory geometric tracking of crack progression across inspection dates. Qualified civil engineer review is mandatory before drawing structural conclusions.
            </div>
          </div>
        )}

        {/* Prior Comparisons Log */}
        <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-6">
          <h3 className="text-sm font-bold text-slate-800 mb-3">Saved Comparisons for this Asset</h3>
          {historicalList.length === 0 ? (
            <p className="text-xs text-slate-400">No prior comparisons registered for this inspection interval.</p>
          ) : (
            <div className="space-y-2">
              {historicalList.map((item) => (
                <div
                  key={item.comparison_id}
                  className="flex items-center justify-between p-3 rounded-lg border border-slate-100 bg-slate-50 text-xs text-slate-700"
                >
                  <div>
                    <span className="font-semibold text-slate-800">Comparison #{item.comparison_id}</span>: Inspection #{item.prev_inspection_id} &rarr; #{item.curr_inspection_id}
                  </div>
                  <span className="text-slate-400">
                    {item.created_at ? new Date(item.created_at).toLocaleDateString() : ''}
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>
      </main>
    </div>
  )
}
export default Comparisons
