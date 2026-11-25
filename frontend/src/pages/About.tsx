import React from 'react'
import { Link } from 'react-router-dom'
import { Navbar } from '../components/Navbar'

export const About: React.FC = () => {
  return (
    <div className="min-h-screen bg-slate-50 flex flex-col">
      <Navbar />
      <div className="container mx-auto px-4 py-8 max-w-5xl flex-1">
        {/* Header */}
        <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-8 mb-6">
          <div className="flex items-center gap-3 mb-2">
            <span className="px-3 py-1 bg-indigo-100 text-indigo-800 text-xs font-semibold rounded-full uppercase">
              Production Release
            </span>
            <span className="text-xs text-gray-500">v1.0.0</span>
          </div>
          <h1 className="text-3xl font-extrabold text-gray-900 tracking-tight">About InfraScan</h1>
          <p className="text-base text-gray-600 mt-2 max-w-3xl">
            InfraScan is an enterprise civil infrastructure defect assessment platform combining computer vision,
            semantic segmentation, quantitative geometry, and explainable AI to assist structural engineers and municipal authorities.
          </p>
        </div>

        {/* Mandatory Safety Notice */}
        <div className="bg-amber-50 border-l-4 border-amber-400 p-4 mb-6 rounded-r shadow-sm">
          <h3 className="text-sm font-bold text-amber-900 uppercase tracking-wide">Mandatory Structural Safety Notice</h3>
          <p className="text-sm text-amber-800 mt-1 font-medium">
            AI result for engineer review, not a final structural safety verdict.
          </p>
          <p className="text-xs text-amber-700 mt-1">
            "No damage detected" is always defined as: <em>No damage detected by the AI. This is not evidence that there is no damage.</em> Qualified civil engineering review is required for all provisional findings.
          </p>
        </div>

        {/* Core Architecture Components */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-8">
          <div className="bg-white p-6 rounded-xl shadow-sm border border-slate-200">
            <div className="w-10 h-10 bg-blue-100 text-blue-700 rounded-lg flex items-center justify-center font-bold mb-3">
              DL
            </div>
            <h2 className="text-lg font-bold text-gray-900 mb-2">Deep Learning Models</h2>
            <ul className="text-sm text-gray-600 space-y-2 list-disc pl-5">
              <li>
                <strong>YOLOv8s (RDD2022)</strong>: Multi-class road distress detection (Longitudinal, Transverse, Alligator Cracks, Potholes).
              </li>
              <li>
                <strong>RT-DETR-L (CODEBRIM)</strong>: Real-time concrete bridge defect detection (Cracks, Spallation, Exposed Bars, Efflorescence, Corrosion).
              </li>
              <li>
                <strong>U-Net++ (Crack500)</strong>: ResNet-34 semantic segmentation with sub-pixel crack boundary extraction.
              </li>
              <li>
                <strong>ResNet-50 (SDNET2018)</strong>: Fast localized crop screening classifier.
              </li>
            </ul>
          </div>

          <div className="bg-white p-6 rounded-xl shadow-sm border border-slate-200">
            <div className="w-10 h-10 bg-indigo-100 text-indigo-700 rounded-lg flex items-center justify-center font-bold mb-3">
              XAI
            </div>
            <h2 className="text-lg font-bold text-gray-900 mb-2">Quantitative &amp; Explainable AI</h2>
            <ul className="text-sm text-gray-600 space-y-2 list-disc pl-5">
              <li>
                <strong>Sub-Pixel Geometry</strong>: Euclidean Distance Transform (EDT2), centerline thinning, width distribution, orientation profiling.
              </li>
              <li>
                <strong>Grad-CAM &amp; Grad-CAM++</strong>: Target activation heatmaps on encoder feature layers for segmentation.
              </li>
              <li>
                <strong>EigenCAM</strong>: Gradient-free attribution for object detection bounding boxes.
              </li>
              <li>
                <strong>Spatial Scale Calibration</strong>: Physical metric conversion (mm) with uncertainty estimation.
              </li>
            </ul>
          </div>
        </div>

        {/* Quick Links */}
        <div className="bg-white p-6 rounded-xl shadow-sm border border-slate-200 flex flex-wrap gap-4 items-center justify-between">
          <div>
            <h3 className="text-base font-bold text-gray-900">Explore Models &amp; User Manuals</h3>
            <p className="text-xs text-gray-500">Access dynamic model registry metrics or role-specific field workflows.</p>
          </div>
          <div className="flex gap-3">
            <Link
              to="/models"
              className="px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-semibold rounded-lg shadow transition"
            >
              Model Registry &rarr;
            </Link>
            <Link
              to="/help"
              className="px-4 py-2 bg-slate-100 hover:bg-slate-200 text-slate-800 text-xs font-semibold rounded-lg transition"
            >
              Role User Guides &rarr;
            </Link>
          </div>
        </div>
      </div>
    </div>
  )
}
export default About
