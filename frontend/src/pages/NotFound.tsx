import React from 'react'
import { Link } from 'react-router-dom'
import { Navbar } from '../components/Navbar'

export const NotFound: React.FC = () => {
  return (
    <div className="min-h-screen bg-slate-50 flex flex-col">
      <Navbar />
      <div className="flex-1 flex items-center justify-center p-4">
        <div className="max-w-md w-full text-center bg-white rounded-xl shadow-sm border border-slate-200 p-8">
          <div className="text-6xl font-extrabold text-indigo-600 mb-2">404</div>
          <h1 className="text-xl font-bold text-gray-900 mb-2">Page Not Found</h1>
          <p className="text-sm text-gray-600 mb-6">
            The screen or resource you requested does not exist or may have been relocated.
          </p>

          <div className="space-y-2">
            <Link
              to="/dashboard"
              className="block w-full px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white text-sm font-semibold rounded-lg shadow transition"
            >
              Return to Dashboard
            </Link>
            <Link
              to="/assets"
              className="block w-full px-4 py-2 bg-slate-100 hover:bg-slate-200 text-slate-800 text-sm font-semibold rounded-lg transition"
            >
              View Assets Registry
            </Link>
          </div>
        </div>
      </div>
    </div>
  )
}
export default NotFound
