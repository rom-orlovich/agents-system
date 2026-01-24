import { render, screen } from "@testing-library/react";
import { expect, test, vi } from "vitest";
import { AnalyticsFeature } from "./AnalyticsFeature";
import { MOCK_AGENT_PERFORMANCE, MOCK_COST_DATA } from "./fixtures";

// Mock the hook
vi.mock("./hooks/useAnalyticsData", () => ({
  useAnalyticsData: () => ({
    costData: MOCK_COST_DATA,
    performanceData: MOCK_AGENT_PERFORMANCE,
    isLoading: false,
    error: null,
  }),
}));

// Mock Recharts to render children and text labels
vi.mock("recharts", async () => {
  const Actual = (await vi.importActual("recharts")) as Record<string, unknown>;
  return {
    ...Actual,
    ResponsiveContainer: ({ children }: { children: React.ReactNode }) => (
      <div data-testid="responsive-container">{children}</div>
    ),
    AreaChart: ({ children, data }: { children: React.ReactNode; data: object[] }) => (
      <div data-testid="area-chart" data-data={JSON.stringify(data)}>
        {children}
      </div>
    ),
    BarChart: ({ children, data }: { children: React.ReactNode; data: object[] }) => (
      <div data-testid="bar-chart" data-data={JSON.stringify(data)}>
        {children}
      </div>
    ),
    XAxis: () => <div />,
    YAxis: () => <div />,
    CartesianGrid: () => <div />,
    Tooltip: () => <div />,
    Area: () => <div />,
    Bar: () => <div />,
    Cell: () => <div />,
  };
});

test("renders analytics titles", () => {
  render(<AnalyticsFeature />);

  expect(screen.getByText(/BURN_RATE_TREND/)).toBeDefined();
  expect(screen.getByText(/AGENT_LEADERBOARD/)).toBeDefined();
});

test("renders chart containers", () => {
  render(<AnalyticsFeature />);

  expect(screen.getByTestId("area-chart")).toBeDefined();
  expect(screen.getAllByTestId("bar-chart")).toBeDefined();
});
