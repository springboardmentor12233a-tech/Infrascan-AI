import { Link } from 'react-router-dom'
import { Calendar as CalendarIcon } from 'lucide-react'
import { StatusBadge } from '@/components/ui/StatusBadge'
import type { Inspection } from '@/types'

export function InspectionCalendar({ inspections }: { inspections: Inspection[] }) {
  const days = Array.from({ length: 30 }, (_, idx) => {
    const day = String(idx + 1).padStart(2, '0')
    const dateStr = `2026-11-${day}`
    const dayInspections = inspections.filter((i) => i.date === dateStr)
    return { day: idx + 1, dateStr, items: dayInspections }
  })

  return (
    <div className="bg-white rounded-lg border border-slate-200 p-5 shadow-xs">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <CalendarIcon className="w-4 h-4 text-cyan-700" />
          <h3 className="text-sm font-semibold text-slate-900">November 2026 — Inspection Schedule</h3>
        </div>
        <span className="text-xs text-slate-500">Click an entry to open inspection workspace</span>
      </div>
      <div className="grid grid-cols-2 sm:grid-cols-5 lg:grid-cols-7 gap-2">
        {days.map((d) => (
          <div key={d.day} className="min-h-[96px] p-2 rounded border border-slate-200 bg-slate-50/50 flex flex-col">
            <span className="text-[11px] font-mono font-semibold text-slate-500 mb-1">Nov {d.day}</span>
            <div className="space-y-1 flex-1">
              {d.items.map((item) => (
                <Link
                  key={item.id}
                  to={`/app/inspections/${item.id}`}
                  className="block p-1.5 rounded bg-white border border-slate-200 hover:border-cyan-500 transition-colors"
                >
                  <p className="text-[10px] font-mono font-semibold text-slate-800 truncate">{item.id}</p>
                  <p className="text-[10px] text-slate-600 truncate">{item.assetName}</p>
                  <div className="mt-1">
                    <StatusBadge status={item.status} className="text-[9px] px-1.5 py-0" />
                  </div>
                </Link>
              ))}
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

