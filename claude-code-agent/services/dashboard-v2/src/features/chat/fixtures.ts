export const MOCK_CONVERSATIONS = [
  {
    id: "conv-1",
    title: "Task Execution Log",
    lastMessage: "Process finished with success.",
    timestamp: "2026-01-22T21:00:00Z",
  },
  {
    id: "conv-2",
    title: "System Alerts",
    lastMessage: "Memory usage high.",
    timestamp: "2026-01-22T20:55:00Z",
  },
];

export const MOCK_MESSAGES = [
  { id: "m-1", role: "user", content: "Run security scan.", timestamp: "2026-01-22T20:50:00Z" },
  {
    id: "m-2",
    role: "assistant",
    content: "Starting vulnerability assessment...",
    timestamp: "2026-01-22T20:51:00Z",
  },
  {
    id: "m-3",
    role: "assistant",
    content: "No critical threats found.",
    timestamp: "2026-01-22T20:52:00Z",
  },
];
