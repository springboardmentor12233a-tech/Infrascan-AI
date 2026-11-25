import React from 'react'
import type { LiveStatus } from '../hooks/useLiveEvents'

interface LiveStatusChipProps {
  status: LiveStatus
}

export const LiveStatusChip: React.FC<LiveStatusChipProps> = ({ status }) => {
  const getBadgeStyle = () => {
    switch (status) {
      case 'Live':
        return {
          dotColor: 'bg-emerald-400',
          textColor: 'text-emerald-400',
          bgColor: 'bg-emerald-950/60 border-emerald-800',
          label: 'Live',
        }
      case 'Reconnecting':
        return {
          dotColor: 'bg-amber-400 animate-pulse',
          textColor: 'text-amber-400',
          bgColor: 'bg-amber-950/60 border-amber-800',
          label: 'Reconnecting',
        }
      case 'Polling':
        return {
          dotColor: 'bg-slate-400',
          textColor: 'text-slate-400',
          bgColor: 'bg-slate-800 border-slate-700',
          label: 'Polling',
        }
    }
  }

  const badge = getBadgeStyle()

  return (
    <div
      className={`inline-flex items-center space-x-1.5 px-2 py-0.5 rounded-full text-[11px] font-medium border ${badge.bgColor}`}
      title={`Real-Time Engine: ${badge.label}`}
    >
      <span className={`w-1.5 h-1.5 rounded-full ${badge.dotColor}`} />
      <span className={badge.textColor}>{badge.label}</span>
    </div>
  )
}
