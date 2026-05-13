import { startTransition, useEffect, useReducer } from "react";
import {
  getCustomers,
  getProviders,
  getSessionMessages,
  getSessions,
  postChatStream,
} from "./lib/api";
import {
  appReducer,
  createInitialState,
  getFilteredSessions,
} from "./lib/state";
import { ChatPanel } from "./components/chat/ChatPanel";
import { AgentProcessPanel } from "./components/process/AgentProcessPanel";
import { Sidebar } from "./components/sidebar/Sidebar";

export default function App() {
  const [state, dispatch] = useReducer(appReducer, undefined, createInitialState);

  useEffect(() => {
    let cancelled = false;

    async function bootstrap() {
      const [customers, providers, sessions] = await Promise.all([
        getCustomers(),
        getProviders(),
        getSessions(),
      ]);

      if (cancelled) {
        return;
      }

      dispatch({
        type: "bootstrap_loaded",
        customers,
        providers,
        sessions,
      });
    }

    void bootstrap();

    return () => {
      cancelled = true;
    };
  }, []);

  const activeCustomer = state.customers.find(
    (customer) => customer.customer_id === state.activeCustomerId,
  );
  const filteredSessions = getFilteredSessions(state);

  async function refreshSessions() {
    const sessions = await getSessions();
    dispatch({ type: "sessions_loaded", sessions });
  }

  async function handleSend(message: string) {
    if (state.view.mode !== "writable" || state.activeCustomerId === null) {
      return;
    }

    const turnId = crypto.randomUUID();
    dispatch({ type: "message_sent", turnId, message });

    try {
      await postChatStream(
        {
          message,
          customer_id: state.activeCustomerId,
          thread_id: state.view.threadId ?? undefined,
          provider: state.selectedProvider ?? undefined,
        },
        (event) => {
          dispatch({ type: "stream_event_received", turnId, event });
        },
      );
    } catch (error) {
      dispatch({
        type: "stream_event_received",
        turnId,
        event: {
          type: "error",
          thread_id: state.view.threadId ?? "",
          error: error instanceof Error ? error.message : "Unknown stream error",
        },
      });
    } finally {
      await refreshSessions();
    }
  }

  async function handleSessionSelect(threadId: string) {
    const transcript = await getSessionMessages(threadId);
    startTransition(() => {
      dispatch({ type: "history_session_loaded", threadId, transcript });
    });
  }

  return (
    <main className="min-h-screen p-4 md:p-6">
      <div
        className={`mx-auto grid min-h-[calc(100vh-2rem)] max-w-[1600px] grid-cols-1 gap-4 ${
          state.rightPanelOpen
            ? "xl:grid-cols-[320px_minmax(0,1fr)_320px]"
            : "xl:grid-cols-[320px_minmax(0,1fr)_88px]"
        }`}
      >
        <Sidebar
          customers={state.customers}
          activeCustomerId={state.activeCustomerId}
          providers={state.providers}
          selectedProvider={state.selectedProvider}
          selectedModel={state.selectedModel}
          sessions={filteredSessions}
          readOnly={state.view.mode === "history"}
          onCustomerSelect={(customerId) =>
            dispatch({ type: "customer_selected", customerId })
          }
          onProviderSelect={(provider) =>
            dispatch({ type: "provider_selected", provider })
          }
          onModelSelect={(model) => dispatch({ type: "model_selected", model })}
          onSessionSelect={(threadId) => {
            void handleSessionSelect(threadId);
          }}
          onNewChat={() => dispatch({ type: "new_chat_requested" })}
        />

        <ChatPanel
          activeCustomerName={activeCustomer?.name ?? "Loading customer..."}
          selectedProvider={state.selectedProvider}
          selectedModel={state.selectedModel}
          view={state.view}
          isStreaming={state.stream.status === "streaming"}
          composerDisabled={
            state.view.mode === "history" ||
            state.activeCustomerId === null ||
            !state.selectedProvider ||
            !state.selectedModel
          }
          onSend={handleSend}
        />

        <AgentProcessPanel
          isOpen={state.rightPanelOpen}
          activeCustomerName={activeCustomer?.name ?? "Loading customer..."}
          selectedProvider={state.selectedProvider}
          selectedModel={state.selectedModel}
          threadId={state.view.threadId}
          events={state.stream.processEvents}
          onToggle={() => dispatch({ type: "right_panel_toggled" })}
        />
      </div>
    </main>
  );
}
