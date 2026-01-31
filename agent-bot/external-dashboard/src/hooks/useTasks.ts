import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '../services/api';
import type { TaskStatus } from '../types';

export function useTasks(status?: TaskStatus, limit = 50, offset = 0) {
  return useQuery({
    queryKey: ['tasks', status, limit, offset],
    queryFn: () => api.tasks.list({ status, limit, offset }),
    refetchInterval: 5000,
  });
}

export function useTask(taskId: string) {
  return useQuery({
    queryKey: ['task', taskId],
    queryFn: () => api.tasks.get(taskId),
    enabled: !!taskId,
    refetchInterval: 2000,
  });
}

export function useTaskStats() {
  return useQuery({
    queryKey: ['taskStats'],
    queryFn: () => api.tasks.getStats(),
    refetchInterval: 5000,
  });
}

export function useQueueLength() {
  return useQuery({
    queryKey: ['queueLength'],
    queryFn: () => api.tasks.getQueueLength(),
    refetchInterval: 3000,
  });
}

export function useCancelTask() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (taskId: string) => api.tasks.cancel(taskId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['tasks'] });
      queryClient.invalidateQueries({ queryKey: ['taskStats'] });
    },
  });
}
