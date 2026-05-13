import { appReducer, createInitialState } from "./state";
import type { ProviderCatalog } from "./types";

const providers: ProviderCatalog = {
  openrouter: {
    available: true,
    models: ["openai/gpt-4o", "google/gemini-2.5-flash"],
    default_model: "google/gemini-2.5-flash",
  },
  ollama: {
    available: false,
    models: [],
    default_model: null,
  },
};

describe("appReducer", () => {
  it("resets the writable Conversation Session when the Customer changes", () => {
    const baseState = appReducer(createInitialState(), {
      type: "bootstrap_loaded",
      customers: [
        { customer_id: 1, name: "Ahmad", email: "ahmad@example.com", created_at: "2026-05-01" },
        { customer_id: 2, name: "Bea", email: "bea@example.com", created_at: "2026-05-01" },
      ],
      providers,
      sessions: [],
    });

    const withTurn = appReducer(baseState, {
      type: "message_sent",
      turnId: "turn-1",
      message: "Where is my order?",
    });
    const completed = appReducer(withTurn, {
      type: "stream_event_received",
      turnId: "turn-1",
      event: { type: "response_end", thread_id: "thread-1", response: "On the way." },
    });

    const nextState = appReducer(completed, {
      type: "customer_selected",
      customerId: 2,
    });

    expect(nextState.activeCustomerId).toBe(2);
    expect(nextState.view).toEqual({
      mode: "writable",
      threadId: null,
      turns: [],
    });
    expect(nextState.stream.processEvents).toEqual([]);
  });

  it("auto-selects a valid model when the Provider changes", () => {
    const baseState = appReducer(createInitialState(), {
      type: "bootstrap_loaded",
      customers: [{ customer_id: 1, name: "Ahmad", email: "ahmad@example.com", created_at: "2026-05-01" }],
      providers: {
        openrouter: {
          available: true,
          models: ["openai/gpt-4o"],
          default_model: "openai/gpt-4o",
        },
        ollama: {
          available: true,
          models: ["qwen3:4b"],
          default_model: "qwen3:4b",
        },
      },
      sessions: [],
    });

    const nextState = appReducer(baseState, {
      type: "provider_selected",
      provider: "ollama",
    });

    expect(nextState.selectedProvider).toBe("ollama");
    expect(nextState.selectedModel).toBe("qwen3:4b");
    expect(nextState.view.threadId).toBeNull();
  });

  it("prefers the provider default model during bootstrap", () => {
    const state = appReducer(createInitialState(), {
      type: "bootstrap_loaded",
      customers: [{ customer_id: 1, name: "Ahmad", email: "ahmad@example.com", created_at: "2026-05-01" }],
      providers,
      sessions: [],
    });

    expect(state.selectedProvider).toBe("openrouter");
    expect(state.selectedModel).toBe("google/gemini-2.5-flash");
  });

  it("keeps partial tokens out of committed assistant history on failure", () => {
    let state = appReducer(createInitialState(), {
      type: "bootstrap_loaded",
      customers: [{ customer_id: 1, name: "Ahmad", email: "ahmad@example.com", created_at: "2026-05-01" }],
      providers,
      sessions: [],
    });

    state = appReducer(state, {
      type: "message_sent",
      turnId: "turn-1",
      message: "Help me",
    });
    state = appReducer(state, {
      type: "stream_event_received",
      turnId: "turn-1",
      event: { type: "response_token", thread_id: "thread-1", token: "Partial" },
    });
    state = appReducer(state, {
      type: "stream_event_received",
      turnId: "turn-1",
      event: { type: "error", thread_id: "thread-1", error: "LLM failed" },
    });

    if (state.view.mode !== "writable") {
      throw new Error("expected writable view");
    }

    expect(state.view.turns[0]).toMatchObject({
      status: "failed",
      assistantMessage: "",
      error: "LLM failed",
    });
    expect(state.stream.processEvents.map((event) => event.type)).toEqual([
      "response_token",
      "error",
    ]);
  });

  it("resets the writable Conversation Session when the model changes", () => {
    let state = appReducer(createInitialState(), {
      type: "bootstrap_loaded",
      customers: [{ customer_id: 1, name: "Ahmad", email: "ahmad@example.com", created_at: "2026-05-01" }],
      providers: {
        openrouter: {
          available: true,
          models: ["openai/gpt-4o", "google/gemini-2.5-flash"],
          default_model: "google/gemini-2.5-flash",
        },
      },
      sessions: [],
    });

    state = appReducer(state, {
      type: "message_sent",
      turnId: "turn-1",
      message: "Help me",
    });
    state = appReducer(state, {
      type: "stream_event_received",
      turnId: "turn-1",
      event: { type: "response_end", thread_id: "thread-1", response: "Done" },
    });

    const nextState = appReducer(state, {
      type: "model_selected",
      model: "google/gemini-2.5-flash",
    });

    expect(nextState.selectedModel).toBe("google/gemini-2.5-flash");
    expect(nextState.view).toEqual({
      mode: "writable",
      threadId: null,
      turns: [],
    });
    expect(nextState.stream.processEvents).toEqual([]);
  });
});
