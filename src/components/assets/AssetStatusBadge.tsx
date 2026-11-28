import { cn } from '@/lib/utils'
import type { AssetOperationalStatus } from '@/types'

const OP_STATUS_STYLES: Record<AssetOperationalStatus, string> = {
  Active: 'bg-emerald-50 text-emerald-700 border-emerald-200',
  Inactive: 'bg-slate-100 text-slate-600 border-slate-200',
  'Under Maintenance': 'bg-amber-50 text-amber-700 border-amber-200',
  Archived: 'bg-slate-100 text-slate-500 border-slate-200',
}

export function AssetStatusBadge({ status = 'Active', className }: { status?: AssetOperationalStatus; className?: string }) {
  return (
    <span
      className={cn(
        'inline-flex items-center px-2.5 py-0.5 rounded text-xs font-medium border whitespace-nowrap',
        OP_STATUS_STYLES[status],
        className
      )}
    >
      {status}
    </span>
  )
}

