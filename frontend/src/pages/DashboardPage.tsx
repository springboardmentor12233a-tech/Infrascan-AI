import { useState } from 'react'
import { Link } from 'react-router-dom'
import {
  Building2,
  ClipboardCheck,
  CheckCircle2,
  AlertTriangle,
  ShieldAlert,
  Clock,
  ArrowRight,
  Plus,
} from 'lucide-react'
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
  PieChart,
  Pie,
  Cell,
  AreaChart,
  Area,
  Legend,
} from 'recharts'
import { DashboardCard } from '@/components/ui/DashboardCard'
import { ChartCard } from '@/components/ui/ChartCard'
import { SeverityBadge } from '@/components/ui/SeverityBadge'
import { StatusBadge } from '@/components/ui/StatusBadge'
import { DemoBanner } from '@/components/ui/DemoBanner'
import { MOCK_ASSETS, MOCK_INSPECTIONS, MOCK_MAINTENANCE_TASKS } from '@/data/mockData'

type TimeRange = '7d' | '30d' | '90d' | '12m'

const TREND_DATA_BY_RANGE: Record<TimeRange, { period: string; total: number; completed: number; pending: number }[]> = {
  '7d': [
    { period: 'Mon', total: 18, completed: 15, pending: 3 },
    { period: 'Tue', total: 22, completed: 19, pending: 3 },
    { period: 'Wed', total: 19, completed: 16, pending: 3 },
    { period: 'Thu', total: 25, completed: 21, pending: 4 },
    { period: 'Fri', total: 28, completed: 24, pending: 4 },
    { period: 'Sat', total: 12, completed: 10, pending: 2 },
    { period: 'Sun', total: 9, completed: 8, pending: 1 },
  ],
  '30d': [
    { period: 'Week 1', total: 82, completed: 71, pending: 11 },
    { period: 'Week 2', total: 94, completed: 82, pending: 12 },
    { period: 'Week 3', total: 106, completed: 92, pending: 14 },
    { period: 'Week 4', total: 112, completed: 98, pending: 14 },
  ],
  '90d': [
    { period: 'Sep', total: 380, completed: 332, pending: 48 },
    { period: 'Oct', total: 425, completed: 374, pending: 51 },
    { period: 'Nov', total: 479, completed: 390, pending: 42 },
  ],
  '12m': [
    { period: 'Q1', total: 280, completed: 245, pending: 35 },
    { period: 'Q2', total: 310, completed: 268, pending: 42 },
    { period: 'Q3', total: 342, completed: 295, pending: 47 },
    { period: 'Q4', total: 352, completed: 288, pending: 42 },
  ],
}

const DAMAGE_DONUT_DATA = [
  { name: 'Cracks', value: 42, color: '#0F2942' },
  { name: 'Spalling', value: 19, color: '#0891B2' },
  { name: 'Corrosion', value: 14, color: '#F59E0B' },
  { name: 'Exposed Reinforcement', value: 9, color: '#EF4444' },
  { name: 'Surface Deterioration', value: 11, color: '#64748B' },
  { name: 'Other Damage', value: 5, color: '#94A3B8' },
]

const FIVE_LEVEL_SEVERITY = [
  { name: 'No Visible Damage', count: 62, color: '#10B981' },
  { name: 'Minor Damage', count: 48, color: '#0891B2' },
  { name: 'Moderate Damage', count: 36, color: '#F59E0B' },
  { name: 'Severe Damage', count: 21, color: '#F97316' },
  { name: 'Critical / Urgent Review', count: 24, color: '#EF4444' },
]

const CRITICAL_FINDINGS_DEMO = [
  {
    id: 'CF-101',
    assetName: 'North River Viaduct — Pier 4',
    category: 'Longitudinal Crack',
    severity: 'Critical' as const,
    date: '2026-11-18',
    reviewStatus: 'Pending Engineer Review',
  },
  {
    id: 'CF-102',
    assetName: 'Oakridge Hydroelectric Spillway',
    category: 'Spalling',
    severity: 'High' as const,
    date: '2026-11-20',
    reviewStatus: 'Under Review',
  },
  {
    id: 'CF-103',
    assetName: 'Harbor Freight Arterial — Mile 12',
    category: 'Alligator Crack',
    severity: 'High' as const,
    date: '2026-11-10',
    reviewStatus: 'Scheduled for Repair',
  },
]

