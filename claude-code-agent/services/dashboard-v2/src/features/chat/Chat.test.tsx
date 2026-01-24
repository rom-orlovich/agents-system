import { render, screen } from "@testing-library/react";
import { expect, test, vi } from "vitest";
import { ChatFeature } from "./ChatFeature";
import { MOCK_CONVERSATIONS, MOCK_MESSAGES } from "./fixtures";

// Mock the hooks
vi.mock("./hooks/useChat", () => ({
  useChat: () => ({
    conversations: MOCK_CONVERSATIONS,
    messages: MOCK_MESSAGES,
    isLoading: false,
    selectedId: "conv-1",
    selectedConversation: MOCK_CONVERSATIONS[0],
    setSelectedConversation: vi.fn(),
    sendMessage: vi.fn(),
    deleteConversation: vi.fn(),
  }),
}));

vi.mock("../../hooks/useCLIStatus", () => ({
  useCLIStatus: () => ({ active: true, isLoading: false }),
}));

vi.mock("../../hooks/useTaskModal", () => ({
  useTaskModal: () => ({ openTask: vi.fn() }),
}));

test("renders conversation list", () => {
  render(<ChatFeature />);

  expect(screen.getAllByText("Task Execution Log").length).toBeGreaterThan(0);
  expect(screen.getAllByText("System Alerts").length).toBeGreaterThan(0);
});

test("renders chat messages", () => {
  render(<ChatFeature />);

  expect(screen.getByText("Run security scan.")).toBeDefined();
  expect(screen.getByText("No critical threats found.")).toBeDefined();
});

test("renders input area", () => {
  render(<ChatFeature />);

  expect(screen.getByPlaceholderText("ENTER_COMMAND...")).toBeDefined();
});
