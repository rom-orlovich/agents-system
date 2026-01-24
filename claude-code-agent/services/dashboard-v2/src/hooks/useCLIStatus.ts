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
    retry: 1,
  });

  return {
    active: data?.active ?? null,
    isLoading,
    error,
    message: data?.message,
  };
}
