import type { ChatStreamEvent, SessionMessage } from "./types";

export type ConversationTurn = {
  id: string;
  userMessage: string;
  assistantMessage: string;
  status: "streaming" | "completed" | "failed";
  error: string | null;
  processEvents: ChatStreamEvent[];
};

export type WritableConversation = {
  mode: "writable";
  threadId: string | null;
  turns: ConversationTurn[];
};

export type HistoryConversation = {
  mode: "history";
  threadId: string;
  transcript: SessionMessage[];
};

export type ConversationView = WritableConversation | HistoryConversation;
