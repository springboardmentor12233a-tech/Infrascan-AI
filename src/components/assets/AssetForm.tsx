import { useEffect, useRef } from 'react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import L from 'leaflet'
import { INFRASTRUCTURE_TYPES } from '@/lib/constants'
import { MOCK_USERS } from '@/data/mockData'
import type { InfrastructureAsset, InfrastructureType } from '@/types'

const MATERIALS = [
  'Reinforced Concrete',
  'Plain Concrete',
  'Steel',
  'Asphalt',
  'Masonry',
  'Brick',
  'Stone',
  'Composite',
  'Other',
]

const assetSchema = z.object({
  name: z.string().min(3, 'Infrastructure name is required (min 3 chars)'),
  type: z.enum([
    'Bridge',
    'Building',
    'Road',
    'Tunnel',
    'Dam',
    'Concrete Structure',
    'Retaining Wall',
    'Industrial Structure',
  ]),
  description: z.string().optional(),
  constructionYear: z.coerce.number().min(1850, 'Enter valid year').max(2030, 'Enter valid year'),
  operationalStatus: z.enum(['Active', 'Inactive', 'Under Maintenance', 'Archived']),
  country: z.string().min(2, 'Country is required'),
  state: z.string().min(2, 'State is required'),
  district: z.string().optional(),
  city: z.string().min(2, 'City is required'),
  address: z.string().optional(),
  postalCode: z.string().optional(),
  latitude: z.coerce.number().min(-90).max(90),
  longitude: z.coerce.number().min(-180).max(180),
  materialType: z.string().min(1, 'Primary material is required'),
  secondaryMaterial: z.string().optional(),
  structuralSystem: z.string().optional(),
  floors: z.coerce.number().optional(),
  lengthMeters: z.coerce.number().optional(),
  widthMeters: z.coerce.number().optional(),
  heightMeters: z.coerce.number().optional(),
  responsibleDepartment: z.string().min(2, 'Department is required'),
  owner: z.string().optional(),
  contactPerson: z.string().optional(),
  contactEmail: z.string().email('Enter valid email').optional().or(z.literal('')),
  contactNumber: z.string().optional(),
  assignedInspector: z.string().optional(),
  inspectionFrequency: z.enum(['Monthly', 'Quarterly', 'Half-Yearly', 'Semi-Annual', 'Annual', 'Annually', 'Custom']),
  lastInspectionDate: z.string().optional(),
  nextInspectionDate: z.string().optional(),
  inspectionPriority: z.string().optional(),
  maintenanceNotes: z.string().optional(),
})

export type AssetFormValues = z.infer<typeof assetSchema>

interface AssetFormProps {
  initialData?: InfrastructureAsset
  onSubmit: (values: AssetFormValues, asDraft?: boolean) => void
  onCancel: () => void
  isSubmitting?: boolean
}

