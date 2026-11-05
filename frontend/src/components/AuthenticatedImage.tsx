import React, { useEffect, useState } from 'react'
import { imagesApi } from '../api/client'

interface AuthenticatedImageProps {
  imageId: number
  alt: string
  className?: string
  isProcessed?: boolean
}

export const AuthenticatedImage: React.FC<AuthenticatedImageProps> = ({
  imageId,
  alt,
  className,
  isProcessed = false,
}) => {
  const [blobUrl, setBlobUrl] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(false)

  useEffect(() => {
    let active = true
    let createdUrl: string | null = null

    const fetchImage = async () => {
      try {
        setLoading(true)
        setError(false)
        const url = isProcessed
          ? await imagesApi.getProcessedFileBlobUrl(imageId)
          : await imagesApi.getFileBlobUrl(imageId)
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
  }, [imageId])

  if (loading) {
    return (
      <div className={`bg-slate-100 flex items-center justify-center text-slate-400 text-xs animate-pulse ${className}`}>
        <span>Loading...</span>
      </div>
    )
  }

  if (error || !blobUrl) {
    return (
      <div className={`bg-slate-100 flex items-center justify-center text-rose-400 text-xs ${className}`}>
        <span>Image unavailable</span>
      </div>
    )
  }

  return <img src={blobUrl} alt={alt} className={className} />
}
