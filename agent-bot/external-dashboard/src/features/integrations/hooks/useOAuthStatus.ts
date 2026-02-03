import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

const API_BASE = import.meta.env.VITE_API_URL || "http://localhost:5000";

export interface OAuthStatus {
  platform: string;
  name: string;
  connected: boolean;
  configured: boolean;
  icon: string;
  description: string;
  installed_at: string | null;
  scopes: string[] | null;
}

export interface OAuthStatusResponse {
  success: boolean;
  statuses: Record<string, OAuthStatus>;
}

export interface OAuthInstallResponse {
  success: boolean;
  redirect_url: string;
}

async function fetchOAuthStatus(): Promise<OAuthStatusResponse> {
  const response = await fetch(`${API_BASE}/api/oauth/status`);
  if (!response.ok) {
    throw new Error("Failed to fetch OAuth status");
  }
  return response.json();
}

async function revokeOAuth(platform: string): Promise<void> {
  const response = await fetch(`${API_BASE}/api/oauth/revoke/${platform}`, {
    method: "DELETE",
  });
  if (!response.ok) {
    throw new Error(`Failed to revoke ${platform} OAuth`);
  }
}

async function startOAuthInstall(platform: string): Promise<string> {
  const response = await fetch(`${API_BASE}/api/oauth/install/${platform}`, {
    method: "POST",
  });
  if (!response.ok) {
    throw new Error(`Failed to start ${platform} OAuth install`);
  }
  const data: OAuthInstallResponse = await response.json();
  return data.redirect_url;
}

export function useOAuthStatus() {
  const queryClient = useQueryClient();

  const query = useQuery({
    queryKey: ["oauth-status"],
    queryFn: fetchOAuthStatus,
    refetchInterval: 30000,
  });

  const revokeMutation = useMutation({
    mutationFn: revokeOAuth,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["oauth-status"] });
    },
  });

  const installMutation = useMutation({
    mutationFn: startOAuthInstall,
    onSuccess: (redirectUrl) => {
      window.location.href = redirectUrl;
    },
  });

  return {
    statuses: query.data?.statuses,
    isLoading: query.isLoading,
    isError: query.isError,
    error: query.error,
    refetch: query.refetch,
    revoke: revokeMutation.mutate,
    isRevoking: revokeMutation.isPending,
    install: installMutation.mutate,
    isInstalling: installMutation.isPending,
  };
}
