import { render, screen } from "@testing-library/react";
import { expect, test, vi } from "vitest";
import { MOCK_METRICS, MOCK_TASKS } from "./fixtures";
import { OverviewFeature } from "./OverviewFeature";

// Mock the hook
vi.mock("./hooks/useMetrics", () => ({
  useMetrics: () => ({
    metrics: MOCK_METRICS,
    tasks: MOCK_TASKS,
    isLoading: false,
    error: null,
  }),
}));

test("renders metrics correctly", () => {
  render(<OverviewFeature />);

  expect(screen.getByText("QUEUE_DEPTH")).toBeDefined();
  expect(screen.getByText("12")).toBeDefined();
  expect(screen.getByText("ACTIVE_SESSIONS")).toBeDefined();
  expect(screen.getByText("4")).toBeDefined();
});

test("renders live feed tasks", () => {
  render(<OverviewFeature />);

  expect(screen.getByText("PROCESS_LOGS")).toBeDefined();
  expect(screen.getByText("GENERATE_REPORT")).toBeDefined();
});
