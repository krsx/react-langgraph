import { vi } from "vitest";
import type {
  AgentType,
  ChatRequest,
  ChatStreamEvent,
  Complaint,
  Customer,
  CustomerMemoryRecord,
  Order,
  ProviderCatalog,
  SessionMessage,
  SessionSummary,
} from "../lib/types";

export type { AgentType };

type StreamRun = {
  events: ChatStreamEvent[];
  chunks?: number[];
  chunkDelayMs?: number;
  chunkEachEvent?: boolean;
};

type MockApiConfig = {
  complaints?: Complaint[];
  customers: Customer[];
  memory?: CustomerMemoryRecord[];
  memoryByCustomerId?: Record<number, CustomerMemoryRecord[]>;
  orders?: Order[];
  providers: ProviderCatalog;
  sessions: SessionSummary[];
  sessionMessages?: Record<string, SessionMessage[]>;
  streamRuns?: StreamRun[];
};

function encodeEvent(event: ChatStreamEvent): string {
  const payload = { ...event };
  const eventName = payload.type;
  delete (payload as { type?: string }).type;
  return `event: ${eventName}\ndata: ${JSON.stringify(payload)}\n\n`;
}

function createStream(
  events: ChatStreamEvent[],
  chunks?: number[],
  chunkDelayMs = 0,
  chunkEachEvent = false,
): ReadableStream<Uint8Array> {
  const encoder = new TextEncoder();
  const frames = events.map(encodeEvent);
  const text = frames.join("");
  const chunkSizes = chunkEachEvent
    ? frames.map((frame) => frame.length)
    : chunks && chunks.length > 0
      ? chunks
      : [text.length];

  return new ReadableStream<Uint8Array>({
    start(controller) {
      async function pump() {
        let cursor = 0;
        for (const size of chunkSizes) {
          const slice = text.slice(cursor, cursor + size);
          if (!slice) {
            break;
          }
          controller.enqueue(encoder.encode(slice));
          cursor += size;
          if (chunkDelayMs > 0) {
            await new Promise((resolve) => {
              setTimeout(resolve, chunkDelayMs);
            });
          }
        }

        if (cursor < text.length) {
          controller.enqueue(encoder.encode(text.slice(cursor)));
        }
        controller.close();
      }

      void pump();
    },
  });
}

