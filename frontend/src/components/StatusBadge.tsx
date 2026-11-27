import React from 'react'

interface StatusBadgeProps {
  status: 'loading' | 'connected' | 'unreachable'
}

// Badge displaying current backend connection state with Lusion dark theme styling
export const StatusBadge: React.FC<StatusBadgeProps> = ({ status }) => {
  if (status === 'loading') {
    return (
      <span className="inline-flex items-center px-3 py-1 rounded-full text-xs font-semibold bg-amber-500/20 text-amber-300 border border-amber-500/30">
        <span className="w-2 h-2 mr-2 bg-amber-400 rounded-full animate-ping"></span>
        Connecting to Engine...
      </span>
    )
  }

  if (status === 'connected') {
    return (
      <span className="inline-flex items-center px-3 py-1 rounded-full text-xs font-semibold bg-emerald-500/20 text-emerald-300 border border-emerald-500/30">
        <span className="w-2 h-2 mr-2 bg-emerald-400 rounded-full"></span>
        FastAPI Backend Live (HTTP 200)
      </span>
    )
  }

  return (
    <span className="inline-flex items-center px-3 py-1 rounded-full text-xs font-semibold bg-rose-500/20 text-rose-300 border border-rose-500/30">
      <span className="w-2 h-2 mr-2 bg-rose-400 rounded-full"></span>
      Backend Offline (Port 8000)
    </span>
  )
}
