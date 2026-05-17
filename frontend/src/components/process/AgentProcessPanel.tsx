import { useState } from "react";
import {
  Brain,
  CheckCircle2,
  Database,
  Save,
  Shield,
  Wrench,
  XCircle,
} from "lucide-react";
import { cn } from "@/lib/utils";
import type { ChatStreamEvent, JsonValue, MemoryContextEntry, PlannerToolCall } from "@/lib/types";

// ── Types ──────────────────────────────────────────────────────────────────────

type StepStatus = "success" | "failed" | "running";

type StepCard =
  | {
      kind: "memory_loaded";
      summary: string;
      context: MemoryContextEntry[];
      rawJson: string;
      status: StepStatus;
    }
  | {
      kind: "planner";
      summary: string;
      content: string;
      toolCalls: PlannerToolCall[];
      rawJson: string;
      status: StepStatus;
    }
  | {
      kind: "tool";
      summary: string;
      toolName: string;
      results: JsonValue;
      rawJson: string;
      status: StepStatus;
    }
  | {
      kind: "verifier";
      summary: string;
      valid: boolean | null;
      checks: string[];
      overrideMessage: string | null;
      rawJson: string;
      status: StepStatus;
    }
  | {
      kind: "memory_updated";
      summary: string;
      key: string;
      value: string;
      rawJson: string;
      status: StepStatus;
    };

// ── Step building ──────────────────────────────────────────────────────────────

function buildSteps(events: ChatStreamEvent[], isStreaming: boolean): StepCard[] {
  const steps: StepCard[] = [];

  for (const event of events) {
    switch (event.type) {
      case "memory_loaded": {
        const n = event.memory_context.length;
        steps.push({
          kind: "memory_loaded",
          summary:
            n === 0
              ? "No stored memory for this customer"
              : `${n} memory item${n === 1 ? "" : "s"} loaded`,
          context: event.memory_context,
          rawJson: JSON.stringify({ memory_context: event.memory_context }, null, 2),
          status: "success",
        });
        break;
      }

      case "planner_start": {
        steps.push({
          kind: "planner",
          summary: "Agent is reasoning…",
          content: "",
          toolCalls: [],
          rawJson: "{}",
          status: "running",
        });
        break;
      }

      case "planner_result": {
        const firstTool = event.tool_calls[0];
        const summary = firstTool
          ? `Agent decided to call ${firstTool.name}`
          : "Agent reasoning complete";
        const plannerStep = {
          kind: "planner" as const,
          summary,
          content: event.content,
          toolCalls: event.tool_calls,
          rawJson: JSON.stringify(
            { content: event.content, tool_calls: event.tool_calls },
            null,
            2,
          ),
          status: "success" as StepStatus,
        };
        const prev = steps[steps.length - 1];
        if (prev?.kind === "planner" && prev.status === "running") {
          steps[steps.length - 1] = plannerStep;
        } else {
          steps.push(plannerStep);
        }
        break;
      }

      case "tool_start": {
        steps.push({
          kind: "tool",
          summary: "Tool execution started",
          toolName: "",
          results: null,
          rawJson: "{}",
          status: "running",
        });
        break;
      }

      case "tool_result": {
        const last = steps[steps.length - 1];
        const summary = event.tool_name
          ? `Tool ${event.tool_name} completed`
          : "Tool execution completed";
        const rawJson = JSON.stringify(
          { tool_name: event.tool_name, results: event.results },
          null,
          2,
        );
        if (last?.kind === "tool" && last.status === "running") {
          steps[steps.length - 1] = {
            ...last,
            toolName: event.tool_name,
            summary,
            results: event.results,
            rawJson,
            status: "success",
          };
          break;
        }
        steps.push({
          kind: "tool",
          summary,
          toolName: event.tool_name,
          results: event.results,
          rawJson,
          status: "success",
        });
        break;
      }

      case "verifier_result": {
        const verdict =
          event.valid === true ? "passed" : event.valid === false ? "failed" : "returned no verdict";
        const checks = event.checks.length;
        const summary =
          checks > 0
            ? `Verifier ${verdict} (${checks}/${checks} check${checks === 1 ? "" : "s"})`
            : `Verifier ${verdict}`;
        steps.push({
          kind: "verifier",
          summary,
          valid: event.valid,
          checks: event.checks,
          overrideMessage: event.override_message,
          rawJson: JSON.stringify(
            {
              valid: event.valid,
              checks: event.checks,
              override_message: event.override_message,
            },
            null,
            2,
          ),
          status: event.valid === false ? "failed" : "success",
        });
        break;
      }

      case "memory_updated": {
        steps.push({
          kind: "memory_updated",
          summary: `Stored ${event.key} in customer memory`,
          key: event.key,
          value: event.value,
          rawJson: JSON.stringify({ key: event.key, value: event.value }, null, 2),
          status: "success",
        });
        break;
      }

      default:
        break;
    }
  }

  // Mark last step as running if still streaming
  if (isStreaming && steps.length > 0) {
    steps[steps.length - 1].status = "running";
  }

  return steps;
}

