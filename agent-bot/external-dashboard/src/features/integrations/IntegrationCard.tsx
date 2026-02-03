import { AlertTriangle, Check, ClipboardList, Github, Link2, MessageSquare, X } from "lucide-react";
import type { OAuthStatus } from "./hooks/useOAuthStatus";

interface IntegrationCardProps {
  status: OAuthStatus;
  onConnect: () => void;
  onDisconnect: () => void;
  isConnecting: boolean;
  isDisconnecting: boolean;
}

const PLATFORM_ICONS: Record<string, React.ReactNode> = {
  github: <Github size={24} />,
  jira: <ClipboardList size={24} />,
  slack: <MessageSquare size={24} />,
  sentry: <AlertTriangle size={24} />,
};

export function IntegrationCard({
  status,
  onConnect,
  onDisconnect,
  isConnecting,
  isDisconnecting,
}: IntegrationCardProps) {
  const icon = PLATFORM_ICONS[status.platform] || <Link2 size={24} />;
  const isLoading = isConnecting || isDisconnecting;

  return (
    <div className="p-6 border border-gray-100 hover:border-primary transition-colors">
      <div className="flex items-start justify-between mb-4">
        <div className="flex items-center gap-3">
          <div className="text-gray-600">{icon}</div>
          <div>
            <h3 className="text-sm font-heading font-bold">{status.name}</h3>
            <p className="text-[10px] text-gray-400">{status.description}</p>
          </div>
        </div>
        <div
          className={`flex items-center gap-1 px-2 py-1 text-[10px] font-heading border ${
            status.connected
              ? "border-green-200 text-green-600 bg-green-50"
              : status.configured
                ? "border-yellow-200 text-yellow-600 bg-yellow-50"
                : "border-gray-200 text-gray-400 bg-gray-50"
          }`}
        >
          {status.connected ? (
            <>
              <Check size={10} />
              CONNECTED
            </>
          ) : status.configured ? (
            <>
              <X size={10} />
              DISCONNECTED
            </>
          ) : (
            "NOT_CONFIGURED"
          )}
        </div>
      </div>

      {status.connected && status.installed_at && (
        <div className="mb-4 text-[10px] text-gray-400">
          Connected: {new Date(status.installed_at).toLocaleDateString()}
          {status.scopes && status.scopes.length > 0 && (
            <span className="ml-2">
              Scopes: {status.scopes.slice(0, 3).join(", ")}
              {status.scopes.length > 3 && ` +${status.scopes.length - 3} more`}
            </span>
          )}
        </div>
      )}

      <div className="flex gap-2">
        {status.connected ? (
          <button
            type="button"
            onClick={onDisconnect}
            disabled={isLoading}
            className="flex-1 px-4 py-2 text-[10px] font-heading border border-red-200 text-red-600 hover:bg-red-50 transition-colors disabled:opacity-50"
          >
            {isDisconnecting ? "DISCONNECTING..." : "DISCONNECT"}
          </button>
        ) : (
          <button
            type="button"
            onClick={onConnect}
            disabled={isLoading || !status.configured}
            className="flex-1 px-4 py-2 text-[10px] font-heading border border-primary text-primary hover:bg-primary hover:text-white transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {isConnecting ? "CONNECTING..." : status.configured ? "CONNECT" : "NOT_CONFIGURED"}
          </button>
        )}
      </div>

      {!status.configured && (
        <p className="mt-2 text-[10px] text-red-400">
          Missing environment variables. Check server configuration.
        </p>
      )}
    </div>
  );
}
