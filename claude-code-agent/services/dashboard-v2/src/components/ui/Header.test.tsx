import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { Header } from './Header';

// Mock the hook (same pattern as Overview.test.tsx)
vi.mock('../../hooks/useCLIStatus', () => ({
  useCLIStatus: vi.fn(),
}));

import { useCLIStatus } from '../../hooks/useCLIStatus';

// Create wrapper with QueryClient (required for React Query)
const createWrapper = () => {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
    },
  });
  return ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  );
};

describe('Header - CLI Status Indicator', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('should show checking state when loading', () => {
    (useCLIStatus as any).mockReturnValue({
      active: null,
      isLoading: true,
      error: null,
    });

    render(<Header />, { wrapper: createWrapper() });
    
    expect(screen.getByText('CLI: CHECKING...')).toBeInTheDocument();
  });

  it('should show active state when CLI is active', () => {
    (useCLIStatus as any).mockReturnValue({
      active: true,
      isLoading: false,
      error: null,
    });

    render(<Header />, { wrapper: createWrapper() });
    
    expect(screen.getByText('CLI: ACTIVE')).toBeInTheDocument();
    // Check that green icon is present (CheckCircle2)
    const activeIndicator = screen.getByText('CLI: ACTIVE').closest('div');
    expect(activeIndicator?.querySelector('.text-green-500')).toBeInTheDocument();
  });

  it('should show inactive state when CLI is inactive', () => {
    (useCLIStatus as any).mockReturnValue({
      active: false,
      isLoading: false,
      error: null,
    });

    render(<Header />, { wrapper: createWrapper() });
    
    expect(screen.getByText('CLI: INACTIVE')).toBeInTheDocument();
    // Check that red icon is present (XCircle)
    const inactiveIndicator = screen.getByText('CLI: INACTIVE').closest('div');
    expect(inactiveIndicator?.querySelector('.text-red-500')).toBeInTheDocument();
  });

  it('should call useCLIStatus hook', () => {
    (useCLIStatus as any).mockReturnValue({
      active: true,
      isLoading: false,
      error: null,
    });

    render(<Header />, { wrapper: createWrapper() });
    
    expect(useCLIStatus).toHaveBeenCalled();
  });

  it('should display CLI status indicator in header', () => {
    (useCLIStatus as any).mockReturnValue({
      active: true,
      isLoading: false,
      error: null,
    });

    const { container } = render(<Header />, { wrapper: createWrapper() });
    
    // Check that CLI status is in header
    const header = container.querySelector('header');
    expect(header).toBeInTheDocument();
    expect(screen.getByText('CLI: ACTIVE')).toBeInTheDocument();
  });

  it('should handle error state', () => {
    (useCLIStatus as any).mockReturnValue({
      active: null,
      isLoading: false,
      error: new Error('Failed to fetch'),
    });

    render(<Header />, { wrapper: createWrapper() });
    
    // Should show checking or inactive when error occurs
    expect(screen.getByText(/CLI:/)).toBeInTheDocument();
  });
});
