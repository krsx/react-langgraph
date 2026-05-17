import { createSseParser } from "./sse";
import type { ChatStreamEvent } from "./types";

describe("createSseParser", () => {
  it("parses chunked SSE frames into typed events", () => {
    const events: ChatStreamEvent[] = [];
    const parser = createSseParser((event) => {
      events.push(event);
    });

    parser.push(
      'event: memory_loaded\ndata: {"thread_id":"thread-1","memory_context":[]}\n\n' +
        'event: response_token\ndata: {"thread_id":"thread-1","token":"Hel',
    );
    parser.push('lo"}\n\n');
    parser.flush();

    expect(events).toEqual([
      { type: "memory_loaded", thread_id: "thread-1", memory_context: [] },
      { type: "response_token", thread_id: "thread-1", token: "Hello" },
    ]);
  });

  it("ignores malformed frames and keeps parsing later events", () => {
    const events: ChatStreamEvent[] = [];
    const parser = createSseParser((event) => {
      events.push(event);
    });

    parser.push(
      "event: response_token\ndata: {not-json}\n\n" +
        'event: response_end\ndata: {"thread_id":"thread-1","response":"Done"}\n\n',
    );
    parser.flush();

    expect(events).toEqual([
      { type: "response_end", thread_id: "thread-1", response: "Done" },
    ]);
  });

  it("parses structured tool_result and memory_updated payloads", () => {
    const events: ChatStreamEvent[] = [];
    const parser = createSseParser((event) => {
      events.push(event);
    });

    parser.push(
      'event: tool_result\ndata: {"thread_id":"thread-1","tool_name":"order_lookup","results":{"order_id":12345,"status":"pending"}}\n\n' +
        'event: memory_updated\ndata: {"thread_id":"thread-1","key":"last_interaction_summary","value":"Summary text"}\n\n',
    );
    parser.flush();

    expect(events).toEqual([
      {
        type: "tool_result",
        thread_id: "thread-1",
        tool_name: "order_lookup",
        results: { order_id: 12345, status: "pending" },
      },
      {
        type: "memory_updated",
        thread_id: "thread-1",
        key: "last_interaction_summary",
        value: "Summary text",
      },
    ]);
  });
});
