import { useEffect, useRef, useState } from 'react'
import { eventsApi } from '../api/client'
import { useAuth } from '../context/AuthContext'

export type LiveStatus = 'Live' | 'Reconnecting' | 'Polling'

export interface LiveEvent {
  event_id: number
  type: string
  entity_type: string
  entity_id: string
  audience?: Record<string, any>
  payload?: Record<string, any>
  created_at?: string
}

export type EventHandler = (event: LiveEvent) => void

export function useLiveEvents(onEvent?: EventHandler) {
  const { user, logout } = useAuth()
  const [status, setStatus] = useState<LiveStatus>('Reconnecting')
  const [lastEvent, setLastEvent] = useState<LiveEvent | null>(null)
  const lastEventIdRef = useRef<number>(0)
  const failureCountRef = useRef<number>(0)
  const eventSourceRef = useRef<EventSource | null>(null)
  const pollingTimerRef = useRef<any>(null)
  const reconnectTimeoutRef = useRef<any>(null)
  const onEventRef = useRef<EventHandler | undefined>(onEvent)

  useEffect(() => {
    onEventRef.current = onEvent
  }, [onEvent])

  useEffect(() => {
    if (!user) {
      if (eventSourceRef.current) {
        eventSourceRef.current.close()
        eventSourceRef.current = null
      }
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current)
        reconnectTimeoutRef.current = null
      }
      if (pollingTimerRef.current) {
        clearInterval(pollingTimerRef.current)
        pollingTimerRef.current = null
      }
      return
    }

    let isCancelled = false

    const handleIncomingEvent = (eventData: LiveEvent) => {
      if (eventData.event_id && eventData.event_id > lastEventIdRef.current) {
        lastEventIdRef.current = eventData.event_id
      }
      setLastEvent(eventData)

      // Built-in handlers for session revocation and role changes
      if (eventData.type === 'user.session_revoked' && eventData.payload?.user_id === user.user_id) {
        logout()
        return
      }

      if (eventData.type === 'user.role_changed' && eventData.payload?.user_id === user.user_id) {
        // Trigger page refresh to re-evaluate role guards
        window.location.reload()
        return
      }

      // Dispatch global window custom event for components to listen to
      window.dispatchEvent(new CustomEvent('infrascan:event', { detail: eventData }))

      if (onEventRef.current) {
        onEventRef.current(eventData)
      }
    }

    const startPollingFallback = () => {
      setStatus('Polling')
      if (pollingTimerRef.current) clearInterval(pollingTimerRef.current)

      const poll = async () => {
        try {
          const res = await eventsApi.poll(lastEventIdRef.current)
          if (res.events && res.events.length > 0) {
            res.events.forEach((evt) => handleIncomingEvent(evt))
          }
          if (res.last_id) {
            lastEventIdRef.current = Math.max(lastEventIdRef.current, res.last_id)
          }
        } catch (e) {
          console.warn('[LiveEvents] Polling error:', e)
        }
      }

      poll()
      pollingTimerRef.current = setInterval(poll, 15000)
    }

    const connectSSE = async () => {
      if (isCancelled) return
      cleanupSSE()

      try {
        setStatus('Reconnecting')
        const { ticket } = await eventsApi.getTicket()
        if (isCancelled) return

        const streamUrl = eventsApi.getStreamUrl(ticket, lastEventIdRef.current)
        const es = new EventSource(streamUrl)
        eventSourceRef.current = es

        es.onopen = () => {
          if (isCancelled) return
          setStatus('Live')
          failureCountRef.current = 0
          if (pollingTimerRef.current) {
            clearInterval(pollingTimerRef.current)
            pollingTimerRef.current = null
          }
        }

        es.onmessage = (e) => {
          if (isCancelled) return
          try {
            const data: LiveEvent = JSON.parse(e.data)
            handleIncomingEvent(data)
          } catch {
            // Heartbeat or malformed comment
          }
        }

        // Generic event listener for typed events
        const knownTypes = [
          'inspection.created',
          'inspection.assigned',
          'inspection.status_changed',
          'inspection.completed',
          'image.uploaded',
          'image.preprocessed',
          'analysis.queued',
          'analysis.stage_started',
          'analysis.completed',
          'analysis.failed',
          'severity.assessed',
          'severity.confirmed',
          'priority.suggested',
          'priority.confirmed',
          'task.created',
          'task.assigned',
          'task.status_changed',
          'task.completed',
          'task.verified',
          'comparison.ready',
          'report.ready',
          'notification.created',
          'asset.created',
          'asset.updated',
          'model.activated',
          'user.role_changed',
          'user.session_revoked',
        ]

        knownTypes.forEach((t) => {
          es.addEventListener(t, (e: any) => {
            if (isCancelled) return
            try {
              const data: LiveEvent = JSON.parse(e.data)
              handleIncomingEvent(data)
            } catch {
              // Ignore parse error
            }
          })
        })

        es.onerror = () => {
          if (isCancelled) return
          es.close()
          failureCountRef.current += 1
          if (failureCountRef.current >= 3) {
            console.warn('[LiveEvents] SSE failed 3 times; falling back to 15s polling.')
            startPollingFallback()
          } else {
            const backoffMs = Math.min(1000 * Math.pow(2, failureCountRef.current), 16000)
            reconnectTimeoutRef.current = setTimeout(connectSSE, backoffMs)
          }
        }
      } catch {
        if (isCancelled) return
        failureCountRef.current += 1
        if (failureCountRef.current >= 3) {
          startPollingFallback()
        } else {
          reconnectTimeoutRef.current = setTimeout(connectSSE, 2000)
        }
      }
    }

    const cleanupSSE = () => {
      if (eventSourceRef.current) {
        eventSourceRef.current.close()
        eventSourceRef.current = null
      }
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current)
        reconnectTimeoutRef.current = null
      }
    }

    const cleanup = () => {
      isCancelled = true
      cleanupSSE()
      if (pollingTimerRef.current) {
        clearInterval(pollingTimerRef.current)
        pollingTimerRef.current = null
      }
    }

    connectSSE()
    return cleanup
  }, [user, logout])

  return {
    status,
    lastEvent,
    lastEventId: lastEventIdRef.current,
  }
}
