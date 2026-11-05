import { useEffect, useState } from 'react'
import axios from 'axios'
import { StatusBadge } from '../components/StatusBadge'

type ConnectionStatus = 'loading' | 'connected' | 'unreachable'

export const Home = () => {
  const [status, setStatus] = useState<ConnectionStatus>('loading')
  const [lastChecked, setLastChecked] = useState<string>('')

  // Function to call FastAPI health endpoint
  const checkStatus = async () => {
    setStatus('loading')
    try {
      // Direct call to FastAPI health check endpoint
      const response = await axios.get('http://localhost:8000/health', {
        timeout: 4000,
      })

      if (response.data && response.data.status === 'ok') {
        setStatus('connected')
      } else {
        setStatus('unreachable')
      }
    } catch {
      setStatus('unreachable')
    } finally {
      setLastChecked(new Date().toLocaleTimeString())
    }
  }

  // Check backend health on initial component load
  useEffect(() => {
    checkStatus()
  }, [])

  return (
    <div className="min-h-screen bg-slate-50 flex items-center justify-center p-6">
      <div className="max-w-md w-full bg-white rounded-xl shadow-md border border-slate-200 p-8 text-center">
        {/* App Title and Subtitle */}
        <h1 className="text-3xl font-bold text-slate-800 tracking-tight">
          InfraScan
        </h1>
        <p className="text-sm text-slate-500 mt-2">
          AI-Powered Infrastructure Crack Detection
        </p>

        {/* Backend Connection Status Section */}
        <div className="mt-8 p-4 bg-slate-50 rounded-lg border border-slate-100 flex flex-col items-center">
          <p className="text-xs uppercase tracking-wider text-slate-400 font-semibold mb-3">
            System Status
          </p>
          <StatusBadge status={status} />

          {lastChecked && (
            <p className="text-xs text-slate-400 mt-3">
              Last checked: {lastChecked}
            </p>
          )}
        </div>

        {/* Action Button */}
        <div className="mt-6">
          <button
            onClick={checkStatus}
            className="w-full py-2.5 px-4 bg-indigo-600 hover:bg-indigo-700 text-white font-medium rounded-lg shadow transition-colors text-sm"
          >
            Recheck Connection
          </button>
        </div>

        {/* Quick Instructions */}
        <div className="mt-6 text-left text-xs text-slate-500 bg-slate-50 p-3 rounded border border-slate-100">
          <p className="font-semibold text-slate-600 mb-1">Quick Note:</p>
          <p>
            Make sure the FastAPI backend is running on{' '}
            <code className="bg-slate-200 px-1 py-0.5 rounded text-slate-700">
              http://localhost:8000
            </code>
            .
          </p>
        </div>
      </div>
    </div>
  )
}
