import { useState } from 'react'
import { Link } from 'react-router-dom'
import {
  ShieldAlert,
  ScanSearch,
  Layers,
  MapPin,
  FileText,
  TrendingUp,
  CheckCircle2,
  ArrowRight,
  Building2,
  Cpu,
  UploadCloud,
  ClipboardCheck,
  AlertTriangle,
  Activity,
  Eye,
} from 'lucide-react'
import { INFRASTRUCTURE_TYPES } from '@/lib/constants'
import { SAMPLE_INSPECTION_IMAGES } from '@/data/mockImages'
import type { InfrastructureType } from '@/types'

const INFRASTRUCTURE_DETAILS: Record<InfrastructureType, { focus: string; countLabel: string }> = {
  Bridge: { focus: 'Pier & deck shear cracks, bearing seat spalling', countLabel: 'Structural Bridges' },
  Building: { focus: 'Facade concrete spalling, settlement cracks', countLabel: 'Civic & Commercial' },
  Road: { focus: 'Alligator, longitudinal & transverse pavement cracks', countLabel: 'Highways & Arterials' },
  Tunnel: { focus: 'Lining cracks, joint efflorescence & moisture', countLabel: 'Subsurface Linings' },
  Dam: { focus: 'Spillway chute cracking & surface erosion', countLabel: 'Hydroelectric & Spillways' },
  'Concrete Structure': { focus: 'Delamination, rebar corrosion staining & spalls', countLabel: 'General Concrete' },
  'Retaining Wall': { focus: 'Lateral displacement cracks & weep-hole drainage', countLabel: 'Geotechnical Walls' },
  'Industrial Structure': { focus: 'Cooling tower shells, silos & heavy foundations', countLabel: 'Industrial Plants' },
}

