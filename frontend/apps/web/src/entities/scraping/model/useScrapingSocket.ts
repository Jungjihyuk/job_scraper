import { useCallback, useEffect, useRef, useState } from 'react'
import { useWebSocket } from '../../../shared/api'
import { fetchScrapingStatus } from '../api/scrapingApi'
import type { ScrapingResult, WsEvent } from '../../../shared/api'

type UseScrapingSocketResult = {
  messages: WsEvent[]
  isConnected: boolean
  isScrapingRunning: boolean
  lastResult: ScrapingResult | null
  clearMessages: () => void
}

const WS_URL = `ws://${typeof window !== 'undefined' ? window.location.host : 'localhost:5173'}/ws`

export function useScrapingSocket(): UseScrapingSocketResult {
  const { messages, isConnected } = useWebSocket(WS_URL)
  const [isScrapingRunning, setIsScrapingRunning] = useState(false)
  const initializedRef = useRef(false)
  const [localMessages, setLocalMessages] = useState<WsEvent[]>([])
  const [lastResult, setLastResult] = useState<ScrapingResult | null>(null)

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
      setLastResult(null)
    } else if (latest.type === 'complete' || latest.type === 'error') {
      setIsScrapingRunning(false)
      setLastResult(latest.result ?? null)
    } else if (latest.type === 'stopped') {
      setIsScrapingRunning(false)
    }

    setLocalMessages(messages)
  }, [messages])

  const clearMessages = useCallback(() => {
    setLocalMessages([])
  }, [])

  return { messages: localMessages, isConnected, isScrapingRunning, lastResult, clearMessages }
}
