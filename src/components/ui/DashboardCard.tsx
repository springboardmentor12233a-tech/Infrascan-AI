import type { LucideIcon } from 'lucide-react'
import { cn } from '@/lib/utils'

interface DashboardCardProps {
  title: string
  value: string | number
  subtitle?: string
  icon: LucideIcon
  trend?: { value: string; positive?: boolean }
  accent?: 'navy' | 'cyan' | 'amber' | 'red' | 'emerald'
}

const ACCENT_MAP = {
  navy: 'bg-[#0F2942]/10 text-[#0F2942]',
  cyan: 'bg-cyan-50 text-cyan-700',
  amber: 'bg-amber-50 text-amber-700',
  red: 'bg-red-50 text-red-700',
  emerald: 'bg-emerald-50 text-emerald-700',
}

export function DashboardCard({ title, value, subtitle, icon: Icon, trend, accent = 'navy' }: DashboardCardProps) {
  return (
    <div className="bg-white rounded-lg border border-slate-200 p-5 shadow-xs hover:border-slate-300 transition-colors">
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="text-xs font-medium uppercase tracking-wider text-slate-500">{title}</p>
          <p className="mt-2 text-2xl font-semibold text-slate-900 tabular-nums">{value}</p>
        </div>
        <div className={cn('p-2.5 rounded-lg shrink-0', ACCENT_MAP[accent])}>
          <Icon className="w-5 h-5" />
        </div>
      </div>
      {(subtitle || trend) && (
        <div className="mt-3 flex items-center gap-2 text-xs">
          {trend && (
            <span className={cn('font-medium', trend.positive ? 'text-emerald-600' : 'text-red-600')}>
              {trend.value}
            </span>
          )}
          {subtitle && <span className="text-slate-500">{subtitle}</span>}
        </div>
      )}
    </div>
  )
}

