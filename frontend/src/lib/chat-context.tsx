import {
  createContext,
  useCallback,
  useContext,
  useReducer,
  useRef,
  type ReactNode,
} from "react";
import { useQueryClient } from "@tanstack/react-query";
import { postChatStream } from "./api";
import type { ConversationTurn, ConversationView, WritableConversation } from "./conversation";
import type { AgentType, ChatStreamEvent, SessionMessage } from "./types";

// ── State ────────────────────────────────────────────────────────────────────

type ChatState = {
  activeAgentType: AgentType;
  activeCustomerId: number | null;
  selectedProvider: string | null;
  selectedModel: string | null;
  view: ConversationView;
  isStreaming: boolean;
};

type ChatAction =
  | { type: "agent_type_selected"; agentType: AgentType }
  | { type: "customer_selected"; customerId: number }
  | { type: "provider_selected"; provider: string; models: string[]; defaultModel?: string | null }
  | { type: "model_selected"; model: string }
  | { type: "history_loaded"; threadId: string; transcript: SessionMessage[] }
  | { type: "new_chat" }
  | { type: "turn_started"; turnId: string; message: string }
  | { type: "stream_event"; turnId: string; event: ChatStreamEvent };

function emptyWritable(): WritableConversation {
  return { mode: "writable", threadId: null, turns: [] };
}

function freshViewState(): Pick<ChatState, "view" | "isStreaming"> {
  return { view: emptyWritable(), isStreaming: false };
}

function pickModel(models: string[], defaultModel?: string | null, previous?: string | null): string | null {
  if (previous && models.includes(previous)) return previous;
  if (defaultModel && models.includes(defaultModel)) return defaultModel;
  return models[0] ?? null;
}

function chatReducer(state: ChatState, action: ChatAction): ChatState {
  switch (action.type) {
    case "agent_type_selected":
      return {
        ...state,
        ...freshViewState(),
        activeAgentType: action.agentType,
        ...(action.agentType !== "customer_service"
          ? { selectedProvider: null, selectedModel: null }
          : {}),
      };

    case "customer_selected":
      return { ...state, ...freshViewState(), activeCustomerId: action.customerId };

    case "provider_selected": {
      const selectedModel = pickModel(action.models, action.defaultModel, state.selectedModel);
      return { ...state, ...freshViewState(), selectedProvider: action.provider, selectedModel };
    }

    case "model_selected":
      return { ...state, ...freshViewState(), selectedModel: action.model };

    case "history_loaded":
      return {
        ...state,
        view: { mode: "history", threadId: action.threadId, transcript: action.transcript },
        isStreaming: false,
      };

    case "new_chat":
      return { ...state, ...freshViewState() };

    case "turn_started": {
      if (state.view.mode !== "writable") return state;
      const newTurn: ConversationTurn = {
        id: action.turnId,
        userMessage: action.message,
        assistantMessage: "",
        status: "streaming",
        error: null,
        processEvents: [],
      };
      return {
        ...state,
        view: { ...state.view, turns: [...state.view.turns, newTurn] },
        isStreaming: true,
      };
    }

    case "stream_event": {
      if (state.view.mode !== "writable") return state;
      const { event, turnId } = action;

      const nextTurns = state.view.turns.map((turn): ConversationTurn => {
        if (turn.id !== turnId) return turn;
        const base: ConversationTurn = { ...turn, processEvents: [...turn.processEvents, event] };
        switch (event.type) {
          case "response_token":
            return { ...base, assistantMessage: base.assistantMessage + event.token };
          case "response_end":
            return { ...base, assistantMessage: event.response, status: "completed" };
          case "error":
            return { ...base, assistantMessage: "", error: event.error, status: "failed" };
          default:
            return base;
        }
      });

      const nextThreadId = event.thread_id || state.view.threadId;
      const isTerminal = event.type === "response_end" || event.type === "error";

      return {
        ...state,
        view: { ...state.view, threadId: nextThreadId, turns: nextTurns },
        isStreaming: !isTerminal,
      };
    }

    default:
      return state;
  }
}

function createInitialChatState(): ChatState {
  return {
    activeAgentType: "customer_service",
    activeCustomerId: null,
    selectedProvider: null,
    selectedModel: null,
    view: emptyWritable(),
    isStreaming: false,
  };
}

// ── Context ───────────────────────────────────────────────────────────────────

type ChatContextValue = ChatState & {
  selectAgentType: (agentType: AgentType) => void;
  selectCustomer: (customerId: number) => void;
  selectProvider: (provider: string, models: string[], defaultModel?: string | null) => void;
  selectModel: (model: string) => void;
  loadHistory: (threadId: string, transcript: SessionMessage[]) => void;
  newChat: () => void;
  sendMessage: (message: string) => Promise<void>;
};

const ChatContext = createContext<ChatContextValue | null>(null);

export function ChatProvider({ children }: { children: ReactNode }) {
  const [state, dispatch] = useReducer(chatReducer, undefined, createInitialChatState);
  const queryClient = useQueryClient();

  // Keep a ref to state so sendMessage doesn't stale-capture view/threadId
  const stateRef = useRef(state);
  stateRef.current = state;

  const selectAgentType = useCallback((agentType: AgentType) => {
    dispatch({ type: "agent_type_selected", agentType });
  }, []);

  const selectCustomer = useCallback((customerId: number) => {
    dispatch({ type: "customer_selected", customerId });
  }, []);

  const selectProvider = useCallback(
    (provider: string, models: string[], defaultModel?: string | null) => {
      dispatch({ type: "provider_selected", provider, models, defaultModel });
    },
    [],
  );

  const selectModel = useCallback((model: string) => {
    dispatch({ type: "model_selected", model });
  }, []);

  const loadHistory = useCallback((threadId: string, transcript: SessionMessage[]) => {
    dispatch({ type: "history_loaded", threadId, transcript });
  }, []);

  const newChat = useCallback(() => {
    dispatch({ type: "new_chat" });
  }, []);

  const sendMessage = useCallback(
    async (message: string) => {
      const { activeAgentType, activeCustomerId, selectedProvider, selectedModel, view } = stateRef.current;
      if (!selectedProvider || !selectedModel) return;
      if (activeAgentType === "customer_service" && !activeCustomerId) return;

      const turnId = crypto.randomUUID();
      dispatch({ type: "turn_started", turnId, message });

      const threadId = view.mode === "writable" ? (view.threadId ?? undefined) : undefined;

      try {
        await postChatStream(
          {
            message,
            agent_type: activeAgentType,
            ...(activeAgentType === "customer_service" && activeCustomerId ? { customer_id: activeCustomerId } : {}),
            thread_id: threadId,
            provider: selectedProvider,
            model: selectedModel,
          },
          (event) => dispatch({ type: "stream_event", turnId, event }),
        );
      } catch (err) {
        dispatch({
          type: "stream_event",
          turnId,
          event: {
            type: "error",
            thread_id: threadId ?? "",
            error: err instanceof Error ? err.message : "Stream error",
          },
        });
      }

      await queryClient.invalidateQueries({ queryKey: ["sessions"] });
    },
    [queryClient],
  );

  const value: ChatContextValue = {
    ...state,
    selectAgentType,
    selectCustomer,
    selectProvider,
    selectModel,
    loadHistory,
    newChat,
    sendMessage,
  };

  return <ChatContext.Provider value={value}>{children}</ChatContext.Provider>;
}

export function useChatContext(): ChatContextValue {
  const ctx = useContext(ChatContext);
  if (!ctx) throw new Error("useChatContext must be used inside ChatProvider");
  return ctx;
}
