import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { createBrowserRouter, RouterProvider } from "react-router-dom";
import { routes } from "./routes";

const appRouter = createBrowserRouter(routes);
const appQueryClient = new QueryClient();

type AppProps = {
  router?: ReturnType<typeof createBrowserRouter>;
  queryClient?: QueryClient;
};

export function App({ router = appRouter, queryClient = appQueryClient }: AppProps) {
  return (
    <QueryClientProvider client={queryClient}>
      <RouterProvider router={router} />
    </QueryClientProvider>
  );
}
