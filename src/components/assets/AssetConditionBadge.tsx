import { cn } from '@/lib/utils'
import type { AssetCondition } from '@/types'

const CONDITION_STYLES: Record<AssetCondition, string> = {
  Good: 'bg-emerald-50 text-emerald-700 border-emerald-200',
  'Minor Damage': 'bg-cyan-50 text-cyan-700 border-cyan-200',
  'Moderate Damage': 'bg-amber-50 text-amber-700 border-amber-200',
  'Severe Visible Damage': 'bg-orange-50 text-orange-700 border-orange-200',
  'Requires Engineering Review': 'bg-red-50 text-red-700 border-red-200',
  'Not Assessed': 'bg-slate-100 text-slate-600 border-slate-200',
}

export function AssetConditionBadge({ condition = 'Not Assessed', className }: { condition?: AssetCondition; className?: string }) {
  return (
    <span
      className={cn(
        'inline-flex items-center px-2.5 py-0.5 rounded text-xs font-medium border whitespace-nowrap',
        CONDITION_STYLES[condition],
        className
      )}
    >
      {condition}
    </span>
  )
}

