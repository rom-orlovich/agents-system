import { describe, it, expect, vi, beforeEach } from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ReactNode } from 'react';
import { useMetrics, type Metric } from './useMetrics';

global.fetch = vi.fn();

const createWrapper = () => {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
    },
  });
  return ({ children }: { children: ReactNode }) => (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  );
};

describe('Metric interface', () => {
  it('should require oauth_session_used field', () => {
    const incompleteMetric = {
      queue_depth: 0,
      active_sessions: 0,
      wires_connected: 0,
      daily_burn: 0,
      total_jobs: 0,
      cumulative_cost: 0,
      oauth_session_limit: 0,
      oauth_session_percentage: 0,
      oauth_weekly_used: 0,
      oauth_weekly_limit: 0,
      oauth_weekly_percentage: 0,
    };

    const metric: Metric = {
      ...incompleteMetric,
      oauth_session_used: 0,
    };

    expect(typeof metric.oauth_session_used).toBe('number');
  });

  it('should require oauth_session_limit field', () => {
    const metricWithoutOAuth: Omit<Metric, 'oauth_session_limit'> = {
      queue_depth: 0,
      active_sessions: 0,
      wires_connected: 0,
      daily_burn: 0,
      total_jobs: 0,
      cumulative_cost: 0,
      oauth_session_used: 0,
      oauth_session_percentage: 0,
      oauth_weekly_used: 0,
      oauth_weekly_limit: 0,
      oauth_weekly_percentage: 0,
    };

    const metric: Metric = {
      ...metricWithoutOAuth,
      oauth_session_limit: 0,
    };

    expect(typeof metric.oauth_session_limit).toBe('number');
  });

  it('should require oauth_session_percentage field', () => {
    const metricWithoutOAuth: Omit<Metric, 'oauth_session_percentage'> = {
      queue_depth: 0,
      active_sessions: 0,
      wires_connected: 0,
      daily_burn: 0,
      total_jobs: 0,
      cumulative_cost: 0,
      oauth_session_used: 0,
      oauth_session_limit: 0,
      oauth_weekly_used: 0,
      oauth_weekly_limit: 0,
      oauth_weekly_percentage: 0,
    };

    const metric: Metric = {
      ...metricWithoutOAuth,
      oauth_session_percentage: 0,
    };

    expect(typeof metric.oauth_session_percentage).toBe('number');
  });

  it('should require oauth_weekly_used field', () => {
    const metricWithoutOAuth: Omit<Metric, 'oauth_weekly_used'> = {
      queue_depth: 0,
      active_sessions: 0,
      wires_connected: 0,
      daily_burn: 0,
      total_jobs: 0,
      cumulative_cost: 0,
      oauth_session_used: 0,
      oauth_session_limit: 0,
      oauth_session_percentage: 0,
      oauth_weekly_limit: 0,
      oauth_weekly_percentage: 0,
    };

    const metric: Metric = {
      ...metricWithoutOAuth,
      oauth_weekly_used: 0,
    };

    expect(typeof metric.oauth_weekly_used).toBe('number');
  });

  it('should require oauth_weekly_limit field', () => {
    const metricWithoutOAuth: Omit<Metric, 'oauth_weekly_limit'> = {
      queue_depth: 0,
      active_sessions: 0,
      wires_connected: 0,
      daily_burn: 0,
      total_jobs: 0,
      cumulative_cost: 0,
      oauth_session_used: 0,
      oauth_session_limit: 0,
      oauth_session_percentage: 0,
      oauth_weekly_used: 0,
      oauth_weekly_percentage: 0,
    };

    const metric: Metric = {
      ...metricWithoutOAuth,
      oauth_weekly_limit: 0,
    };

    expect(typeof metric.oauth_weekly_limit).toBe('number');
  });

  it('should require oauth_weekly_percentage field', () => {
    const metricWithoutOAuth: Omit<Metric, 'oauth_weekly_percentage'> = {
      queue_depth: 0,
      active_sessions: 0,
      wires_connected: 0,
      daily_burn: 0,
      total_jobs: 0,
      cumulative_cost: 0,
      oauth_session_used: 0,
      oauth_session_limit: 0,
      oauth_session_percentage: 0,
      oauth_weekly_used: 0,
      oauth_weekly_limit: 0,
    };

    const metric: Metric = {
      ...metricWithoutOAuth,
      oauth_weekly_percentage: 0,
    };

    expect(typeof metric.oauth_weekly_percentage).toBe('number');
  });

  it('should accept all OAuth fields with correct types', () => {
    const metric: Metric = {
      queue_depth: 0,
      active_sessions: 0,
      wires_connected: 0,
      daily_burn: 0,
      total_jobs: 0,
      cumulative_cost: 0,
      oauth_session_used: 100,
      oauth_session_limit: 1000,
      oauth_session_percentage: 10.5,
      oauth_weekly_used: 500,
      oauth_weekly_limit: 5000,
      oauth_weekly_percentage: 10.0,
    };

    expect(metric.oauth_session_used).toBe(100);
    expect(metric.oauth_session_limit).toBe(1000);
    expect(metric.oauth_session_percentage).toBe(10.5);
    expect(metric.oauth_weekly_used).toBe(500);
    expect(metric.oauth_weekly_limit).toBe(5000);
    expect(metric.oauth_weekly_percentage).toBe(10.0);
  });
});

