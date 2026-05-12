import type { ChatStreamEvent } from "../../lib/types";
import { Button } from "../ui/button";

type RightPanelProps = {
  isOpen: boolean;
  activeCustomerName: string;
  selectedProvider: string | null;
  selectedModel: string | null;
  threadId: string | null;
  events: ChatStreamEvent[];
  onToggle: () => void;
};

export function RightPanelPlaceholder({
  isOpen,
  activeCustomerName,
  selectedProvider,
  selectedModel,
  threadId,
  events,
  onToggle,
}: RightPanelProps) {
  return (
    <aside
      className={`flex h-full flex-col rounded-[28px] border border-border/80 bg-card/90 shadow-panel transition-all ${
        isOpen ? "w-full p-5" : "w-full p-3"
      }`}
    >
      <div className="flex items-center justify-between gap-3">
        <div className={isOpen ? "block" : "hidden"}>
          <p className="text-xs uppercase tracking-[0.24em] text-muted-foreground">Right Panel</p>
          <h2 className="text-xl font-bold">Agent Process Placeholder</h2>
        </div>
        <Button variant="outline" onClick={onToggle}>
          {isOpen ? "Collapse" : "Expand"}
        </Button>
      </div>

      {isOpen ? (
        <div className="mt-5 space-y-5">
          <section className="rounded-2xl bg-background/70 p-4">
            <h3 className="text-sm font-semibold">Execution Context</h3>
            <dl className="mt-3 space-y-2 text-sm text-muted-foreground">
              <div>
                <dt className="font-medium text-foreground">Customer</dt>
                <dd>{activeCustomerName}</dd>
              </div>
              <div>
                <dt className="font-medium text-foreground">Provider</dt>
                <dd>{selectedProvider ?? "Not selected"}</dd>
              </div>
              <div>
                <dt className="font-medium text-foreground">Model</dt>
                <dd>{selectedModel ?? "Not selected"}</dd>
              </div>
              <div>
                <dt className="font-medium text-foreground">Transport ID</dt>
                <dd>{threadId ?? "Pending first stream event"}</dd>
              </div>
            </dl>
          </section>

          <section className="rounded-2xl bg-background/70 p-4">
            <h3 className="text-sm font-semibold">Current Turn Events</h3>
            <ul className="mt-3 space-y-2 text-sm text-muted-foreground">
              {events.map((event, index) => (
                <li key={`${event.type}-${index}`} className="rounded-xl border border-border/70 px-3 py-2">
                  {event.type}
                </li>
              ))}
              {events.length === 0 ? (
                <li className="rounded-xl border border-dashed border-border px-3 py-2">
                  No stream activity yet.
                </li>
              ) : null}
            </ul>
          </section>
        </div>
      ) : null}
    </aside>
  );
}
