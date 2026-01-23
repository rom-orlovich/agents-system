import { useQuery } from "@tanstack/react-query";

export interface Metric {
  queue_depth: number;
  active_sessions: number;
  wires_connected: number;
  daily_burn: number;
  total_jobs: number;
  cumulative_cost: number;
  oauth_session_used: number;
  oauth_session_limit: number;
  oauth_session_percentage: number;
  oauth_weekly_used: number;
  oauth_weekly_limit: number;
  oauth_weekly_percentage: number;
}

export interface Task {
  id: string;
  name: string;
  status: string;
  cost: number;
  timestamp: string;
}

interface AnalyticsSummaryResponse {
  today_cost: number;
  today_tasks: number;
  total_cost: number;
  total_tasks: number;
}

interface HealthResponse {
  queue_length: number;
  sessions: number;
  connections: number;
}

interface SessionUsage {
  used: number;
  limit: number;
  remaining: number;
  percentage: number;
  is_exceeded: boolean;
}

interface WeeklyUsage {
  used: number;
  limit: number;
  remaining: number;
  percentage: number;
  is_exceeded: boolean;
}

interface OAuthUsageResponse {
  success: boolean;
  error?: string | null;
  session: SessionUsage | null;
  weekly: WeeklyUsage | null;
}

export function useMetrics() {
  const {
    data: healthData,
    isLoading: isHealthLoading,
    error: healthError,
    refetch: refetchHealth,
  } = useQuery<HealthResponse>({
    queryKey: ["health"],
    queryFn: async () => {
      const res = await fetch("/api/health");
      if (!res.ok) throw new Error("Failed to fetch health");
      return res.json();
    },
    refetchInterval: 2000,
  });

  const {
    data: analyticsData,
    isLoading: isAnalyticsLoading,
    error: analyticsError,
    refetch: refetchAnalytics,
  } = useQuery<AnalyticsSummaryResponse>({
    queryKey: ["analytics-summary"],
    queryFn: async () => {
      const res = await fetch("/api/analytics/summary");
      if (!res.ok) throw new Error("Failed to fetch analytics");
      return res.json();
    },
    refetchInterval: 2000,
  });

  const {
    data: oauthData,
    isLoading: isOAuthLoading,
    error: oauthError,
    refetch: refetchOAuth,
  } = useQuery<OAuthUsageResponse>({
    queryKey: ["oauth-usage"],
    queryFn: async () => {
      try {
        const res = await fetch("/api/credentials/usage");
        if (!res.ok) throw new Error("Failed to fetch OAuth usage");
        return res.json();
      } catch (error) {
        return {
          success: false,
          error: error instanceof Error ? error.message : "Unknown error",
          session: null,
          weekly: null,
        };
      }
    },
    refetchInterval: 60000,
    retry: 2,
    staleTime: 30000,
  });

  const metrics: Metric | undefined = healthData
    ? {
        queue_depth: healthData.queue_length,
        active_sessions: healthData.sessions,
        wires_connected: healthData.connections,
        daily_burn: analyticsData?.today_cost ?? 0,
        total_jobs: analyticsData?.total_tasks ?? 0,
        cumulative_cost: analyticsData?.total_cost ?? 0,
        oauth_session_used: oauthData?.session?.used ?? 0,
        oauth_session_limit: oauthData?.session?.limit ?? 0,
        oauth_session_percentage: oauthData?.session?.percentage ?? 0,
        oauth_weekly_used: oauthData?.weekly?.used ?? 0,
        oauth_weekly_limit: oauthData?.weekly?.limit ?? 0,
        oauth_weekly_percentage: oauthData?.weekly?.percentage ?? 0,
      }
    : undefined;

  const isMetricsLoading = isHealthLoading || isAnalyticsLoading || isOAuthLoading;
  const metricsError = healthError || analyticsError || oauthError;

  interface TaskResponse {
    task_id: string;
    assigned_agent?: string;
    agent_type?: string;
    status: string;
    cost_usd: number;
    created_at: string;
  }

  const {
    data: tasks,
    isLoading: isTasksLoading,
    error: tasksError,
    refetch: refetchTasks,
  } = useQuery<Task[]>({
    queryKey: ["tasks"],
    queryFn: async () => {
      const res = await fetch("/api/tasks");
      if (!res.ok) throw new Error("Failed to fetch tasks");
      const taskData: TaskResponse[] = await res.json();
      return taskData.map((t: TaskResponse): Task => ({
        id: t.task_id,
        name: t.assigned_agent || t.agent_type || "unknown",
        status: t.status,
        cost: t.cost_usd,
        timestamp: t.created_at,
      }));
    },
    refetchInterval: 2000,
  });

  return {
    metrics,
    tasks,
    isLoading: isMetricsLoading || isTasksLoading,
    error: metricsError || tasksError,
    refetch: () => {
      refetchHealth();
      refetchAnalytics();
      refetchOAuth();
      refetchTasks();
    },
  };
}
