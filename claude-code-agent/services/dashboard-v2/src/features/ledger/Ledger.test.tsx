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

  // Use getAllByText because headers might be duplicated in mobile card view
  expect(screen.getAllByText("TASK_ID").length).toBeGreaterThan(0);
  expect(screen.getAllByText("AGENT").length).toBeGreaterThan(0);
  expect(screen.getAllByText("STATUS").length).toBeGreaterThan(0);
  expect(screen.getByText("TIMESTAMP")).toBeDefined();
});

test("renders task data", () => {
  render(<LedgerFeature />);

  expect(screen.getAllByText("task-1").length).toBeGreaterThan(0);
  expect(screen.getAllByText("task-5").length).toBeGreaterThan(0);
});

test("renders filters", () => {
  render(<LedgerFeature />);

  expect(screen.getByPlaceholderText("FILTER_SESSION...")).toBeDefined();
  expect(screen.getByText("ALL_STATUS")).toBeDefined();
});