describe('useMetrics analytics fetch', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('should fetch analytics summary and map today_cost to daily_burn', async () => {
    (global.fetch as unknown as ReturnType<typeof vi.fn>)
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          queue_length: 5,
          sessions: 2,
          connections: 3,
        }),
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          today_cost: 12.5,
          today_tasks: 10,
          total_cost: 100.0,
          total_tasks: 50,
        }),
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => [],
      });

    const { result } = renderHook(() => useMetrics(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    expect(result.current.metrics?.daily_burn).toBe(12.5);
  });

  it('should map total_tasks to total_jobs', async () => {
    (global.fetch as unknown as ReturnType<typeof vi.fn>)
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          queue_length: 0,
          sessions: 0,
          connections: 0,
        }),
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          today_cost: 0,
          today_tasks: 0,
          total_cost: 0,
          total_tasks: 42,
        }),
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => [],
      });

    const { result } = renderHook(() => useMetrics(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    expect(result.current.metrics?.total_jobs).toBe(42);
  });

  it('should map total_cost to cumulative_cost', async () => {
    (global.fetch as unknown as ReturnType<typeof vi.fn>)
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          queue_length: 0,
          sessions: 0,
          connections: 0,
        }),
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          today_cost: 0,
          today_tasks: 0,
          total_cost: 250.75,
          total_tasks: 0,
        }),
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => [],
      });

    const { result } = renderHook(() => useMetrics(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    expect(result.current.metrics?.cumulative_cost).toBe(250.75);
  });

  it('should handle analytics fetch errors gracefully', async () => {
    (global.fetch as unknown as ReturnType<typeof vi.fn>)
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          queue_length: 0,
          sessions: 0,
          connections: 0,
        }),
      })
      .mockRejectedValueOnce(new Error('Analytics fetch failed'))
      .mockResolvedValueOnce({
        ok: true,
        json: async () => [],
      });

    const { result } = renderHook(() => useMetrics(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    expect(result.current.metrics?.daily_burn).toBe(0);
    expect(result.current.metrics?.total_jobs).toBe(0);
    expect(result.current.metrics?.cumulative_cost).toBe(0);
  });

  it('should call analytics summary endpoint', async () => {
    (global.fetch as unknown as ReturnType<typeof vi.fn>)
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          queue_length: 0,
          sessions: 0,
          connections: 0,
        }),
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          today_cost: 0,
          today_tasks: 0,
          total_cost: 0,
          total_tasks: 0,
        }),
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => [],
      });

    renderHook(() => useMetrics(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(global.fetch).toHaveBeenCalledWith('/api/analytics/summary');
    });
  });
});

