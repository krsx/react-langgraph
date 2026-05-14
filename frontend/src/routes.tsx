import { Navigate } from "react-router-dom";
import type { RouteObject } from "react-router-dom";
import { Layout } from "./routes/layout";
import { ChatPage } from "./routes/chat";
import { DataPage } from "./routes/data";
import { MemoryPage } from "./routes/memory";

export const routes: RouteObject[] = [
  {
    path: "/",
    element: <Layout />,
    children: [
      { index: true, element: <Navigate to="/chat" replace /> },
      { path: "chat", element: <ChatPage /> },
      { path: "data", element: <DataPage /> },
      { path: "memory", element: <MemoryPage /> },
    ],
  },
];
