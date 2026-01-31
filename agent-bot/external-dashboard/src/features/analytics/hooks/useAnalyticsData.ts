import { useQuery } from "@tanstack/react-query";
import { api } from "../../../services/api";

export interface AnalyticsData {
  tasks_by_status: {
    status: string;
    count: number;
  }[];
  tasks_by_source: {
    source: string;
    count: number;
  }[];
  tasks_over_time: {
    date: string;
    completed: number;
    failed: number;
  }[];
  average_duration_seconds: number;
  total_cost_usd: number;
  success_rate: number;
}

export function useAnalyticsData(period: "day" | "week" | "month" = "week") {
  return useQuery({
    queryKey: ["analytics", period],
    queryFn: async (): Promise<AnalyticsData> => {
      const response = await api.get(`/api/v1/analytics?period=${period}`);
      return response.data;
    },
    staleTime: 60000,
    refetchInterval: 60000,
  });
}
