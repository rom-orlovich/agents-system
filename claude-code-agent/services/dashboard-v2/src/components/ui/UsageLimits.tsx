import { useOAuthUsage } from "../../hooks/useOAuthUsage";

interface UsageBarProps {
  label: string;
  used: number;
  limit: number;
  remaining: number;
  percentage: number;
  isExceeded: boolean;
  period: string;
}

function UsageBar({
  label,
  used,
  limit,
  remaining,
  percentage,
  isExceeded,
  period,
}: UsageBarProps) {
  const barColor = isExceeded
    ? "bg-red-500"
    : percentage >= 90
      ? "bg-yellow-500"
      : percentage >= 75
        ? "bg-orange-500"
        : "bg-blue-500";

  return (
    <div className="space-y-2">
      <div className="flex justify-between items-center text-xs">
        <span className="font-mono font-bold text-gray-700 dark:text-gray-300 uppercase tracking-wider">
          {label}
        </span>
        <span
          className={`font-mono font-bold ${isExceeded ? "text-red-600 dark:text-red-400" : "text-gray-600 dark:text-gray-400"}`}
        >
          {used.toLocaleString()} / {limit.toLocaleString()} ({period})
        </span>
      </div>
      <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-3 overflow-hidden">
        <div
          className={`h-full transition-all duration-300 ${barColor}`}
          style={{ width: `${Math.min(100, percentage)}%` }}
        />
      </div>
      <div className="flex justify-between items-center text-xs">
        <span
          className={`font-mono ${isExceeded ? "text-red-600 dark:text-red-400 font-bold" : "text-gray-500 dark:text-gray-400"}`}
        >
          {isExceeded ? "LIMIT EXCEEDED" : `${remaining.toLocaleString()} remaining`}
        </span>
        <span className="font-mono text-gray-500 dark:text-gray-400">{percentage.toFixed(1)}%</span>
      </div>
    </div>
  );
}

export function UsageLimits() {
  const { usage, isLoading, error } = useOAuthUsage();

  if (isLoading) {
    return (
      <div className="panel p-4">
        <div className="text-sm font-mono text-gray-500 dark:text-gray-400 animate-pulse">
          LOADING_USAGE_DATA...
        </div>
      </div>
    );
  }

  if (error || !usage?.success) {
    return (
      <div className="panel p-4 border border-yellow-500/20 bg-yellow-900/10">
        <div className="text-sm font-mono text-yellow-600 dark:text-yellow-400">
          ⚠️ {usage?.error || "Failed to load usage data"}
        </div>
        {usage?.error?.includes("credentials") && (
          <div className="text-xs text-gray-500 dark:text-gray-400 mt-2">
            Upload credentials via /api/credentials/upload
          </div>
        )}
      </div>
    );
  }

  const hasData = usage.session || usage.weekly;

  if (!hasData) {
    return (
      <div className="panel p-4">
        <div className="text-sm font-mono text-gray-500 dark:text-gray-400">
          No usage data available
        </div>
      </div>
    );
  }

  return (
    <div className="panel p-6 space-y-6">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-heading font-bold tracking-wider text-gray-900 dark:text-gray-100">
          CLAUDE_CODE_USAGE_LIMITS
        </h3>
        <div className="text-xs font-mono text-gray-500 dark:text-gray-400">FROM_ANTHROPIC_API</div>
      </div>

      {usage.session && (
        <UsageBar
          label="Session Limit"
          used={usage.session.used}
          limit={usage.session.limit}
          remaining={usage.session.remaining}
          percentage={usage.session.percentage}
          isExceeded={usage.session.is_exceeded}
          period="5-hour window"
        />
      )}

      {usage.weekly && (
        <UsageBar
          label="Weekly Limit"
          used={usage.weekly.used}
          limit={usage.weekly.limit}
          remaining={usage.weekly.remaining}
          percentage={usage.weekly.percentage}
          isExceeded={usage.weekly.is_exceeded}
          period="7-day window"
        />
      )}

      {usage.session?.is_exceeded || usage.weekly?.is_exceeded ? (
        <div className="mt-4 p-3 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded">
          <div className="text-sm font-mono font-bold text-red-700 dark:text-red-400">
            ⚠️ USAGE_LIMIT_EXCEEDED
          </div>
          <div className="text-xs text-red-600 dark:text-red-500 mt-1">
            Some features may be unavailable until limits reset.
          </div>
        </div>
      ) : null}
    </div>
  );
}
