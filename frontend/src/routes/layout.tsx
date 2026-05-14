import { useNavigate, useLocation, NavLink, Outlet } from "react-router-dom";
import { Brain, ChevronDown, Database, MessageSquare, Plus, Terminal } from "lucide-react";
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
} from "@/components/ui/sidebar";
import { TooltipProvider } from "@/components/ui/tooltip";
import { Button } from "@/components/ui/button";
import { getSessions, getSessionMessages } from "@/lib/api";
import { useChatContext } from "@/lib/chat-context";

const NAV_ITEMS = [
  { to: "/chat", label: "Chat", icon: MessageSquare },
  { to: "/data", label: "Data Explorer", icon: Database },
  { to: "/memory", label: "Memory Manager", icon: Brain },
] as const;

export function Layout() {
  const navigate = useNavigate();
  const location = useLocation();
  const { activeCustomerId, loadHistory, newChat } = useChatContext();

  const { data: sessions = [] } = useQuery({
    queryKey: ["sessions"],
    queryFn: getSessions,
  });

  const visibleSessions = activeCustomerId === null
    ? []
    : sessions.filter((s) => s.customer_id === activeCustomerId);

  async function handleSessionClick(threadId: string) {
    const messages = await getSessionMessages(threadId);
    loadHistory(threadId, messages);
    if (location.pathname !== "/chat") navigate("/chat");
  }

  function handleNewChat() {
    newChat();
    if (location.pathname !== "/chat") navigate("/chat");
  }

  return (
    <TooltipProvider>
      <SidebarProvider>
        <Sidebar variant="inset" collapsible="icon">
          <SidebarHeader className="border-b border-sidebar-border px-4 py-3">
            <div className="flex items-center gap-2 group-data-[collapsible=icon]:justify-center">
              <Terminal className="size-5 shrink-0 text-sidebar-primary" />
              <span className="font-mono text-sm font-semibold tracking-tight group-data-[collapsible=icon]:hidden">
                Agent Console
              </span>
            </div>
          </SidebarHeader>

          <SidebarContent>
            <SidebarGroup>
              <SidebarGroupLabel>Navigation</SidebarGroupLabel>
              <SidebarGroupContent>
                <SidebarMenu>
                  {NAV_ITEMS.map(({ to, label, icon: Icon }) => (
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

            <Collapsible defaultOpen className="group/collapsible">
              <SidebarGroup>
                <SidebarGroupLabel asChild>
                  <CollapsibleTrigger className="flex w-full items-center">
                    Session History
                    <ChevronDown className="ml-auto size-4 transition-transform group-data-[state=open]/collapsible:rotate-180" />
                  </CollapsibleTrigger>
                </SidebarGroupLabel>
                <CollapsibleContent>
                  <SidebarGroupContent>
                    <div className="px-2 pt-1 pb-2">
                      <Button
                        size="sm"
                        variant="ghost"
                        className="w-full justify-start gap-1.5 text-xs"
                        onClick={handleNewChat}
                      >
                        <Plus className="size-3.5" />
                        New Chat
                      </Button>
                    </div>

                    {visibleSessions.length === 0 ? (
                      <p className="px-2 py-2 text-xs text-muted-foreground">
                        No sessions yet.
                      </p>
                    ) : (
                      <SidebarMenu>
                        {visibleSessions.map((session) => (
                          <SidebarMenuItem key={session.thread_id}>
                            <SidebarMenuButton
                              className="h-auto flex-col items-start gap-0 py-2 text-left"
                              onClick={() => void handleSessionClick(session.thread_id)}
                            >
                              <span className="line-clamp-2 text-xs leading-snug">
                                {session.first_message}
                              </span>
                              <span className="text-[10px] text-muted-foreground">
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
          </SidebarContent>
        </Sidebar>

        <SidebarInset>
          <header className="flex h-12 items-center gap-2 border-b px-4">
            <SidebarTrigger />
          </header>
          <main className="flex h-[calc(100vh-3rem)] flex-col">
            <Outlet />
          </main>
        </SidebarInset>
      </SidebarProvider>
    </TooltipProvider>
  );
}
