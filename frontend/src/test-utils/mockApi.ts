import { vi } from "vitest";
import type {
  ChatRequest,
  ChatStreamEvent,
  Customer,
  ProviderCatalog,
  SessionMessage,
  SessionSummary,
} from "../lib/types";

type StreamRun = {
  events: ChatStreamEvent[];
  chunks?: number[];
};

type MockApiConfig = {
  customers: Customer[];
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

function createStream(events: ChatStreamEvent[], chunks?: number[]): ReadableStream<Uint8Array> {
  const encoder = new TextEncoder();
  const text = events.map(encodeEvent).join("");
  const chunkSizes = chunks && chunks.length > 0 ? chunks : [text.length];

  return new ReadableStream<Uint8Array>({
    start(controller) {
      let cursor = 0;
      for (const size of chunkSizes) {
        const slice = text.slice(cursor, cursor + size);
        if (!slice) {
          break;
        }
        controller.enqueue(encoder.encode(slice));
        cursor += size;
      }
      if (cursor < text.length) {
        controller.enqueue(encoder.encode(text.slice(cursor)));
      }
      controller.close();
    },
  });
}

export function createMockFetch(config: MockApiConfig) {
  const requests: ChatRequest[] = [];
  const streamRuns = [...(config.streamRuns ?? [])];

  const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = typeof input === "string" ? input : input instanceof URL ? input.toString() : input.url;
    const { pathname } = new URL(url);

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

    if (pathname === "/chat/stream") {
      const body = init?.body ? JSON.parse(String(init.body)) as ChatRequest : null;
      if (body) {
        requests.push(body);
      }
      const streamRun = streamRuns.shift() ?? { events: [] };
      return new Response(createStream(streamRun.events, streamRun.chunks), {
        status: 200,
        headers: { "Content-Type": "text/event-stream" },
      });
    }

    return new Response(null, { status: 404 });
  });

  return { fetchMock, requests };
}
