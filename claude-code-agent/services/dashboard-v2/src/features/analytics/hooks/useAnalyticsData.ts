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
// Generate slots in Local Time for display
const generateTimeSlots = (days: number): string[] => {
  const slots: string[] = [];
  const now = new Date();
  
  if (days <= 2) {
    // Hourly slots for the last 24h * days
    // We go from oldest to newest to match chart L->R
    for (let i = (days * 24); i >= 0; i--) {
      const d = new Date(now.getTime() - i * 60 * 60 * 1000);
      const hours = d.getHours().toString().padStart(2, '0');
      slots.push(`${hours}:00`);
    }
  } else {
    // Daily slots
    for (let i = days; i >= 0; i--) {
      const d = new Date(now.getTime() - i * 24 * 60 * 60 * 1000);
      const month = (d.getMonth() + 1).toString().padStart(2, '0');
      const day = d.getDate().toString().padStart(2, '0');
      slots.push(`${month}/${day}`);
    }
  }
  return slots;
};

const mapTrendData = (data: any, days: number): DailyMetric[] => {
  const slots = generateTimeSlots(days);
  const dataMap = new Map<string, DailyMetric>();
  
  if (data?.dates) {
    data.dates.forEach((dateStr: string, i: number) => {
      // Backend returns UTC string "YYYY-MM-DD HH:00:00" or "YYYY-MM-DD"
      // We need to convert this UTC time to Local Time to match our slots
      let key = "";
      
      try {
        // Append 'Z' to treat as UTC if it's a standard ISO-like string without timezone
        const cleanDateStr = dateStr.replace(" ", "T") + "Z"; 
        const d = new Date(cleanDateStr);
        
        if (days <= 2) {
           // Extract Local Hours
           if (!isNaN(d.getTime())) {
             const hours = d.getHours().toString().padStart(2, '0');
             key = `${hours}:00`;
           }
        } else {
           // Extract Local Date
           if (!isNaN(d.getTime())) {
             const month = (d.getMonth() + 1).toString().padStart(2, '0');
             const day = d.getDate().toString().padStart(2, '0');
             key = `${month}/${day}`;
           }
        }
      } catch (e) {
        console.error("Date parsing error", e);
      }
      
      if (key) {
        // Aggregate if multiple backend buckets fall into same local slot (rare but safest)
        const existing = dataMap.get(key);
        dataMap.set(key, {
          date: key,
          cost: (existing?.cost || 0) + (data.costs[i] || 0),
          tokens: (existing?.tokens || 0) + (data.tokens?.[i] || 0),
          latency: Math.max(existing?.latency || 0, Math.round(data.avg_latency?.[i] || 0)), // Take max latency
          errors: (existing?.errors || 0) + (data.error_counts?.[i] || 0),
        });
      }
    });
  }

  // Merge slots with data
  return slots.map(slot => {
    return dataMap.get(slot) || {
      date: slot,
      cost: 0,
      tokens: 0,
      latency: 0,
      errors: 0
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