// ── Sub-components ─────────────────────────────────────────────────────────────

type StepIconProps = { kind: StepCard["kind"] };

const STEP_ICONS: Record<StepCard["kind"], React.ElementType> = {
  memory_loaded: Database,
  planner: Brain,
  tool: Wrench,
  verifier: Shield,
  memory_updated: Save,
};

const STEP_ICON_COLORS: Record<StepCard["kind"], string> = {
  memory_loaded: "text-sky-500",
  planner: "text-violet-500",
  tool: "text-amber-500",
  verifier: "text-emerald-500",
  memory_updated: "text-sky-500",
};

function StepIcon({ kind }: StepIconProps) {
  const Icon = STEP_ICONS[kind];
  return <Icon className={cn("size-4 shrink-0", STEP_ICON_COLORS[kind])} />;
}

function StatusBadge({ status }: { status: StepStatus }) {
  if (status === "running") {
    return (
      <span className="flex items-center gap-1 rounded-full border border-amber-400/30 bg-amber-400/10 px-2 py-0.5 text-[10px] font-medium uppercase tracking-widest text-amber-500">
        <span className="relative flex size-1.5">
          <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-amber-400 opacity-75" />
          <span className="relative inline-flex size-1.5 rounded-full bg-amber-500" />
        </span>
        Running
      </span>
    );
  }
  if (status === "failed") {
    return (
      <span className="flex items-center gap-1 rounded-full border border-destructive/30 bg-destructive/10 px-2 py-0.5 text-[10px] font-medium uppercase tracking-widest text-destructive">
        <XCircle className="size-2.5" />
        Failed
      </span>
    );
  }
  return (
    <span className="flex items-center gap-1 rounded-full border border-emerald-400/30 bg-emerald-400/10 px-2 py-0.5 text-[10px] font-medium uppercase tracking-widest text-emerald-600 dark:text-emerald-400">
      <CheckCircle2 className="size-2.5" />
      Done
    </span>
  );
}

// ── Layer 2 content ────────────────────────────────────────────────────────────

function formatValue(v: unknown): string {
  if (v === null) return "null";
  if (typeof v === "object") return JSON.stringify(v);
  return String(v);
}

function KVRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="grid grid-cols-[auto_1fr] gap-x-3 gap-y-0.5 rounded-none bg-muted/50 px-3 py-2 font-mono text-xs">
      <span className="shrink-0 font-semibold text-foreground/70">{label}</span>
      <span className="min-w-0 break-all text-foreground">{value}</span>
    </div>
  );
}

function MemoryLayer2({ context }: { context: MemoryContextEntry[] }) {
  if (context.length === 0) {
    return (
      <p className="text-xs text-muted-foreground">No memory entries for this turn.</p>
    );
  }
  return (
    <div className="space-y-1.5">
      {context.map((entry, i) =>
        entry.type === "memory" ? (
          <KVRow key={i} label={entry.key} value={entry.value} />
        ) : (
          <div key={i} className="rounded-none bg-muted/50 px-3 py-2 font-mono text-xs">
            <span className="font-semibold text-foreground/70">complaint</span>
            <span className="ml-3 text-foreground">{entry.issue}</span>
          </div>
        ),
      )}
    </div>
  );
}

