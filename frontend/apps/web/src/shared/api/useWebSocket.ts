import { useEffect, useRef, useState } from 'react'
import type { WsEvent } from './types'

type UseWebSocketResult = {
  messages: WsEvent[]
  isConnected: boolean
  send: (data: string) => void
}

export function useWebSocket(url: string): UseWebSocketResult {
  const [messages, setMessages] = useState<WsEvent[]>([])
  const [isConnected, setIsConnected] = useState(false)
  const wsRef = useRef<WebSocket | null>(null)
  const retryCountRef = useRef(0)
  const maxRetries = 5

  useEffect(() => {
    let retryTimeout: ReturnType<typeof setTimeout> | null = null

    const connect = () => {
      const ws = new WebSocket(url)
      wsRef.current = ws

      ws.onopen = () => {
        setIsConnected(true)
        retryCountRef.current = 0
      }

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data as string) as WsEvent
          setMessages((prev) => {
            const next = [...prev, data]
            return next.length > 500 ? next.slice(next.length - 500) : next
          })
        } catch {
          // ignore parse errors
        }
      }

      ws.onclose = () => {
        setIsConnected(false)
        if (retryCountRef.current < maxRetries) {
          retryCountRef.current += 1
          retryTimeout = setTimeout(connect, 3000)
        }
      }

      ws.onerror = () => {
        ws.close()
      }
    }

    connect()

    return () => {
      if (retryTimeout) clearTimeout(retryTimeout)
      if (wsRef.current) {
        wsRef.current.onclose = null // prevent retry on intentional close
        wsRef.current.close()
      }
    }
  }, [url])

  const send = (data: string) => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(data)
    }
  }

  return { messages, isConnected, send }
}
