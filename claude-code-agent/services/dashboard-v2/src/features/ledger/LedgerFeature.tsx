import { ChevronLeft, ChevronRight, Filter, RefreshCcw } from "lucide-react";
import { useLedger } from "./hooks/useLedger";
import { useTaskModal } from "../../hooks/useTaskModal";

export function LedgerFeature() {
  const { tasks, agents, isLoading, refetch, filters, setFilters, page, setPage, totalPages } = useLedger();
  const { openTask } = useTaskModal();

  return (
    <div className="space-y-6 animate-in fade-in duration-500">
      <section className="panel" data-label="CENTRAL_LEDGER">
        <div className="flex flex-col md:flex-row gap-4 justify-between items-stretch md:items-center mb-6 w-full">
          <div className="flex flex-col sm:flex-row flex-wrap gap-2 items-stretch sm:items-center w-full md:w-auto">
            <div className="flex items-center gap-2 px-3 py-1.5 border border-input-border bg-background-app text-app-muted">
              <Filter size={14} />
              <span className="text-[10px] font-heading font-bold">FILTERS</span>
            </div>

            <input
              type="text"
              placeholder="FILTER_SESSION..."
              className="px-3 py-1.5 border border-input-border text-xs font-mono focus:border-primary outline-none bg-input-bg text-input-text w-full sm:w-auto"
              value={filters.session_id}
              onChange={(e) => setFilters({ session_id: e.target.value })}
            />

            <select
              className="px-3 py-1.5 border border-input-border text-xs font-heading focus:border-primary outline-none bg-input-bg text-input-text w-full sm:w-auto"
              value={filters.status}
              onChange={(e) => setFilters({ status: e.target.value })}
            >
              <option value="">ALL_STATUS</option>
              <option value="completed">COMPLETED</option>
              <option value="failed">FAILED</option>
              <option value="running">RUNNING</option>
              <option value="queued">QUEUED</option>
            </select>

            <select
              className="px-3 py-1.5 border border-input-border text-xs font-heading focus:border-primary outline-none bg-input-bg text-input-text w-full sm:w-auto"
              value={filters.assigned_agent}
              onChange={(e) => setFilters({ assigned_agent: e.target.value })}
            >
              <option value="">ALL_AGENTS</option>
              {agents.map((agent) => (
                <option key={agent} value={agent}>
                  {agent.toUpperCase()}
                </option>
              ))}
            </select>
          </div>

          <button
            type="button"
            onClick={() => refetch()}
            className="flex items-center gap-2 px-4 py-2 bg-primary border border-primary/20 hover:opacity-90 text-white text-[10px] font-heading font-bold transition-all hover:scale-105 active:scale-95 shadow-lg shadow-primary/20 rounded-sm"
          >
            <RefreshCcw size={14} className={isLoading ? "animate-spin" : "group-hover:rotate-180 transition-transform duration-500"} />
            REFRESH_LEDGER
          </button>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="border-b border-panel-border">
                <th className="py-3 px-4 text-[10px] font-heading text-app-muted uppercase tracking-wider">
                  TASK_ID
                </th>
                <th className="py-3 px-4 text-[10px] font-heading text-app-muted uppercase tracking-wider hidden sm:table-cell">
                  SESSION
                </th>
                <th className="py-3 px-4 text-[10px] font-heading text-app-muted uppercase tracking-wider">
                  AGENT
                </th>
                <th className="py-3 px-4 text-[10px] font-heading text-app-muted uppercase tracking-wider">
                  STATUS
                </th>
                <th className="py-3 px-4 text-[10px] font-heading text-app-muted uppercase tracking-wider hidden lg:table-cell">
                  COST
                </th>
                <th className="py-3 px-4 text-[10px] font-heading text-app-muted uppercase tracking-wider hidden lg:table-cell">
                  TIME
                </th>
                <th className="py-3 px-4 text-[10px] font-heading text-app-muted uppercase tracking-wider hidden md:table-cell">
                  TIMESTAMP
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-panel-border/50">
              {isLoading ? (
                <tr>
                  <td
                    colSpan={7}
                    className="py-8 text-center text-xs font-heading text-app-muted animate-pulse"
                  >
                    SYNCING_RECORDS...
                  </td>
                </tr>
              ) : tasks.length === 0 ? (
                <tr>
                  <td colSpan={7} className="py-8 text-center text-xs font-heading text-app-muted">
                    NO_RECORDS_FOUND
                  </td>
                </tr>
              ) : (
                tasks.map((task) => (
                  <tr 
                    key={task.id} 
                    onClick={() => openTask(task.id)}
                    className="hover:bg-slate-500/5 transition-colors group cursor-pointer"
                  >
                    <td className="py-3 px-4 text-xs font-mono font-bold group-hover:text-primary">
                      <span className="md:hidden">{task.id.slice(0, 8)}...</span>
                      <span className="hidden md:inline">{task.id}</span>
                    </td>
                    <td className="py-3 px-4 text-xs font-mono text-app-muted hidden sm:table-cell">{task.session_id}</td>
                    <td className="py-3 px-4 text-xs font-heading text-app-main">
                      {task.assigned_agent}
                    </td>
                    <td className="py-3 px-4">
                      <span
                        className={`inline-block px-2 py-0.5 text-[9px] font-heading border ${getStatusClasses(task.status)}`}
                      >
                        {task.status.toUpperCase()}
                      </span>
                    </td>
                    <td className="py-3 px-4 text-xs font-mono font-bold text-app-main hidden lg:table-cell">${parseFloat(task.cost_usd).toFixed(4)}</td>
                    <td className="py-3 px-4 text-xs font-mono text-app-muted hidden lg:table-cell">
                      {task.duration_seconds}s
                    </td>
                    <td className="py-3 px-4 text-[10px] text-app-muted hidden md:table-cell">
                      {new Date(task.created_at).toLocaleString()}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>

        <div className="flex items-center justify-between mt-6 pt-6 border-t border-panel-border">
          <div className="text-[10px] font-heading text-app-muted">
            SHOWING_PAGE <span className="text-app-main">{page}</span> OF{" "}
            <span className="text-app-main">{totalPages}</span>
          </div>
          <div className="flex gap-2 text-app-main">
            <button
              type="button"
              disabled={page === 1}
              onClick={() => setPage((p) => p - 1)}
              className="p-1.5 border border-input-border hover:bg-background-app disabled:opacity-30 disabled:hover:bg-transparent transition-colors"
            >
              <ChevronLeft size={16} />
            </button>
            <button
              type="button"
              disabled={page === totalPages}
              onClick={() => setPage((p) => p + 1)}
              className="p-1.5 border border-input-border hover:bg-background-app disabled:opacity-30 disabled:hover:bg-transparent transition-colors"
            >
              <ChevronRight size={16} />
            </button>
          </div>
        </div>
      </section>
    </div>
  );
}

function getStatusClasses(status: string) {
  switch (status) {
    case "completed":
      return "border-green-500/20 text-green-500 bg-green-500/10";
    case "running":
      return "border-blue-500/20 text-blue-500 bg-blue-500/10";
    case "failed":
      return "border-red-500/20 text-red-500 bg-red-500/10";
    case "queued":
      return "border-gray-500/20 text-gray-400 bg-gray-500/10";
    default:
      return "border-gray-100/20 text-gray-400 bg-gray-50/10";
  }
}
