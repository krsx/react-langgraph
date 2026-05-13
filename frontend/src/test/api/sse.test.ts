import { describe, it, expect } from 'vitest'
import { parseSseFrames, collectStream } from '@/api/sse'

function makeStream(chunks: string[]): ReadableStream<Uint8Array> {
  const encoder = new TextEncoder()
  return new ReadableStream({
    start(controller) {
      for (const chunk of chunks) controller.enqueue(encoder.encode(chunk))
      controller.close()
    },
  })
}

describe('parseSseFrames', () => {
  it('parses a single well-formed frame', async () => {
    const stream = makeStream(['event: response_token\ndata: {"token":"hello"}\n\n'])
    const frames = await collectStream(parseSseFrames(stream))
    expect(frames).toHaveLength(1)
    expect(frames[0]).toEqual({ event: 'response_token', data: { token: 'hello' } })
  })

  it('parses multiple frames from one chunk', async () => {
    const raw =
      'event: planner_start\ndata: {"thread_id":"t1"}\n\n' +
      'event: response_end\ndata: {"thread_id":"t1","response":"done"}\n\n'
    const frames = await collectStream(parseSseFrames(makeStream([raw])))
    expect(frames).toHaveLength(2)
    expect(frames[0].event).toBe('planner_start')
    expect(frames[1].event).toBe('response_end')
  })

  it('handles a frame split across two chunks', async () => {
    const chunks = [
      'event: response_token\ndata: {"tok',
      'en":"split"}\n\n',
    ]
    const frames = await collectStream(parseSseFrames(makeStream(chunks)))
    expect(frames).toHaveLength(1)
    expect(frames[0].data).toEqual({ token: 'split' })
  })

  it('skips malformed frames missing the event line', async () => {
    const raw =
      'data: {"orphan":true}\n\n' +
      'event: memory_updated\ndata: {"thread_id":"t1"}\n\n'
    const frames = await collectStream(parseSseFrames(makeStream([raw])))
    expect(frames).toHaveLength(1)
    expect(frames[0].event).toBe('memory_updated')
  })

  it('skips frames with unparseable JSON data', async () => {
    const raw =
      'event: tool_result\ndata: not-json\n\n' +
      'event: response_end\ndata: {"thread_id":"t1","response":"ok"}\n\n'
    const frames = await collectStream(parseSseFrames(makeStream([raw])))
    expect(frames).toHaveLength(1)
    expect(frames[0].event).toBe('response_end')
  })
})
