import { useState, useRef } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { ArrowLeft, CheckCircle2, UploadCloud, Trash2, Building2 } from 'lucide-react'
import { MOCK_ASSETS, MOCK_USERS } from '@/data/mockData'
import { inspectionService } from '@/services/inspectionService'
import { StatusBadge } from '@/components/ui/StatusBadge'

const STEPS = [
  '1. Select Infrastructure',
  '2. Inspection Details',
  '3. Location',
  '4. Image Acquisition',
  '5. Review & Create',
]

export function InspectionWizardPage() {
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const fileRef = useRef<HTMLInputElement>(null)

  const [step, setStep] = useState(0)
  const [assetSearch, setAssetSearch] = useState('')
  const [selectedAssetId, setSelectedAssetId] = useState(MOCK_ASSETS[0].id)
  const [title, setTitle] = useState('')
  const [inspType, setInspType] = useState('Routine Inspection')
  const [date, setDate] = useState(new Date().toISOString().slice(0, 10))
  const [time, setTime] = useState('09:30')
  const [inspectorId, setInspectorId] = useState(MOCK_USERS[0].id)
  const [priority, setPriority] = useState('High')
  const [method, setMethod] = useState('Drone Inspection')
  const [objective, setObjective] = useState('')
  const [notes, setNotes] = useState('')
  const [uploadedFiles, setUploadedFiles] = useState<{ name: string; size: number; url: string }[]>([])

  const selectedAsset = MOCK_ASSETS.find((a) => a.id === selectedAssetId) || MOCK_ASSETS[0]
  const selectedInspector = MOCK_USERS.find((u) => u.id === inspectorId) || MOCK_USERS[0]

  const createMutation = useMutation({
    mutationFn: (asDraft: boolean) =>
      inspectionService.create({
        title: title || `${selectedAsset.name} — ${inspType}`,
        type: inspType,
        assetId: selectedAsset.id,
        assetName: selectedAsset.name,
        assetType: selectedAsset.type,
        inspectorId: selectedInspector.id,
        inspectorName: selectedInspector.name,
        date,
        time,
        priority,
        method,
        objective,
        location: selectedAsset.location,
        status: asDraft ? 'Draft' : 'Scheduled',
        imageCount: uploadedFiles.length,
        notes: notes || 'Scheduled via Inspection Creation Wizard.',
      }),
    onSuccess: (created) => {
      queryClient.invalidateQueries({ queryKey: ['inspections'] })
      navigate(`/app/inspections/${created.id}`)
    },
  })

  const handleFiles = (files: FileList | null) => {
    if (!files) return
    const valid = Array.from(files)
      .filter((f) => ['image/jpeg', 'image/png', 'image/webp'].includes(f.type))
      .map((f) => ({ name: f.name, size: f.size, url: URL.createObjectURL(f) }))
    setUploadedFiles((prev) => [...prev, ...valid])
  }

  return (
    <div className="space-y-5 max-w-5xl">
      <div>
        <Link to="/app/inspections" className="inline-flex items-center gap-1.5 text-xs text-slate-500 hover:text-slate-800 mb-2">
          <ArrowLeft className="w-3.5 h-3.5" /> Back to Inspections
        </Link>
        <h1 className="text-xl font-semibold text-slate-900">Create New Inspection</h1>
        <p className="text-xs text-slate-500 mt-0.5">5-step structured inspection scheduling & image acquisition workflow</p>
      </div>

      {/* Progress Stepper */}
      <div className="grid grid-cols-2 sm:grid-cols-5 gap-2">
        {STEPS.map((label, idx) => (
          <button
            key={label}
            type="button"
            onClick={() => setStep(idx)}
            className={`p-2.5 rounded-md border text-left text-xs font-medium transition-colors ${
              step === idx
                ? 'bg-[#0F2942] text-white border-[#0F2942]'
                : idx < step
                ? 'bg-cyan-50 text-cyan-900 border-cyan-200'
                : 'bg-white text-slate-500 border-slate-200'
            }`}
          >
            {label}
          </button>
        ))}
      </div>

      {/* Step Content */}
      <div className="bg-white rounded-lg border border-slate-200 p-6 space-y-5">
        {step === 0 && (
          <div className="space-y-4">
            <div className="flex items-center justify-between gap-3">
              <input
                type="text"
                value={assetSearch}
                onChange={(e) => setAssetSearch(e.target.value)}
                placeholder="Search registered infrastructure by ID or name..."
                className="flex-1 px-3 py-2 text-xs border border-slate-300 rounded-md"
              />
              <Link to="/app/assets/new" className="text-xs font-medium text-cyan-700 hover:underline shrink-0">
                + Register New Asset
              </Link>
            </div>
            <div className="grid sm:grid-cols-2 gap-3">
              {MOCK_ASSETS.filter(
                (a) =>
                  a.name.toLowerCase().includes(assetSearch.toLowerCase()) ||
                  a.id.toLowerCase().includes(assetSearch.toLowerCase())
              ).map((asset) => (
                <button
                  key={asset.id}
                  type="button"
                  onClick={() => setSelectedAssetId(asset.id)}
                  className={`text-left p-4 rounded-lg border transition-colors ${
                    selectedAssetId === asset.id
                      ? 'border-cyan-600 bg-cyan-50/50 ring-1 ring-cyan-600'
                      : 'border-slate-200 hover:border-slate-300'
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <span className="font-mono text-xs font-semibold text-slate-700">{asset.id}</span>
                    <StatusBadge status={asset.status} />
                  </div>
                  <p className="text-sm font-semibold text-slate-900 mt-1 flex items-center gap-1.5">
                    <Building2 className="w-3.5 h-3.5 text-cyan-700" /> {asset.name}
                  </p>
                  <p className="text-xs text-slate-500 mt-1">
                    {asset.type} · {asset.materialType} · {asset.location}
                  </p>
                </button>
              ))}
            </div>
          </div>
        )}

        {step === 1 && (
          <div className="grid sm:grid-cols-2 gap-4 text-xs">
            <div className="sm:col-span-2">
              <label className="block font-medium text-slate-700 mb-1">Inspection Title</label>
              <input
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                placeholder={`${selectedAsset.name} — ${inspType}`}
                className="w-full px-3 py-2 border border-slate-300 rounded-md"
              />
            </div>
            <div>
              <label className="block font-medium text-slate-700 mb-1">Inspection Type</label>
              <select value={inspType} onChange={(e) => setInspType(e.target.value)} className="w-full px-3 py-2 border border-slate-300 rounded-md bg-white">
                <option>Routine Inspection</option>
                <option>Detailed Inspection</option>
                <option>Damage Assessment</option>
                <option>Follow-up Inspection</option>
                <option>Emergency Inspection</option>
              </select>
            </div>
            <div>
              <label className="block font-medium text-slate-700 mb-1">Assigned Inspector</label>
              <select value={inspectorId} onChange={(e) => setInspectorId(e.target.value)} className="w-full px-3 py-2 border border-slate-300 rounded-md bg-white">
                {MOCK_USERS.map((u) => (
                  <option key={u.id} value={u.id}>{u.name} ({u.role})</option>
                ))}
              </select>
            </div>
            <div>
              <label className="block font-medium text-slate-700 mb-1">Inspection Date</label>
              <input type="date" value={date} onChange={(e) => setDate(e.target.value)} className="w-full px-3 py-2 border border-slate-300 rounded-md" />
            </div>
            <div>
              <label className="block font-medium text-slate-700 mb-1">Inspection Time</label>
              <input type="time" value={time} onChange={(e) => setTime(e.target.value)} className="w-full px-3 py-2 border border-slate-300 rounded-md" />
            </div>
            <div>
              <label className="block font-medium text-slate-700 mb-1">Priority</label>
              <select value={priority} onChange={(e) => setPriority(e.target.value)} className="w-full px-3 py-2 border border-slate-300 rounded-md bg-white">
                <option>Low</option>
                <option>Medium</option>
                <option>High</option>
                <option>Urgent Engineering Review</option>
              </select>
            </div>
            <div>
              <label className="block font-medium text-slate-700 mb-1">Method</label>
              <select value={method} onChange={(e) => setMethod(e.target.value)} className="w-full px-3 py-2 border border-slate-300 rounded-md bg-white">
                <option>Visual Inspection</option>
                <option>Camera Inspection</option>
                <option>Drone Inspection</option>
                <option>Manual Engineering Inspection</option>
              </select>
            </div>
            <div className="sm:col-span-2">
              <label className="block font-medium text-slate-700 mb-1">Objective & Notes</label>
              <textarea rows={3} value={objective} onChange={(e) => setObjective(e.target.value)} className="w-full px-3 py-2 border border-slate-300 rounded-md" />
            </div>
          </div>
        )}

        {step === 2 && (
          <div className="space-y-4 text-xs">
            <div className="grid sm:grid-cols-2 gap-4">
              <div>
                <label className="block font-medium text-slate-700 mb-1">Infrastructure Location</label>
                <input disabled value={selectedAsset.location} className="w-full px-3 py-2 border border-slate-200 rounded-md bg-slate-50" />
              </div>
              <div>
                <label className="block font-medium text-slate-700 mb-1">Demo Coordinates</label>
                <input
                  disabled
                  value={`${selectedAsset.coordinates[0].toFixed(4)}, ${selectedAsset.coordinates[1].toFixed(4)}`}
                  className="w-full px-3 py-2 border border-slate-200 rounded-md bg-slate-50 font-mono"
                />
              </div>
            </div>
            <div>
              <label className="block font-medium text-slate-700 mb-1">Location Access Notes</label>
              <textarea rows={3} value={notes} onChange={(e) => setNotes(e.target.value)} placeholder="Access gates, traffic control, or UAV launch zone notes..." className="w-full px-3 py-2 border border-slate-300 rounded-md" />
            </div>
          </div>
        )}

        {step === 3 && (
          <div className="space-y-4 text-xs">
            <div
              onClick={() => fileRef.current?.click()}
              onDragOver={(e) => e.preventDefault()}
              onDrop={(e) => {
                e.preventDefault()
                handleFiles(e.dataTransfer.files)
              }}
              className="border-2 border-dashed border-slate-300 hover:border-cyan-600 rounded-lg p-8 text-center cursor-pointer bg-slate-50/70"
            >
              <UploadCloud className="w-8 h-8 text-cyan-700 mx-auto mb-2" />
              <p className="font-medium text-slate-800">Drag & drop inspection photographs here, or click to browse</p>
              <p className="text-slate-500 mt-1">Supported: JPG, JPEG, PNG, WEBP (Optional — can be uploaded later)</p>
              <input ref={fileRef} type="file" multiple accept="image/jpeg,image/png,image/webp" className="hidden" onChange={(e) => handleFiles(e.target.files)} />
            </div>
            {uploadedFiles.length > 0 && (
              <div className="grid sm:grid-cols-3 gap-3">
                {uploadedFiles.map((f, idx) => (
                  <div key={idx} className="border border-slate-200 rounded-md p-2 flex items-center justify-between gap-2">
                    <div className="flex items-center gap-2 min-w-0">
                      <img src={f.url} alt={f.name} className="w-10 h-10 object-cover rounded" />
                      <span className="truncate font-mono text-[11px]">{f.name}</span>
                    </div>
                    <button
                      type="button"
                      onClick={() => setUploadedFiles((prev) => prev.filter((_, i) => i !== idx))}
                      className="text-slate-400 hover:text-red-600 p-1"
                    >
                      <Trash2 className="w-3.5 h-3.5" />
                    </button>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {step === 4 && (
          <div className="space-y-4 text-xs">
            <div className="p-4 rounded-md bg-slate-50 border border-slate-200 grid sm:grid-cols-2 gap-3">
              <div><span className="text-slate-500">Infrastructure:</span> <span className="font-semibold">{selectedAsset.name} ({selectedAsset.id})</span></div>
              <div><span className="text-slate-500">Inspection Type:</span> <span className="font-semibold">{inspType}</span></div>
              <div><span className="text-slate-500">Inspector:</span> <span className="font-semibold">{selectedInspector.name}</span></div>
              <div><span className="text-slate-500">Date & Time:</span> <span className="font-semibold">{date} at {time}</span></div>
              <div><span className="text-slate-500">Priority:</span> <span className="font-semibold">{priority}</span></div>
              <div><span className="text-slate-500">Uploaded Images:</span> <span className="font-semibold">{uploadedFiles.length}</span></div>
            </div>
          </div>
        )}

        {/* Navigation Buttons */}
        <div className="pt-4 border-t border-slate-200 flex items-center justify-between">
          <button
            type="button"
            disabled={step === 0}
            onClick={() => setStep((s) => s - 1)}
            className="px-4 py-2 border border-slate-200 rounded-md text-xs font-medium disabled:opacity-40"
          >
            Previous
          </button>
          <div className="flex gap-2">
            {step < 4 ? (
              <button
                type="button"
                onClick={() => setStep((s) => s + 1)}
                className="px-4 py-2 bg-[#0F2942] text-white rounded-md text-xs font-medium"
              >
                Next Step
              </button>
            ) : (
              <>
                <button
                  type="button"
                  onClick={() => createMutation.mutate(true)}
                  className="px-4 py-2 border border-slate-300 bg-slate-100 rounded-md text-xs font-medium"
                >
                  Save as Draft
                </button>
                <button
                  type="button"
                  onClick={() => createMutation.mutate(false)}
                  className="inline-flex items-center gap-1.5 px-4 py-2 bg-[#0F2942] text-white rounded-md text-xs font-semibold"
                >
                  <CheckCircle2 className="w-3.5 h-3.5" /> Create Inspection
                </button>
              </>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}

