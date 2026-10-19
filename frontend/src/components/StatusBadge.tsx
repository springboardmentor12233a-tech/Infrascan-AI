import React from 'react'

interface StatusBadgeProps {
  status: 'loading' | 'connected' | 'unreachable'
}

// Badge displaying current backend connection state
export const StatusBadge: React.FC<StatusBadgeProps> = ({ status }) => {
  if (status === 'loading') {
    return (
      <span className="inline-flex items-center px-3 py-1 rounded-full text-sm font-medium bg-amber-100 text-amber-800">
        <span className="w-2 h-2 mr-2 bg-amber-500 rounded-full animate-pulse"></span>
        Checking backend connection...
      </span>
    )
  }

  if (status === 'connected') {
    return (
      <span className="inline-flex items-center px-3 py-1 rounded-full text-sm font-medium bg-emerald-100 text-emerald-800">
        <span className="w-2 h-2 mr-2 bg-emerald-500 rounded-full"></span>
        Backend connected
      </span>
    )
  }

  return (
    <span className="inline-flex items-center px-3 py-1 rounded-full text-sm font-medium bg-rose-100 text-rose-800">
      <span className="w-2 h-2 mr-2 bg-rose-500 rounded-full"></span>
      Backend not reachable
    </span>
  )
}
