import { Info } from 'lucide-react'
import { DEMO_DISCLAIMER } from '@/lib/constants'

export function DemoBanner({ message = DEMO_DISCLAIMER }: { message?: string }) {
  return (
    <div className="flex items-center gap-2.5 px-3.5 py-2 rounded-md bg-cyan-50/80 border border-cyan-200 text-xs text-cyan-900">
      <Info className="w-4 h-4 text-cyan-700 shrink-0" />
      <span>{message}</span>
    </div>
  )
}

