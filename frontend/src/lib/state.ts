import type {
  ChatStreamEvent,
  Customer,
  ProviderCatalog,
  ProviderState,
  SessionMessage,
  SessionSummary,
} from "./types";

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

export type AppState = {
  customers: Customer[];
  providers: ProviderCatalog;
  sessions: SessionSummary[];
  activeCustomerId: number | null;
  selectedProvider: string | null;
  selectedModel: string | null;
  view: ConversationView;
  stream: {
    status: "idle" | "streaming" | "error";
    currentTurnId: string | null;
    processEvents: ChatStreamEvent[];
  };
  rightPanelOpen: boolean;
};

export type AppAction =
  | {
      type: "bootstrap_loaded";
      customers: Customer[];
      providers: ProviderCatalog;
      sessions: SessionSummary[];
    }
  | {
      type: "sessions_loaded";
      sessions: SessionSummary[];
    }
  | {
      type: "customer_selected";
      customerId: number;
    }
  | {
      type: "provider_selected";
      provider: string;
    }
  | {
      type: "model_selected";
      model: string;
    }
  | {
      type: "history_session_loaded";
      threadId: string;
      transcript: SessionMessage[];
    }
  | {
      type: "new_chat_requested";
    }
  | {
      type: "message_sent";
      turnId: string;
      message: string;
    }
  | {
      type: "stream_event_received";
      turnId: string;
      event: ChatStreamEvent;
    }
  | {
      type: "right_panel_toggled";
    };

function chooseProvider(
  providers: ProviderCatalog,
  previousProvider: string | null,
): string | null {
  if (previousProvider && providers[previousProvider]) {
    return previousProvider;
  }

  const available = Object.entries(providers).find(([, provider]) => provider.available && provider.models.length > 0);
  if (available) {
    return available[0];
  }

  return Object.keys(providers)[0] ?? null;
}

function chooseModel(provider: ProviderState | undefined, previousModel: string | null): string | null {
  if (!provider) {
    return null;
  }

  if (previousModel && provider.models.includes(previousModel)) {
    return previousModel;
  }

  return provider.models[0] ?? null;
}

function emptyWritableView(): WritableConversation {
  return { mode: "writable", threadId: null, turns: [] };
}

export function createInitialState(): AppState {
  return {
    customers: [],
    providers: {},
    sessions: [],
    activeCustomerId: null,
    selectedProvider: null,
    selectedModel: null,
    view: emptyWritableView(),
    stream: {
      status: "idle",
      currentTurnId: null,
      processEvents: [],
    },
    rightPanelOpen: true,
  };
}

function resetConversation(state: AppState, patch?: Partial<AppState>): AppState {
  return {
    ...state,
    ...patch,
    view: emptyWritableView(),
    stream: {
      status: "idle",
      currentTurnId: null,
      processEvents: [],
    },
  };
}

function updateTurn(
  turns: ConversationTurn[],
  turnId: string,
  updater: (turn: ConversationTurn) => ConversationTurn,
): ConversationTurn[] {
  return turns.map((turn) => (turn.id === turnId ? updater(turn) : turn));
}

export function appReducer(state: AppState, action: AppAction): AppState {
  switch (action.type) {
    case "bootstrap_loaded": {
      const selectedProvider = chooseProvider(action.providers, state.selectedProvider);
      const selectedModel = chooseModel(
        selectedProvider ? action.providers[selectedProvider] : undefined,
        state.selectedModel,
      );
      const activeCustomerId = state.activeCustomerId ?? action.customers[0]?.customer_id ?? null;

      return {
        ...state,
        customers: action.customers,
        providers: action.providers,
        sessions: action.sessions,
        activeCustomerId,
        selectedProvider,
        selectedModel,
      };
    }
    case "sessions_loaded":
      return {
        ...state,
        sessions: action.sessions,
      };
    case "customer_selected":
      return resetConversation(state, { activeCustomerId: action.customerId });
    case "provider_selected": {
      const selectedModel = chooseModel(state.providers[action.provider], state.selectedModel);
      return resetConversation(state, {
        selectedProvider: action.provider,
        selectedModel,
      });
    }
    case "model_selected":
      return resetConversation(state, { selectedModel: action.model });
    case "history_session_loaded":
      return {
        ...state,
        view: {
          mode: "history",
          threadId: action.threadId,
          transcript: action.transcript,
        },
        stream: {
          status: "idle",
          currentTurnId: null,
          processEvents: [],
        },
      };
    case "new_chat_requested":
      return resetConversation(state);
    case "message_sent":
      if (state.view.mode !== "writable") {
        return state;
      }

      return {
        ...state,
        view: {
          ...state.view,
          turns: [
            ...state.view.turns,
            {
              id: action.turnId,
              userMessage: action.message,
              assistantMessage: "",
              status: "streaming",
              error: null,
              processEvents: [],
            },
          ],
        },
        stream: {
          status: "streaming",
          currentTurnId: action.turnId,
          processEvents: [],
        },
      };
    case "stream_event_received":
      if (state.view.mode !== "writable") {
        return state;
      }

      const nextView: WritableConversation = {
        ...state.view,
        threadId: action.event.thread_id || state.view.threadId,
        turns: updateTurn(state.view.turns, action.turnId, (turn) => {
          const baseTurn = {
            ...turn,
            processEvents: [...turn.processEvents, action.event],
          };

          switch (action.event.type) {
            case "response_token":
              return {
                ...baseTurn,
                assistantMessage: `${baseTurn.assistantMessage}${action.event.token}`,
              };
            case "response_end":
              return {
                ...baseTurn,
                assistantMessage: action.event.response,
                status: "completed",
              };
            case "error":
              return {
                ...baseTurn,
                assistantMessage: "",
                error: action.event.error,
                status: "failed",
              };
            default:
              return baseTurn;
          }
        }),
      };

      const terminal = action.event.type === "response_end" || action.event.type === "error";

      return {
        ...state,
        view: nextView,
        stream: {
          status: action.event.type === "error" ? "error" : terminal ? "idle" : state.stream.status,
          currentTurnId: terminal ? null : action.turnId,
          processEvents: [...state.stream.processEvents, action.event],
        },
      };
    case "right_panel_toggled":
      return {
        ...state,
        rightPanelOpen: !state.rightPanelOpen,
      };
    default:
      return state;
  }
}

export function getFilteredSessions(state: AppState): SessionSummary[] {
  if (state.activeCustomerId === null) {
    return [];
  }

  return state.sessions.filter((session) => session.customer_id === state.activeCustomerId);
}
