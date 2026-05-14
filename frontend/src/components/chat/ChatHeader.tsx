import { useEffect } from "react";
import { useQuery } from "@tanstack/react-query";
import { getCustomers, getProviders } from "@/lib/api";
import { useChatContext } from "@/lib/chat-context";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

export function ChatHeader() {
  const {
    activeCustomerId,
    selectedProvider,
    selectedModel,
    selectCustomer,
    selectProvider,
    selectModel,
  } = useChatContext();

  const { data: customers = [] } = useQuery({ queryKey: ["customers"], queryFn: getCustomers });
  const { data: providers = {} } = useQuery({ queryKey: ["providers"], queryFn: getProviders });

  // Auto-select first customer when data arrives
  useEffect(() => {
    if (customers.length > 0 && activeCustomerId === null) {
      selectCustomer(customers[0].customer_id);
    }
  }, [customers, activeCustomerId, selectCustomer]);

  // Auto-select first available provider when data arrives
  useEffect(() => {
    if (Object.keys(providers).length === 0) return;
    if (selectedProvider !== null) return;

    const available = Object.entries(providers).find(([, p]) => p.available && p.models.length > 0);
    const entry = available ?? Object.entries(providers)[0];
    if (entry) {
      const [name, p] = entry;
      selectProvider(name, p.models, p.default_model);
    }
  }, [providers, selectedProvider, selectProvider]);

  const activeProviderModels = selectedProvider ? (providers[selectedProvider]?.models ?? []) : [];

  return (
    <div className="flex items-center gap-2 border-b border-border bg-background/95 px-4 py-2">
      {/* Customer */}
      <div className="flex min-w-0 flex-1 flex-col gap-0.5">
        <span className="text-[10px] font-medium uppercase tracking-widest text-muted-foreground">Customer</span>
        <Select
          value={activeCustomerId !== null ? String(activeCustomerId) : ""}
          onValueChange={(v) => selectCustomer(Number(v))}
        >
          <SelectTrigger aria-label="Customer" className="h-8 min-w-[140px] max-w-[200px]">
            <SelectValue placeholder="Select customer" />
          </SelectTrigger>
          <SelectContent>
            {customers.map((c) => (
              <SelectItem key={c.customer_id} value={String(c.customer_id)}>
                {c.name}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      <div className="h-8 w-px bg-border" />

      {/* Provider */}
      <div className="flex flex-col gap-0.5">
        <span className="text-[10px] font-medium uppercase tracking-widest text-muted-foreground">Provider</span>
        <Select
          value={selectedProvider ?? ""}
          onValueChange={(v) => {
            const p = providers[v];
            if (p) selectProvider(v, p.models, p.default_model);
          }}
        >
          <SelectTrigger aria-label="Provider" className="h-8 min-w-[120px]">
            <SelectValue placeholder="Provider" />
          </SelectTrigger>
          <SelectContent>
            {Object.entries(providers).map(([name, p]) => (
              <SelectItem key={name} value={name} disabled={!p.available}>
                {name}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      {/* Model */}
      <div className="flex flex-col gap-0.5">
        <span className="text-[10px] font-medium uppercase tracking-widest text-muted-foreground">Model</span>
        <Select
          value={selectedModel ?? ""}
          onValueChange={(v) => selectModel(v)}
        >
          <SelectTrigger aria-label="Model" className="h-8 min-w-[140px]">
            <SelectValue placeholder="Model" />
          </SelectTrigger>
          <SelectContent>
            {activeProviderModels.map((m) => (
              <SelectItem key={m} value={m}>
                {m}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>
    </div>
  );
}
