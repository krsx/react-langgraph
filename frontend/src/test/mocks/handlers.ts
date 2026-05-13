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

  http.get('/api/orders', ({ request }) => {
    const url = new URL(request.url)
    const customerId = url.searchParams.get('customer_id')
    const orders = [
      { order_id: 12345, customer_id: 1, product_name: 'Wireless Headphones', status: 'pending', order_date: '2026-04-01T10:00:00', delivery_date: null },
      { order_id: 5678, customer_id: 1, product_name: 'USB-C Hub', status: 'delivered', order_date: '2026-03-10T08:00:00', delivery_date: '2026-03-15T14:00:00' },
      { order_id: 9999, customer_id: 2, product_name: 'Other Product', status: 'processing', order_date: '2026-04-10T09:00:00', delivery_date: null },
    ]
    return HttpResponse.json(
      customerId ? orders.filter((o) => o.customer_id === Number(customerId)) : orders
    )
  }),

  http.get('/api/complaints', ({ request }) => {
    const url = new URL(request.url)
    const customerId = url.searchParams.get('customer_id')
    const complaints = [
      { complaint_id: 1, customer_id: 1, order_id: 5678, issue: 'Package arrived late', status: 'resolved', created_at: '2026-03-16T10:00:00' },
    ]
    return HttpResponse.json(
      customerId ? complaints.filter((c) => c.customer_id === Number(customerId)) : complaints
    )
  }),

  http.get('/api/memory/:customerId', ({ params }) => {
    if (String(params.customerId) === '1') {
      return HttpResponse.json([
        { key: 'late_delivery_pattern', value: 'Customer has late delivery pattern', created_at: '2026-01-01T00:00:00' },
        { key: 'complaint_count', value: '2', created_at: '2026-01-01T00:00:00' },
      ])
    }
    return HttpResponse.json([])
  }),

  http.put('/api/memory/:customerId', async ({ request }) => {
    const body = await request.json()
    return HttpResponse.json({ updated: Array.isArray(body) ? (body as unknown[]).length : 1 })
  }),

  http.delete('/api/memory/:customerId/:key', () =>
    HttpResponse.json({ deleted: true })
  ),
]
