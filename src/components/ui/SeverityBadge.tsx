import { cn } from '@/lib/utils'
import type { SeverityLevel } from '@/types'

const SEVERITY_STYLES: Record<SeverityLevel | 'None', string> = {
  Low: 'bg-emerald-50 text-emerald-700 border-emerald-200',
  Moderate: 'bg-amber-50 text-amber-700 border-amber-200',
  High: 'bg-orange-50 text-orange-700 border-orange-200',
  Critical: 'bg-red-50 text-red-700 border-red-200',
  None: 'bg-slate-100 text-slate-600 border-slate-200',
}

export function SeverityBadge({ severity, className }: { severity: SeverityLevel | 'None'; className?: string }) {
  return (
    <span
      className={cn(
        'inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded text-xs font-medium border',
        SEVERITY_STYLES[severity],
        className
      )}
    >
      <span
        className={cn(
          'w-1.5 h-1.5 rounded-full',
          severity === 'Critical' && 'bg-red-600',
          severity === 'High' && 'bg-orange-500',
          severity === 'Moderate' && 'bg-amber-500',
          severity === 'Low' && 'bg-emerald-500',
          severity === 'None' && 'bg-slate-400'
        )}
      />
      {severity}
    </span>
  )
}

