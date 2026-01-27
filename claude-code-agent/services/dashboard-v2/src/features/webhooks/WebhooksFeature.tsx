import { Activity, Globe, Plus, RefreshCw } from "lucide-react";
import { useState } from "react";
import { CreateWebhookModal } from "./CreateWebhookModal";
import { useWebhooks, type Webhook } from "./hooks/useWebhooks";

export function WebhooksFeature() {
  const { webhooks, events, isLoading, refreshEvents, createWebhook } = useWebhooks();
  const [isModalOpen, setIsModalOpen] = useState(false);

  if (isLoading) return <div className="p-8 text-center font-heading">SYNCING_LISTENERS...</div>;

  return (
    <div className="space-y-8 animate-in fade-in duration-500">
      <section className="panel" data-label="WEBHOOK_MONITOR">
        <div className="flex justify-between items-center mb-6">
          <div className="flex gap-8">
            <div className="stat-mini">
              <div className="text-[10px] font-heading text-gray-400">LISTENERS</div>
              <div className="text-xl font-heading font-black">{webhooks?.length || 0}</div>
            </div>
            <div className="stat-mini">
              <div className="text-[10px] font-heading text-gray-400">STATUS</div>
              <div className="text-xl font-heading font-black text-green-500">READY</div>
            </div>
          </div>
          <div className="flex gap-2">
            <button
              type="button"
              onClick={() => setIsModalOpen(true)}
              className="flex items-center gap-2 px-4 py-2 border border-gray-200 hover:bg-gray-50 text-[10px] font-heading transition-colors"
            >
              <Plus size={14} /> NEW_LISTENER
            </button>
            <button
              type="button"
              onClick={() => refreshEvents()}
              className="p-2 border border-gray-200 hover:bg-gray-50 transition-colors"
            >
              <RefreshCw size={14} />
            </button>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {webhooks?.map((wh) => (
            <div
              key={wh.id}
              className="p-4 border border-gray-100 group hover:border-primary transition-colors"
            >
              <div className="flex justify-between items-start mb-2">
                <div className="text-xs font-heading font-bold">{wh.name}</div>
                <div
                  className={`px-2 py-0.5 text-[10px] font-heading border ${wh.status === "active" ? "border-green-200 text-green-600 bg-green-50" : "border-gray-200 text-gray-400"}`}
                >
                  {wh.status === "active" ? "ACTIVE" : "INACTIVE"}
                </div>
              </div>
              <div className="text-[10px] text-gray-400 font-mono mb-4 truncate">{wh.url}</div>
              <div className="flex items-center gap-2 text-[10px] font-heading text-gray-500 group-hover:text-primary transition-colors border-t border-gray-50 pt-3">
                <Globe size={12} />{" "}
                <span className="tracking-tight">{wh.provider.toUpperCase()}</span>
              </div>
            </div>
          ))}
        </div>
      </section>

      <section className="panel" data-label="INBOUND_TRAFFIC">
        <h2 className="text-sm mb-4 font-heading text-gray-400">EVENT_HISTORY_REALTIME</h2>
        <div className="space-y-2">
          {events?.map((ev) => (
            <div
              key={ev.id}
              className="flex items-center justify-between p-2 text-xs font-mono border-b border-gray-50 group hover:bg-gray-50/50 transition-colors"
            >
              <div className="flex items-center gap-4">
                <div
                  className={`w-1 h-3 ${ev.status === "processed" ? "bg-green-500" : "bg-red-500"}`}
                />
                <span className="text-gray-400">[{whName(webhooks, ev.webhook_id)}]</span>
                <span className="font-bold">{ev.event}</span>
              </div>
              <div className="flex gap-6 items-center">
                <span className="text-[10px] text-gray-400 tabular-nums">
                  {ev.timestamp ? new Date(ev.timestamp).toLocaleTimeString() : "--:--:--"}
                </span>
                <Activity
                  size={12}
                  className={ev.status === "processed" ? "text-gray-200" : "text-red-300"}
                />
              </div>
            </div>
          ))}
        </div>
      </section>
      <CreateWebhookModal
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        onSubmit={async (data) => {
          await createWebhook.mutateAsync(data);
        }}
      />
    </div>
  );
}

function whName(webhooks: Webhook[] | undefined, id: string) {
  return webhooks?.find((w) => w.id === id)?.name || "UNKNOWN";
}
