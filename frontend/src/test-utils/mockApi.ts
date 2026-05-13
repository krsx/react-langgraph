import { vi } from "vitest";
import type {
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

  const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = typeof input === "string" ? input : input instanceof URL ? input.toString() : input.url;
    const parsedUrl = new URL(url);
    const { pathname, searchParams } = parsedUrl;

    if (pathname === "/customers") {
      return new Response(JSON.stringify(config.customers), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      });
    }

    if (pathname === "/providers") {
      return new Response(JSON.stringify(config.providers), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      });
    }

    if (pathname === "/orders") {
      const customerId = searchParams.get("customer_id");
      const availableOrders = [...(config.orders ?? [])];
      const rows = customerId === null
        ? availableOrders
        : availableOrders.filter((order) => order.customer_id === Number(customerId));
      return new Response(JSON.stringify(rows), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      });
    }

    if (pathname === "/complaints") {
      const customerId = searchParams.get("customer_id");
      const availableComplaints = [...(config.complaints ?? [])];
      const rows = customerId === null
        ? availableComplaints
        : availableComplaints.filter((complaint) => complaint.customer_id === Number(customerId));
      return new Response(JSON.stringify(rows), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      });
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
