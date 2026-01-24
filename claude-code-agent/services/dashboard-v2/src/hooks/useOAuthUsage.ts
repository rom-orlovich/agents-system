import { useQuery } from "@tanstack/react-query";

export interface SessionUsage {
  used: number;
  limit: number;
  remaining: number;
  percentage: number;
  is_exceeded: boolean;
}

export interface WeeklyUsage {
  used: number;
  limit: number;
  remaining: number;
  percentage: number;
  is_exceeded: boolean;
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
