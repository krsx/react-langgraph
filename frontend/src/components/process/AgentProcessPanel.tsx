import { useState } from "react";
import { cn } from "../../lib/utils";
import type {
  ChatStreamEvent,
  PlannerToolCall,
} from "../../lib/types";
import { Button } from "../ui/button";

type AgentProcessPanelProps = {
  activeCustomerName: string;
  selectedProvider: string | null;
  selectedModel: string | null;
  threadId: string | null;
  events: ChatStreamEvent[];
};

type AgentProcessPanelWrapperProps = AgentProcessPanelProps & {
  isOpen: boolean;
  onToggle: () => void;
};

type StepCard =
  | {
      kind: "memory_loaded";
      title: string;
      summary: string;
      detail: string;
    }
  | {
      kind: "planner";
      title: string;
      summary: string;
      detail: string;
      toolCalls: PlannerToolCall[];
    }
  | {
      kind: "tool";
      title: string;
      summary: string;
      detail: string;
      toolCalls: PlannerToolCall[];
    }
  | {
      kind: "verifier";
      title: string;
      summary: string;
      detail: string;
    }
  | {
      kind: "memory_updated";
      title: string;
      summary: string;
      detail: string;
    };

function formatJson(value: unknown): string {
  return JSON.stringify(value, null, 2);
}

function buildStepCards(events: ChatStreamEvent[]): StepCard[] {
  const cards: StepCard[] = [];
  let latestToolCalls: PlannerToolCall[] = [];

  for (const event of events) {
    switch (event.type) {
      case "memory_loaded": {
        const contextCount = event.memory_context.length;
        cards.push({
          kind: "memory_loaded",
          title: "Memory Loaded",
          summary: contextCount > 0
            ? `${contextCount} memory item${contextCount === 1 ? "" : "s"} loaded`
            : "No stored memory loaded for this turn",
          detail: contextCount > 0
            ? formatJson(event.memory_context)
            : "[]",
        });
        break;
      }
      case "planner_result": {
        latestToolCalls = event.tool_calls;
        cards.push({
          kind: "planner",
          title: "Planner",
          summary: event.content || "Planner returned without visible reasoning text.",
          detail: formatJson({
            content: event.content,
            tool_calls: event.tool_calls,
          }),
          toolCalls: event.tool_calls,
        });
        break;
      }
      case "tool_start": {
        cards.push({
          kind: "tool",
          title: "Tool Result",
          summary: latestToolCalls.length > 0
            ? `${latestToolCalls.length} planned tool call${latestToolCalls.length === 1 ? "" : "s"} executing`
            : "Tool execution started",
          detail: "Awaiting tool result payload.",
          toolCalls: latestToolCalls,
        });
        break;
      }
      case "tool_result": {
        const existing = cards[cards.length - 1];
        if (existing?.kind === "tool" && existing.detail === "Awaiting tool result payload.") {
          existing.summary = event.results;
          existing.detail = event.results;
          existing.toolCalls = latestToolCalls;
          break;
        }

        cards.push({
          kind: "tool",
          title: "Tool Result",
          summary: event.results,
          detail: event.results,
          toolCalls: latestToolCalls,
        });
        break;
      }
      case "verifier_result": {
        const verdict = event.valid === true ? "passed" : event.valid === false ? "failed" : "returned no verdict";
        const summary = event.checks.length > 0
          ? `Verifier ${verdict}: ${event.checks.join(", ")}`
          : `Verifier ${verdict}`;
        cards.push({
          kind: "verifier",
          title: "Verifier",
          summary: event.override_message ? `${summary}. ${event.override_message}` : summary,
          detail: formatJson({
            valid: event.valid,
            checks: event.checks,
            override_message: event.override_message,
          }),
        });
        break;
      }
      case "memory_updated":
        cards.push({
          kind: "memory_updated",
          title: "Memory Updated",
          summary: "Turn memory update completed",
          detail: formatJson(event),
        });
        break;
      default:
        break;
    }
  }

  return cards;
}

