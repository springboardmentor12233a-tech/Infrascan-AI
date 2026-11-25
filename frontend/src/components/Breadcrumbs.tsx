import React from 'react'
import { Link } from 'react-router-dom'

export interface BreadcrumbItem {
  label: string
  to?: string
}

interface BreadcrumbsProps {
  items: BreadcrumbItem[]
}

export const Breadcrumbs: React.FC<BreadcrumbsProps> = ({ items }) => {
  return (
    <nav className="flex items-center text-xs text-gray-500 mb-4 overflow-x-auto" aria-label="Breadcrumb">
      <Link to="/dashboard" className="hover:text-indigo-600 transition flex items-center">
        <svg className="w-3.5 h-3.5 mr-1" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth="2"
            d="M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6"
          />
        </svg>
        Home
      </Link>
      {items.map((item, idx) => (
        <React.Fragment key={idx}>
          <span className="mx-2 text-gray-400">/</span>
          {item.to ? (
            <Link to={item.to} className="hover:text-indigo-600 transition font-medium text-gray-600">
              {item.label}
            </Link>
          ) : (
            <span className="font-semibold text-gray-800 truncate max-w-xs">{item.label}</span>
          )}
        </React.Fragment>
      ))}
    </nav>
  )
}
export default Breadcrumbs
