import { cn } from '@/lib/utils'

const STATUS_MAP: Record<string, string> = {
  Operational: 'bg-emerald-50 text-emerald-700 border-emerald-200',
  Completed: 'bg-emerald-50 text-emerald-700 border-emerald-200',
  Approved: 'bg-emerald-50 text-emerald-700 border-emerald-200',
  Active: 'bg-emerald-50 text-emerald-700 border-emerald-200',

  'Under Inspection': 'bg-cyan-50 text-cyan-700 border-cyan-200',
  Processing: 'bg-cyan-50 text-cyan-700 border-cyan-200',
  'In Progress': 'bg-cyan-50 text-cyan-700 border-cyan-200',
  Scheduled: 'bg-blue-50 text-blue-700 border-blue-200',

  'Maintenance Required': 'bg-amber-50 text-amber-700 border-amber-200',
  'Requires Review': 'bg-amber-50 text-amber-700 border-amber-200',
  'Pending Review': 'bg-amber-50 text-amber-700 border-amber-200',
  Pending: 'bg-amber-50 text-amber-700 border-amber-200',
  Open: 'bg-amber-50 text-amber-700 border-amber-200',

  Critical: 'bg-red-50 text-red-700 border-red-200',
  'Revision Requested': 'bg-red-50 text-red-700 border-red-200',

  Draft: 'bg-slate-100 text-slate-600 border-slate-200',
  Archived: 'bg-slate-100 text-slate-500 border-slate-200',
  Deferred: 'bg-slate-100 text-slate-500 border-slate-200',
  Inactive: 'bg-slate-100 text-slate-500 border-slate-200',
}

export function StatusBadge({ status, className }: { status: string; className?: string }) {
  return (
    <span
      className={cn(
        'inline-flex items-center px-2.5 py-0.5 rounded text-xs font-medium border whitespace-nowrap',
        STATUS_MAP[status] || 'bg-slate-100 text-slate-700 border-slate-200',
        className
      )}
    >
      {status}
    </span>
  )
}

