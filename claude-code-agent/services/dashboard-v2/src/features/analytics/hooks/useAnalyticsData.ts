import { useQuery } from "@tanstack/react-query";

export function useAnalyticsData() {
  const { data: costData, isLoading: isCostLoading } = useQuery({
    queryKey: ["analytics", "costs"],
    queryFn: async () => {
      const res = await fetch("/api/analytics/costs/daily");
      if (!res.ok) throw new Error("Failed to fetch cost data");
      const data = await res.json();
      return data.dates.map((date: string, i: number) => ({
        date: date.split("-").slice(1).join("/"), // MM/DD for cleaner display
        cost: data.costs[i],
      }));
    },
    refetchInterval: 5000,
  });

  const { data: performanceData, isLoading: isPerfLoading } = useQuery({
    queryKey: ["analytics", "performance"],
    queryFn: async () => {
      const res = await fetch("/api/analytics/costs/by-subagent");
      if (!res.ok) throw new Error("Failed to fetch performance data");
      const data = await res.json();
      return data.subagents.map((name: string, i: number) => ({
        name: name.toUpperCase(),
        cost: data.costs[i],
      }));
    },
    refetchInterval: 5000,
  });

  return {
    costData,
    performanceData,
    isLoading: isCostLoading || isPerfLoading,
    error: null,
  };
}
