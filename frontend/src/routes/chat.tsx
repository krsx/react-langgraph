import { useState } from "react";
import { ChatHeader } from "@/components/chat/ChatHeader";
import { ConversationArea } from "@/components/chat/ConversationArea";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { useChatContext } from "@/lib/chat-context";

export function ChatPage() {
  const {
    activeCustomerId,
    selectedProvider,
    selectedModel,
    view,
    isStreaming,
    sendMessage,
  } = useChatContext();

  const [composer, setComposer] = useState("");

  const isHistoryMode = view.mode === "history";
  const composerDisabled =
    isHistoryMode ||
    isStreaming ||
    activeCustomerId === null ||
    selectedProvider === null ||
    selectedModel === null;

  async function handleSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const text = composer.trim();
    if (!text || composerDisabled) return;
    setComposer("");
    await sendMessage(text);
  }

  return (
    <div className="flex h-full flex-col">
      <ChatHeader />

      <ConversationArea />

      <form
        className="border-t border-border bg-background/95 px-4 py-3"
        onSubmit={handleSubmit}
      >
        <div className="flex flex-col gap-2">
          <Textarea
            id="chat-message"
            aria-label="Message"
            placeholder={
              isHistoryMode
                ? 'Click "New Chat" to start a new conversation.'
                : !activeCustomerId || !selectedProvider || !selectedModel
                  ? "Select a customer, provider, and model to begin."
                  : "Ask the agent a question..."
            }
            value={composer}
            disabled={composerDisabled}
            onChange={(e) => setComposer(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                e.currentTarget.form?.requestSubmit();
              }
            }}
            className="min-h-[72px] resize-none"
          />
          <div className="flex justify-end">
            <Button type="submit" disabled={composerDisabled || !composer.trim()}>
              {isStreaming ? "Streaming…" : "Send"}
            </Button>
          </div>
        </div>
      </form>
    </div>
  );
}
