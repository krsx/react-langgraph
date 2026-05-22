import { useNavigate, useLocation, NavLink, Outlet } from "react-router-dom";
import { Brain, CalendarDays, ChevronDown, Database, HeadphonesIcon, Mail, Terminal } from "lucide-react";
import { useQuery } from "@tanstack/react-query";
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@/components/ui/collapsible";
import {
  Sidebar,
  SidebarContent,
  SidebarGroup,
  SidebarGroupContent,
  SidebarGroupLabel,
  SidebarHeader,
  SidebarInset,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
  SidebarProvider,
  SidebarTrigger,
  useSidebar,
} from "@/components/ui/sidebar";
import { TooltipProvider } from "@/components/ui/tooltip";
import { getSessions, getSessionMessages } from "@/lib/api";
import { useChatContext } from "@/lib/chat-context";
import type { AgentType } from "@/lib/types";

const AGENT_TYPE_ITEMS: Array<{
  agentType: AgentType;
  label: string;
  icon: React.ComponentType<{ className?: string }>;
}> = [
  { agentType: "customer_service", label: "Customer Service", icon: HeadphonesIcon },
  { agentType: "refund_email", label: "Refund Email", icon: Mail },
  { agentType: "calendar", label: "Calendar", icon: CalendarDays },
];

const TOOL_ITEMS = [
  { to: "/data", label: "Data Explorer", icon: Database },
  { to: "/memory", label: "Memory Manager", icon: Brain },
] as const;

export function Layout() {
  const navigate = useNavigate();
  const location = useLocation();
  const { loadHistory, selectAgentType, activeAgentType } = useChatContext();

  const { data: sessions = [] } = useQuery({
    queryKey: ["sessions"],
    queryFn: getSessions,
  });

  const sessionsByAgentType = AGENT_TYPE_ITEMS.reduce((acc, item) => {
    acc[item.agentType] = sessions
      .filter((s) => s.agent_type === item.agentType)
      .sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime());
    return acc;
  }, {} as Record<AgentType, typeof sessions>);

  async function handleSessionClick(threadId: string, agentType: AgentType, customerId: number | null) {
    const messages = await getSessionMessages(threadId);
    selectAgentType(agentType);
    loadHistory(threadId, messages, customerId);
    if (location.pathname !== "/chat") navigate("/chat");
  }

  function handleAgentTypeClick(agentType: AgentType) {
    selectAgentType(agentType);
    if (location.pathname !== "/chat") navigate("/chat");
  }

  return (
    <TooltipProvider>
      <SidebarProvider className="h-svh overflow-hidden">
        <Sidebar collapsible="icon">
          <SidebarHeader className="border-b border-sidebar-border px-4 py-3">
            <div className="flex items-center gap-1 group-data-[collapsible=icon]:justify-center">
              <Terminal className="size-4 shrink-0 text-sidebar-primary text-white bg-primary" />
              <span className="font-mono text-sm font-semibold tracking-tight group-data-[collapsible=icon]:hidden">
                Agent Console
              </span>
            </div>
          </SidebarHeader>

          <SidebarContent>
            <SidebarGroup data-testid="agent-type-nav">
              <SidebarGroupLabel>Agents</SidebarGroupLabel>
              <SidebarGroupContent>
                <SidebarMenu>
                  {AGENT_TYPE_ITEMS.map((item) => (
                    <SidebarMenuItem key={item.agentType}>
                      <SidebarMenuButton
                        tooltip={item.label}
                        data-active={activeAgentType === item.agentType}
                        onClick={() => handleAgentTypeClick(item.agentType)}
                      >
                        <item.icon className="size-4" />
                        <span>{item.label}</span>
                      </SidebarMenuButton>
                    </SidebarMenuItem>
                  ))}
                </SidebarMenu>
              </SidebarGroupContent>
            </SidebarGroup>

            <SidebarGroup>
              <SidebarGroupLabel>Navigation</SidebarGroupLabel>
              <SidebarGroupContent>
                <SidebarMenu>
                  {TOOL_ITEMS.map(({ to, label, icon: Icon }) => (
                    <SidebarMenuItem key={to}>
                      <SidebarMenuButton asChild tooltip={label}>
                        <NavLink to={to}>
                          <Icon />
                          <span>{label}</span>
                        </NavLink>
                      </SidebarMenuButton>
                    </SidebarMenuItem>
                  ))}
                </SidebarMenu>
              </SidebarGroupContent>
            </SidebarGroup>

            <SessionHistorySection
              agentTypeItems={AGENT_TYPE_ITEMS}
              sessionsByAgentType={sessionsByAgentType}
              onSessionClick={handleSessionClick}
            />
          </SidebarContent>
        </Sidebar>

        <SidebarInset className="min-h-0 overflow-hidden">
          <header className="flex h-12 shrink-0 items-center gap-2 border-b px-4">
            <SidebarTrigger />
          </header>
          <main className="flex min-h-0 flex-1 flex-col overflow-hidden">
            <Outlet />
          </main>
        </SidebarInset>
      </SidebarProvider>
    </TooltipProvider>
  );
}

function SessionHistorySection({
  agentTypeItems,
  sessionsByAgentType,
  onSessionClick,
}: {
  agentTypeItems: typeof AGENT_TYPE_ITEMS;
  sessionsByAgentType: Record<AgentType, Array<{ thread_id: string; customer_id: number | null; first_message: string; created_at: string; agent_type: AgentType }>>;
  onSessionClick: (threadId: string, agentType: AgentType, customerId: number | null) => Promise<void>;
}) {
  const { state } = useSidebar();

  if (state !== "expanded") return null;

  return (
    <>
      {agentTypeItems.map((item) => {
        const agentSessions = sessionsByAgentType[item.agentType] ?? [];
        return (
          <Collapsible key={item.agentType} className="group/collapsible">
            <SidebarGroup>
              <SidebarGroupLabel asChild>
                <CollapsibleTrigger className="flex w-full items-center">
                  {item.label}
                  <ChevronDown className="ml-auto size-4 transition-transform group-data-[state=open]/collapsible:rotate-180" />
                </CollapsibleTrigger>
              </SidebarGroupLabel>
              <CollapsibleContent>
                <SidebarGroupContent>
                  {agentSessions.length === 0 ? (
                    <p className="px-2 py-2 text-xs text-muted-foreground">
                      No sessions yet.
                    </p>
                  ) : (
                    <SidebarMenu>
                      {agentSessions.map((session) => (
                        <SidebarMenuItem key={session.thread_id}>
                          <SidebarMenuButton
                            className="h-auto flex-col items-start gap-0 py-2 text-left"
                            onClick={() => void onSessionClick(session.thread_id, item.agentType, session.customer_id)}
                          >
                            <span className="line-clamp-2 text-sm leading-snug">
                              {session.first_message}
                            </span>
                            <span className="text-xs text-muted-foreground">
                              {new Date(session.created_at).toLocaleDateString()}
                            </span>
                          </SidebarMenuButton>
                        </SidebarMenuItem>
                      ))}
                    </SidebarMenu>
                  )}
                </SidebarGroupContent>
              </CollapsibleContent>
            </SidebarGroup>
          </Collapsible>
        );
      })}
    </>
  );
}
