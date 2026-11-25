import React from 'react'
import { Link, useLocation } from 'react-router-dom'
import { Navbar } from '../components/Navbar'

export const Forbidden: React.FC = () => {
  const location = useLocation()
  const allowedRoles = (location.state as any)?.allowedRoles as string[] | undefined

  return (
    <div className="min-h-screen bg-slate-50 flex flex-col">
      <Navbar />
      <div className="flex-1 flex items-center justify-center p-6">
        <div className="max-w-md w-full bg-white rounded-xl shadow-sm border border-slate-200 p-8 text-center">
          <div className="w-16 h-16 bg-rose-50 border border-rose-200 text-rose-600 rounded-full flex items-center justify-center mx-auto mb-4 text-2xl font-bold">
            403
          </div>
          <h1 className="text-xl font-bold text-slate-800 mb-2">Access Denied</h1>
          <p className="text-sm text-slate-600 mb-4">
            You do not have the required permissions to access this page.
          </p>
          {allowedRoles && allowedRoles.length > 0 && (
            <div className="bg-slate-50 rounded-lg p-3 text-xs text-slate-600 border border-slate-200 mb-6">
              Required role(s): <span className="font-semibold text-slate-800">{allowedRoles.join(', ')}</span>
            </div>
          )}
          <div className="flex gap-3 justify-center">
            <Link
              to="/dashboard"
              className="inline-flex items-center px-4 py-2 bg-indigo-600 text-white text-sm font-medium rounded-lg hover:bg-indigo-700 transition-colors shadow-sm"
            >
              Return to Dashboard
            </Link>
          </div>
        </div>
      </div>
    </div>
  )
}

export default Forbidden