export function AssetForm({ initialData, onSubmit, onCancel, isSubmitting }: AssetFormProps) {
  const mapRef = useRef<HTMLDivElement>(null)
  const leafletMap = useRef<L.Map | null>(null)
  const markerRef = useRef<L.CircleMarker | null>(null)

  const {
    register,
    handleSubmit,
    watch,
    setValue,
    formState: { errors },
  } = useForm<AssetFormValues>({
    resolver: zodResolver(assetSchema) as never,
    defaultValues: {
      name: initialData?.name || '',
      type: (initialData?.type as InfrastructureType) || 'Bridge',
      description: initialData?.description || '',
      constructionYear: initialData?.constructionYear || 2015,
      operationalStatus: initialData?.operationalStatus || 'Active',
      country: initialData?.country || 'India',
      state: initialData?.state || 'Tamil Nadu',
      district: initialData?.district || 'Coimbatore',
      city: initialData?.city || 'Coimbatore',
      address: initialData?.address || initialData?.location || '',
      postalCode: initialData?.postalCode || '641001',
      latitude: initialData?.coordinates?.[0] ?? 11.0168,
      longitude: initialData?.coordinates?.[1] ?? 76.9558,
      materialType: initialData?.materialType || 'Reinforced Concrete',
      secondaryMaterial: initialData?.secondaryMaterial || '',
      structuralSystem: initialData?.structuralSystem || 'Box Girder / Pier',
      floors: initialData?.floors,
      lengthMeters: initialData?.lengthMeters,
      widthMeters: initialData?.widthMeters,
      heightMeters: initialData?.heightMeters,
      responsibleDepartment: initialData?.responsibleDepartment || 'Structural Bridges Division',
      owner: initialData?.owner || 'State Highways Authority',
      contactPerson: initialData?.contactPerson || 'Elena Vance, PE',
      contactEmail: initialData?.contactEmail || 'elena.vance@infrascan.io',
      contactNumber: initialData?.contactNumber || '+91 98765 43210',
      assignedInspector: initialData?.assignedInspector || MOCK_USERS[0].name,
      inspectionFrequency: initialData?.inspectionFrequency || 'Quarterly',
      lastInspectionDate: initialData?.lastInspectionDate || new Date().toISOString().slice(0, 10),
      nextInspectionDate: initialData?.nextInspectionDate || '2027-02-25',
      inspectionPriority: initialData?.inspectionPriority || 'High Priority',
      maintenanceNotes: initialData?.maintenanceNotes || '',
    },
  })

  const selectedType = watch('type')
  const lat = watch('latitude')
  const lng = watch('longitude')

  useEffect(() => {
    if (!mapRef.current || leafletMap.current) return
    const map = L.map(mapRef.current).setView([lat || 11.0168, lng || 76.9558], 12)
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
      attribution: '&copy; OpenStreetMap',
    }).addTo(map)

    const marker = L.circleMarker([lat || 11.0168, lng || 76.9558], {
      radius: 9,
      fillColor: '#0891B2',
      color: '#FFFFFF',
      weight: 2,
      fillOpacity: 0.9,
    }).addTo(map)

    map.on('click', (e: L.LeafletMouseEvent) => {
      setValue('latitude', Number(e.latlng.lat.toFixed(5)))
      setValue('longitude', Number(e.latlng.lng.toFixed(5)))
    })

    leafletMap.current = map
    markerRef.current = marker
    return () => {
      map.remove()
      leafletMap.current = null
    }
  }, [])

  useEffect(() => {
    if (leafletMap.current && markerRef.current && !Number.isNaN(lat) && !Number.isNaN(lng)) {
      markerRef.current.setLatLng([lat, lng])
      leafletMap.current.setView([lat, lng])
    }
  }, [lat, lng])

  const inputCls = 'w-full px-3 py-2 text-xs border border-slate-300 rounded-md focus:outline-none focus:border-cyan-600 bg-white'
  const labelCls = 'block text-xs font-medium text-slate-700 mb-1'

  return (
    <form onSubmit={handleSubmit((v) => onSubmit(v, false))} className="space-y-6">
      {/* SECTION A: BASIC INFORMATION */}
      <div className="bg-white rounded-lg border border-slate-200 p-5 space-y-4">
        <h2 className="text-sm font-semibold text-slate-900 border-b border-slate-100 pb-2">
          Section A: Basic Information
        </h2>
        <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
          <div className="sm:col-span-2">
            <label className={labelCls}>Infrastructure Name *</label>
            <input {...register('name')} placeholder="e.g., Coimbatore Central Bridge" className={inputCls} />
            {errors.name && <p className="text-[11px] text-red-600 mt-1">{errors.name.message}</p>}
          </div>
          <div>
            <label className={labelCls}>Infrastructure Type *</label>
            <select {...register('type')} className={inputCls}>
              {INFRASTRUCTURE_TYPES.map((t) => (
                <option key={t} value={t}>{t}</option>
              ))}
            </select>
          </div>
          <div>
            <label className={labelCls}>Construction Year *</label>
            <input type="number" {...register('constructionYear')} className={inputCls} />
            {errors.constructionYear && <p className="text-[11px] text-red-600 mt-1">{errors.constructionYear.message}</p>}
          </div>
          <div>
            <label className={labelCls}>Operational Status</label>
            <select {...register('operationalStatus')} className={inputCls}>
              <option value="Active">Active</option>
              <option value="Inactive">Inactive</option>
              <option value="Under Maintenance">Under Maintenance</option>
              <option value="Archived">Archived</option>
            </select>
          </div>
          <div className="sm:col-span-2 lg:col-span-3">
            <label className={labelCls}>Description</label>
            <textarea rows={2} {...register('description')} className={inputCls} placeholder="Brief structural overview..." />
          </div>
        </div>
      </div>

      {/* SECTION B: LOCATION INFORMATION */}
      <div className="bg-white rounded-lg border border-slate-200 p-5 space-y-4">
        <h2 className="text-sm font-semibold text-slate-900 border-b border-slate-100 pb-2">
          Section B: Location Information
        </h2>
        <div className="grid lg:grid-cols-12 gap-5">
          <div className="lg:col-span-7 grid sm:grid-cols-2 gap-3.5">
            <div>
              <label className={labelCls}>Country *</label>
              <input {...register('country')} className={inputCls} />
            </div>
            <div>
              <label className={labelCls}>State *</label>
              <input {...register('state')} className={inputCls} />
            </div>
            <div>
              <label className={labelCls}>District</label>
              <input {...register('district')} className={inputCls} />
            </div>
            <div>
              <label className={labelCls}>City *</label>
              <input {...register('city')} className={inputCls} />
            </div>
            <div className="sm:col-span-2">
              <label className={labelCls}>Address</label>
              <input {...register('address')} className={inputCls} />
            </div>
            <div>
              <label className={labelCls}>Latitude</label>
              <input type="number" step="any" {...register('latitude')} className={inputCls} />
            </div>
            <div>
              <label className={labelCls}>Longitude</label>
              <input type="number" step="any" {...register('longitude')} className={inputCls} />
            </div>
          </div>
          <div className="lg:col-span-5">
            <p className="text-[11px] text-slate-500 mb-1.5">Click map to set demonstration coordinates</p>
            <div ref={mapRef} className="h-56 w-full rounded-md border border-slate-200" />
          </div>
        </div>
      </div>

      {/* SECTION C: STRUCTURAL INFORMATION */}
      <div className="bg-white rounded-lg border border-slate-200 p-5 space-y-4">
        <h2 className="text-sm font-semibold text-slate-900 border-b border-slate-100 pb-2">
          Section C: Structural Information
        </h2>
        <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <div>
            <label className={labelCls}>Primary Material *</label>
            <select {...register('materialType')} className={inputCls}>
              {MATERIALS.map((m) => (
                <option key={m} value={m}>{m}</option>
              ))}
            </select>
          </div>
          <div>
            <label className={labelCls}>Secondary Material</label>
            <select {...register('secondaryMaterial')} className={inputCls}>
              <option value="">None</option>
              {MATERIALS.map((m) => (
                <option key={m} value={m}>{m}</option>
              ))}
            </select>
          </div>
          <div>
            <label className={labelCls}>Structural System</label>
            <input {...register('structuralSystem')} className={inputCls} />
          </div>
          {(selectedType === 'Building' || selectedType === 'Industrial Structure') && (
            <div>
              <label className={labelCls}>Number of Floors</label>
              <input type="number" {...register('floors')} className={inputCls} />
            </div>
          )}
          <div>
            <label className={labelCls}>Approx. Length (m)</label>
            <input type="number" step="any" {...register('lengthMeters')} className={inputCls} />
          </div>
          <div>
            <label className={labelCls}>Approx. Width (m)</label>
            <input type="number" step="any" {...register('widthMeters')} className={inputCls} />
          </div>
          <div>
            <label className={labelCls}>Approx. Height (m)</label>
            <input type="number" step="any" {...register('heightMeters')} className={inputCls} />
          </div>
        </div>
      </div>

      {/* SECTION D: OWNERSHIP AND MANAGEMENT */}
      <div className="bg-white rounded-lg border border-slate-200 p-5 space-y-4">
        <h2 className="text-sm font-semibold text-slate-900 border-b border-slate-100 pb-2">
          Section D: Ownership & Management
        </h2>
        <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
          <div>
            <label className={labelCls}>Responsible Department *</label>
            <input {...register('responsibleDepartment')} className={inputCls} />
          </div>
          <div>
            <label className={labelCls}>Asset Owner</label>
            <input {...register('owner')} className={inputCls} />
          </div>
          <div>
            <label className={labelCls}>Assigned Inspector</label>
            <select {...register('assignedInspector')} className={inputCls}>
              {MOCK_USERS.map((u) => (
                <option key={u.id} value={u.name}>{u.name}</option>
              ))}
            </select>
          </div>
          <div>
            <label className={labelCls}>Contact Person</label>
            <input {...register('contactPerson')} className={inputCls} />
          </div>
          <div>
            <label className={labelCls}>Contact Email</label>
            <input type="email" {...register('contactEmail')} className={inputCls} />
            {errors.contactEmail && <p className="text-[11px] text-red-600 mt-1">{errors.contactEmail.message}</p>}
          </div>
          <div>
            <label className={labelCls}>Contact Number</label>
            <input {...register('contactNumber')} className={inputCls} />
          </div>
        </div>
      </div>

      {/* SECTION E: INSPECTION CONFIGURATION */}
      <div className="bg-white rounded-lg border border-slate-200 p-5 space-y-4">
        <h2 className="text-sm font-semibold text-slate-900 border-b border-slate-100 pb-2">
          Section E: Inspection Configuration
        </h2>
        <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <div>
            <label className={labelCls}>Inspection Frequency</label>
            <select {...register('inspectionFrequency')} className={inputCls}>
              <option value="Monthly">Monthly</option>
              <option value="Quarterly">Quarterly</option>
              <option value="Half-Yearly">Half-Yearly</option>
              <option value="Annually">Annually</option>
              <option value="Custom">Custom</option>
            </select>
          </div>
          <div>
            <label className={labelCls}>Last Inspection Date</label>
            <input type="date" {...register('lastInspectionDate')} className={inputCls} />
          </div>
          <div>
            <label className={labelCls}>Next Scheduled Inspection</label>
            <input type="date" {...register('nextInspectionDate')} className={inputCls} />
          </div>
          <div>
            <label className={labelCls}>Inspection Priority</label>
            <select {...register('inspectionPriority')} className={inputCls}>
              <option value="Routine">Routine</option>
              <option value="Medium">Medium</option>
              <option value="High Priority">High Priority</option>
              <option value="Urgent">Urgent</option>
            </select>
          </div>
          <div className="sm:col-span-2 lg:col-span-4">
            <label className={labelCls}>Maintenance Notes</label>
            <textarea rows={2} {...register('maintenanceNotes')} className={inputCls} />
          </div>
        </div>
      </div>

      {/* Form Actions */}
      <div className="flex flex-wrap items-center justify-end gap-3">
        <button
          type="button"
          onClick={onCancel}
          className="px-4 py-2 rounded-md border border-slate-200 bg-white hover:bg-slate-50 text-xs font-medium text-slate-700"
        >
          Cancel
        </button>
        <button
          type="button"
          disabled={isSubmitting}
          onClick={handleSubmit((v) => onSubmit(v, true))}
          className="px-4 py-2 rounded-md border border-slate-300 bg-slate-100 hover:bg-slate-200 text-xs font-medium text-slate-800"
        >
          Save as Draft
        </button>
        <button
          type="submit"
          disabled={isSubmitting}
          className="px-5 py-2 rounded-md bg-[#0F2942] hover:bg-[#163859] text-white text-xs font-semibold"
        >
          {isSubmitting ? 'Saving...' : initialData ? 'Update Infrastructure' : 'Register Infrastructure'}
        </button>
      </div>
    </form>
  )
}

