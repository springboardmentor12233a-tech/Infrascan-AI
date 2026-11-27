import React, { useEffect, useState } from 'react'
import { imagesApi, analysisApi } from '../api/client'

export type ImageViewMode = 'original' | 'processed' | 'mask' | 'heatmap'

interface AuthenticatedImageProps {
  imageId: number
  alt: string
  className?: string
  isProcessed?: boolean
  mode?: ImageViewMode
}

export const AuthenticatedImage: React.FC<AuthenticatedImageProps> = ({
  imageId,
  alt,
  className,
  isProcessed = false,
  mode,
}) => {
  const [blobUrl, setBlobUrl] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(false)

  const activeMode: ImageViewMode = mode || (isProcessed ? 'processed' : 'original')

  useEffect(() => {
    let active = true
    let createdUrl: string | null = null

    const fetchImage = async () => {
      try {
        setLoading(true)
        setError(false)
        let url = ''

        if (activeMode === 'mask') {
          url = await analysisApi.getMaskBlobUrl(imageId)
        } else if (activeMode === 'heatmap') {
          url = await analysisApi.getHeatmapBlobUrl(imageId)
        } else if (activeMode === 'processed') {
          url = await imagesApi.getProcessedFileBlobUrl(imageId)
        } else {
          url = await imagesApi.getFileBlobUrl(imageId)
        }

        if (active) {
          createdUrl = url
          setBlobUrl(url)
        } else {
          URL.revokeObjectURL(url)
        }
      } catch {
        if (active) setError(true)
      } finally {
        if (active) setLoading(false)
      }
    }

    fetchImage()

    return () => {
      active = false
      if (createdUrl) {
        URL.revokeObjectURL(createdUrl)
      }
    }
  }, [imageId, activeMode])

  if (loading) {
    return (
      <div className={`bg-[#141619]/80 flex flex-col items-center justify-center text-[#B3B4BD] text-xs animate-pulse p-4 ${className}`}>
        <div className="w-5 h-5 border-2 border-[#0A21C0] border-t-transparent rounded-full animate-spin mb-2"></div>
        <span>Loading {activeMode}...</span>
      </div>
    )
  }

  if (error || !blobUrl) {
    return (
      <div className={`bg-[#141619] flex flex-col items-center justify-center text-rose-400 text-xs p-4 text-center border border-dashed border-[#2C2E3A] ${className}`}>
        <span className="font-semibold text-rose-300 mb-1">Image layer unavailable</span>
        <span className="text-[10px] text-[#B3B4BD]">
          {activeMode === 'mask' || activeMode === 'heatmap'
            ? 'Run damage analysis first to generate this layer'
            : 'Original file not reachable'}
        </span>
      </div>
    )
  }

  return <img src={blobUrl} alt={alt} className={className} />
}