export function createMockFetch(config: MockApiConfig) {
  const requests: ChatRequest[] = [];
  const streamRuns = [...(config.streamRuns ?? [])];
  const memoryByCustomerId = new Map<number, CustomerMemoryRecord[]>(
    Object.entries(config.memoryByCustomerId ?? {}).map(([customerId, entries]) => [
      Number(customerId),
      [...entries],
    ]),
  );

  if (config.memory && !memoryByCustomerId.has(1)) {
    memoryByCustomerId.set(1, [...config.memory]);
  }

  let customers = [...config.customers];
  let orders = [...(config.orders ?? [])];
  let complaints = [...(config.complaints ?? [])];

  const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = typeof input === "string" ? input : input instanceof URL ? input.toString() : input.url;
    const parsedUrl = new URL(url);
    const { pathname, searchParams } = parsedUrl;

    if (pathname === "/customers" && (!init?.method || init.method === "GET")) {
      return new Response(JSON.stringify(customers), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      });
    }

    if (pathname === "/customers" && init?.method === "POST") {
      const body = JSON.parse(String(init.body)) as { name: string; email: string };
      const newId = Math.max(0, ...customers.map((c) => c.customer_id)) + 1;
      const newCustomer = { customer_id: newId, name: body.name, email: body.email, created_at: new Date().toISOString() };
      customers = [...customers, newCustomer];
      return new Response(JSON.stringify(newCustomer), { status: 201, headers: { "Content-Type": "application/json" } });
    }

    const customerMatch = pathname.match(/^\/customers\/(\d+)$/);
    if (customerMatch) {
      const customerId = Number(customerMatch[1]);
      if (init?.method === "PUT") {
        const body = JSON.parse(String(init.body)) as Partial<{ name: string; email: string }>;
        customers = customers.map((c) => c.customer_id === customerId ? { ...c, ...body } : c);
        const updated = customers.find((c) => c.customer_id === customerId);
        return new Response(JSON.stringify(updated), { status: 200, headers: { "Content-Type": "application/json" } });
      }
      if (init?.method === "DELETE") {
        customers = customers.filter((c) => c.customer_id !== customerId);
        return new Response(JSON.stringify({ deleted: true, customer_id: customerId }), { status: 200, headers: { "Content-Type": "application/json" } });
      }
    }

    if (pathname === "/providers") {
      return new Response(JSON.stringify(config.providers), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      });
    }

    if (pathname === "/orders" && (!init?.method || init.method === "GET")) {
      const customerId = searchParams.get("customer_id");
      const rows = customerId === null
        ? orders
        : orders.filter((order) => order.customer_id === Number(customerId));
      return new Response(JSON.stringify(rows), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      });
    }

    if (pathname === "/orders" && init?.method === "POST") {
      const body = JSON.parse(String(init.body)) as { customer_id: number; product_name: string; status: string };
      const newId = Math.max(0, ...orders.map((o) => o.order_id)) + 1;
      const newOrder = { order_id: newId, customer_id: body.customer_id, product_name: body.product_name, status: body.status, order_date: new Date().toISOString(), delivery_date: null };
      orders = [...orders, newOrder];
      return new Response(JSON.stringify(newOrder), { status: 201, headers: { "Content-Type": "application/json" } });
    }

    const orderMatch = pathname.match(/^\/orders\/(\d+)$/);
    if (orderMatch) {
      const orderId = Number(orderMatch[1]);
      if (init?.method === "PUT") {
        const body = JSON.parse(String(init.body)) as Partial<{ customer_id: number; product_name: string; status: string }>;
        orders = orders.map((o) => o.order_id === orderId ? { ...o, ...body } : o);
        const updated = orders.find((o) => o.order_id === orderId);
        return new Response(JSON.stringify(updated), { status: 200, headers: { "Content-Type": "application/json" } });
      }
      if (init?.method === "DELETE") {
        orders = orders.filter((o) => o.order_id !== orderId);
        return new Response(JSON.stringify({ deleted: true, order_id: orderId }), { status: 200, headers: { "Content-Type": "application/json" } });
      }
    }

    if (pathname === "/complaints" && (!init?.method || init.method === "GET")) {
      const customerId = searchParams.get("customer_id");
      const rows = customerId === null
        ? complaints
        : complaints.filter((complaint) => complaint.customer_id === Number(customerId));
      return new Response(JSON.stringify(rows), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      });
    }

    if (pathname === "/complaints" && init?.method === "POST") {
      const body = JSON.parse(String(init.body)) as { customer_id: number; order_id: number; issue: string; status: string };
      const newId = Math.max(0, ...complaints.map((c) => c.complaint_id)) + 1;
      const newComplaint = { complaint_id: newId, customer_id: body.customer_id, order_id: body.order_id, issue: body.issue, status: body.status, created_at: new Date().toISOString() };
      complaints = [...complaints, newComplaint];
      return new Response(JSON.stringify(newComplaint), { status: 201, headers: { "Content-Type": "application/json" } });
    }

    const complaintMatch = pathname.match(/^\/complaints\/(\d+)$/);
    if (complaintMatch) {
      const complaintId = Number(complaintMatch[1]);
      if (init?.method === "PUT") {
        const body = JSON.parse(String(init.body)) as Partial<{ customer_id: number; order_id: number; issue: string; status: string }>;
        complaints = complaints.map((c) => c.complaint_id === complaintId ? { ...c, ...body } : c);
        const updated = complaints.find((c) => c.complaint_id === complaintId);
        return new Response(JSON.stringify(updated), { status: 200, headers: { "Content-Type": "application/json" } });
      }
      if (init?.method === "DELETE") {
        complaints = complaints.filter((c) => c.complaint_id !== complaintId);
        return new Response(JSON.stringify({ deleted: true, complaint_id: complaintId }), { status: 200, headers: { "Content-Type": "application/json" } });
      }
    }

    if (pathname === "/sessions" && (!init?.method || init.method === "GET")) {
      return new Response(JSON.stringify(config.sessions), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      });
    }

    if (pathname.startsWith("/sessions/")) {
      const threadId = pathname.split("/").pop() ?? "";
      return new Response(
        JSON.stringify(config.sessionMessages?.[threadId] ?? []),
        {
          status: 200,
          headers: { "Content-Type": "application/json" },
        },
      );
    }

    if (pathname.startsWith("/memory/")) {
      const [, , customerIdText, ...keyParts] = pathname.split("/");
      const customerId = Number(customerIdText);
      const existingEntries = memoryByCustomerId.get(customerId) ?? [];

      if (!init?.method || init.method === "GET") {
        return new Response(JSON.stringify(existingEntries), {
          status: 200,
          headers: { "Content-Type": "application/json" },
        });
      }

      if (init.method === "PUT") {
        const entries = init.body
          ? JSON.parse(String(init.body)) as Array<{ key: string; value: string }>
          : [];

        const nextEntries = [...existingEntries];
        for (const entry of entries) {
          const existingIndex = nextEntries.findIndex((item) => item.key === entry.key);
          if (existingIndex >= 0) {
            nextEntries[existingIndex] = {
              ...nextEntries[existingIndex],
              value: entry.value,
            };
          } else {
            nextEntries.push({
              key: entry.key,
              value: entry.value,
              created_at: "2026-05-01T00:00:00Z",
            });
          }
        }
        memoryByCustomerId.set(customerId, nextEntries);

        return new Response(JSON.stringify({ updated: entries.length }), {
          status: 200,
          headers: { "Content-Type": "application/json" },
        });
      }

      if (init.method === "DELETE") {
        const key = decodeURIComponent(keyParts.join("/"));
        const nextEntries = existingEntries.filter((entry) => entry.key !== key);
        const deleted = nextEntries.length !== existingEntries.length;
        memoryByCustomerId.set(customerId, nextEntries);

        return new Response(
          JSON.stringify(deleted ? { deleted: true } : { detail: "Memory entry not found" }),
          {
            status: deleted ? 200 : 404,
            headers: { "Content-Type": "application/json" },
          },
        );
      }
    }

    if (pathname === "/chat/stream") {
      const body = init?.body ? JSON.parse(String(init.body)) as ChatRequest : null;
      if (body) {
        requests.push(body);
      }
      const streamRun = streamRuns.shift() ?? { events: [] };
      return new Response(
        createStream(
          streamRun.events,
          streamRun.chunks,
          streamRun.chunkDelayMs,
          streamRun.chunkEachEvent,
        ),
        {
        status: 200,
        headers: { "Content-Type": "text/event-stream" },
        },
      );
    }

    return new Response(null, { status: 404 });
  });

  return { fetchMock, requests };
}
