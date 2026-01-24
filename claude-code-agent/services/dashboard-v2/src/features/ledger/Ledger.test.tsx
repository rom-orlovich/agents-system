import { render, screen } from "@testing-library/react";
import { expect, test, vi } from "vitest";
import { MOCK_AGENTS, MOCK_LEDGER_TASKS } from "./fixtures";
import { LedgerFeature } from "./LedgerFeature";

// Mock the hook
vi.mock("./hooks/useLedger", () => ({
  useLedger: () => ({
    tasks: MOCK_LEDGER_TASKS,
    agents: MOCK_AGENTS,
    isLoading: false,
    filters: {},
    setFilters: vi.fn(),
    page: 1,
    setPage: vi.fn(),
    totalPages: 3,
  }),
}));

test("renders ledger table headers", () => {
  render(<LedgerFeature />);

  expect(screen.getByText("TASK_ID")).toBeDefined();
  expect(screen.getByText("AGENT")).toBeDefined();
  expect(screen.getByText("STATUS")).toBeDefined();
  expect(screen.getByText("TIMESTAMP")).toBeDefined();
});

test("renders task data", () => {
  render(<LedgerFeature />);

  expect(screen.getByText("task-1")).toBeDefined();
  expect(screen.getByText("task-5")).toBeDefined();
});

test("renders filters", () => {
  render(<LedgerFeature />);

  expect(screen.getByPlaceholderText("FILTER_SESSION...")).toBeDefined();
  expect(screen.getByText("ALL_STATUS")).toBeDefined();
});
