import { Navigate } from "react-router-dom";
import type { RouteObject } from "react-router-dom";
import { Layout } from "./routes/layout";
import { ChatPage } from "./routes/chat";
import { DataPage } from "./routes/data";
import { MemoryPage } from "./routes/memory";
import { ChatProvider } from "./lib/chat-context";

export const routes: RouteObject[] = [
  {
    path: "/",
    element: (
      <ChatProvider>
        <Layout />
      </ChatProvider>
    ),
    children: [
      { index: true, element: <Navigate to="/chat" replace /> },
      { path: "chat", element: <ChatPage /> },
      { path: "data", element: <DataPage /> },
      { path: "memory", element: <MemoryPage /> },
    ],
  },
];
