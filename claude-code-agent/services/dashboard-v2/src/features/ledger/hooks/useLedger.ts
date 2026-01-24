import { useQuery } from "@tanstack/react-query";
import { useState } from "react";

export interface LedgerTask {
  id: string;
  session_id: string;
  assigned_agent: string;
  status: string;
  cost_usd: string;
  duration_seconds: number;
  created_at: string;
}

export function useLedger() {
  const [page, setPage] = useState(1);
  const [filters, setFilters] = useState({
    session_id: "",
    status: "",
    assigned_agent: "",
  });

  const queryParams = new URLSearchParams({
    page: page.toString(),
    session_id: filters.session_id,
    status: filters.status,
    subagent: filters.assigned_agent,
  }).toString();

  const { data, isLoading, refetch } = useQuery<{ tasks: LedgerTask[]; totalPages: number }>({
    queryKey: ["ledger", page, filters],
    queryFn: async () => {
      const res = await fetch(`/api/tasks/table?${queryParams}`);
      if (!res.ok) throw new Error("Failed to fetch ledger");
      const result = await res.json();
      return {
        tasks: (result.tasks || []).map((t: any) => ({
          ...t,
          task_id: t.task_id || "N/A",
          id: t.task_id || Math.random().toString(),
        })),
        totalPages: result.total_pages || 1,
      };
    },
    refetchInterval: 2000,
  });

  const { data: agents } = useQuery<string[]>({
    queryKey: ["agents"],
    queryFn: async () => {
      const res = await fetch("/api/agents");
      const data = await res.json();
      return Array.isArray(data) ? data.map((a: any) => typeof a === 'string' ? a : a.name || "") : [];
    },
  });

  return {
    tasks: data?.tasks || [],
    agents: agents || [],
    isLoading,
    refetch,
    filters,
    setFilters: (newFilters: Partial<typeof filters>) => {
      setFilters((prev) => ({ ...prev, ...newFilters }));
      setPage(1);
    },
    page,
    setPage,
    totalPages: data?.totalPages || 1,
  };
}
