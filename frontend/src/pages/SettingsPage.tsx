import { useState } from 'react'
import { Save, CheckCircle2 } from 'lucide-react'
import { useAppStore } from '@/store/useAppStore'

export function SettingsPage() {
  const currentUser = useAppStore((s) => s.currentUser)
  const [saved, setSaved] = useState(false)
  const [emailAlerts, setEmailAlerts] = useState(true)
  const [criticalAlerts, setCriticalAlerts] = useState(true)

  const handleSave = (e: React.FormEvent) => {
    e.preventDefault()
    setSaved(true)
    setTimeout(() => setSaved(false), 2500)
  }

  return (
    <div className="space-y-6 max-w-3xl">
      <div>
        <h1 className="text-xl font-semibold text-slate-900">Settings</h1>
        <p className="text-xs text-slate-500 mt-0.5">Manage your profile, notification preferences, and security</p>
      </div>

      <form onSubmit={handleSave} className="bg-white rounded-lg border border-slate-200 p-6 space-y-6 text-xs">
        <div>
          <h2 className="text-sm font-semibold text-slate-900 mb-3">User Profile</h2>
          <div className="grid sm:grid-cols-2 gap-4">
            <div>
              <label className="block font-medium text-slate-700 mb-1">Full Name</label>
              <input defaultValue={currentUser.name} className="w-full px-3 py-2 border border-slate-300 rounded-md" />
            </div>
            <div>
              <label className="block font-medium text-slate-700 mb-1">Email</label>
              <input defaultValue={currentUser.email} className="w-full px-3 py-2 border border-slate-300 rounded-md" />
            </div>
            <div>
              <label className="block font-medium text-slate-700 mb-1">Role</label>
              <input disabled value={currentUser.role} className="w-full px-3 py-2 border border-slate-200 rounded-md bg-slate-50 text-slate-500" />
            </div>
            <div>
              <label className="block font-medium text-slate-700 mb-1">Department</label>
              <input defaultValue={currentUser.department} className="w-full px-3 py-2 border border-slate-300 rounded-md" />
            </div>
          </div>
        </div>

        <div className="pt-4 border-t border-slate-200">
          <h2 className="text-sm font-semibold text-slate-900 mb-3">Notification Preferences</h2>
          <div className="space-y-2.5">
            <label className="flex items-center gap-2.5 cursor-pointer">
              <input type="checkbox" checked={emailAlerts} onChange={(e) => setEmailAlerts(e.target.checked)} />
              <span>Email me when inspections are completed</span>
            </label>
            <label className="flex items-center gap-2.5 cursor-pointer">
              <input type="checkbox" checked={criticalAlerts} onChange={(e) => setCriticalAlerts(e.target.checked)} />
              <span>Immediate alert for Critical severity AI findings</span>
            </label>
          </div>
        </div>

        <div className="pt-4 border-t border-slate-200 flex items-center justify-between">
          {saved ? (
            <span className="inline-flex items-center gap-1.5 text-emerald-700 font-medium">
              <CheckCircle2 className="w-4 h-4" /> Settings saved
            </span>
          ) : (
            <span />
          )}
          <button
            type="submit"
            className="inline-flex items-center gap-1.5 px-4 py-2 bg-[#0F2942] hover:bg-[#163859] text-white rounded-md font-medium"
          >
            <Save className="w-3.5 h-3.5" /> Save Preferences
          </button>
        </div>
      </form>
    </div>
  )
}

