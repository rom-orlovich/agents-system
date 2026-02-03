import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

const API_BASE = import.meta.env.VITE_API_URL || "http://localhost:5000";
const DEFAULT_ORG_ID = import.meta.env.VITE_ORG_ID || "default-org";

export interface DataSource {
  source_id: string;
  org_id: string;
  source_type: "github" | "jira" | "confluence";
  name: string;
  enabled: boolean;
  config_json: string;
  last_sync_at: string | null;
  last_sync_status: string | null;
  created_at: string;
  updated_at: string;
  oauth_connected: boolean;
  oauth_platform: string | null;
}

export interface SourceTypeInfo {
  source_type: string;
  name: string;
  oauth_platform: string;
  oauth_connected: boolean;
  oauth_required: boolean;
  description: string;
}

export interface IndexingJob {
  job_id: string;
  org_id: string;
  source_id: string | null;
  job_type: string;
  status: string;
  progress_percent: number;
  items_total: number;
  items_processed: number;
  items_failed: number;
  error_message: string | null;
  started_at: string | null;
  completed_at: string | null;
  created_at: string;
}

export interface CreateSourceRequest {
  name: string;
  source_type: string;
  config: Record<string, unknown>;
  enabled?: boolean;
}

export interface UpdateSourceRequest {
  name?: string;
  config?: Record<string, unknown>;
  enabled?: boolean;
}

async function fetchSourceTypes(): Promise<SourceTypeInfo[]> {
  const response = await fetch(`${API_BASE}/api/sources/types/available`);
  if (!response.ok) {
    throw new Error("Failed to fetch source types");
  }
  return response.json();
}

async function fetchSources(orgId: string): Promise<DataSource[]> {
  const response = await fetch(`${API_BASE}/api/sources/${orgId}`);
  if (!response.ok) {
    throw new Error("Failed to fetch data sources");
  }
  return response.json();
}

async function fetchSource(
  orgId: string,
  sourceId: string
): Promise<DataSource> {
  const response = await fetch(`${API_BASE}/api/sources/${orgId}/${sourceId}`);
  if (!response.ok) {
    throw new Error("Failed to fetch data source");
  }
  return response.json();
}

async function createSource(
  orgId: string,
  request: CreateSourceRequest
): Promise<DataSource> {
  const response = await fetch(`${API_BASE}/api/sources/${orgId}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(request),
  });
  if (!response.ok) {
    throw new Error("Failed to create data source");
  }
  return response.json();
}

async function updateSource(
  orgId: string,
  sourceId: string,
  request: UpdateSourceRequest
): Promise<DataSource> {
  const response = await fetch(`${API_BASE}/api/sources/${orgId}/${sourceId}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(request),
  });
  if (!response.ok) {
    throw new Error("Failed to update data source");
  }
  return response.json();
}

async function deleteSource(orgId: string, sourceId: string): Promise<void> {
  const response = await fetch(`${API_BASE}/api/sources/${orgId}/${sourceId}`, {
    method: "DELETE",
  });
  if (!response.ok) {
    throw new Error("Failed to delete data source");
  }
}

async function triggerSync(
  orgId: string,
  sourceId?: string,
  jobType: string = "incremental"
): Promise<IndexingJob> {
  const response = await fetch(`${API_BASE}/api/sources/${orgId}/sync`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ source_id: sourceId, job_type: jobType }),
  });
  if (!response.ok) {
    throw new Error("Failed to trigger sync");
  }
  return response.json();
}

async function fetchJobs(orgId: string, limit: number = 20): Promise<IndexingJob[]> {
  const response = await fetch(`${API_BASE}/api/sources/${orgId}/jobs?limit=${limit}`);
  if (!response.ok) {
    throw new Error("Failed to fetch indexing jobs");
  }
  return response.json();
}

export function useSources(orgId: string = DEFAULT_ORG_ID) {
  const queryClient = useQueryClient();

  const sourcesQuery = useQuery({
    queryKey: ["sources", orgId],
    queryFn: () => fetchSources(orgId),
    refetchInterval: 30000,
  });

  const jobsQuery = useQuery({
    queryKey: ["indexing-jobs", orgId],
    queryFn: () => fetchJobs(orgId),
    refetchInterval: 10000,
  });

  const createMutation = useMutation({
    mutationFn: (request: CreateSourceRequest) => createSource(orgId, request),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["sources", orgId] });
    },
  });

  const updateMutation = useMutation({
    mutationFn: ({
      sourceId,
      request,
    }: {
      sourceId: string;
      request: UpdateSourceRequest;
    }) => updateSource(orgId, sourceId, request),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["sources", orgId] });
    },
  });

  const deleteMutation = useMutation({
    mutationFn: (sourceId: string) => deleteSource(orgId, sourceId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["sources", orgId] });
    },
  });

  const syncMutation = useMutation({
    mutationFn: ({
      sourceId,
      jobType,
    }: {
      sourceId?: string;
      jobType?: string;
    }) => triggerSync(orgId, sourceId, jobType),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["indexing-jobs", orgId] });
    },
  });

  return {
    sources: sourcesQuery.data ?? [],
    jobs: jobsQuery.data ?? [],
    isLoading: sourcesQuery.isLoading,
    isJobsLoading: jobsQuery.isLoading,
    isError: sourcesQuery.isError,
    error: sourcesQuery.error,
    refetch: sourcesQuery.refetch,
    refetchJobs: jobsQuery.refetch,
    create: createMutation.mutate,
    isCreating: createMutation.isPending,
    update: updateMutation.mutate,
    isUpdating: updateMutation.isPending,
    remove: deleteMutation.mutate,
    isDeleting: deleteMutation.isPending,
    sync: syncMutation.mutate,
    isSyncing: syncMutation.isPending,
  };
}

export function useSource(orgId: string, sourceId: string) {
  return useQuery({
    queryKey: ["source", orgId, sourceId],
    queryFn: () => fetchSource(orgId, sourceId),
    enabled: !!sourceId,
  });
}

export function useSourceTypes() {
  return useQuery({
    queryKey: ["source-types"],
    queryFn: fetchSourceTypes,
    staleTime: 60000,
  });
}
