import type { SseFrame, SseEventName } from './types'

export async function* parseSseFrames(
  stream: ReadableStream<Uint8Array>
): AsyncGenerator<SseFrame> {
  const reader = stream.getReader()
  const decoder = new TextDecoder()
  let buffer = ''

  try {
    while (true) {
      const { done, value } = await reader.read()
      if (done) break
      buffer += decoder.decode(value, { stream: true })

      let boundary: number
      while ((boundary = buffer.indexOf('\n\n')) !== -1) {
        const raw = buffer.slice(0, boundary)
        buffer = buffer.slice(boundary + 2)

        let event: string | null = null
        let data: string | null = null

        for (const line of raw.split('\n')) {
          if (line.startsWith('event:')) event = line.slice(6).trim()
          else if (line.startsWith('data:')) data = line.slice(5).trim()
        }

        if (!event || !data) continue

        let parsed: Record<string, unknown>
        try {
          parsed = JSON.parse(data)
        } catch {
          continue
        }

        yield { event: event as SseEventName, data: parsed }
      }
    }
  } finally {
    reader.releaseLock()
  }
}

export async function collectStream<T>(gen: AsyncGenerator<T>): Promise<T[]> {
  const results: T[] = []
  for await (const item of gen) results.push(item)
  return results
}

export async function* streamChat(
  payload: {
    message: string
    customer_id: number
    thread_id?: string
    provider?: string
    model?: string
  },
  signal?: AbortSignal
): AsyncGenerator<SseFrame> {
  const response = await fetch('/api/chat/stream', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
    signal,
  })

  if (!response.body) throw new Error('No response body')

  yield* parseSseFrames(response.body)
}
