import { describe, it, expect, vi, beforeEach } from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ReactNode } from 'react';
import { useCLIStatus } from './useCLIStatus';

// Mock fetch globally
global.fetch = vi.fn();

// Create wrapper with QueryClient
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

describe('useCLIStatus', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('should start with loading state', () => {
    (global.fetch as any).mockResolvedValueOnce({
      ok: true,
      json: async () => ({ active: true }),
    });

    const { result } = renderHook(() => useCLIStatus(), {
      wrapper: createWrapper(),
    });
    
    expect(result.current.isLoading).toBe(true);
    expect(result.current.active).toBe(null);
  });

  it('should load active status successfully', async () => {
    (global.fetch as any).mockResolvedValueOnce({
      ok: true,
      json: async () => ({ active: true }),
    });

    const { result } = renderHook(() => useCLIStatus(), {
      wrapper: createWrapper(),
    });
    
    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });
    
    expect(result.current.active).toBe(true);
    expect(result.current.error).toBeNull();
  });

  it('should load inactive status successfully', async () => {
    (global.fetch as any).mockResolvedValueOnce({
      ok: true,
      json: async () => ({ active: false }),
    });

    const { result } = renderHook(() => useCLIStatus(), {
      wrapper: createWrapper(),
    });
    
    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });
    
    expect(result.current.active).toBe(false);
  });

  it('should handle fetch errors gracefully', async () => {
    (global.fetch as any).mockRejectedValueOnce(new Error('Network error'));

    const { result } = renderHook(() => useCLIStatus(), {
      wrapper: createWrapper(),
    });
    
    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });
    
    expect(result.current.error).toBeTruthy();
    expect(result.current.active).toBe(null);
  });

  it('should handle non-ok responses', async () => {
    (global.fetch as any).mockResolvedValueOnce({
      ok: false,
      status: 500,
    });

    const { result } = renderHook(() => useCLIStatus(), {
      wrapper: createWrapper(),
    });
    
    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });
    
    expect(result.current.error).toBeTruthy();
  });

  it('should use correct query key', () => {
    (global.fetch as any).mockResolvedValueOnce({
      ok: true,
      json: async () => ({ active: true }),
    });

    renderHook(() => useCLIStatus(), {
      wrapper: createWrapper(),
    });
    
    // Verify fetch was called with correct endpoint
    expect(global.fetch).toHaveBeenCalledWith('/api/credentials/cli-status');
  });
});