function ExecutionContextCard({
  activeCustomerName,
  selectedProvider,
  selectedModel,
  threadId,
}: Pick<
  AgentProcessPanelProps,
  "activeCustomerName" | "selectedProvider" | "selectedModel" | "threadId"
>) {
  return (
    <section className="rounded-[24px] border border-border/70 bg-background/80 p-4 shadow-sm">
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="text-xs uppercase tracking-[0.24em] text-muted-foreground">Execution Context</p>
          <h3 className="mt-2 text-lg font-bold">Current Turn</h3>
        </div>
        <span className="rounded-full bg-secondary px-3 py-1 text-xs font-semibold text-secondary-foreground">
          Live
        </span>
      </div>

      <dl className="mt-4 grid gap-3 text-sm sm:grid-cols-2">
        <div className="rounded-2xl bg-card px-3 py-3">
          <dt className="text-xs uppercase tracking-[0.16em] text-muted-foreground">Customer</dt>
          <dd className="mt-1 font-medium text-foreground">{activeCustomerName}</dd>
        </div>
        <div className="rounded-2xl bg-card px-3 py-3">
          <dt className="text-xs uppercase tracking-[0.16em] text-muted-foreground">Provider</dt>
          <dd className="mt-1 font-medium text-foreground">{selectedProvider ?? "Not selected"}</dd>
        </div>
        <div className="rounded-2xl bg-card px-3 py-3">
          <dt className="text-xs uppercase tracking-[0.16em] text-muted-foreground">Model</dt>
          <dd className="mt-1 font-medium text-foreground">{selectedModel ?? "Not selected"}</dd>
        </div>
        <div className="rounded-2xl bg-card px-3 py-3">
          <dt className="text-xs uppercase tracking-[0.16em] text-muted-foreground">Conversation Session</dt>
          <dd className="mt-1 font-medium text-foreground">{threadId ?? "Pending first stream event"}</dd>
        </div>
      </dl>
    </section>
  );
}

type ProcessStepCardProps = {
  card: StepCard;
  index: number;
};

function ProcessStepCard({ card, index }: ProcessStepCardProps) {
  const [expanded, setExpanded] = useState(false);

  return (
    <article className="rounded-[24px] border border-border/70 bg-background/80 p-4 shadow-sm">
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="text-xs uppercase tracking-[0.24em] text-muted-foreground">
            Step {index + 1}
          </p>
          <h3 className="mt-2 text-lg font-bold">{card.title}</h3>
        </div>
        <Button
          variant="outline"
          aria-expanded={expanded}
          aria-controls={`process-step-detail-${index}`}
          onClick={() => setExpanded((current) => !current)}
        >
          {expanded ? "Hide detail" : "Show detail"}
        </Button>
      </div>

      <p className="mt-4 text-sm leading-6 text-foreground">{card.summary}</p>

      {"toolCalls" in card && card.toolCalls.length > 0 ? (
        <div className="mt-4 space-y-3">
          <p className="text-xs uppercase tracking-[0.16em] text-muted-foreground">Planned tool calls</p>
          {card.toolCalls.map((toolCall, toolIndex) => (
            <div key={`${toolCall.name}-${toolIndex}`} className="rounded-2xl bg-card px-3 py-3">
              <p className="font-medium text-foreground">{toolCall.name}</p>
              <pre className="mt-2 overflow-x-auto text-xs leading-5 text-muted-foreground">
                {formatJson(toolCall.args)}
              </pre>
            </div>
          ))}
        </div>
      ) : null}

      {expanded ? (
        <pre
          id={`process-step-detail-${index}`}
          className="mt-4 overflow-x-auto rounded-2xl bg-card px-3 py-3 text-xs leading-5 text-muted-foreground"
        >
          {card.detail}
        </pre>
      ) : null}
    </article>
  );
}

export function AgentProcessPanelContent({
  activeCustomerName,
  selectedProvider,
  selectedModel,
  threadId,
  events,
}: AgentProcessPanelProps) {
  const cards = buildStepCards(events);

  return (
    <div className="space-y-5 overflow-y-auto">
      <ExecutionContextCard
        activeCustomerName={activeCustomerName}
        selectedProvider={selectedProvider}
        selectedModel={selectedModel}
        threadId={threadId}
      />

      {cards.length > 0 ? (
        cards.map((card, index) => (
          <ProcessStepCard key={`${card.kind}-${index}`} card={card} index={index} />
        ))
      ) : (
        <section className="rounded-[24px] border border-dashed border-border bg-background/60 px-4 py-6 text-sm text-muted-foreground">
          Current-turn process steps will appear here as SSE events arrive.
        </section>
      )}
    </div>
  );
}

export function AgentProcessPanel({
  isOpen,
  activeCustomerName,
  selectedProvider,
  selectedModel,
  threadId,
  events,
  onToggle,
}: AgentProcessPanelWrapperProps) {
  return (
    <aside
      className={cn(
        "flex h-full flex-col rounded-[28px] border border-border/80 bg-card/90 shadow-panel transition-all",
        isOpen ? "p-5" : "items-center p-3",
      )}
    >
      <div className={cn("flex items-center gap-3", isOpen ? "justify-between" : "flex-col")}>
        {isOpen ? (
          <div>
            <p className="text-xs uppercase tracking-[0.24em] text-muted-foreground">Right Panel</p>
            <h2 className="text-xl font-bold">Agent Process Panel</h2>
          </div>
        ) : null}
        <Button variant="outline" aria-expanded={isOpen} onClick={onToggle}>
          {isOpen ? "Collapse" : "Expand"}
        </Button>
      </div>

      {isOpen ? (
        <div className="mt-5">
          <AgentProcessPanelContent
            activeCustomerName={activeCustomerName}
            selectedProvider={selectedProvider}
            selectedModel={selectedModel}
            threadId={threadId}
            events={events}
          />
        </div>
      ) : null}
    </aside>
  );
}
