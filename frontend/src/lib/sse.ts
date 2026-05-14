import type { ChatRequest, ChatStreamEvent, JsonValue } from "./types";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

type Frame = {
  event: string;
  data: string;
};

function parseFrame(frame: string): Frame | null {
  const lines = frame.split(/\r?\n/);
  let event = "";
  const dataLines: string[] = [];

  for (const line of lines) {
    if (line.startsWith("event:")) {
      event = line.slice("event:".length).trim();
      continue;
    }
    if (line.startsWith("data:")) {
      dataLines.push(line.slice("data:".length).trim());
    }
  }

  if (!event || dataLines.length === 0) {
    return null;
  }

  return { event, data: dataLines.join("\n") };
}

function parsePayload(event: Frame): ChatStreamEvent | null {
  let payload: unknown;
  try {
    payload = JSON.parse(event.data);
  } catch {
    return null;
  }

  if (!payload || typeof payload !== "object") {
    return null;
  }

  const base = payload as Record<string, unknown>;
  const thread_id = typeof base.thread_id === "string" ? base.thread_id : "";

  switch (event.event) {
    case "memory_loaded":
      return {
        type: "memory_loaded",
        thread_id,
        memory_context: Array.isArray(base.memory_context)
          ? (base.memory_context as never[])
          : [],
      };
    case "planner_start":
      return { type: "planner_start", thread_id };
    case "planner_result":
      return {
        type: "planner_result",
        thread_id,
        content: typeof base.content === "string" ? base.content : "",
        tool_calls: Array.isArray(base.tool_calls) ? (base.tool_calls as never[]) : [],
      };
    case "tool_start":
      return { type: "tool_start", thread_id };
    case "tool_result":
      return {
        type: "tool_result",
        thread_id,
        tool_name: typeof base.tool_name === "string" ? base.tool_name : "",
        results: (base.results as JsonValue | undefined) ?? null,
      };
    case "verifier_result":
      return {
        type: "verifier_result",
        thread_id,
        valid: typeof base.valid === "boolean" ? base.valid : null,
        checks: Array.isArray(base.checks) ? (base.checks as string[]) : [],
        override_message: typeof base.override_message === "string" || base.override_message === null
          ? (base.override_message as string | null)
          : null,
      };
    case "memory_updated":
      return {
        type: "memory_updated",
        thread_id,
        key: typeof base.key === "string" ? base.key : "",
        value: typeof base.value === "string" ? base.value : "",
      };
    case "response_token":
      return {
        type: "response_token",
        thread_id,
        token: typeof base.token === "string" ? base.token : "",
      };
    case "response_end":
      return {
        type: "response_end",
        thread_id,
        response: typeof base.response === "string" ? base.response : "",
      };
    case "error":
      return {
        type: "error",
        thread_id,
        error: typeof base.error === "string" ? base.error : "Unknown stream error",
      };
    default:
      return null;
  }
}

export function createSseParser(onEvent: (event: ChatStreamEvent) => void) {
  let buffer = "";

  return {
    push(chunk: string) {
      buffer += chunk;
      const frames = buffer.split(/\n\n/);
      buffer = frames.pop() ?? "";

      for (const rawFrame of frames) {
        const frame = parseFrame(rawFrame.trim());
        if (!frame) {
          continue;
        }
        const event = parsePayload(frame);
        if (event) {
          onEvent(event);
        }
      }
    },
    flush() {
      const frame = parseFrame(buffer.trim());
      if (!frame) {
        return;
      }
      const event = parsePayload(frame);
      if (event) {
        onEvent(event);
      }
    },
  };
}

export async function* parseSseStream(
  stream: ReadableStream<Uint8Array>,
): AsyncGenerator<ChatStreamEvent> {
  const reader = stream.getReader();
  const decoder = new TextDecoder();
  const queue: ChatStreamEvent[] = [];
  const parser = createSseParser((event) => {
    queue.push(event);
  });

  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) {
        break;
      }
      parser.push(decoder.decode(value, { stream: true }));
      while (queue.length > 0) {
        yield queue.shift()!;
      }
    }
    parser.flush();
    while (queue.length > 0) {
      yield queue.shift()!;
    }
  } finally {
    reader.releaseLock();
  }
}

export async function streamChat(
  request: ChatRequest,
  onEvent: (event: ChatStreamEvent) => void,
  fetchImpl: typeof fetch = fetch,
): Promise<void> {
  const response = await fetchImpl(`${API_BASE_URL}/chat/stream`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(request),
  });

  if (!response.ok) {
    throw new Error(`Chat stream failed with status ${response.status}`);
  }

  if (!response.body) {
    throw new Error("Chat stream did not return a readable body");
  }

  for await (const event of parseSseStream(response.body)) {
    onEvent(event);
  }
}
