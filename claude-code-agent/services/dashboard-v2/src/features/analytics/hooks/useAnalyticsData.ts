import { useQuery } from "@tanstack/react-query";

interface DailyMetric {
  date: string;
  cost: number;
  tokens: number;
  latency: number;
  errors: number;
}

interface AgentMetric {
  name: string;
  cost: number;
  tasks: number;
  efficiency: number; // 0-100 score
}

// Map API response to UI data structure
const mapTrendData = (data: any, days: number): DailyMetric[] => {
  if (!data?.dates) return [];
  return data.dates.map((date: string, i: number) => {
    // If we are in "hourly" mode (short timeframe), show HH:00
    // Date string from backend is either "YYYY-MM-DD" or "YYYY-MM-DD HH:00:00"
    let displayDate = "";
    if (days <= 2) {
      // Extract time part: YYYY-MM-DD HH:00:00 -> HH:00
      const timePart = date.split(" ")[1];
      displayDate = timePart ? timePart.substring(0, 5) : date.substring(5);
    } else {
      // Daily: YYYY-MM-DD -> MM/DD
      displayDate = date.split("-").slice(1).join("/");
    }

    return {
      date: displayDate,
      cost: data.costs[i] || 0,
      tokens: data.tokens?.[i] || 0,
      latency: Math.round(data.avg_latency?.[i] || 0),
      errors: data.error_counts?.[i] || 0,
    };
  });
};

const mapAgentData = (data: any): AgentMetric[] => {
  if (!data?.subagents) return [];
  return data.subagents.map((name: string, i: number) => {
    const cost = data.costs[i] || 0;
    const tasks = data.task_counts?.[i] || 0;
    const efficiency = Math.min(100, Math.round((tasks / (cost + 0.1)) * 5)); 
    
    return {
      name: name.toUpperCase(),
      cost,
      tasks,
      efficiency,
    };
  });
};

export function useAnalyticsData(days: number = 7) {
  const granularity = days <= 2 ? "hour" : "day";

  const { data: trendData, isLoading: isTrendLoading } = useQuery({
    queryKey: ["analytics", "trends", days, granularity],
    queryFn: async () => {
      const res = await fetch(`/api/analytics/costs/histogram?days=${days}&granularity=${granularity}`);
      if (!res.ok) throw new Error("Failed to fetch trend data");
      return mapTrendData(await res.json(), days);
    },
    refetchInterval: 10000,
  });

  const { data: agentData, isLoading: isAgentLoading } = useQuery({
    queryKey: ["analytics", "agents", days],
    queryFn: async () => {
      const res = await fetch(`/api/analytics/costs/by-subagent?days=${days}`);
      if (!res.ok) throw new Error("Failed to fetch agent data");
      return mapAgentData(await res.json());
    },
    refetchInterval: 10000,
  });

  return {
    trendData,
    agentData,
    isLoading: isTrendLoading || isAgentLoading,
    error: null,
  };
}
