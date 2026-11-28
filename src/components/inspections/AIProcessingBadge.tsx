import { cn } from '@/lib/utils'
import type { AiProcessingStatus } from '@/types'

const AI_STATUS_STYLES: Record<AiProcessingStatus, string> = {
  'Not Started': 'bg-slate-100 text-slate-600 border-slate-200',
  Queued: 'bg-blue-50 text-blue-700 border-blue-200',
  Processing: 'bg-cyan-50 text-cyan-700 border-cyan-200',
  Completed: 'bg-emerald-50 text-emerald-700 border-emerald-200',
  Failed: 'bg-red-50 text-red-700 border-red-200',
}

export function AIProcessingBadge({ status = 'Not Started', className }: { status?: AiProcessingStatus; className?: string }) {
  return (
    <span
      className={cn(
        'inline-flex items-center px-2.5 py-0.5 rounded text-xs font-medium border whitespace-nowrap',
        AI_STATUS_STYLES[status],
        className
      )}
    >
      {status}
    </span>
  )
}