function PlannerLayer2({
  content,
  toolCalls,
}: {
  content: string;
  toolCalls: PlannerToolCall[];
}) {
  return (
    <div className="space-y-3">
      {content ? (
        <p className="text-xs leading-relaxed text-foreground/80">{content}</p>
      ) : null}
      {toolCalls.length > 0 ? (
        <div className="space-y-1.5">
          <p className="text-[10px] font-semibold uppercase tracking-widest text-muted-foreground">
            Tool Calls
          </p>
          {toolCalls.map((tc, i) => (
            <div key={i} className="rounded-none bg-muted/50 px-3 py-2 font-mono text-xs">
              <p className="font-semibold text-foreground/70">{tc.name}</p>
              <div className="mt-1.5 space-y-1">
                {Object.entries(tc.args).map(([k, v]) => (
                  <div key={k} className="flex gap-2">
                    <span className="shrink-0 text-muted-foreground">{k}:</span>
                    <span className="text-foreground">{formatValue(v)}</span>
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>
      ) : null}
    </div>
  );
}

function ToolLayer2({ results }: { results: JsonValue }) {
  if (results === null || typeof results !== "object" || Array.isArray(results)) {
    return (
      <pre className="rounded-none bg-muted/50 p-3 font-mono text-xs text-foreground/80">
        {JSON.stringify(results, null, 2)}
      </pre>
    );
  }
  const entries = Object.entries(results as Record<string, JsonValue>);
  return (
    <div className="space-y-1.5">
      {entries.map(([k, v]) => (
        <KVRow key={k} label={k} value={formatValue(v)} />
      ))}
    </div>
  );
}

function VerifierLayer2({
  checks,
  valid,
  overrideMessage,
}: {
  checks: string[];
  valid: boolean | null;
  overrideMessage: string | null;
}) {
  return (
    <div className="space-y-2">
      {checks.map((check, i) => (
        <div key={i} className="flex items-start gap-2 text-xs">
          {valid !== false ? (
            <CheckCircle2 className="mt-0.5 size-3.5 shrink-0 text-emerald-500" />
          ) : (
            <XCircle className="mt-0.5 size-3.5 shrink-0 text-destructive" />
          )}
          <span className="text-foreground/80">{check}</span>
        </div>
      ))}
      {overrideMessage ? (
        <p className="mt-2 rounded-none border border-amber-300/30 bg-amber-50/50 px-3 py-2 text-xs text-amber-700 dark:bg-amber-950/20 dark:text-amber-400">
          {overrideMessage}
        </p>
      ) : null}
    </div>
  );
}

function MemoryUpdatedLayer2({ memKey, value }: { memKey: string; value: string }) {
  return (
    <div className="space-y-1.5">
      <KVRow label={memKey} value={value} />
    </div>
  );
}

// ── Timeline step ──────────────────────────────────────────────────────────────

function TimelineStep({
  step,
}: {
  step: StepCard;
}) {
  const [layer2Open, setLayer2Open] = useState(false);
  const [layer3Open, setLayer3Open] = useState(false);

  return (
    <li
      role="listitem"
      className="flex items-start gap-3"
    >
      {/* Icon — mt-0.5 aligns its center with the text cap-height of text-xs leading-snug */}
      <div className="mt-0.5 shrink-0">
        <StepIcon kind={step.kind} />
      </div>

      {/* Content */}
      <div className="min-w-0 flex-1 pb-5">
        {/* Layer 1: summary button */}
        <button
          type="button"
          aria-expanded={layer2Open}
          aria-label={step.summary}
          onClick={() => {
            setLayer2Open((v) => {
              if (v) setLayer3Open(false);
              return !v;
            });
          }}
          className={cn(
            "w-full text-left",
            "flex flex-wrap items-start justify-between gap-x-3 gap-y-1",
          )}
        >
          <span className="text-xs font-medium leading-snug text-foreground">
            {step.summary}
          </span>
          <StatusBadge status={step.status} />
        </button>

        {/* Layer 2: verbose content */}
        {layer2Open && (
          <div className="mt-3 space-y-3 rounded-none border border-border/50 bg-card/50 p-3">
            <div className="rounded-none bg-secondary px-3 py-2.5">
              {step.kind === "memory_loaded" && <MemoryLayer2 context={step.context} />}
              {step.kind === "planner" && (
                <PlannerLayer2 content={step.content} toolCalls={step.toolCalls} />
              )}
              {step.kind === "tool" && <ToolLayer2 results={step.results} />}
              {step.kind === "verifier" && (
                <VerifierLayer2
                  checks={step.checks}
                  valid={step.valid}
                  overrideMessage={step.overrideMessage}
                />
              )}
              {step.kind === "memory_updated" && (
                <MemoryUpdatedLayer2 memKey={step.key} value={step.value} />
              )}
            </div>

            {/* Layer 3 toggle */}
            <button
              type="button"
              onClick={() => setLayer3Open((v) => !v)}
              className="text-[10px] text-primary/70 underline-offset-2 hover:text-primary hover:underline transition-colors"
            >
              {layer3Open ? "Hide payload" : "View payload"}
            </button>
            {layer3Open && (
              <pre className="overflow-x-auto rounded-none bg-muted/60 p-3 font-mono text-[10px] leading-relaxed text-muted-foreground">
                {step.rawJson}
              </pre>
            )}
          </div>
        )}
      </div>
    </li>
  );
}

// ── Public component ───────────────────────────────────────────────────────────

type AgentProcessPanelProps = {
  events: ChatStreamEvent[];
  isHistoryMode: boolean;
  isStreaming: boolean;
};

export function AgentProcessPanel({ events, isHistoryMode, isStreaming }: AgentProcessPanelProps) {
  if (isHistoryMode) {
    return (
      <div className="flex h-full items-center justify-center p-6 text-center">
        <div className="space-y-2">
          <div className="mx-auto flex size-10 items-center justify-center rounded-full bg-muted/50">
            <Brain className="size-5 text-muted-foreground/50" />
          </div>
          <p className="text-xs font-medium text-muted-foreground">
            Process trace is only available during live conversation
          </p>
        </div>
      </div>
    );
  }

  const steps = buildSteps(events, isStreaming);

  if (steps.length === 0) {
    return (
      <div className="flex h-full items-center justify-center p-6 text-center">
        <div className="space-y-2">
          <div className="mx-auto flex size-10 items-center justify-center rounded-full bg-muted/50">
            <Brain className="size-5 text-muted-foreground/50" />
          </div>
          <p className="text-xs font-medium text-muted-foreground">
            Process steps will appear here as events arrive
          </p>
        </div>
      </div>
    );
  }

  return (
    <ul className="space-y-0 px-4 py-3" aria-label="Agent process timeline">
      {steps.map((step, i) => (
        <TimelineStep
          key={`${step.kind}-${i}`}
          step={step}
        />
      ))}
    </ul>
  );
}
