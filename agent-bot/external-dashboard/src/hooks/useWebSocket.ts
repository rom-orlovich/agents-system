import { useEffect, useRef } from "react";
import { useQueryClient } from "@tanstack/react-query";

interface WebSocketMessage {
  type: string;
  task_id?: string;
  status?: string;
  output?: string;
  [key: string]: unknown;
}

export function useWebSocket(sessionId: string = "dashboard") {
  const wsRef = useRef<WebSocket | null>(null);
  const queryClient = useQueryClient();
  const reconnectTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    let ws: WebSocket | null = null;

    const connect = () => {
      const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
      const host = import.meta.env.VITE_API_URL || window.location.host;
      const wsUrl = `${protocol}//${host}/ws/${sessionId}`;

      ws = new WebSocket(wsUrl);
      wsRef.current = ws;

      ws.onopen = () => {
        console.log("WebSocket connected");
        if (reconnectTimeoutRef.current) {
          clearTimeout(reconnectTimeoutRef.current);
          reconnectTimeoutRef.current = null;
        }
      };

      ws.onmessage = (event) => {
        try {
          const message: WebSocketMessage = JSON.parse(event.data);

          switch (message.type) {
            case "task_update":
              queryClient.invalidateQueries({ queryKey: ["tasks"] });
              if (message.task_id) {
                queryClient.invalidateQueries({ queryKey: ["task", message.task_id] });
                queryClient.invalidateQueries({ queryKey: ["task-logs", message.task_id] });
              }
              break;
            case "metrics_update":
              queryClient.invalidateQueries({ queryKey: ["metrics"] });
              break;
            case "agent_status":
              queryClient.invalidateQueries({ queryKey: ["agents"] });
              break;
          }
        } catch (error) {
          console.error("Failed to parse WebSocket message", error);
        }
      };

      ws.onerror = (error) => {
        console.error("WebSocket error", error);
      };

      ws.onclose = () => {
        console.log("WebSocket disconnected, reconnecting...");
        wsRef.current = null;
        reconnectTimeoutRef.current = setTimeout(() => {
          connect();
        }, 3000);
      };
    };

    connect();

    return () => {
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }
      if (ws) {
        ws.close();
      }
      wsRef.current = null;
    };
  }, [sessionId, queryClient]);

  return wsRef.current;
}