describe('useMetrics OAuth fetch', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('should fetch OAuth usage and map session data', async () => {
    (global.fetch as unknown as ReturnType<typeof vi.fn>)
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          queue_length: 0,
          sessions: 0,
          connections: 0,
        }),
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          today_cost: 0,
          today_tasks: 0,
          total_cost: 0,
          total_tasks: 0,
        }),
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          success: true,
          session: {
            used: 100,
            limit: 1000,
            remaining: 900,
            percentage: 10.0,
            is_exceeded: false,
          },
          weekly: null,
        }),
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => [],
      });

    const { result } = renderHook(() => useMetrics(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    expect(result.current.metrics?.oauth_session_used).toBe(100);
    expect(result.current.metrics?.oauth_session_limit).toBe(1000);
    expect(result.current.metrics?.oauth_session_percentage).toBe(10.0);
  });

  it('should map OAuth weekly data', async () => {
    (global.fetch as unknown as ReturnType<typeof vi.fn>)
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          queue_length: 0,
          sessions: 0,
          connections: 0,
        }),
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          today_cost: 0,
          today_tasks: 0,
          total_cost: 0,
          total_tasks: 0,
        }),
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          success: true,
          session: null,
          weekly: {
            used: 500,
            limit: 5000,
            remaining: 4500,
            percentage: 10.0,
            is_exceeded: false,
          },
        }),
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => [],
      });

    const { result } = renderHook(() => useMetrics(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    expect(result.current.metrics?.oauth_weekly_used).toBe(500);
    expect(result.current.metrics?.oauth_weekly_limit).toBe(5000);
    expect(result.current.metrics?.oauth_weekly_percentage).toBe(10.0);
  });

  it('should calculate percentage from used and limit', async () => {
    (global.fetch as unknown as ReturnType<typeof vi.fn>)
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          queue_length: 0,
          sessions: 0,
          connections: 0,
        }),
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          today_cost: 0,
          today_tasks: 0,
          total_cost: 0,
          total_tasks: 0,
        }),
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          success: true,
          session: {
            used: 250,
            limit: 1000,
            remaining: 750,
            percentage: 25.0,
            is_exceeded: false,
          },
          weekly: {
            used: 1250,
            limit: 5000,
            remaining: 3750,
            percentage: 25.0,
            is_exceeded: false,
          },
        }),
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => [],
      });

    const { result } = renderHook(() => useMetrics(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    expect(result.current.metrics?.oauth_session_percentage).toBe(25.0);
    expect(result.current.metrics?.oauth_weekly_percentage).toBe(25.0);
  });

  it('should handle null OAuth data gracefully', async () => {
    (global.fetch as unknown as ReturnType<typeof vi.fn>)
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          queue_length: 0,
          sessions: 0,
          connections: 0,
        }),
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          today_cost: 0,
          today_tasks: 0,
          total_cost: 0,
          total_tasks: 0,
        }),
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          success: true,
          session: null,
          weekly: null,
        }),
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => [],
      });

    const { result } = renderHook(() => useMetrics(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    expect(result.current.metrics?.oauth_session_used).toBe(0);
    expect(result.current.metrics?.oauth_session_limit).toBe(0);
    expect(result.current.metrics?.oauth_weekly_used).toBe(0);
    expect(result.current.metrics?.oauth_weekly_limit).toBe(0);
  });

  it('should handle OAuth fetch errors gracefully', async () => {
    (global.fetch as unknown as ReturnType<typeof vi.fn>)
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          queue_length: 0,
          sessions: 0,
          connections: 0,
        }),
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          today_cost: 0,
          today_tasks: 0,
          total_cost: 0,
          total_tasks: 0,
        }),
      })
      .mockRejectedValueOnce(new Error('OAuth fetch failed'))
      .mockResolvedValueOnce({
        ok: true,
        json: async () => [],
      });

    const { result } = renderHook(() => useMetrics(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    expect(result.current.metrics?.oauth_session_used).toBe(0);
    expect(result.current.metrics?.oauth_weekly_used).toBe(0);
  });

  it('should call OAuth usage endpoint', async () => {
    (global.fetch as unknown as ReturnType<typeof vi.fn>)
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          queue_length: 0,
          sessions: 0,
          connections: 0,
        }),
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          today_cost: 0,
          today_tasks: 0,
          total_cost: 0,
          total_tasks: 0,
        }),
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          success: true,
          session: null,
          weekly: null,
        }),
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => [],
      });

    renderHook(() => useMetrics(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(global.fetch).toHaveBeenCalledWith('/api/credentials/usage');
    });
  });
});

