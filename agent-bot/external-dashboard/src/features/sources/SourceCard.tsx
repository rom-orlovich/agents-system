import { GitBranch, FileText, TicketIcon, RefreshCw, Trash2, Power, PowerOff } from "lucide-react";
import type { DataSource } from "./hooks/useSources";

interface SourceCardProps {
  source: DataSource;
  onSync: () => void;
  onToggle: () => void;
  onDelete: () => void;
  isSyncing: boolean;
  isUpdating: boolean;
  isDeleting: boolean;
}

const SOURCE_ICONS = {
  github: GitBranch,
  jira: TicketIcon,
  confluence: FileText,
};

const SOURCE_COLORS = {
  github: "text-gray-800",
  jira: "text-blue-600",
  confluence: "text-blue-400",
};

export function SourceCard({
  source,
  onSync,
  onToggle,
  onDelete,
  isSyncing,
  isUpdating,
  isDeleting,
}: SourceCardProps) {
  const Icon = SOURCE_ICONS[source.source_type] || FileText;
  const colorClass = SOURCE_COLORS[source.source_type] || "text-gray-600";

  const config = JSON.parse(source.config_json || "{}");

  const getStatusColor = (status: string | null) => {
    switch (status) {
      case "completed":
        return "bg-green-500";
      case "failed":
        return "bg-red-500";
      case "running":
        return "bg-yellow-500";
      default:
        return "bg-gray-400";
    }
  };

  const formatDate = (dateStr: string | null) => {
    if (!dateStr) return "Never";
    return new Date(dateStr).toLocaleString();
  };

  return (
    <div
      className={`border p-4 transition-all ${
        source.enabled
          ? "border-gray-200 bg-white"
          : "border-gray-100 bg-gray-50 opacity-60"
      }`}
    >
      <div className="flex items-start justify-between mb-3">
        <div className="flex items-center gap-3">
          <div className={`p-2 border border-gray-200 ${colorClass}`}>
            <Icon size={20} />
          </div>
          <div>
            <div className="font-heading text-sm">{source.name}</div>
            <div className="text-[10px] text-gray-400 uppercase">
              {source.source_type}
            </div>
          </div>
        </div>

        <div className="flex items-center gap-1">
          <div
            className={`w-2 h-2 rounded-full ${getStatusColor(
              source.last_sync_status
            )}`}
            title={source.last_sync_status || "Not synced"}
          />
        </div>
      </div>

      <div className="space-y-2 mb-4 text-[10px] text-gray-500">
        <div className="flex justify-between">
          <span>Last Sync:</span>
          <span className="font-mono">{formatDate(source.last_sync_at)}</span>
        </div>
        <div className="flex justify-between">
          <span>Status:</span>
          <span className="font-mono uppercase">
            {source.last_sync_status || "PENDING"}
          </span>
        </div>
        {source.source_type === "github" && config.include_patterns && (
          <div className="flex justify-between">
            <span>Repos:</span>
            <span className="font-mono truncate max-w-[150px]">
              {config.include_patterns.join(", ") || "All"}
            </span>
          </div>
        )}
        {source.source_type === "jira" && config.issue_types && (
          <div className="flex justify-between">
            <span>Types:</span>
            <span className="font-mono truncate max-w-[150px]">
              {config.issue_types.join(", ")}
            </span>
          </div>
        )}
        {source.source_type === "confluence" && config.spaces && (
          <div className="flex justify-between">
            <span>Spaces:</span>
            <span className="font-mono truncate max-w-[150px]">
              {config.spaces.join(", ") || "All"}
            </span>
          </div>
        )}
      </div>

      <div className="flex gap-2">
        <button
          type="button"
          onClick={onSync}
          disabled={isSyncing || !source.enabled}
          className="flex-1 flex items-center justify-center gap-1 px-2 py-1.5 border border-gray-200 hover:bg-gray-50 text-[10px] font-heading disabled:opacity-50 disabled:cursor-not-allowed"
        >
          <RefreshCw size={12} className={isSyncing ? "animate-spin" : ""} />
          {isSyncing ? "SYNCING..." : "SYNC"}
        </button>

        <button
          type="button"
          onClick={onToggle}
          disabled={isUpdating}
          className={`flex items-center justify-center gap-1 px-2 py-1.5 border text-[10px] font-heading disabled:opacity-50 ${
            source.enabled
              ? "border-orange-200 text-orange-600 hover:bg-orange-50"
              : "border-green-200 text-green-600 hover:bg-green-50"
          }`}
          title={source.enabled ? "Disable source" : "Enable source"}
        >
          {source.enabled ? <PowerOff size={12} /> : <Power size={12} />}
        </button>

        <button
          type="button"
          onClick={onDelete}
          disabled={isDeleting}
          className="flex items-center justify-center gap-1 px-2 py-1.5 border border-red-200 text-red-600 hover:bg-red-50 text-[10px] font-heading disabled:opacity-50"
          title="Delete source"
        >
          <Trash2 size={12} />
        </button>
      </div>
    </div>
  );
}
