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
const mapTrendData = (data: any): DailyMetric[] => {
  if (!data?.dates) return [];
  return data.dates.map((date: string, i: number) => ({
    date: date.split("-").slice(1).join("/"), // MM/DD
    cost: data.costs[i] || 0,
    tokens: data.tokens?.[i] || 0,
    latency: Math.round(data.avg_latency?.[i] || 0),
    errors: data.error_counts?.[i] || 0,
  }));
};

const mapAgentData = (data: any): AgentMetric[] => {
  if (!data?.subagents) return [];
  return data.subagents.map((name: string, i: number) => {
    const cost = data.costs[i] || 0;
    const tasks = data.task_counts?.[i] || 0;
    // Simple efficiency score: more tasks per dollar is better
    // Capped at 100. Arbitrary formula for visual demo.
    const efficiency = Math.min(100, Math.round((tasks / (cost + 0.1)) * 5)); 
    
    return {
      name: name.toUpperCase(),
      cost,
      tasks,
      efficiency,
    };
  });
};

export function useAnalyticsData() {
  const { data: trendData, isLoading: isTrendLoading } = useQuery({
    queryKey: ["analytics", "trends"],
    queryFn: async () => {
      const res = await fetch("/api/analytics/costs/daily?days=30");
      if (!res.ok) throw new Error("Failed to fetch trend data");
      return mapTrendData(await res.json());
    },
    refetchInterval: 10000,
  });

  const { data: agentData, isLoading: isAgentLoading } = useQuery({
    queryKey: ["analytics", "agents"],
    queryFn: async () => {
      const res = await fetch("/api/analytics/costs/by-subagent?days=30");
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
