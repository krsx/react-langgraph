import { useState } from "react";
import { ArrowUp, Brain, Loader2, X } from "lucide-react";
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
import { Input } from "@/components/ui/input";
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
  const [isPanelOpen, setIsPanelOpen] = useState(true);
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
    <div className="flex h-full flex-col overflow-hidden">
      <ChatHeader />

      <ResizablePanelGroup orientation="horizontal" className="min-h-0 flex-1">
        {/* ── Conversation panel ── */}
        <ResizablePanel id="conversation" defaultSize={68} className="min-h-0">
          <div className="relative flex h-full min-h-0 flex-col overflow-hidden">
            <ConversationArea />

            <form
              data-testid="chat-composer"
              className="sticky bottom-0 z-20 border-t border-border bg-background/95 px-4 py-3 backdrop-blur supports-[backdrop-filter]:bg-background/80"
              onSubmit={handleSubmit}
            >
              <div className="flex items-center gap-2 rounded-xl border border-input bg-background px-2 py-1 transition-all focus-within:border-ring focus-within:ring-1 focus-within:ring-ring/50">
                {!isPanelOpen && (
                  <Button
                    type="button"
                    variant="ghost"
                    size="icon"
                    aria-label="Open Agent Process Panel"
                    onClick={openPanel}
                    className="size-8 shrink-0 text-muted-foreground hover:text-foreground"
                  >
                    <Brain className="size-4" />
                  </Button>
                )}
                <Input
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
                    if (e.key === "Enter") {
                      e.preventDefault();
                      e.currentTarget.form?.requestSubmit();
                    }
                  }}
                  className="h-9 flex-1 border-0 bg-transparent px-1 shadow-none focus-visible:ring-0 text-sm"
                />
                <Button
                  type="submit"
                  size="icon"
                  disabled={composerDisabled || !composer.trim()}
                  className="size-8 shrink-0 rounded-lg"
                  aria-label="Send message"
                >
                  {isStreaming ? (
                    <Loader2 className="size-4 animate-spin" />
                  ) : (
                    <ArrowUp className="size-4" />
                  )}
                </Button>
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
          defaultSize={32}
          minSize={20}
          className="min-h-0"
          panelRef={panelRef}
        >
          {isPanelOpen && (
            <div className="flex h-full min-h-0 flex-col border-l border-border/60">
              {/* Panel header */}
              <div
                data-testid="agent-process-header"
                className="sticky top-0 z-20 flex shrink-0 items-center justify-between border-b border-border/60 bg-background/95 px-4 py-2.5 backdrop-blur supports-[backdrop-filter]:bg-background/80"
              >
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
              <div
                data-testid="agent-process-scroll-region"
                className="min-h-0 flex-1 overflow-y-auto overscroll-contain"
              >
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
