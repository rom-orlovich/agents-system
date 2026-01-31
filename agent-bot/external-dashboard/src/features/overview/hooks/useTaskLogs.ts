import { useQuery } from "@tanstack/react-query";
import { api } from "../../../services/api";

export interface TaskLogs {
  task_id: string;
  status: "queued" | "running" | "completed" | "failed";
  output: string;
  is_live: boolean;
  started_at: string | null;
  completed_at: string | null;
}

export function useTaskLogs(taskId: string | null) {
  return useQuery({
    queryKey: ["task-logs", taskId],
    queryFn: async (): Promise<TaskLogs> => {
      if (!taskId) throw new Error("No task ID");
      const response = await api.get(`/api/v1/tasks/${taskId}/logs`);
      return response.data;
    },
    enabled: !!taskId,
    refetchInterval: (query) => {
      const data = query.state.data;
      if (data?.is_live) {
        return 1000;
      }
      return false;
    },
  });
}
