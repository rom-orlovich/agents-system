import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";

export interface Webhook {
  id: string;
  name: string;
  provider: string;
  status: "active" | "inactive";
  url: string;
}

export interface WebhookEvent {
  id: string;
  webhook_id: string;
  event: string;
  timestamp: string;
  status: "processed" | "error";
}

export function useWebhooks() {
  const queryClient = useQueryClient();
  const { data: webhooks, isLoading: isWhLoading } = useQuery<Webhook[]>({
    queryKey: ["webhooks"],
    queryFn: async () => {
      const res = await fetch("/api/webhooks-status");
      const json = await res.json();
      return (json.data?.webhooks || []).map((wh: any) => ({
        id: wh.webhook_id,
        name: wh.name,
        provider: wh.provider,
        status: wh.enabled ? "active" : "inactive",
        url: wh.endpoint,
      }));
    },
  });

  const {
    data: events,
    isLoading: isEvLoading,
    refetch: refreshEvents,
  } = useQuery<WebhookEvent[]>({
    queryKey: ["webhook-events"],
    queryFn: async () => {
      const res = await fetch("/api/webhooks/events/recent");
      const json = await res.json();
      return (json.data || []).map((ev: any) => ({
        id: ev.event_id,
        webhook_id: ev.webhook_id,
        event: ev.event_type,
        timestamp: ev.created_at,
        status: ev.response_sent ? "processed" : "error",
      }));
    },
    refetchInterval: 5000,
  });

  return {
    webhooks,
    events,
    isLoading: isWhLoading || isEvLoading,
    refreshEvents,
    createWebhook: useMutation({
      mutationFn: async (newWebhook: Partial<Webhook>) => {
        const res = await fetch("/api/webhooks", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            name: newWebhook.name,
            provider: newWebhook.provider,
            enabled: true,
            commands: [],
          }),
        });
        if (!res.ok) throw new Error("Failed to create webhook");
        return res.json();
      },
      onSuccess: () => {
        queryClient.invalidateQueries({ queryKey: ["webhooks"] });
      },
    }),
  };
}
