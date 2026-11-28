import { useNavigate, useParams, Link } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { ArrowLeft } from 'lucide-react'
import { infrastructureService } from '@/services/infrastructureService'
import { AssetForm, type AssetFormValues } from '@/components/assets/AssetForm'

export function AssetFormPage() {
  const { id } = useParams<{ id: string }>()
  const isEdit = Boolean(id)
  const navigate = useNavigate()
  const queryClient = useQueryClient()

  const { data: existing, isLoading } = useQuery({
    queryKey: ['asset', id],
    queryFn: () => infrastructureService.getById(id!),
    enabled: isEdit,
  })

  const createMutation = useMutation({
    mutationFn: (values: AssetFormValues) =>
      infrastructureService.create({
        name: values.name,
        type: values.type,
        description: values.description,
        location: `${values.city}, ${values.state}`,
        city: values.city,
        state: values.state,
        country: values.country,
        district: values.district,
        address: values.address,
        postalCode: values.postalCode,
        coordinates: [values.latitude, values.longitude],
        constructionYear: values.constructionYear,
        materialType: values.materialType,
        secondaryMaterial: values.secondaryMaterial,
        structuralSystem: values.structuralSystem,
        floors: values.floors,
        lengthMeters: values.lengthMeters,
        widthMeters: values.widthMeters,
        heightMeters: values.heightMeters,
        responsibleDepartment: values.responsibleDepartment,
        owner: values.owner,
        contactPerson: values.contactPerson,
        contactEmail: values.contactEmail,
        contactNumber: values.contactNumber,
        assignedInspector: values.assignedInspector,
        inspectionFrequency: values.inspectionFrequency,
        lastInspectionDate: values.lastInspectionDate || new Date().toISOString().slice(0, 10),
        nextInspectionDate: values.nextInspectionDate,
        inspectionPriority: values.inspectionPriority,
        maintenanceNotes: values.maintenanceNotes,
        operationalStatus: values.operationalStatus,
        status: values.operationalStatus === 'Under Maintenance' ? 'Maintenance Required' : 'Operational',
      }),
    onSuccess: (created) => {
      queryClient.invalidateQueries({ queryKey: ['assets'] })
      navigate(`/app/assets/${created.id}`)
    },
  })

  const updateMutation = useMutation({
    mutationFn: (values: AssetFormValues) =>
      infrastructureService.update(id!, {
        name: values.name,
        type: values.type,
        description: values.description,
        location: `${values.city}, ${values.state}`,
        coordinates: [values.latitude, values.longitude],
        constructionYear: values.constructionYear,
        materialType: values.materialType,
        responsibleDepartment: values.responsibleDepartment,
        inspectionFrequency: values.inspectionFrequency,
        operationalStatus: values.operationalStatus,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['assets'] })
      queryClient.invalidateQueries({ queryKey: ['asset', id] })
      navigate(`/app/assets/${id}`)
    },
  })

  if (isEdit && isLoading) {
    return <div className="p-8 text-center text-xs text-slate-500">Loading asset record...</div>
  }

  return (
    <div className="space-y-5 max-w-5xl">
      <div>
        <Link to="/app/assets" className="inline-flex items-center gap-1.5 text-xs text-slate-500 hover:text-slate-800 mb-2">
          <ArrowLeft className="w-3.5 h-3.5" /> Back to Asset Registry
        </Link>
        <h1 className="text-xl font-semibold text-slate-900">
          {isEdit ? `Edit Infrastructure: ${existing?.name || id}` : 'Register Infrastructure Asset'}
        </h1>
        <p className="text-xs text-slate-500 mt-0.5">
          Complete structural, location, and inspection configuration details
        </p>
      </div>

      <AssetForm
        initialData={existing}
        isSubmitting={createMutation.isPending || updateMutation.isPending}
        onCancel={() => navigate(isEdit ? `/app/assets/${id}` : '/app/assets')}
        onSubmit={(values) => {
          if (isEdit) {
            updateMutation.mutate(values)
          } else {
            createMutation.mutate(values)
          }
        }}
      />
    </div>
  )
}

