import { render, screen } from "@testing-library/react";
import { expect, test, vi } from "vitest";
import { MOCK_WEBHOOK_EVENTS, MOCK_WEBHOOKS } from "./fixtures";
import { WebhooksFeature } from "./WebhooksFeature";

// Mock the hook
vi.mock("./hooks/useWebhooks", () => ({
  useWebhooks: () => ({
    webhooks: MOCK_WEBHOOKS,
    events: MOCK_WEBHOOK_EVENTS,
    isLoading: false,
    refreshEvents: vi.fn(),
    createWebhook: vi.fn(),
  }),
}));

test("renders webhooks list", () => {
  render(<WebhooksFeature />);

  expect(screen.getByText("GitHub Global")).toBeDefined();
  expect(screen.getByText("Jira Cloud")).toBeDefined();
});

test("renders event logs", () => {
  render(<WebhooksFeature />);

  expect(screen.getByText("issue_created")).toBeDefined();
  expect(screen.getByText("issue_updated")).toBeDefined();
});

test("renders webhook status", () => {
  render(<WebhooksFeature />);

  expect(screen.getAllByText("ACTIVE").length).toBeGreaterThan(0);
  expect(screen.getByText("https://hooks.machine.io/gh-global")).toBeDefined();
});
