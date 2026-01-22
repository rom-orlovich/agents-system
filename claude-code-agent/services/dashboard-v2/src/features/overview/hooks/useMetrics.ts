import { useQuery } from "@tanstack/react-query";

export interface Metric {
  queue_depth: number;
  active_sessions: number;
  wires_connected: number;
  daily_burn: number;
  total_jobs: number;
  cumulative_cost: number;
}

export interface Task {
  id: string;
  name: string;
  status: string;
  cost: number;
  timestamp: string;
}

export function useMetrics() {
  const {
    data: metrics,
    isLoading: isMetricsLoading,
    error: metricsError,
  } = useQuery<Metric>({
    queryKey: ["metrics"],
    queryFn: async () => {
      const res = await fetch("/api/health");
      if (!res.ok) throw new Error("Failed to fetch metrics");
      const data = await res.json();
      return {
        queue_depth: data.queue_length,
        active_sessions: data.sessions,
        wires_connected: data.connections,
        daily_burn: 0, // Not available in health
        total_jobs: 0, // Not available in health
        cumulative_cost: 0, // Not available in health
      };
    },
    refetchInterval: 2000,
  });

  const {
    data: tasks,
    isLoading: isTasksLoading,
    error: tasksError,
  } = useQuery<Task[]>({
    queryKey: ["tasks"],
    queryFn: async () => {
      const res = await fetch("/api/tasks");
      if (!res.ok) throw new Error("Failed to fetch tasks");
      const data = await res.json();
      return data.map((t: any) => ({
        id: t.task_id,
        name: t.assigned_agent || t.agent_type,
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
  };
}
