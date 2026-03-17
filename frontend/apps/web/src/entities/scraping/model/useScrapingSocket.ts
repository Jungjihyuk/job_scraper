import { useCallback, useEffect, useRef, useState } from 'react'
import { useWebSocket } from '../../../shared/api'
import { fetchScrapingStatus } from '../api/scrapingApi'
import type { WsEvent } from '../../../shared/api'

type UseScrapingSocketResult = {
  messages: WsEvent[]
  isConnected: boolean
  isScrapingRunning: boolean
  clearMessages: () => void
}

const WS_URL = `ws://${typeof window !== 'undefined' ? window.location.host : 'localhost:5173'}/ws`

export function useScrapingSocket(): UseScrapingSocketResult {
  const { messages, isConnected } = useWebSocket(WS_URL)
  const [isScrapingRunning, setIsScrapingRunning] = useState(false)
  const initializedRef = useRef(false)
  const [localMessages, setLocalMessages] = useState<WsEvent[]>([])

  useEffect(() => {
    if (!initializedRef.current) {
      initializedRef.current = true
      const checkStatus = async () => {
        try {
          const status = await fetchScrapingStatus()
          setIsScrapingRunning(status.is_scraping)
        } catch {
          // ignore — default to not running
        }
      }
      void checkStatus()
    }
  }, [])

  useEffect(() => {
    if (messages.length === 0) return
    const latest = messages[messages.length - 1]
    if (!latest) return

    if (latest.type === 'status') {
      setIsScrapingRunning(true)
    } else if (latest.type === 'complete' || latest.type === 'error' || latest.type === 'stopped') {
      setIsScrapingRunning(false)
    }

    setLocalMessages(messages)
  }, [messages])

  const clearMessages = useCallback(() => {
    setLocalMessages([])
  }, [])

  return { messages: localMessages, isConnected, isScrapingRunning, clearMessages }
}
