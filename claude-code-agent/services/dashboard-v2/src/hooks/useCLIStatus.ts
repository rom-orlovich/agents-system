import { useQuery } from "@tanstack/react-query";

interface CLIStatusResponse {
  active: boolean;
  message?: string;
}

export function useCLIStatus() {
  const { data, isLoading, error } = useQuery<CLIStatusResponse>({
    queryKey: ["cli-status"],
    queryFn: async () => {
      const res = await fetch("/api/credentials/cli-status");
      if (!res.ok) throw new Error("Failed to fetch CLI status");
      return res.json();
    },
    refetchInterval: 5000, // Poll every 5 seconds (same as other hooks)
    retry: 1, // Retry once on failure
  });

  return {
    active: data?.active ?? null,
    isLoading,
    error,
    message: data?.message,
  };
}
