export type Customer = {
  customer_id: number;
  name: string;
  email: string;
  created_at: string;
};

export type ProviderState = {
  available: boolean;
  models: string[];
};

export type ProviderCatalog = Record<string, ProviderState>;

export type SessionSummary = {
  thread_id: string;
  customer_id: number;
  created_at: string;
  first_message: string;
};

export type SessionMessage = {
  message_id: number;
  role: "human" | "ai";
  content: string;
  created_at: string;
};

export type ChatRequest = {
  message: string;
  customer_id: number;
  thread_id?: string;
  provider?: string;
  model?: string;
};

export type MemoryEntry = {
  type: "memory";
  key: string;
  value: string;
};

export type ComplaintEntry = {
  type: "complaint";
  order_id: number;
  issue: string;
  status: string;
  created_at: string;
};

export type MemoryContextEntry = MemoryEntry | ComplaintEntry;

export type PlannerToolCall = {
  name: string;
  args: Record<string, unknown>;
};

export type ChatStreamEvent =
  | { type: "memory_loaded"; thread_id: string; memory_context: MemoryContextEntry[] }
  | { type: "planner_start"; thread_id: string }
  | { type: "planner_result"; thread_id: string; content: string; tool_calls: PlannerToolCall[] }
  | { type: "tool_start"; thread_id: string }
  | { type: "tool_result"; thread_id: string; results: string }
  | { type: "verifier_result"; thread_id: string; valid: boolean | null; checks: string[]; override_message: string | null }
  | { type: "memory_updated"; thread_id: string }
  | { type: "response_token"; thread_id: string; token: string }
  | { type: "response_end"; thread_id: string; response: string }
  | { type: "error"; thread_id: string; error: string };
