import React from 'react'
import { Link } from 'react-router-dom'
import { Navbar } from '../components/Navbar'
import { useAuth } from '../context/AuthContext'

export const Dashboard: React.FC = () => {
  const { user } = useAuth()

  return (
    <div className="min-h-screen bg-slate-50 flex flex-col">
      <Navbar />

      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Welcome Banner */}
        <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-6 md:p-8 mb-6">
          <h1 className="text-2xl md:text-3xl font-bold text-slate-800 tracking-tight">
            Welcome, {user?.full_name}{' '}
            <span className="text-indigo-600 font-medium text-xl md:text-2xl">
              ({user?.role})
            </span>
          </h1>
          <p className="text-sm text-slate-500 mt-2">
            You are signed in to the InfraScan Infrastructure Crack Detection platform.
          </p>
        </div>

        {/* Info Cards Grid */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {/* Account Details Card */}
          <div className="bg-white p-6 rounded-xl shadow-sm border border-slate-200">
            <h2 className="text-base font-semibold text-slate-800 mb-4">
              Your Account Details
            </h2>
            <div className="space-y-3 text-sm">
              <div>
                <span className="text-slate-400 block text-xs">Email</span>
                <span className="font-medium text-slate-700">{user?.email}</span>
              </div>
              <div>
                <span className="text-slate-400 block text-xs">Role</span>
                <span className="inline-block px-2 py-0.5 text-xs font-semibold rounded bg-indigo-50 text-indigo-700 uppercase">
                  {user?.role.replace('_', ' ')}
                </span>
              </div>
              <div>
                <span className="text-slate-400 block text-xs">Status</span>
                <span className="inline-flex items-center text-xs font-medium text-emerald-700">
                  <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 mr-1.5"></span>
                  Active
                </span>
              </div>
            </div>
            <div className="mt-5 pt-4 border-t border-slate-100">
              <Link
                to="/profile"
                className="text-xs text-indigo-600 hover:text-indigo-700 font-semibold"
              >
                Edit Profile or Change Password &rarr;
              </Link>
            </div>
          </div>

          {/* Role Scope Card */}
          <div className="bg-white p-6 rounded-xl shadow-sm border border-slate-200">
            <h2 className="text-base font-semibold text-slate-800 mb-4">
              Assigned Permissions
            </h2>
            <p className="text-xs text-slate-500 mb-3">
              Your capabilities in InfraScan are scoped by your role:
            </p>
            <ul className="text-xs text-slate-600 space-y-2 list-disc pl-4">
              {user?.role === 'admin' ? (
                <>
                  <li>Full system administration</li>
                  <li>Assign & modify user roles</li>
                  <li>Activate & deactivate user accounts</li>
                  <li>View user registry & audit history</li>
                </>
              ) : (
                <>
                  <li>Submit concrete and pavement inspection images</li>
                  <li>View AI crack segmentation results</li>
                  <li>Update personal profile details</li>
                </>
              )}
            </ul>
            {user?.role === 'admin' && (
              <div className="mt-5 pt-4 border-t border-slate-100">
                <Link
                  to="/users"
                  className="text-xs text-indigo-600 hover:text-indigo-700 font-semibold"
                >
                  Manage Users & Roles &rarr;
                </Link>
              </div>
            )}
          </div>

          {/* Quick Stats / System Status */}
          <div className="bg-white p-6 rounded-xl shadow-sm border border-slate-200">
            <h2 className="text-base font-semibold text-slate-800 mb-4">
              System Ready
            </h2>
            <p className="text-xs text-slate-500 mb-4">
              The AI Crack Detection pipeline and database are active and authenticated.
            </p>
            <div className="p-3 bg-emerald-50 border border-emerald-200 rounded-lg flex items-center space-x-2">
              <span className="w-2.5 h-2.5 rounded-full bg-emerald-500"></span>
              <span className="text-xs font-semibold text-emerald-800">
                FastAPI Backend Connected
              </span>
            </div>
          </div>
        </div>
      </main>
    </div>
  )
}