export function DashboardPage() {
  const [timeRange, setTimeRange] = useState<TimeRange>('90d')
  const trendData = TREND_DATA_BY_RANGE[timeRange]

  return (
    <div className="space-y-6">
      {/* A. PAGE HEADER */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-semibold text-slate-900">Infrastructure Overview</h1>
          <p className="text-xs text-slate-500 mt-0.5">
            Monitor infrastructure assets, inspection activities and AI-powered damage findings across your
            infrastructure portfolio.
          </p>
        </div>
        <div className="flex items-center gap-2.5">
          <Link
            to="/app/inspections"
            className="inline-flex items-center gap-1.5 px-3.5 py-2 rounded-md bg-[#0F2942] hover:bg-[#163859] text-white text-xs font-medium transition-colors"
          >
            <Plus className="w-3.5 h-3.5" /> Create Inspection
          </Link>
          <Link
            to="/app/assets"
            className="inline-flex items-center gap-1.5 px-3.5 py-2 rounded-md bg-white border border-slate-200 hover:bg-slate-50 text-slate-700 text-xs font-medium transition-colors"
          >
            Register Infrastructure
          </Link>
        </div>
      </div>

      <DemoBanner message="Demonstration Figures: All portfolio counts, inspection metrics, and AI findings shown on this dashboard are simulated demonstration data." />

      {/* B. KPI CARDS */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6 gap-4">
        <DashboardCard title="Total Infrastructure Assets" value="248" icon={Building2} accent="navy" subtitle="Total registered assets" />
        <DashboardCard title="Total Inspections" value="1,284" icon={ClipboardCheck} accent="cyan" subtitle="Total inspections conducted" />
        <DashboardCard title="Completed Inspections" value="1,096" icon={CheckCircle2} accent="emerald" subtitle="Completed inspection records" />
        <DashboardCard title="Damaged Assets" value="186" icon={AlertTriangle} accent="amber" subtitle="Recorded visible damage" />
        <DashboardCard title="Critical Findings" value="24" icon={ShieldAlert} accent="red" subtitle="Urgent engineering review" />
        <DashboardCard title="Pending Inspections" value="42" icon={Clock} accent="navy" subtitle="Awaiting completion" />
      </div>

      {/* C. INSPECTION ANALYTICS & D. DAMAGE CATEGORY DISTRIBUTION */}
      <div className="grid lg:grid-cols-3 gap-6">
        <ChartCard
          title="Inspection Analytics"
          subtitle="Total, completed, and pending inspections over time"
          className="lg:col-span-2"
          action={
            <select
              value={timeRange}
              onChange={(e) => setTimeRange(e.target.value as TimeRange)}
              className="px-2.5 py-1 text-xs border border-slate-200 rounded-md bg-white text-slate-700"
            >
              <option value="7d">Last 7 days</option>
              <option value="30d">Last 30 days</option>
              <option value="90d">Last 90 days</option>
              <option value="12m">Last 12 months</option>
            </select>
          }
        >
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={trendData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#E2E8F0" />
                <XAxis dataKey="period" tick={{ fontSize: 12, fill: '#64748B' }} />
                <YAxis tick={{ fontSize: 12, fill: '#64748B' }} />
                <Tooltip />
                <Legend wrapperStyle={{ fontSize: 12 }} />
                <Area type="monotone" dataKey="total" name="Total Inspections" stroke="#0F2942" fill="#0F2942" fillOpacity={0.1} strokeWidth={2} />
                <Area type="monotone" dataKey="completed" name="Completed" stroke="#0891B2" fill="#0891B2" fillOpacity={0.15} strokeWidth={2} />
                <Area type="monotone" dataKey="pending" name="Pending" stroke="#F59E0B" fill="#F59E0B" fillOpacity={0.1} strokeWidth={2} />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </ChartCard>

        <ChartCard title="Damage Category Distribution" subtitle="Detected defect classes (%)">
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie data={DAMAGE_DONUT_DATA} dataKey="value" nameKey="name" cx="50%" cy="50%" innerRadius={48} outerRadius={78} paddingAngle={2}>
                  {DAMAGE_DONUT_DATA.map((entry) => (
                    <Cell key={entry.name} fill={entry.color} />
                  ))}
                </Pie>
                <Tooltip formatter={(value) => `${value}%`} />
                <Legend wrapperStyle={{ fontSize: 11 }} />
              </PieChart>
            </ResponsiveContainer>
          </div>
        </ChartCard>
      </div>

      {/* E. DAMAGE SEVERITY DISTRIBUTION & H. CRITICAL FINDINGS */}
      <div className="grid lg:grid-cols-2 gap-6">
        <ChartCard title="Damage Severity Distribution" subtitle="5-level preliminary engineering triage">
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={FIVE_LEVEL_SEVERITY} layout="vertical" margin={{ left: 30 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#E2E8F0" />
                <XAxis type="number" tick={{ fontSize: 12, fill: '#64748B' }} />
                <YAxis type="category" dataKey="name" width={145} tick={{ fontSize: 11, fill: '#334155' }} />
                <Tooltip />
                <Bar dataKey="count" name="Findings" radius={[0, 4, 4, 0]}>
                  {FIVE_LEVEL_SEVERITY.map((entry) => (
                    <Cell key={entry.name} fill={entry.color} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </ChartCard>

        <div className="bg-white rounded-lg border border-slate-200 p-5 shadow-xs">
          <div className="flex items-center justify-between mb-3">
            <div>
              <h3 className="text-sm font-semibold text-slate-900">Critical Findings</h3>
              <p className="text-xs text-slate-500">High-priority findings awaiting engineering verification</p>
            </div>
            <Link to="/app/analysis" className="text-xs font-medium text-cyan-700 hover:underline">
              AI Workspace
            </Link>
          </div>
          <div className="space-y-3">
            {CRITICAL_FINDINGS_DEMO.map((cf) => (
              <div key={cf.id} className="p-3 rounded-md bg-slate-50 border border-slate-200 flex items-center justify-between gap-3">
                <div className="min-w-0">
                  <p className="text-xs font-semibold text-slate-900 truncate">{cf.assetName}</p>
                  <p className="text-[11px] text-slate-500 mt-0.5">
                    {cf.category} · Detected {cf.date} · {cf.reviewStatus}
                  </p>
                </div>
                <div className="flex items-center gap-2 shrink-0">
                  <SeverityBadge severity={cf.severity} />
                  <Link to="/app/analysis" className="text-xs font-medium text-cyan-700 hover:underline">
                    View
                  </Link>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* F. INFRASTRUCTURE CONDITION OVERVIEW & G. RECENT INSPECTIONS */}
      <div className="grid lg:grid-cols-2 gap-6">
        <div className="bg-white rounded-lg border border-slate-200 shadow-xs overflow-hidden">
          <div className="px-5 py-4 border-b border-slate-200 flex items-center justify-between">
            <h3 className="text-sm font-semibold text-slate-900">Infrastructure Condition Overview</h3>
            <Link to="/app/assets" className="text-xs font-medium text-cyan-700 hover:underline inline-flex items-center gap-1">
              All Assets <ArrowRight className="w-3 h-3" />
            </Link>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-slate-50 text-slate-500 border-b border-slate-200">
                <tr>
                  <th className="px-4 py-2.5 font-medium">Infrastructure</th>
                  <th className="px-4 py-2.5 font-medium">Type</th>
                  <th className="px-4 py-2.5 font-medium">Condition</th>
                  <th className="px-4 py-2.5 font-medium">Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {MOCK_ASSETS.slice(0, 5).map((asset) => (
                  <tr key={asset.id} className="hover:bg-slate-50">
                    <td className="px-4 py-3 font-medium text-slate-900">{asset.name}</td>
                    <td className="px-4 py-3 text-slate-600">{asset.type}</td>
                    <td className="px-4 py-3 font-mono font-semibold text-slate-800">{asset.conditionScore}/100</td>
                    <td className="px-4 py-3">
                      <StatusBadge status={asset.status} />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        <div className="bg-white rounded-lg border border-slate-200 shadow-xs overflow-hidden">
          <div className="px-5 py-4 border-b border-slate-200 flex items-center justify-between">
            <h3 className="text-sm font-semibold text-slate-900">Recent Inspections</h3>
            <Link to="/app/inspections" className="text-xs font-medium text-cyan-700 hover:underline">
              View all
            </Link>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-slate-50 text-slate-500 border-b border-slate-200">
                <tr>
                  <th className="px-4 py-2.5 font-medium">ID</th>
                  <th className="px-4 py-2.5 font-medium">Infrastructure</th>
                  <th className="px-4 py-2.5 font-medium">AI Status</th>
                  <th className="px-4 py-2.5 font-medium">Findings</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {MOCK_INSPECTIONS.slice(0, 5).map((insp) => (
                  <tr key={insp.id} className="hover:bg-slate-50">
                    <td className="px-4 py-3 font-mono font-medium text-slate-800">{insp.id}</td>
                    <td className="px-4 py-3 text-slate-700">{insp.assetName}</td>
                    <td className="px-4 py-3">
                      <StatusBadge status={insp.status} />
                    </td>
                    <td className="px-4 py-3">
                      <SeverityBadge severity={insp.maxSeverity} />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>

      {/* I. MAINTENANCE PRIORITIES */}
      <div className="bg-white rounded-lg border border-slate-200 p-5 shadow-xs">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-sm font-semibold text-slate-900">Maintenance Priorities</h3>
          <Link to="/app/maintenance" className="text-xs font-medium text-cyan-700 hover:underline">
            Manage Tasks
          </Link>
        </div>
        <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {MOCK_MAINTENANCE_TASKS.map((task) => (
            <div key={task.id} className="p-3.5 rounded-md bg-slate-50 border border-slate-200 space-y-1.5">
              <span className="text-[11px] font-semibold text-cyan-800">{task.priority}</span>
              <p className="text-xs font-semibold text-slate-900 line-clamp-2">{task.title}</p>
              <div className="flex items-center justify-between text-[11px] text-slate-500 pt-1">
                <span>{task.assignedTo}</span>
                <span>Due {task.dueDate}</span>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
