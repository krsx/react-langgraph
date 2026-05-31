import { useEffect, useRef } from "react";
import ReactMarkdown from "react-markdown";
import { useChatContext } from "@/lib/chat-context";

export function ConversationArea() {
  const { view, isStreaming } = useChatContext();
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [view]);

  if (view.mode === "history") {
    return (
      <div
        data-testid="conversation-scroll-region"
        className="flex min-h-0 flex-1 flex-col gap-3 overflow-y-auto px-4 py-4 overscroll-contain"
      >
        {view.transcript.map((msg) => (
          <MessageBubble
            key={msg.message_id}
            role={msg.role}
            content={msg.content}
            isStreaming={false}
          />
        ))}
        <div ref={bottomRef} />
      </div>
    );
  }

  const { turns } = view;

  if (turns.length === 0) {
    return (
      <div
        data-testid="conversation-scroll-region"
        className="flex min-h-0 flex-1 flex-col items-center justify-center overflow-y-auto p-8 overscroll-contain"
      >
        <EmptyState />
      </div>
    );
  }

  return (
    <div
      data-testid="conversation-scroll-region"
      className="flex min-h-0 flex-1 flex-col gap-3 overflow-y-auto px-4 py-4 overscroll-contain"
    >
      {turns.map((turn) => (
        <div key={turn.id} className="flex flex-col gap-2">
          <MessageBubble role="human" content={turn.userMessage} isStreaming={false} />

          {turn.status === "failed" ? (
            <div className="max-w-[85%] self-start rounded-none border border-destructive/30 bg-destructive/10 px-3 py-2 text-sm text-destructive">
              {turn.error ?? "An error occurred."}
            </div>
          ) : turn.assistantMessage ? (
            <MessageBubble
              role="ai"
              content={turn.assistantMessage}
              isStreaming={turn.status === "streaming"}
            />
          ) : isStreaming && turn.status === "streaming" ? (
            <ThinkingIndicator />
          ) : null}
        </div>
      ))}
      <div ref={bottomRef} />
    </div>
  );
}

function MessageBubble({
  role,
  content,
  isStreaming,
}: {
  role: "human" | "ai";
  content: string;
  isStreaming: boolean;
}) {
  if (role === "human") {
    return (
      <div className="ml-auto max-w-[85%] rounded-none bg-primary px-3.5 py-2 text-sm text-primary-foreground shadow-sm">
        {content}
      </div>
    );
  }

  return (
    <div
      className="prose prose-sm dark:prose-invert prose-code:text-red-500 prose-a:text-red-500 prose-strong:text-red-500 prose-em:text-red-500 max-w-[85%] self-start rounded-none bg-secondary px-3.5 py-2 text-sm text-secondary-foreground shadow-sm"
      data-streaming={isStreaming ? "true" : undefined}
    >
      <ReactMarkdown>{content}</ReactMarkdown>
    </div>
  );
}

function ThinkingIndicator() {
  return (
    <div className="flex max-w-[85%] items-center gap-1 self-start rounded-none bg-secondary px-3.5 py-2">
      <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-muted-foreground [animation-delay:0ms]" />
      <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-muted-foreground [animation-delay:150ms]" />
      <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-muted-foreground [animation-delay:300ms]" />
    </div>
  );
}

function EmptyState() {
  return (
    <div className="flex flex-col items-center gap-3 rounded-xl border border-dashed border-border/60 bg-muted/30 px-8 py-12 text-center">
      <div className="flex size-12 items-center justify-center rounded-full bg-primary/10">
        <svg className="size-6 text-primary" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z" />
        </svg>
      </div>
      <div>
        <p className="text-sm font-semibold text-foreground">Start a fresh Conversation Session</p>
        <p className="mt-1 text-xs text-muted-foreground">
          Ask about orders, complaints, or customer memory.
        </p>
      </div>
    </div>
  );
}
