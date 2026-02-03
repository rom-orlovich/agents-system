import { RefreshCw } from "lucide-react";
import { IntegrationCard } from "./IntegrationCard";
import { useOAuthStatus } from "./hooks/useOAuthStatus";

const PLATFORM_ORDER = ["github", "jira", "slack", "sentry"];

export function IntegrationsFeature() {
  const {
    statuses,
    isLoading,
    isError,
    error,
    refetch,
    revoke,
    isRevoking,
    install,
    isInstalling,
  } = useOAuthStatus();

  if (isLoading) {
    return (
      <div className="p-8 text-center font-heading">LOADING_INTEGRATIONS...</div>
    );
  }

  if (isError) {
    return (
      <div className="p-8 text-center">
        <div className="text-red-500 font-heading mb-4">
          ERROR: {error instanceof Error ? error.message : "Failed to load integrations"}
        </div>
        <button
          type="button"
          onClick={() => refetch()}
          className="px-4 py-2 border border-gray-200 hover:bg-gray-50 text-[10px] font-heading"
        >
          RETRY
        </button>
      </div>
    );
  }

  const orderedStatuses = PLATFORM_ORDER.map(
    (platform) => statuses?.[platform]
  ).filter(Boolean);

  const connectedCount = orderedStatuses.filter((s) => s?.connected).length;
  const configuredCount = orderedStatuses.filter((s) => s?.configured).length;

  return (
    <div className="space-y-8 animate-in fade-in duration-500">
      <section className="panel" data-label="INTEGRATIONS">
        <div className="flex justify-between items-center mb-6">
          <div className="flex gap-8">
            <div className="stat-mini">
              <div className="text-[10px] font-heading text-gray-400">
                CONNECTED
              </div>
              <div className="text-xl font-heading font-black text-green-500">
                {connectedCount}
              </div>
            </div>
            <div className="stat-mini">
              <div className="text-[10px] font-heading text-gray-400">
                CONFIGURED
              </div>
              <div className="text-xl font-heading font-black">
                {configuredCount}
              </div>
            </div>
            <div className="stat-mini">
              <div className="text-[10px] font-heading text-gray-400">TOTAL</div>
              <div className="text-xl font-heading font-black">
                {PLATFORM_ORDER.length}
              </div>
            </div>
          </div>
          <button
            type="button"
            onClick={() => refetch()}
            className="p-2 border border-gray-200 hover:bg-gray-50 transition-colors"
          >
            <RefreshCw size={14} />
          </button>
        </div>

        <p className="text-[10px] text-gray-400 mb-6">
          Connect your external services to enable webhook integrations and
          automated workflows. OAuth connections allow the agent to interact
          with these services on your behalf.
        </p>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {orderedStatuses.map(
            (status) =>
              status && (
                <IntegrationCard
                  key={status.platform}
                  status={status}
                  onConnect={() => install(status.platform)}
                  onDisconnect={() => revoke(status.platform)}
                  isConnecting={isInstalling}
                  isDisconnecting={isRevoking}
                />
              )
          )}
        </div>
      </section>

      <section className="panel" data-label="CONFIGURATION_GUIDE">
        <h2 className="text-sm mb-4 font-heading text-gray-400">
          SETUP_INSTRUCTIONS
        </h2>
        <div className="space-y-4 text-[10px] font-mono text-gray-600">
          <div>
            <div className="font-heading text-gray-800 mb-1">GitHub</div>
            <p>
              1. Create a GitHub App at github.com/settings/apps
              <br />
              2. Set GITHUB_CLIENT_ID and GITHUB_CLIENT_SECRET
              <br />
              3. Configure webhook URL: {"{BASE_URL}"}/webhooks/github
            </p>
          </div>
          <div>
            <div className="font-heading text-gray-800 mb-1">Jira</div>
            <p>
              1. Create OAuth 2.0 app at developer.atlassian.com
              <br />
              2. Set JIRA_CLIENT_ID and JIRA_CLIENT_SECRET
              <br />
              3. Add callback URL: {"{BASE_URL}"}/oauth/callback/jira
            </p>
          </div>
          <div>
            <div className="font-heading text-gray-800 mb-1">Slack</div>
            <p>
              1. Create Slack App at api.slack.com/apps
              <br />
              2. Set SLACK_CLIENT_ID and SLACK_CLIENT_SECRET
              <br />
              3. Configure OAuth redirect: {"{BASE_URL}"}/oauth/callback/slack
            </p>
          </div>
          <div>
            <div className="font-heading text-gray-800 mb-1">Sentry</div>
            <p>
              1. Generate auth token at sentry.io/settings/auth-tokens
              <br />
              2. Set SENTRY_AUTH_TOKEN and SENTRY_ORG_SLUG
              <br />
              3. Configure webhook in Sentry project settings
            </p>
          </div>
        </div>
      </section>
    </div>
  );
}
