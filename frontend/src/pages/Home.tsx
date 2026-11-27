import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
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
      const response = await axios.get('/health', {
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

  useEffect(() => {
    checkStatus()
  }, [])

  return (
    <div className="min-h-screen bg-[#141619] text-white flex items-center justify-center p-6 relative overflow-hidden font-sans selection:bg-[#0A21C0] selection:text-white">
      {/* Background glow effects matching Lusion image */}
      <div className="absolute top-1/4 left-1/4 w-96 h-96 bg-[#0A21C0]/15 rounded-full blur-3xl pointer-events-none"></div>
      <div className="absolute bottom-1/4 right-1/4 w-96 h-96 bg-[#050A44]/40 rounded-full blur-3xl pointer-events-none"></div>

      <div className="max-w-md w-full bg-[#2C2E3A] rounded-2xl shadow-2xl border border-[#2C2E3A] p-8 text-center relative z-10">
        <div className="w-12 h-12 bg-[#0A21C0] rounded-xl flex items-center justify-center mx-auto mb-4 shadow-lg shadow-[#0A21C0]/40">
          <span className="text-white font-black text-xl">IS</span>
        </div>

        <h1 className="text-3xl font-extrabold text-white tracking-tight">
          InfraScan
        </h1>
        <p className="text-xs text-[#B3B4BD] mt-1.5">
          AI-Powered Crack & Damage Assessment for Civil Infrastructure
        </p>

        {/* Backend Connection Status Section */}
        <div className="mt-8 p-5 bg-[#141619] rounded-xl border border-[#2C2E3A] flex flex-col items-center">
          <p className="text-[10px] uppercase tracking-wider text-[#B3B4BD] font-mono font-bold mb-3">
            FastAPI Intelligence Engine Status
          </p>
          <StatusBadge status={status} />

          {lastChecked && (
            <p className="text-[10px] text-[#B3B4BD] mt-3 font-mono">
              Last probe: {lastChecked}
            </p>
          )}
        </div>

        {/* Action Buttons */}
        <div className="mt-6 space-y-3">
          <Link
            to="/dashboard"
            className="w-full py-3 px-4 bg-[#0A21C0] hover:bg-[#081ba0] text-white font-semibold rounded-full shadow-lg shadow-[#0A21C0]/30 transition-all text-xs block cursor-pointer"
          >
            Enter Operational Dashboard &rarr;
          </Link>

          <button
            onClick={checkStatus}
            className="w-full py-2.5 px-4 bg-[#141619] hover:bg-[#050A44] border border-[#2C2E3A] hover:border-[#0A21C0]/50 text-[#B3B4BD] hover:text-white font-medium rounded-full transition-all text-xs cursor-pointer"
          >
            Recheck Engine Connection
          </button>
        </div>
      </div>
    </div>
  )
}

export default Home
