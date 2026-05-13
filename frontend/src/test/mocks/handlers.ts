import { http, HttpResponse } from 'msw'

export const handlers = [
  http.get('/api/customers', () =>
    HttpResponse.json([
      { customer_id: 1, name: 'Ahmad Rifqi', email: 'customer1@example.com', created_at: '2026-01-01T00:00:00' },
      { customer_id: 2, name: 'Jane Doe', email: 'customer2@example.com', created_at: '2026-01-02T00:00:00' },
    ])
  ),

  http.get('/api/providers', () =>
    HttpResponse.json({
      openrouter: { available: true, models: ['google/gemini-2.5-flash', 'openai/gpt-4o'] },
      ollama: { available: false, models: [] },
    })
  ),

  http.get('/api/sessions', () =>
    HttpResponse.json([
      { thread_id: 'thread-1', customer_id: 1, created_at: '2026-05-01T10:00:00', first_message: 'Where is my order?' },
      { thread_id: 'thread-2', customer_id: 2, created_at: '2026-05-02T10:00:00', first_message: 'I need a refund' },
    ])
  ),

  http.get('/api/sessions/:id', ({ params }) => {
    if (params.id === 'thread-1') {
      return HttpResponse.json([
        { message_id: 1, role: 'human', content: 'Where is my order?', created_at: '2026-05-01T10:00:00' },
        { message_id: 2, role: 'ai', content: 'Your order is on the way.', created_at: '2026-05-01T10:00:01' },
      ])
    }
    return HttpResponse.json({ detail: 'Session not found' }, { status: 404 })
  }),
]
