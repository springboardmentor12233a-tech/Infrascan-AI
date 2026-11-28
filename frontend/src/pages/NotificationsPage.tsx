import { Bell, CheckCheck } from 'lucide-react'
import { Link } from 'react-router-dom'
import { useAppStore } from '@/store/useAppStore'
import { SeverityBadge } from '@/components/ui/SeverityBadge'
import { formatDateTime } from '@/lib/utils'

export function NotificationsPage() {
  const { notifications, markNotificationRead, markAllNotificationsRead } = useAppStore()

  return (
    <div className="space-y-5 max-w-4xl">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold text-slate-900">Notifications</h1>
          <p className="text-xs text-slate-500 mt-0.5">
            Inspection assignments, AI damage alerts, and maintenance deadlines
          </p>
        </div>
        <button
          onClick={markAllNotificationsRead}
          className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-md border border-slate-200 bg-white hover:bg-slate-50 text-xs font-medium text-slate-700"
        >
          <CheckCheck className="w-3.5 h-3.5" /> Mark all read
        </button>
      </div>

      <div className="bg-white rounded-lg border border-slate-200 divide-y divide-slate-100">
        {notifications.map((n) => (
          <div
            key={n.id}
            onClick={() => markNotificationRead(n.id)}
            className={`p-4 flex items-start justify-between gap-4 cursor-pointer transition-colors ${
              n.read ? 'bg-white' : 'bg-cyan-50/40'
            }`}
          >
            <div className="flex items-start gap-3">
              <div className={`p-2 rounded-md ${n.read ? 'bg-slate-100 text-slate-500' : 'bg-cyan-100 text-cyan-800'}`}>
                <Bell className="w-4 h-4" />
              </div>
              <div>
                <div className="flex items-center gap-2">
                  <p className="text-xs font-semibold text-slate-900">{n.title}</p>
                  {n.severity && <SeverityBadge severity={n.severity} />}
                </div>
                <p className="text-xs text-slate-600 mt-1">{n.message}</p>
                <p className="text-[11px] text-slate-400 mt-1">{formatDateTime(n.timestamp)}</p>
              </div>
            </div>
            {n.linkTo && (
              <Link to={n.linkTo} className="text-xs font-medium text-cyan-700 hover:underline shrink-0">
                Open
              </Link>
            )}
          </div>
        ))}
      </div>
    </div>
  )
}

