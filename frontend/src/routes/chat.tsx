import { useState } from "react";
import { Brain, X } from "lucide-react";
import { ChatHeader } from "@/components/chat/ChatHeader";
import { ConversationArea } from "@/components/chat/ConversationArea";
import { AgentProcessPanel } from "@/components/process/AgentProcessPanel";
import {
  ResizableHandle,
  ResizablePanel,
  ResizablePanelGroup,
  usePanelRef,
} from "@/components/ui/resizable";
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
  const [isPanelOpen, setIsPanelOpen] = useState(false);
  const panelRef = usePanelRef();

  const isHistoryMode = view.mode === "history";
  const composerDisabled =
    isHistoryMode ||
    isStreaming ||
    activeCustomerId === null ||
    selectedProvider === null ||
    selectedModel === null;

  const latestTurn =
    view.mode === "writable" && view.turns.length > 0
      ? view.turns[view.turns.length - 1]
      : null;
  const processEvents = latestTurn?.processEvents ?? [];

  async function handleSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const text = composer.trim();
    if (!text || composerDisabled) return;
    setComposer("");
    await sendMessage(text);
  }

  function openPanel() {
    setIsPanelOpen(true);
    panelRef.current?.expand();
  }

  function closePanel() {
    setIsPanelOpen(false);
    panelRef.current?.collapse();
  }

  return (
    <div className="flex h-full flex-col">
      <ChatHeader />

      <ResizablePanelGroup orientation="horizontal" className="min-h-0 flex-1">
        {/* ── Conversation panel ── */}
        <ResizablePanel id="conversation" defaultSize={100}>
          <div className="relative flex h-full flex-col">
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
                <div className="flex items-center justify-between">
                  {!isPanelOpen && (
                    <Button
                      type="button"
                      variant="ghost"
                      size="sm"
                      aria-label="Open Agent Process Panel"
                      onClick={openPanel}
                      className="gap-1.5 text-xs text-muted-foreground hover:text-foreground"
                    >
                      <Brain className="size-3.5" />
                      Agent Process
                    </Button>
                  )}
                  <div className="ml-auto">
                    <Button
                      type="submit"
                      disabled={composerDisabled || !composer.trim()}
                    >
                      {isStreaming ? "Streaming…" : "Send"}
                    </Button>
                  </div>
                </div>
              </div>
            </form>
          </div>
        </ResizablePanel>

        {/* ── Resize handle ── */}
        <ResizableHandle withHandle />

        {/* ── Agent Process Panel ── */}
        <ResizablePanel
          id="process"
          collapsible
          collapsedSize={0}
          defaultSize={0}
          minSize={20}
          panelRef={panelRef}
        >
          {isPanelOpen && (
            <div className="flex h-full flex-col border-l border-border/60">
              {/* Panel header */}
              <div className="flex shrink-0 items-center justify-between border-b border-border/60 bg-background/95 px-4 py-2.5">
                <div className="flex items-center gap-2">
                  <Brain className="size-3.5 text-violet-500" />
                  <div>
                    <p className="text-[10px] font-semibold uppercase tracking-widest text-muted-foreground">
                      Trace
                    </p>
                    <h2 className="text-sm font-semibold leading-none">Agent Process</h2>
                  </div>
                </div>
                <Button
                  type="button"
                  variant="ghost"
                  size="sm"
                  aria-label="Close Agent Process Panel"
                  onClick={closePanel}
                  className="size-7 p-0"
                >
                  <X className="size-3.5" />
                </Button>
              </div>

              {/* Panel content */}
              <div className="min-h-0 flex-1 overflow-y-auto">
                <AgentProcessPanel
                  events={processEvents}
                  isHistoryMode={isHistoryMode}
                  isStreaming={isStreaming}
                />
              </div>
            </div>
          )}
        </ResizablePanel>
      </ResizablePanelGroup>
    </div>
  );
}
