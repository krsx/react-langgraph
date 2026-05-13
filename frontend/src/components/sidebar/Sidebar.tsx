import { Button } from "../ui/button";
import { SelectField } from "../ui/select";
import type { Customer, ProviderCatalog, SessionSummary } from "../../lib/types";

type SidebarProps = {
  customers: Customer[];
  activeCustomerId: number | null;
  providers: ProviderCatalog;
  selectedProvider: string | null;
  selectedModel: string | null;
  sessions: SessionSummary[];
  readOnly: boolean;
  onCustomerSelect: (customerId: number) => void;
  onProviderSelect: (provider: string) => void;
  onModelSelect: (model: string) => void;
  onSessionSelect: (threadId: string) => void;
  onNewChat: () => void;
};

export function Sidebar({
  customers,
  activeCustomerId,
  providers,
  selectedProvider,
  selectedModel,
  sessions,
  readOnly,
  onCustomerSelect,
  onProviderSelect,
  onModelSelect,
  onSessionSelect,
  onNewChat,
}: SidebarProps) {
  const providerEntries = Object.entries(providers);
  const availableModels = selectedProvider ? providers[selectedProvider]?.models ?? [] : [];

  return (
    <aside className="flex h-full flex-col gap-5 rounded-[28px] border border-border/80 bg-card/90 p-5 shadow-panel">
      <div className="space-y-1">
        <p className="text-xs uppercase tracking-[0.24em] text-muted-foreground">Evaluator Workspace</p>
        <h1 className="text-2xl font-bold">Conversation Sessions</h1>
      </div>

      <Button onClick={onNewChat} className="w-full justify-center">
        New Chat
      </Button>

      <SelectField
        label="Customer"
        aria-label="Customer"
        value={activeCustomerId ?? ""}
        onChange={(event) => onCustomerSelect(Number(event.target.value))}
      >
        {customers.map((customer) => (
          <option key={customer.customer_id} value={customer.customer_id}>
            {customer.name}
          </option>
        ))}
      </SelectField>

      <SelectField
        label="Provider"
        aria-label="Provider"
        value={selectedProvider ?? ""}
        onChange={(event) => onProviderSelect(event.target.value)}
      >
        {providerEntries.map(([providerName, provider]) => (
          <option
            key={providerName}
            value={providerName}
            disabled={!provider.available || provider.models.length === 0}
            data-unavailable={!provider.available || provider.models.length === 0}
          >
            {providerName}
            {!provider.available ? " (unavailable)" : ""}
          </option>
        ))}
      </SelectField>

      <SelectField
        label="Model"
        aria-label="Model"
        value={selectedModel ?? ""}
        onChange={(event) => onModelSelect(event.target.value)}
        disabled
      >
        {availableModels.map((model) => (
          <option key={model} value={model}>
            {model}
          </option>
        ))}
      </SelectField>

      <section className="flex min-h-0 flex-1 flex-col gap-3">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-sm font-semibold">Session History</h2>
            <p className="text-xs text-muted-foreground">
              {readOnly ? "Inspecting a read-only Conversation Session." : "Choose a saved Conversation Session."}
            </p>
          </div>
        </div>

        <ul className="flex min-h-0 flex-1 flex-col gap-2 overflow-y-auto">
          {sessions.map((session) => (
            <li key={session.thread_id}>
              <button
                type="button"
                className="w-full rounded-2xl border border-border bg-background/60 p-3 text-left transition hover:border-primary hover:bg-secondary"
                onClick={() => onSessionSelect(session.thread_id)}
              >
                <p className="line-clamp-1 text-sm font-medium">{session.first_message}</p>
                <p className="mt-1 text-xs text-muted-foreground">{session.thread_id}</p>
              </button>
            </li>
          ))}
          {sessions.length === 0 ? (
            <li className="rounded-2xl border border-dashed border-border p-4 text-sm text-muted-foreground">
              No Conversation Sessions for this Customer yet.
            </li>
          ) : null}
        </ul>
      </section>
    </aside>
  );
}
