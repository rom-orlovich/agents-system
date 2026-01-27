import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import type { ReactNode } from "react";
import { expect, test, vi } from "vitest";
import { MOCK_METRICS, MOCK_TASKS } from "./fixtures";
import { OverviewFeature } from "./OverviewFeature";

vi.mock("./hooks/useMetrics", () => ({
  useMetrics: () => ({
    metrics: MOCK_METRICS,
    tasks: MOCK_TASKS,
    isLoading: false,
    error: null,
    refetch: vi.fn(),
  }),
}));

vi.mock("./hooks/useTaskLogs", () => ({
  useTaskLogs: () => ({
    data: null,
    isLoading: false,
  }),
  useGlobalLogs: () => ({
    data: [],
  }),
}));

const createWrapper = () => {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
    },
  });
  return ({ children }: { children: ReactNode }) => (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  );
};

test("renders metrics correctly", () => {
  render(<OverviewFeature />, { wrapper: createWrapper() });

  expect(screen.getByText("QUEUE_DEPTH")).toBeDefined();
  expect(screen.getByText("12")).toBeDefined();
  expect(screen.getByText("ACTIVE_SESSIONS")).toBeDefined();
  expect(screen.getByText("4")).toBeDefined();
});

test("renders OAuth usage metrics", () => {
  render(<OverviewFeature />, { wrapper: createWrapper() });

  expect(screen.getByText("OAUTH_SESSION_USAGE")).toBeDefined();
  expect(screen.getByText("OAUTH_WEEKLY_USAGE")).toBeDefined();

  const sessionUsage = screen.getByText("OAUTH_SESSION_USAGE").closest(".panel");
  const weeklyUsage = screen.getByText("OAUTH_WEEKLY_USAGE").closest(".panel");

  expect(sessionUsage?.textContent).toContain("10.0%");
  expect(weeklyUsage?.textContent).toContain("10.0%");
});

test("renders live feed tasks", () => {
  render(<OverviewFeature />, { wrapper: createWrapper() });

  expect(screen.getByText("PROCESS_LOGS")).toBeDefined();
  expect(screen.getByText("GENERATE_REPORT")).toBeDefined();
});
