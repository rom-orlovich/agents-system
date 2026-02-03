import { useState } from "react";
import { RefreshCw, Plus, Database, Activity } from "lucide-react";
import { useSources } from "./hooks/useSources";
import { SourceCard } from "./SourceCard";
import { AddSourceModal } from "./AddSourceModal";

export function SourcesFeature() {
  const [isModalOpen, setIsModalOpen] = useState(false);
  const {
    sources,
    jobs,
    isLoading,
    isError,
    error,
    refetch,
    refetchJobs,
    create,
    isCreating,
    update,
    isUpdating,
    remove,
    isDeleting,
    sync,
    isSyncing,
  } = useSources();

  if (isLoading) {
    return (
      <div className="p-8 text-center font-heading">LOADING_SOURCES...</div>
    );
  }

  if (isError) {
    return (
      <div className="p-8 text-center">
        <div className="text-red-500 font-heading mb-4">
          ERROR:{" "}
          {error instanceof Error ? error.message : "Failed to load sources"}
        </div>
        <button
          type="button"
          onClick={() => refetch()}
          className="px-4 py-2 border border-gray-200 hover:bg-gray-50 text-[10px] font-heading"
        >
          RETRY
        </button>
      </div>
    );
  }

  const enabledCount = sources.filter((s) => s.enabled).length;
  const syncedCount = sources.filter(
    (s) => s.last_sync_status === "completed"
  ).length;
  const runningJobs = jobs.filter(
    (j) => j.status === "running" || j.status === "queued"
  );

  return (
    <div className="space-y-8 animate-in fade-in duration-500">
      <section className="panel" data-label="DATA_SOURCES">
        <div className="flex justify-between items-center mb-6">
          <div className="flex gap-8">
            <div className="stat-mini">
              <div className="text-[10px] font-heading text-gray-400">TOTAL</div>
              <div className="text-xl font-heading font-black">
                {sources.length}
              </div>
            </div>
            <div className="stat-mini">
              <div className="text-[10px] font-heading text-gray-400">
                ENABLED
              </div>
              <div className="text-xl font-heading font-black text-green-500">
                {enabledCount}
              </div>
            </div>
            <div className="stat-mini">
              <div className="text-[10px] font-heading text-gray-400">
                SYNCED
              </div>
              <div className="text-xl font-heading font-black text-blue-500">
                {syncedCount}
              </div>
            </div>
            <div className="stat-mini">
              <div className="text-[10px] font-heading text-gray-400">
                RUNNING
              </div>
              <div className="text-xl font-heading font-black text-yellow-500">
                {runningJobs.length}
              </div>
            </div>
          </div>
          <div className="flex gap-2">
            <button
              type="button"
              onClick={() => {
                refetch();
                refetchJobs();
              }}
              className="p-2 border border-gray-200 hover:bg-gray-50 transition-colors"
              title="Refresh"
            >
              <RefreshCw size={14} />
            </button>
            <button
              type="button"
              onClick={() => setIsModalOpen(true)}
              className="flex items-center gap-1 px-3 py-2 bg-black text-white hover:bg-gray-800 text-[10px] font-heading"
            >
              <Plus size={14} />
              ADD_SOURCE
            </button>
          </div>
        </div>

        <p className="text-[10px] text-gray-400 mb-6">
          Configure data sources for indexing. Each source provides searchable
          context for the AI agent. Sources can be enabled/disabled individually
          without affecting others.
        </p>

        {sources.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-12 text-center border border-dashed border-gray-200">
            <Database size={32} className="text-gray-300 mb-3" />
            <div className="font-heading text-sm text-gray-500 mb-1">
              NO_SOURCES_CONFIGURED
            </div>
            <p className="text-[10px] text-gray-400 mb-4 max-w-xs">
              Add data sources to enable knowledge-based features. The agent can
              operate without sources, but with reduced context.
            </p>
            <button
              type="button"
              onClick={() => setIsModalOpen(true)}
              className="flex items-center gap-1 px-4 py-2 border border-gray-200 hover:bg-gray-50 text-[10px] font-heading"
            >
              <Plus size={12} />
              ADD_FIRST_SOURCE
            </button>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {sources.map((source) => (
              <SourceCard
                key={source.source_id}
                source={source}
                onSync={() =>
                  sync({ sourceId: source.source_id, jobType: "incremental" })
                }
                onToggle={() =>
                  update({
                    sourceId: source.source_id,
                    request: { enabled: !source.enabled },
                  })
                }
                onDelete={() => {
                  if (
                    window.confirm(
                      `Delete source "${source.name}"? This action cannot be undone.`
                    )
                  ) {
                    remove(source.source_id);
                  }
                }}
                isSyncing={isSyncing}
                isUpdating={isUpdating}
                isDeleting={isDeleting}
              />
            ))}
          </div>
        )}
      </section>

      <section className="panel" data-label="INDEXING_JOBS">
        <div className="flex justify-between items-center mb-4">
          <div className="flex items-center gap-2">
            <Activity size={14} className="text-gray-400" />
            <h2 className="text-sm font-heading text-gray-400">RECENT_JOBS</h2>
          </div>
          <button
            type="button"
            onClick={() => sync({ jobType: "full" })}
            disabled={isSyncing || sources.length === 0}
            className="flex items-center gap-1 px-3 py-1.5 border border-gray-200 hover:bg-gray-50 text-[10px] font-heading disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <RefreshCw size={12} className={isSyncing ? "animate-spin" : ""} />
            SYNC_ALL
          </button>
        </div>

        {jobs.length === 0 ? (
          <div className="text-center py-8 text-[10px] text-gray-400">
            No indexing jobs yet
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-[10px]">
              <thead>
                <tr className="border-b border-gray-200">
                  <th className="text-left py-2 px-2 font-heading text-gray-400">
                    JOB_ID
                  </th>
                  <th className="text-left py-2 px-2 font-heading text-gray-400">
                    TYPE
                  </th>
                  <th className="text-left py-2 px-2 font-heading text-gray-400">
                    STATUS
                  </th>
                  <th className="text-left py-2 px-2 font-heading text-gray-400">
                    PROGRESS
                  </th>
                  <th className="text-left py-2 px-2 font-heading text-gray-400">
                    CREATED
                  </th>
                </tr>
              </thead>
              <tbody>
                {jobs.slice(0, 10).map((job) => (
                  <tr
                    key={job.job_id}
                    className="border-b border-gray-100 hover:bg-gray-50"
                  >
                    <td className="py-2 px-2 font-mono">
                      {job.job_id.slice(0, 8)}...
                    </td>
                    <td className="py-2 px-2 uppercase">{job.job_type}</td>
                    <td className="py-2 px-2">
                      <span
                        className={`px-2 py-0.5 text-[8px] uppercase font-heading ${
                          job.status === "completed"
                            ? "bg-green-100 text-green-700"
                            : job.status === "failed"
                            ? "bg-red-100 text-red-700"
                            : job.status === "running"
                            ? "bg-yellow-100 text-yellow-700"
                            : "bg-gray-100 text-gray-700"
                        }`}
                      >
                        {job.status}
                      </span>
                    </td>
                    <td className="py-2 px-2">
                      <div className="flex items-center gap-2">
                        <div className="w-20 h-1.5 bg-gray-200">
                          <div
                            className="h-full bg-blue-500"
                            style={{ width: `${job.progress_percent}%` }}
                          />
                        </div>
                        <span className="font-mono">{job.progress_percent}%</span>
                      </div>
                    </td>
                    <td className="py-2 px-2 font-mono text-gray-500">
                      {new Date(job.created_at).toLocaleString()}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      <section className="panel" data-label="INFO">
        <h2 className="text-sm mb-4 font-heading text-gray-400">
          KNOWLEDGE_SYSTEM_INFO
        </h2>
        <div className="space-y-3 text-[10px] text-gray-600">
          <p>
            <span className="font-heading text-gray-800">INDEPENDENCE:</span>{" "}
            The agent engine can operate without knowledge services. Sources are
            optional enhancements.
          </p>
          <p>
            <span className="font-heading text-gray-800">MODULARITY:</span> Each
            source type (GitHub, Jira, Confluence) is independent and can be
            enabled/disabled without affecting others.
          </p>
          <p>
            <span className="font-heading text-gray-800">GRACEFUL_DEGRADATION:</span>{" "}
            If knowledge services are unavailable, the agent continues
            operating with reduced context.
          </p>
        </div>
      </section>

      <AddSourceModal
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        onSubmit={(request) => {
          create(request, {
            onSuccess: () => setIsModalOpen(false),
          });
        }}
        isSubmitting={isCreating}
      />
    </div>
  );
}
