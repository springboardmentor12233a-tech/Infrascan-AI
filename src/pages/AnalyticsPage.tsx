import {
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  LineChart,
  Line,
  Legend,
} from 'recharts'
import { ChartCard } from '@/components/ui/ChartCard'
import { DemoBanner } from '@/components/ui/DemoBanner'
import {
  MONTHLY_INSPECTION_TRENDS,
  DAMAGE_CATEGORY_DISTRIBUTION,
  MODEL_PERFORMANCE_METRICS,
} from '@/data/mockData'

export function AnalyticsPage() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-semibold text-slate-900">Infrastructure Analytics</h1>
        <p className="text-xs text-slate-500 mt-0.5">
          Portfolio condition trends, defect distributions, and inspection cadence
        </p>
      </div>
      <DemoBanner />
      <div className="grid lg:grid-cols-2 gap-6">
        <ChartCard title="Monthly Inspection & Critical Finding Trends">
          <div className="h-72">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={MONTHLY_INSPECTION_TRENDS}>
                <CartesianGrid strokeDasharray="3 3" stroke="#E2E8F0" />
                <XAxis dataKey="month" tick={{ fontSize: 12 }} />
                <YAxis tick={{ fontSize: 12 }} />
                <Tooltip />
                <Legend />
                <Line type="monotone" dataKey="inspections" name="Inspections" stroke="#0F2942" strokeWidth={2} />
                <Line type="monotone" dataKey="findings" name="Findings" stroke="#0891B2" strokeWidth={2} />
                <Line type="monotone" dataKey="critical" name="Critical" stroke="#EF4444" strokeWidth={2} />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </ChartCard>

        <ChartCard title="Damage Category Frequency">
          <div className="h-72">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={DAMAGE_CATEGORY_DISTRIBUTION}>
                <CartesianGrid strokeDasharray="3 3" stroke="#E2E8F0" />
                <XAxis dataKey="name" tick={{ fontSize: 10 }} />
                <YAxis tick={{ fontSize: 12 }} />
                <Tooltip />
                <Bar dataKey="count" name="Occurrences" fill="#0F2942" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </ChartCard>
      </div>
    </div>
  )
}

export function ModelPerformancePage() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-semibold text-slate-900">AI Model Performance</h1>
        <p className="text-xs text-slate-500 mt-0.5">
          Evaluation metrics across InfraScan-CrackNet releases (Simulated Benchmark Data)
        </p>
      </div>
      <DemoBanner />
      <ChartCard title="Precision, Recall, F1 & mIoU Progression">
        <div className="h-80">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={MODEL_PERFORMANCE_METRICS}>
              <CartesianGrid strokeDasharray="3 3" stroke="#E2E8F0" />
              <XAxis dataKey="epoch" tick={{ fontSize: 12 }} />
              <YAxis domain={[0.6, 1]} tick={{ fontSize: 12 }} />
              <Tooltip />
              <Legend />
              <Line type="monotone" dataKey="precision" name="Precision" stroke="#0F2942" strokeWidth={2} />
              <Line type="monotone" dataKey="recall" name="Recall" stroke="#0891B2" strokeWidth={2} />
              <Line type="monotone" dataKey="f1" name="F1 Score" stroke="#10B981" strokeWidth={2} />
              <Line type="monotone" dataKey="mIoU" name="mIoU" stroke="#F59E0B" strokeWidth={2} />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </ChartCard>
    </div>
  )
}

