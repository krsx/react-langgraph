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
  chunkDelayMs?: number;
  chunkEachEvent?: boolean;
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
