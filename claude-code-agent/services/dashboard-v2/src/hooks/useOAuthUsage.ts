import { useQuery } from "@tanstack/react-query";

/**
 * Session (5-hour) usage data from Anthropic OAuth API.
 * The API returns utilization as a percentage (0-100).
 */
export interface SessionUsage {
  utilization: number; // Percentage used (0-100)
  percentage: number; // Same as utilization
  remaining_percentage: number; // 100 - utilization
  is_exceeded: boolean;
  resets_at: string | null; // ISO timestamp when limit resets
}

/**
 * Weekly (7-day) usage data from Anthropic OAuth API.
 * The API returns utilization as a percentage (0-100).
 */
export interface WeeklyUsage {
  utilization: number; // Percentage used (0-100)
  percentage: number; // Same as utilization
  remaining_percentage: number; // 100 - utilization
  is_exceeded: boolean;
  resets_at: string | null; // ISO timestamp when limit resets
}

export interface OAuthUsageResponse {
  success: boolean;
  error?: string | null;
  session: SessionUsage | null;
  weekly: WeeklyUsage | null;
}

export function useOAuthUsage() {
  const { data, isLoading, error, refetch } = useQuery<OAuthUsageResponse>({
    queryKey: ["oauth-usage"],
    queryFn: async () => {
      const res = await fetch("/api/credentials/usage");
      if (!res.ok) throw new Error("Failed to fetch OAuth usage");
      return res.json();
    },
    refetchInterval: 60000, // Poll every 60 seconds (usage doesn't change as frequently)
    retry: 2,
    staleTime: 30000, // Consider data fresh for 30 seconds
  });

  return {
    usage: data,
    isLoading,
    error,
    refetch,
    hasSessionData: data?.session !== null,
    hasWeeklyData: data?.weekly !== null,
  };
}