export function LandingPage() {
  const [selectedInfra, setSelectedInfra] = useState<InfrastructureType>('Bridge')
  const [showcaseSample, setShowcaseSample] = useState<'bridge' | 'road'>('bridge')

  const showcaseImg =
    showcaseSample === 'bridge' ? SAMPLE_INSPECTION_IMAGES.bridgePierCrack : SAMPLE_INSPECTION_IMAGES.roadAlligatorCrack

  return (
    <div className="min-h-screen bg-white text-slate-900">
      {/* Top Navbar (Preserved) */}
      <header className="sticky top-0 z-30 bg-white/95 backdrop-blur border-b border-slate-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
          <Link to="/" className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-md bg-[#0F2942] flex items-center justify-center text-white">
              <ShieldAlert className="w-5 h-5 text-cyan-400" />
            </div>
            <span className="font-semibold text-slate-900 tracking-tight">InfraScan</span>
          </Link>
          <nav className="hidden md:flex items-center gap-7 text-sm font-medium text-slate-600">
            <a href="#capabilities" className="hover:text-slate-900">Capabilities</a>
            <a href="#how-it-works" className="hover:text-slate-900">How It Works</a>
            <a href="#ai-showcase" className="hover:text-slate-900">AI Showcase</a>
            <a href="#infrastructure" className="hover:text-slate-900">Infrastructure</a>
            <a href="#report-preview" className="hover:text-slate-900">Reports</a>
          </nav>
          <div className="flex items-center gap-3">
            <Link to="/login" className="text-sm font-medium text-slate-700 hover:text-slate-900 px-3 py-1.5">
              Sign In
            </Link>
            <Link
              to="/dashboard"
              className="text-sm font-medium bg-[#0F2942] text-white px-4 py-2 rounded-md hover:bg-[#163859] transition-colors"
            >
              Explore Platform
            </Link>
          </div>
        </div>
      </header>

      {/* Hero Section (Preserved) */}
      <section className="bg-[#0B162C] text-white py-20 lg:py-24 border-b border-slate-800">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 grid lg:grid-cols-2 gap-12 items-center">
          <div>
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-cyan-500/10 border border-cyan-500/30 text-cyan-300 text-xs font-medium mb-6">
              <Cpu className="w-3.5 h-3.5" /> Enterprise Civil Infrastructure Intelligence
            </div>
            <h1 className="text-3xl sm:text-4xl lg:text-5xl font-bold tracking-tight leading-[1.12]">
              Intelligent Infrastructure Inspection. Powered by AI.
            </h1>
            <p className="mt-5 text-base sm:text-lg text-slate-300 leading-relaxed max-w-xl">
              Detect, analyze and monitor structural damage with advanced computer vision and AI-powered infrastructure
              intelligence.
            </p>
            <div className="mt-8 flex flex-wrap gap-3">
              <Link
                to="/register"
                className="inline-flex items-center gap-2 px-5 py-2.5 rounded-md bg-cyan-600 hover:bg-cyan-500 text-white text-sm font-semibold transition-colors"
              >
                Get Started <ArrowRight className="w-4 h-4" />
              </Link>
              <Link
                to="/dashboard"
                className="inline-flex items-center gap-2 px-5 py-2.5 rounded-md bg-slate-800 hover:bg-slate-700 text-white border border-slate-700 text-sm font-semibold transition-colors"
              >
                Explore Platform
              </Link>
            </div>
            <div className="mt-8 grid grid-cols-3 gap-6 pt-8 border-t border-slate-800 text-xs">
              <div>
                <p className="text-xl font-bold text-white">Demo UI</p>
                <p className="text-slate-400 mt-0.5">Simulated Crack Detection</p>
              </div>
              <div>
                <p className="text-xl font-bold text-white">8 Asset Types</p>
                <p className="text-slate-400 mt-0.5">Bridges, Dams, Tunnels & More</p>
              </div>
              <div>
                <p className="text-xl font-bold text-white">Calibrated</p>
                <p className="text-slate-400 mt-0.5">Dimension Estimation Support</p>
              </div>
            </div>
          </div>

          {/* Technical Visual Preview */}
          <div className="bg-[#112240] border border-slate-700/80 rounded-lg p-3 shadow-2xl">
            <div className="flex items-center justify-between px-2 pb-2.5 border-b border-slate-700/80 text-xs text-slate-300">
              <span className="font-mono">viaduct_pier4_east_01.jpg — Demo AI Overlay</span>
              <span className="px-2 py-0.5 rounded bg-red-500/20 text-red-300 font-medium">Demo: Critical</span>
            </div>
            <div className="relative mt-2 rounded overflow-hidden">
              <img
                src={SAMPLE_INSPECTION_IMAGES.bridgePierCrack}
                alt="AI Crack Detection Preview"
                className="w-full h-auto block"
              />
              <div className="absolute top-[18%] left-[16%] w-[42%] h-[62%] border-2 border-red-500 bg-red-500/10 rounded-xs">
                <span className="bg-red-600 text-white text-[10px] font-mono px-1.5 py-0.5">
                  Longitudinal Crack (Demo)
                </span>
              </div>
              <div className="absolute top-[26%] left-[61%] w-[17%] h-[19%] border-2 border-amber-400 bg-amber-400/10 rounded-xs">
                <span className="bg-amber-500 text-slate-950 text-[10px] font-mono px-1.5 py-0.5">Spalling (Demo)</span>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* 1. CAPABILITIES (Refined with hover effects, icon presentation & mini visual previews) */}
      <section id="capabilities" className="py-20 bg-[#F8FAFC]">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="max-w-2xl">
            <p className="text-xs font-semibold uppercase tracking-wider text-cyan-700">Platform Capabilities</p>
            <h2 className="mt-2 text-2xl sm:text-3xl font-bold text-slate-900">
              End-to-End Structural Inspection & Asset Intelligence
            </h2>
          </div>
          <div className="mt-10 grid sm:grid-cols-2 lg:grid-cols-3 gap-6">
            {[
              {
                icon: ScanSearch,
                title: 'AI Crack Detection & Segmentation',
                desc: 'Pixel-level segmentation masks and bounding boxes for longitudinal, transverse, and alligator cracks.',
                badge: 'Detection + Mask',
              },
              {
                icon: Layers,
                title: 'Surface Damage Classification',
                desc: 'Identify spalling, efflorescence, delamination, and corrosion staining across concrete and asphalt.',
                badge: 'Multi-Class',
              },
              {
                icon: TrendingUp,
                title: 'Calibrated Dimension Estimation',
                desc: 'Estimate crack length, width, and affected area in millimeters where camera calibration permits.',
                badge: 'Calibration-Aware',
              },
              {
                icon: MapPin,
                title: 'Geospatial Damage Mapping',
                desc: 'Visualize asset condition and severity markers across regional corridors with interactive Leaflet maps.',
                badge: 'Leaflet + OSM',
              },
              {
                icon: ClipboardCheck,
                title: 'Maintenance & Progression Tracking',
                desc: 'Compare historical inspections side-by-side and prioritize urgent engineering reviews.',
                badge: 'Time-Series',
              },
              {
                icon: FileText,
                title: 'Automated Inspection Reports',
                desc: 'Generate audit-ready engineering reports with AI findings, overlays, and review sign-off.',
                badge: 'PDF / CSV Export',
              },
            ].map((cap) => {
              const Icon = cap.icon
              return (
                <div
                  key={cap.title}
                  className="bg-white p-6 rounded-lg border border-slate-200 shadow-xs hover:border-cyan-400/70 hover:shadow-md transition-all duration-200 group flex flex-col justify-between"
                >
                  <div>
                    <div className="flex items-center justify-between mb-4">
                      <div className="w-10 h-10 rounded-md bg-[#0F2942]/10 text-[#0F2942] ring-1 ring-[#0F2942]/15 group-hover:bg-[#0F2942] group-hover:text-cyan-300 transition-colors flex items-center justify-center">
                        <Icon className="w-5 h-5" />
                      </div>
                      <span className="text-[11px] font-mono px-2 py-0.5 rounded bg-slate-100 text-slate-600 border border-slate-200">
                        {cap.badge}
                      </span>
                    </div>
                    <h3 className="text-base font-semibold text-slate-900">{cap.title}</h3>
                    <p className="mt-2 text-sm text-slate-600 leading-relaxed">{cap.desc}</p>
                  </div>
                </div>
              )
            })}
          </div>
        </div>
      </section>

      {/* 2. HOW IT WORKS (4-step workflow with horizontal connector & image-to-AI visual) */}
      <section id="how-it-works" className="py-20 bg-white border-y border-slate-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center max-w-2xl mx-auto">
            <p className="text-xs font-semibold uppercase tracking-wider text-cyan-700">Workflow</p>
            <h2 className="mt-2 text-2xl sm:text-3xl font-bold text-slate-900">How InfraScan Works</h2>
            <p className="mt-2 text-sm text-slate-600">
              From raw field imagery to calibrated engineering review in four structured stages.
            </p>
          </div>

          <div className="mt-12 relative">
            {/* Horizontal connector on desktop */}
            <div className="hidden md:block absolute top-10 left-[12%] right-[12%] h-0.5 bg-slate-200 z-0" />
            <div className="grid md:grid-cols-4 gap-6 relative z-10">
              {[
                { step: '01', icon: Building2, title: 'Register Assets', desc: 'Catalog bridges, tunnels, dams, and buildings with inspection schedules.' },
                { step: '02', icon: UploadCloud, title: 'Upload Imagery', desc: 'Ingest UAV, DSLR, or mobile inspection photos with optional calibration.' },
                { step: '03', icon: Cpu, title: 'Run AI Analysis', desc: 'Detect cracks, generate segmentation masks, and classify damage severity.' },
                { step: '04', icon: CheckCircle2, title: 'Review & Maintain', desc: 'Assign engineering reviews, track progression, and export reports.' },
              ].map((item) => {
                const Icon = item.icon
                return (
                  <div key={item.step} className="p-5 rounded-lg border border-slate-200 bg-[#F8FAFC] hover:border-cyan-300 transition-colors">
                    <div className="flex items-center justify-between">
                      <span className="font-mono text-xs font-semibold text-cyan-700 bg-cyan-50 px-2 py-0.5 rounded border border-cyan-200">
                        STEP {item.step}
                      </span>
                      <Icon className="w-5 h-5 text-[#0F2942]" />
                    </div>
                    <h3 className="text-sm font-semibold text-slate-900 mt-4">{item.title}</h3>
                    <p className="mt-1.5 text-xs text-slate-600 leading-relaxed">{item.desc}</p>
                  </div>
                )
              })}
            </div>
          </div>
        </div>
      </section>

      {/* 4. AI ANALYSIS SHOWCASE (Original vs Detection vs Segmentation) */}
      <section id="ai-showcase" className="py-20 bg-[#F8FAFC]">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex flex-col md:flex-row md:items-end justify-between gap-4 mb-8">
            <div>
              <p className="text-xs font-semibold uppercase tracking-wider text-cyan-700">
                AI Analysis Showcase · Demonstration Data
              </p>
              <h2 className="mt-2 text-2xl sm:text-3xl font-bold text-slate-900">
                Original Image vs. Detection vs. Segmentation
              </h2>
            </div>
            <div className="flex items-center gap-2">
              <button
                onClick={() => setShowcaseSample('bridge')}
                className={`px-3 py-1.5 rounded-md text-xs font-medium border transition-colors ${
                  showcaseSample === 'bridge'
                    ? 'bg-[#0F2942] text-white border-[#0F2942]'
                    : 'bg-white text-slate-700 border-slate-200 hover:bg-slate-50'
                }`}
              >
                Bridge Pier Sample
              </button>
              <button
                onClick={() => setShowcaseSample('road')}
                className={`px-3 py-1.5 rounded-md text-xs font-medium border transition-colors ${
                  showcaseSample === 'road'
                    ? 'bg-[#0F2942] text-white border-[#0F2942]'
                    : 'bg-white text-slate-700 border-slate-200 hover:bg-slate-50'
                }`}
              >
                Pavement Sample
              </button>
            </div>
          </div>

          <div className="grid md:grid-cols-3 gap-6">
            {/* Original */}
            <div className="bg-white rounded-lg border border-slate-200 overflow-hidden shadow-xs">
              <div className="px-4 py-2.5 border-b border-slate-100 flex items-center justify-between text-xs">
                <span className="font-semibold text-slate-900">1. Original Inspection Image</span>
                <span className="font-mono text-slate-400">RAW</span>
              </div>
              <img src={showcaseImg} alt="Original inspection" className="w-full aspect-video object-cover block" />
            </div>

            {/* Detection */}
            <div className="bg-white rounded-lg border border-slate-200 overflow-hidden shadow-xs">
              <div className="px-4 py-2.5 border-b border-slate-100 flex items-center justify-between text-xs">
                <span className="font-semibold text-slate-900">2. AI Crack Detection</span>
                <span className="font-mono text-cyan-700">BBox Overlay (Demo)</span>
              </div>
              <div className="relative">
                <img src={showcaseImg} alt="AI Detection" className="w-full aspect-video object-cover block" />
                <div className="absolute top-[18%] left-[16%] w-[42%] h-[62%] border-2 border-red-500 bg-red-500/10">
                  <span className="bg-red-600 text-white text-[10px] font-mono px-1">Crack (Demo)</span>
                </div>
              </div>
            </div>

            {/* Segmentation */}
            <div className="bg-white rounded-lg border border-slate-200 overflow-hidden shadow-xs">
              <div className="px-4 py-2.5 border-b border-slate-100 flex items-center justify-between text-xs">
                <span className="font-semibold text-slate-900">3. Segmentation Mask</span>
                <span className="font-mono text-cyan-700">Pixel Mask (Demo)</span>
              </div>
              <div className="relative">
                <img src={showcaseImg} alt="Segmentation Mask" className="w-full aspect-video object-cover block" />
                <svg viewBox="0 0 1000 700" className="absolute inset-0 w-full h-full pointer-events-none" preserveAspectRatio="none">
                  <polygon
                    points="175,135 245,190 340,285 460,400 568,545 552,555 442,412 322,298 225,202 168,148"
                    fill="#EF4444"
                    fillOpacity="0.55"
                    stroke="#EF4444"
                    strokeWidth="3"
                  />
                </svg>
              </div>
            </div>
          </div>

          <div className="mt-6 flex items-center justify-between flex-wrap gap-3 text-xs text-slate-500">
            <span>Note: Overlays shown above are simulated demonstration outputs.</span>
            <Link to="/analysis" className="inline-flex items-center gap-1.5 font-semibold text-cyan-700 hover:underline">
              Open Interactive AI Analysis Workspace <ArrowRight className="w-3.5 h-3.5" />
            </Link>
          </div>
        </div>
      </section>

      {/* 3. INFRASTRUCTURE COVERAGE (Interactive, consistent dimensions) */}
      <section id="infrastructure" className="py-20 bg-white border-y border-slate-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex flex-col md:flex-row md:items-end justify-between gap-4 mb-10">
            <div>
              <p className="text-xs font-semibold uppercase tracking-wider text-cyan-700">Asset Coverage</p>
              <h2 className="mt-2 text-2xl sm:text-3xl font-bold text-slate-900">Supported Infrastructure Types</h2>
            </div>
            <Link to="/assets" className="text-sm font-medium text-cyan-700 hover:underline inline-flex items-center gap-1">
              View Asset Registry <ArrowRight className="w-4 h-4" />
            </Link>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            {INFRASTRUCTURE_TYPES.map((type) => {
              const active = selectedInfra === type
              const info = INFRASTRUCTURE_DETAILS[type]
              return (
                <button
                  key={type}
                  type="button"
                  onClick={() => setSelectedInfra(type)}
                  className={`text-left p-4 rounded-lg border min-h-[120px] flex flex-col justify-between transition-all ${
                    active
                      ? 'bg-[#0F2942] text-white border-[#0F2942] shadow-md'
                      : 'bg-[#F8FAFC] text-slate-800 border-slate-200 hover:border-cyan-400'
                  }`}
                >
                  <div className="flex items-center justify-between w-full">
                    <span className="text-sm font-semibold">{type}</span>
                    <Building2 className={`w-4 h-4 shrink-0 ${active ? 'text-cyan-400' : 'text-cyan-700'}`} />
                  </div>
                  <div className="mt-3">
                    <p className={`text-[11px] leading-snug ${active ? 'text-slate-300' : 'text-slate-500'}`}>
                      {info.focus}
                    </p>
                  </div>
                </button>
              )
            })}
          </div>
        </div>
      </section>

      {/* 5. ENGINEERING INTELLIGENCE SECTION */}
      <section className="py-20 bg-[#F8FAFC]">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 grid lg:grid-cols-2 gap-10 items-center">
          <div>
            <p className="text-xs font-semibold uppercase tracking-wider text-cyan-700">Engineering Intelligence</p>
            <h2 className="mt-2 text-2xl sm:text-3xl font-bold text-slate-900">
              Built for Civil Engineers, Not Just Computer Vision
            </h2>
            <p className="mt-3 text-sm text-slate-600 leading-relaxed">
              InfraScan translates raw detections into actionable structural engineering workflows—combining
              preliminary severity assessment, calibrated measurements, and multi-cycle condition monitoring.
            </p>
            <div className="mt-6 space-y-3">
              {[
                { icon: Layers, title: 'Damage Categorization', desc: 'Longitudinal, transverse, alligator cracking, spalling, and efflorescence.' },
                { icon: AlertTriangle, title: 'Preliminary Severity Assessment', desc: 'Low, Moderate, High, and Critical triage for engineering review.' },
                { icon: Activity, title: 'Condition & Progression History', desc: 'Track crack growth across inspection cycles with side-by-side comparisons.' },
              ].map((item) => {
                const Icon = item.icon
                return (
                  <div key={item.title} className="flex items-start gap-3 p-3.5 rounded-lg bg-white border border-slate-200">
                    <Icon className="w-4 h-4 text-cyan-700 shrink-0 mt-0.5" />
                    <div>
                      <p className="text-xs font-semibold text-slate-900">{item.title}</p>
                      <p className="text-xs text-slate-600 mt-0.5">{item.desc}</p>
                    </div>
                  </div>
                )
              })}
            </div>
          </div>

          {/* 6. INSPECTION REPORT PREVIEW */}
          <div id="report-preview" className="bg-white rounded-lg border border-slate-200 shadow-sm overflow-hidden">
            <div className="px-5 py-3.5 bg-[#0F2942] text-white flex items-center justify-between">
              <div className="flex items-center gap-2 text-xs font-semibold">
                <FileText className="w-4 h-4 text-cyan-400" />
                Inspection Report Preview (Demo)
              </div>
              <span className="px-2 py-0.5 rounded bg-amber-500/20 text-amber-300 text-[11px] font-medium">
                Pending Engineer Review
              </span>
            </div>
            <div className="p-5 space-y-4 text-xs">
              <div className="grid grid-cols-2 gap-3 pb-3 border-b border-slate-100">
                <div>
                  <p className="text-slate-400">Asset</p>
                  <p className="font-semibold text-slate-900">North River Viaduct — Pier 4</p>
                </div>
                <div>
                  <p className="text-slate-400">Inspection ID</p>
                  <p className="font-mono font-semibold text-slate-900">INSP-2026-089</p>
                </div>
              </div>
              <div className="flex gap-4 items-center">
                <img
                  src={SAMPLE_INSPECTION_IMAGES.bridgePierCrack}
                  alt="Report thumbnail"
                  className="w-28 h-20 object-cover rounded border border-slate-200 shrink-0"
                />
                <div className="space-y-1">
                  <p className="font-semibold text-slate-900">Primary Finding: Longitudinal Crack (Demo)</p>
                  <p className="text-slate-600">
                    Preliminary severity flagged as Critical. Calibrated reference scale present; awaiting Senior Civil
                    Engineer sign-off.
                  </p>
                </div>
              </div>
              <div className="pt-2 flex justify-end">
                <Link
                  to="/reports"
                  className="inline-flex items-center gap-1.5 text-xs font-semibold text-cyan-700 hover:underline"
                >
                  <Eye className="w-3.5 h-3.5" /> Open Inspection Reports
                </Link>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* CTA (Preserved) */}
      <section id="technology" className="py-16 bg-[#0F2942] text-white">
        <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
          <h2 className="text-2xl sm:text-3xl font-bold">Ready to Modernize Structural Inspections?</h2>
          <p className="mt-3 text-slate-300 text-sm sm:text-base max-w-2xl mx-auto">
            Launch the InfraScan workspace to explore AI crack analysis, geospatial mapping, and maintenance workflows.
          </p>
          <div className="mt-7 flex justify-center gap-3">
            <Link
              to="/dashboard"
              className="px-5 py-2.5 rounded-md bg-cyan-600 hover:bg-cyan-500 text-white text-sm font-semibold transition-colors"
            >
              Open Dashboard
            </Link>
            <Link
              to="/analysis"
              className="px-5 py-2.5 rounded-md bg-white/10 hover:bg-white/20 text-white text-sm font-semibold transition-colors"
            >
              Try AI Damage Analysis
            </Link>
          </div>
        </div>
      </section>

      {/* Footer (Preserved) */}
      <footer className="bg-[#060D1A] text-slate-400 py-10 border-t border-slate-800">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex flex-col sm:flex-row items-center justify-between gap-4 text-xs">
          <div className="flex items-center gap-2 text-white font-semibold">
            <ShieldAlert className="w-4 h-4 text-cyan-400" /> InfraScan Platform
          </div>
          <p>© {new Date().getFullYear()} InfraScan Engineering Intelligence. Frontend Demonstration Build.</p>
        </div>
      </footer>
    </div>
  )
}
