import { useQuery } from '@tanstack/react-query';
import { api } from '../services/api';

export function useAgents() {
  return useQuery({
    queryKey: ['agents'],
    queryFn: () => api.agents.list(),
    refetchInterval: 10000,
  });
}

export function useAgentsStatus() {
  return useQuery({
    queryKey: ['agentsStatus'],
    queryFn: () => api.agents.getStatus(),
    refetchInterval: 5000,
  });
}

export function useAgentsHealth() {
  return useQuery({
    queryKey: ['agentsHealth'],
    queryFn: () => api.agents.getHealth(),
    refetchInterval: 10000,
  });
}

export function useAgentsMetrics() {
  return useQuery({
    queryKey: ['agentsMetrics'],
    queryFn: () => api.agents.getMetrics(),
    refetchInterval: 5000,
  });
}
