import { API_BASE_URL } from '../config'

type QueryParams = Record<string, string | number | boolean | undefined>

export async function getJson<T>(path: string, params?: QueryParams): Promise<T> {
  const url = new URL(`${API_BASE_URL}${path}`, window.location.origin)
  if (params) {
    Object.entries(params).forEach(([key, value]) => {
      if (value !== undefined) {
        url.searchParams.set(key, String(value))
      }
    })
  }
  const res = await fetch(url.toString())
  if (!res.ok) throw new Error(`요청 실패 (${res.status})`)
  const contentType = res.headers.get('content-type') ?? ''
  if (!contentType.includes('application/json')) {
    const body = await res.text()
    throw new Error(
      `JSON 응답이 아닙니다. content-type=${contentType || 'unknown'}, body=${body.slice(0, 80)}`,
    )
  }
  return (await res.json()) as T
}

export async function postJson<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(`${API_BASE_URL}${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
  if (!res.ok) throw new Error(`요청 실패 (${res.status})`)
  const contentType = res.headers.get('content-type') ?? ''
  if (!contentType.includes('application/json')) {
    const body2 = await res.text()
    throw new Error(
      `JSON 응답이 아닙니다. content-type=${contentType || 'unknown'}, body=${body2.slice(0, 80)}`,
    )
  }
  return (await res.json()) as T
}
