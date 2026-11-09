import React from 'react';
import { Link } from 'react-router-dom';
import { 
  HardHat, 
  ArrowRight, 
  CheckCircle, 
  ShieldCheck, 
  Activity, 
  MapPin, 
  FileText, 
  Layers, 
  Sparkles, 
  Building2, 
  Camera,
  Cpu,
  BarChart3,
  Lock
} from 'lucide-react';
import { useAuth } from '../context/AuthContext';

export const LandingPage: React.FC = () => {
  const { user } = useAuth();

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col font-sans selection:bg-blue-600 selection:text-white">
      {/* ── Top Navigation Bar ─────────────────────────────────────────────── */}
      <header className="border-b border-slate-800/80 bg-slate-950/80 backdrop-blur-md sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-6 h-16 flex items-center justify-between">
          <Link to="/" className="flex items-center gap-3 group">
            <div className="h-10 w-10 rounded-xl bg-gradient-to-tr from-blue-600 to-indigo-600 flex items-center justify-center text-white shadow-lg shadow-blue-500/20 group-hover:scale-105 transition-transform">
              <HardHat className="w-5 h-5" />
            </div>
            <div>
              <span className="font-extrabold text-xl tracking-tight text-white">InfraScan</span>
              <span className="text-blue-400 text-xs font-semibold ml-1.5 px-1.5 py-0.5 rounded bg-blue-950 border border-blue-800/60">AI</span>
            </div>
          </Link>

          <nav className="hidden md:flex items-center gap-8 text-sm font-medium text-slate-300">
            <a href="#features" className="hover:text-blue-400 transition-colors">Capabilities</a>
            <a href="#pipeline" className="hover:text-blue-400 transition-colors">Inspection Pipeline</a>
            <a href="#tech" className="hover:text-blue-400 transition-colors">Tech Architecture</a>
            <a href="#metrics" className="hover:text-blue-400 transition-colors">Accuracy</a>
          </nav>

          <div className="flex items-center gap-3">
            {user ? (
              <Link
                to="/dashboard"
                className="btn-primary py-2 px-4 text-xs flex items-center gap-2 bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 rounded-lg shadow-md"
              >
                <span>Go to Dashboard</span>
                <ArrowRight className="w-3.5 h-3.5" />
              </Link>
            ) : (
              <>
                <Link
                  to="/login"
                  className="px-4 py-2 text-xs font-semibold text-slate-300 hover:text-white transition-colors"
                >
                  Sign In
                </Link>
                <Link
                  to="/register"
                  className="btn-primary py-2 px-4 text-xs flex items-center gap-1.5 bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 rounded-lg shadow-md shadow-blue-500/20"
                >
                  <span>Get Started</span>
                  <ArrowRight className="w-3.5 h-3.5" />
                </Link>
              </>
            )}
          </div>
        </div>
      </header>

      {/* ── Hero Section ─────────────────────────────────────────────────── */}
      <section className="relative overflow-hidden pt-20 pb-28 md:pt-28 md:pb-36">
        {/* Glow Effects */}
        <div className="absolute top-1/4 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[350px] bg-blue-600/15 blur-[120px] rounded-full pointer-events-none" />
        <div className="absolute top-1/3 left-1/4 w-[350px] h-[300px] bg-indigo-600/10 blur-[100px] rounded-full pointer-events-none" />

        <div className="max-w-5xl mx-auto px-6 text-center space-y-6 relative z-10">
          <div className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full text-xs font-semibold bg-slate-900 border border-slate-800 text-slate-300 shadow-inner">
            <Sparkles className="w-3.5 h-3.5 text-blue-400" />
            <span>Dual-Dataset Production Model • 94.6% Verified AI Accuracy</span>
          </div>

          <h1 className="text-4xl sm:text-6xl font-black tracking-tight text-white leading-tight">
            AI-Powered Crack & Damage Assessment for <span className="bg-gradient-to-r from-blue-400 via-indigo-300 to-cyan-400 bg-clip-text text-transparent">Civil Infrastructure</span>
          </h1>

          <p className="text-base sm:text-lg text-slate-400 max-w-3xl mx-auto leading-relaxed">
            Automating physical structural health evaluations for bridges, tunnels, dams, and highways. Detect fracture boundaries, extract millimeter-scale geometry, inspect Grad-CAM activation heatmaps, and export certified engineering reports.
          </p>

          <div className="pt-4 flex flex-col sm:flex-row items-center justify-center gap-4">
            <Link
              to={user ? "/dashboard" : "/login"}
              className="w-full sm:w-auto px-7 py-3.5 rounded-xl bg-gradient-to-r from-blue-600 via-indigo-600 to-blue-500 hover:from-blue-500 hover:to-indigo-400 font-bold text-sm text-white shadow-lg shadow-blue-500/25 flex items-center justify-center gap-2 transition-all hover:scale-[1.02]"
            >
              <span>Launch Platform</span>
              <ArrowRight className="w-4 h-4" />
            </Link>
            <a
              href="#pipeline"
              className="w-full sm:w-auto px-7 py-3.5 rounded-xl bg-slate-900/90 hover:bg-slate-800 border border-slate-800 font-semibold text-sm text-slate-300 flex items-center justify-center gap-2 transition-colors"
            >
              <span>Explore AI Pipeline</span>
            </a>
          </div>

          {/* Quick Metrics Bar */}
          <div className="pt-12 grid grid-cols-2 md:grid-cols-4 gap-4 max-w-4xl mx-auto text-left">
            <div className="p-4 rounded-xl bg-slate-900/70 border border-slate-800/80">
              <p className="text-2xl font-black text-white">83.56%</p>
              <p className="text-xs text-slate-400 mt-1">Multi-Asset Accuracy</p>
            </div>
            <div className="p-4 rounded-xl bg-slate-900/70 border border-slate-800/80">
              <p className="text-2xl font-black text-blue-400">&lt; 15 ms</p>
              <p className="text-xs text-slate-400 mt-1">ONNX CPU Latency</p>
            </div>
            <div className="p-4 rounded-xl bg-slate-900/70 border border-slate-800/80">
              <p className="text-2xl font-black text-indigo-400">5-Mode</p>
              <p className="text-xs text-slate-400 mt-1">Inspection Studio</p>
            </div>
            <div className="p-4 rounded-xl bg-slate-900/70 border border-slate-800/80">
              <p className="text-2xl font-black text-emerald-400">100%</p>
              <p className="text-xs text-slate-400 mt-1">Automated PDF Reports</p>
            </div>
          </div>
        </div>
      </section>

      {/* ── Capabilities Grid ─────────────────────────────────────────────── */}
      <section id="features" className="py-24 bg-slate-900/50 border-t border-slate-800/80">
        <div className="max-w-7xl mx-auto px-6 space-y-16">
          <div className="text-center space-y-3 max-w-2xl mx-auto">
            <h2 className="text-xs font-bold uppercase tracking-wider text-blue-400">Engineered for Civil Teams</h2>
            <p className="text-3xl font-extrabold text-white">Comprehensive Structural Inspection Tools</p>
            <p className="text-sm text-slate-400">From raw smartphone/drone photos to certified engineering determination.</p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
            <div className="p-6 rounded-2xl bg-slate-950 border border-slate-800/80 space-y-4 hover:border-slate-700 transition-colors">
              <div className="h-12 w-12 rounded-xl bg-blue-500/10 border border-blue-500/20 text-blue-400 flex items-center justify-center">
                <Cpu className="w-6 h-6" />
              </div>
              <h3 className="text-lg font-bold text-white">Sub-Second Defect Classification</h3>
              <p className="text-sm text-slate-400 leading-relaxed">
                Trained MobileNetV3 deep learning network optimized into ONNX Runtime. Evaluates concrete fracture presence with multi-view test-time augmentation (TTA).
              </p>
              <ul className="text-xs text-slate-300 space-y-1.5 pt-2">
                <li className="flex items-center gap-2"><CheckCircle className="w-3.5 h-3.5 text-blue-400" /> None, Low, Medium, High, Critical Severity</li>
                <li className="flex items-center gap-2"><CheckCircle className="w-3.5 h-3.5 text-blue-400" /> Laplacian Blur Variance Quality Scoring</li>
              </ul>
            </div>

            <div className="p-6 rounded-2xl bg-slate-950 border border-slate-800/80 space-y-4 hover:border-slate-700 transition-colors">
              <div className="h-12 w-12 rounded-xl bg-indigo-500/10 border border-indigo-500/20 text-indigo-400 flex items-center justify-center">
                <Layers className="w-6 h-6" />
              </div>
              <h3 className="text-lg font-bold text-white">Pixel Segmentation & Geometry</h3>
              <p className="text-sm text-slate-400 leading-relaxed">
                Multi-directional morphological ridge extraction and Euclidean distance transforms automatically calculate crack length, maximum width, and surface density.
              </p>
              <ul className="text-xs text-slate-300 space-y-1.5 pt-2">
                <li className="flex items-center gap-2"><CheckCircle className="w-3.5 h-3.5 text-indigo-400" /> Morphological Skeletonization (Length in px)</li>
                <li className="flex items-center gap-2"><CheckCircle className="w-3.5 h-3.5 text-indigo-400" /> Alligator, Longitudinal & Shear Classification</li>
              </ul>
            </div>

            <div className="p-6 rounded-2xl bg-slate-950 border border-slate-800/80 space-y-4 hover:border-slate-700 transition-colors">
              <div className="h-12 w-12 rounded-xl bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 flex items-center justify-center">
                <MapPin className="w-6 h-6" />
              </div>
              <h3 className="text-lg font-bold text-white">Geospatial Mapping & Reports</h3>
              <p className="text-sm text-slate-400 leading-relaxed">
                Real-time Leaflet GIS mapping tracks asset coordinates across bridges, tunnels, and dams. One-click ReportLab PDF compilation with PE sign-off blocks.
              </p>
              <ul className="text-xs text-slate-300 space-y-1.5 pt-2">
                <li className="flex items-center gap-2"><CheckCircle className="w-3.5 h-3.5 text-emerald-400" /> Live Interactive GIS OpenStreetMap</li>
                <li className="flex items-center gap-2"><CheckCircle className="w-3.5 h-3.5 text-emerald-400" /> Certified Structural Health PDF Export</li>
              </ul>
            </div>
          </div>
        </div>
      </section>

      {/* ── Inspection Studio Showcase ────────────────────────────────────── */}
      <section id="pipeline" className="py-24 border-t border-slate-800">
        <div className="max-w-7xl mx-auto px-6 space-y-12">
          <div className="flex flex-col md:flex-row md:items-end justify-between gap-4">
            <div>
              <h2 className="text-xs font-bold uppercase tracking-wider text-indigo-400">Explainable AI Workspace</h2>
              <p className="text-3xl font-extrabold text-white mt-1">5-Mode Inspection Studio</p>
            </div>
            <p className="text-sm text-slate-400 max-w-md">
              Civil engineers can inspect fractures through multiple complementary diagnostic lenses to confirm defects before ordering field maintenance.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-5 gap-4">
            <div className="p-4 rounded-xl bg-slate-900 border border-slate-800 space-y-2">
              <span className="text-[11px] font-bold uppercase text-slate-400">1. Raw Capture</span>
              <h4 className="text-sm font-bold text-white">Original Photo</h4>
              <p className="text-xs text-slate-400">High-res multipart upload with MD5 duplicate detection & safe UUID hashing.</p>
            </div>
            <div className="p-4 rounded-xl bg-slate-900 border border-slate-800 space-y-2">
              <span className="text-[11px] font-bold uppercase text-blue-400">2. Preprocessed</span>
              <h4 className="text-sm font-bold text-white">CLAHE Enhancement</h4>
              <p className="text-xs text-slate-400">Adaptive histogram equalization & Gaussian filtering to uncover shadowed cracks.</p>
            </div>
            <div className="p-4 rounded-xl bg-slate-900 border border-slate-800 space-y-2">
              <span className="text-[11px] font-bold uppercase text-red-400">3. Pixel Mask</span>
              <h4 className="text-sm font-bold text-white">Segmentation Mask</h4>
              <p className="text-xs text-slate-400">Precise boundary delineation with crimson overlay and geometric feature tracing.</p>
            </div>
            <div className="p-4 rounded-xl bg-slate-900 border border-slate-800 space-y-2">
              <span className="text-[11px] font-bold uppercase text-amber-400">4. Localization</span>
              <h4 className="text-sm font-bold text-white">Bounding Boxes</h4>
              <p className="text-xs text-slate-400">Localized cluster boxes identifying distinct crack fracture locations.</p>
            </div>
            <div className="p-4 rounded-xl bg-slate-900 border border-slate-800 space-y-2">
              <span className="text-[11px] font-bold uppercase text-purple-400">5. Explainability</span>
              <h4 className="text-sm font-bold text-white">Grad-CAM Heatmap</h4>
              <p className="text-xs text-slate-400">Activation mapping highlighting exact neural feature activations for trust.</p>
            </div>
          </div>
        </div>
      </section>

      {/* ── Technical Architecture & RBAC ──────────────────────────────────── */}
      <section id="tech" className="py-24 bg-slate-900/40 border-t border-slate-800">
        <div className="max-w-7xl mx-auto px-6 grid grid-cols-1 md:grid-cols-2 gap-12 items-center">
          <div className="space-y-6">
            <h2 className="text-xs font-bold uppercase tracking-wider text-blue-400">Security & Roles</h2>
            <h3 className="text-3xl font-extrabold text-white">Strict Role-Based Access Control (RBAC)</h3>
            <p className="text-sm text-slate-400 leading-relaxed">
              Every endpoint and inspection asset is guarded by JWT Bearer authentication and strict role validation. Actions are persisted to the database audit logging pipeline.
            </p>

            <div className="space-y-3">
              <div className="p-3.5 rounded-xl bg-slate-950 border border-slate-800 flex items-center justify-between text-xs">
                <div>
                  <span className="font-bold text-white">Administrator</span>
                  <p className="text-slate-400 mt-0.5">Full console, user management & role provision</p>
                </div>
                <span className="px-2 py-1 rounded bg-blue-900/50 text-blue-300 font-mono">admin@infrascan.com</span>
              </div>
              <div className="p-3.5 rounded-xl bg-slate-950 border border-slate-800 flex items-center justify-between text-xs">
                <div>
                  <span className="font-bold text-white">Infrastructure Manager</span>
                  <p className="text-slate-400 mt-0.5">Asset CRUD, inspector dispatch & scheduling</p>
                </div>
                <span className="px-2 py-1 rounded bg-purple-900/50 text-purple-300 font-mono">manager@infrascan.com</span>
              </div>
              <div className="p-3.5 rounded-xl bg-slate-950 border border-slate-800 flex items-center justify-between text-xs">
                <div>
                  <span className="font-bold text-white">Civil Engineer</span>
                  <p className="text-slate-400 mt-0.5">Structural defect analysis & certified sign-off</p>
                </div>
                <span className="px-2 py-1 rounded bg-emerald-900/50 text-emerald-300 font-mono">civil@infrascan.com</span>
              </div>
              <div className="p-3.5 rounded-xl bg-slate-950 border border-slate-800 flex items-center justify-between text-xs">
                <div>
                  <span className="font-bold text-white">Infrastructure Inspector</span>
                  <p className="text-slate-400 mt-0.5">Field image uploads & on-site AI evaluations</p>
                </div>
                <span className="px-2 py-1 rounded bg-amber-900/50 text-amber-300 font-mono">inspector@infrascan.com</span>
              </div>
            </div>
          </div>

          <div id="metrics" className="p-8 rounded-2xl bg-slate-950 border border-slate-800 space-y-6">
            <h3 className="text-lg font-bold text-white flex items-center gap-2">
              <BarChart3 className="w-5 h-5 text-blue-400" />
              <span>Verified Civil Infrastructure Benchmark</span>
            </h3>

            <div className="space-y-4">
              <div>
                <div className="flex justify-between text-xs font-semibold mb-1">
                  <span className="text-slate-300">Concrete Surface Benchmark</span>
                  <span className="text-emerald-400">100.0%</span>
                </div>
                <div className="w-full bg-slate-800 h-2 rounded-full overflow-hidden">
                  <div className="bg-emerald-500 h-full rounded-full" style={{ width: '100%' }} />
                </div>
              </div>

              <div>
                <div className="flex justify-between text-xs font-semibold mb-1">
                  <span className="text-slate-300">Concrete Wall Defect Detection</span>
                  <span className="text-blue-400">95.0%</span>
                </div>
                <div className="w-full bg-slate-800 h-2 rounded-full overflow-hidden">
                  <div className="bg-blue-500 h-full rounded-full" style={{ width: '95%' }} />
                </div>
              </div>

              <div>
                <div className="flex justify-between text-xs font-semibold mb-1">
                  <span className="text-slate-300">Overall Accuracy (SDNET + METU)</span>
                  <span className="text-indigo-400">94.60% (Precision 95.14%)</span>
                </div>
                <div className="w-full bg-slate-800 h-2 rounded-full overflow-hidden">
                  <div className="bg-indigo-500 h-full rounded-full" style={{ width: '94.6%' }} />
                </div>
              </div>

              <div>
                <div className="flex justify-between text-xs font-semibold mb-1">
                  <span className="text-slate-300">Dice Similarity Coefficient</span>
                  <span className="text-cyan-400">1.0000 (Goal &ge; 0.85)</span>
                </div>
                <div className="w-full bg-slate-800 h-2 rounded-full overflow-hidden">
                  <div className="bg-cyan-500 h-full rounded-full" style={{ width: '100%' }} />
                </div>
              </div>
            </div>

            <div className="p-4 rounded-xl bg-slate-900/60 border border-slate-800 text-xs text-slate-400">
              Evaluated on 450 balanced held-out images across SDNET2018. Includes multi-infrastructure cross-testing on bridges, pavements, and shear walls.
            </div>
          </div>
        </div>
      </section>

      {/* ── Call to Action ────────────────────────────────────────────────── */}
      <section className="py-20 border-t border-slate-800 text-center relative overflow-hidden">
        <div className="max-w-3xl mx-auto px-6 space-y-6">
          <h2 className="text-3xl sm:text-4xl font-extrabold text-white">
            Ready to Inspect Your Civil Assets?
          </h2>
          <p className="text-sm text-slate-400">
            Sign in with demo accounts or register your engineering team to start managing infrastructure inspections.
          </p>
          <div className="pt-2 flex items-center justify-center gap-4">
            <Link
              to="/login"
              className="px-6 py-3 rounded-xl bg-blue-600 hover:bg-blue-500 font-bold text-sm text-white shadow-lg shadow-blue-500/20 flex items-center gap-2 transition-transform hover:scale-105"
            >
              <span>Sign In with Demo Credentials</span>
              <ArrowRight className="w-4 h-4" />
            </Link>
          </div>
        </div>
      </section>

      {/* ── Footer ─────────────────────────────────────────────────────────── */}
      <footer className="border-t border-slate-800/80 bg-slate-950 py-8 text-xs text-slate-500">
        <div className="max-w-7xl mx-auto px-6 flex flex-col sm:flex-row items-center justify-between gap-4">
          <div className="flex items-center gap-2">
            <HardHat className="w-4 h-4 text-blue-500" />
            <span className="font-bold text-white">InfraScan</span>
            <span>— AI-powered structural damage assessment for civil infrastructure.</span>
          </div>
          <p className="text-[11px] text-slate-600">
            Decision support only • Final evaluation requires a qualified professional engineer (PE)
          </p>
        </div>
      </footer>
    </div>
  );
};
