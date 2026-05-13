import { useState } from "react";
import { cn } from "../../lib/utils";
import { DataExplorerPanel } from "../data/DataExplorerPanel";
import { MemoryManagerPanel } from "../memory/MemoryManagerPanel";
import { AgentProcessPanelContent } from "../process/AgentProcessPanel";
import { Button } from "../ui/button";
import type { ChatStreamEvent } from "../../lib/types";

type RightPanelTab = "process" | "data" | "memory";

type RightPanelProps = {
  activeCustomerId: number | null;
  activeCustomerName: string;
  events: ChatStreamEvent[];
  isOpen: boolean;
  onMemoryDirtyChange: (dirty: boolean) => void;
  onToggle: () => void;
  selectedModel: string | null;
  selectedProvider: string | null;
  threadId: string | null;
};

const TAB_LABELS: Record<RightPanelTab, string> = {
  process: "Agent Process",
  data: "Data Explorer",
  memory: "Memory Manager",
};

export function RightPanel({
  activeCustomerId,
  activeCustomerName,
  events,
  isOpen,
  onMemoryDirtyChange,
  onToggle,
  selectedModel,
  selectedProvider,
  threadId,
}: RightPanelProps) {
  const [activeTab, setActiveTab] = useState<RightPanelTab>("process");

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
            {activeTab === "process" ? <h2 className="text-xl font-bold">Agent Process Panel</h2> : null}
          </div>
        ) : null}
        <Button variant="outline" aria-expanded={isOpen} onClick={onToggle}>
          {isOpen ? "Collapse" : "Expand"}
        </Button>
      </div>

      {isOpen ? (
        <div className="mt-5 flex min-h-0 flex-1 flex-col">
          <div aria-label="Right Panel tabs" className="flex flex-wrap gap-2" role="tablist">
            {(["process", "data", "memory"] as RightPanelTab[]).map((tab) => (
              <button
                key={tab}
                aria-selected={activeTab === tab}
                className={cn(
                  "rounded-full px-3 py-2 text-sm font-medium transition",
                  activeTab === tab
                    ? "bg-primary text-primary-foreground"
                    : "bg-secondary text-secondary-foreground hover:opacity-90",
                )}
                onClick={() => setActiveTab(tab)}
                role="tab"
                type="button"
              >
                {TAB_LABELS[tab]}
              </button>
            ))}
          </div>

          <div className="mt-5 min-h-0 flex-1 overflow-y-auto">
            {activeTab === "process" ? (
              <AgentProcessPanelContent
                activeCustomerName={activeCustomerName}
                selectedProvider={selectedProvider}
                selectedModel={selectedModel}
                threadId={threadId}
                events={events}
              />
            ) : null}

            {activeTab === "data" ? <DataExplorerPanel activeCustomerId={activeCustomerId} /> : null}

            {activeTab === "memory" ? (
              <MemoryManagerPanel
                activeCustomerId={activeCustomerId}
                onDirtyChange={onMemoryDirtyChange}
              />
            ) : null}
          </div>
        </div>
      ) : null}
    </aside>
  );
}
