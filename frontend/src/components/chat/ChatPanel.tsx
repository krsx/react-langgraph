import { useState } from "react";
import type { ConversationView } from "../../lib/state";
import { Button } from "../ui/button";

type ChatPanelProps = {
  activeCustomerName: string;
  selectedProvider: string | null;
  selectedModel: string | null;
  view: ConversationView;
  isStreaming: boolean;
  composerDisabled: boolean;
  onSend: (message: string) => Promise<void>;
};

export function ChatPanel({
  activeCustomerName,
  selectedProvider,
  selectedModel,
  view,
  isStreaming,
  composerDisabled,
  onSend,
}: ChatPanelProps) {
  const [message, setMessage] = useState("");

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const nextMessage = message.trim();
    if (!nextMessage || composerDisabled) {
      return;
    }

    setMessage("");
    await onSend(nextMessage);
  }

  return (
    <section className="flex h-full flex-col rounded-[28px] border border-border/80 bg-card/90 shadow-panel">
      <header className="border-b border-border/70 px-6 py-5">
        <p className="text-xs uppercase tracking-[0.24em] text-muted-foreground">Active Customer</p>
        <div className="mt-2 flex flex-wrap items-end justify-between gap-3">
          <div>
            <h2 className="text-2xl font-bold">{activeCustomerName}</h2>
            <p className="text-sm text-muted-foreground">
              {selectedProvider ?? "No provider"} / {selectedModel ?? "No model"}
            </p>
          </div>
          {view.mode === "history" ? (
            <span className="rounded-full bg-secondary px-3 py-1 text-xs font-semibold text-secondary-foreground">
              Read-only history
            </span>
          ) : null}
        </div>
      </header>

      <div className="flex min-h-0 flex-1 flex-col gap-4 overflow-y-auto px-6 py-5">
        {view.mode === "history" ? (
          view.transcript.map((messageItem) => (
            <article
              key={messageItem.message_id}
              className={`max-w-[80%] rounded-3xl px-4 py-3 text-sm shadow-sm ${
                messageItem.role === "human"
                  ? "ml-auto bg-primary text-primary-foreground"
                  : "bg-secondary text-secondary-foreground"
              }`}
            >
              <p>{messageItem.content}</p>
            </article>
          ))
        ) : (
          view.turns.map((turn) => (
            <div key={turn.id} className="space-y-3">
              <article className="ml-auto max-w-[80%] rounded-3xl bg-primary px-4 py-3 text-sm text-primary-foreground shadow-sm">
                <p>{turn.userMessage}</p>
              </article>
              {turn.status !== "failed" && turn.assistantMessage ? (
                <article
                  className="max-w-[80%] rounded-3xl bg-secondary px-4 py-3 text-sm text-secondary-foreground shadow-sm"
                  data-streaming={turn.status === "streaming" ? "true" : "false"}
                >
                  <p>{turn.assistantMessage}</p>
                </article>
              ) : null}
              {turn.status === "failed" ? (
                <article className="max-w-[80%] rounded-3xl border border-destructive/30 bg-destructive/10 px-4 py-3 text-sm text-destructive">
                  <p>Turn failed: {turn.error}</p>
                </article>
              ) : null}
            </div>
          ))
        )}

        {view.mode === "writable" && view.turns.length === 0 ? (
          <div className="m-auto rounded-[28px] border border-dashed border-border bg-background/60 px-8 py-10 text-center">
            <p className="text-lg font-semibold">Start a fresh Conversation Session</p>
            <p className="mt-2 text-sm text-muted-foreground">
              Ask about orders, complaints, or stored customer memory.
            </p>
          </div>
        ) : null}
      </div>

      <form className="border-t border-border/70 px-6 py-5" onSubmit={handleSubmit}>
        <label className="mb-2 block text-xs uppercase tracking-[0.24em] text-muted-foreground" htmlFor="chat-message">
          Message
        </label>
        <div className="flex flex-col gap-3 md:flex-row">
          <textarea
            id="chat-message"
            aria-label="Message composer"
            className="min-h-24 flex-1 rounded-2xl border border-border bg-background/70 px-4 py-3 text-sm outline-none transition focus:border-primary focus:ring-2 focus:ring-primary/20 disabled:cursor-not-allowed disabled:opacity-50"
            placeholder={view.mode === "history" ? "Select New Chat to continue." : "Ask the agent a question."}
            value={message}
            disabled={composerDisabled}
            onChange={(event) => setMessage(event.target.value)}
          />
          <Button type="submit" disabled={composerDisabled || isStreaming} className="h-fit min-w-28">
            {isStreaming ? "Streaming..." : "Send"}
          </Button>
        </div>
      </form>
    </section>
  );
}
