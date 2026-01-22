import { ChevronLeft, ChevronRight, Filter, RefreshCcw } from "lucide-react";
import { useLedger } from "./hooks/useLedger";

export function LedgerFeature() {
  const { tasks, agents, isLoading, filters, setFilters, page, setPage, totalPages } = useLedger();

  return (
    <div className="space-y-6 animate-in fade-in duration-500">
      <section className="panel" data-label="CENTRAL_LEDGER">
        <div className="flex flex-col md:flex-row gap-4 justify-between items-start md:items-center mb-6">
          <div className="flex flex-wrap gap-2 items-center">
            <div className="flex items-center gap-2 px-3 py-1.5 border border-gray-200 bg-gray-50 text-gray-400">
              <Filter size={14} />
              <span className="text-[10px] font-heading font-bold">FILTERS</span>
            </div>

            <input
              type="text"
              placeholder="FILTER_SESSION..."
              className="px-3 py-1.5 border border-gray-200 text-xs font-mono focus:border-primary outline-none bg-white"
              value={filters.session_id}
              onChange={(e) => setFilters({ session_id: e.target.value })}
            />

            <select
              className="px-3 py-1.5 border border-gray-200 text-xs font-heading focus:border-primary outline-none bg-white"
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
              className="px-3 py-1.5 border border-gray-200 text-xs font-heading focus:border-primary outline-none bg-white"
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
            className="flex items-center gap-2 px-4 py-2 bg-gray-900 hover:bg-gray-800 text-white text-[10px] font-heading font-bold transition-all hover:scale-105 active:scale-95 shadow-sm rounded-sm"
          >
            <RefreshCcw size={14} className="group-hover:rotate-180 transition-transform duration-500" />
            REFRESH_LEDGER
          </button>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="border-b border-gray-200">
                <th className="py-3 px-4 text-[10px] font-heading text-gray-400 uppercase tracking-wider">
                  TASK_ID
                </th>
                <th className="py-3 px-4 text-[10px] font-heading text-gray-400 uppercase tracking-wider">
                  SESSION
                </th>
                <th className="py-3 px-4 text-[10px] font-heading text-gray-400 uppercase tracking-wider">
                  AGENT
                </th>
                <th className="py-3 px-4 text-[10px] font-heading text-gray-400 uppercase tracking-wider">
                  STATUS
                </th>
                <th className="py-3 px-4 text-[10px] font-heading text-gray-400 uppercase tracking-wider">
                  COST
                </th>
                <th className="py-3 px-4 text-[10px] font-heading text-gray-400 uppercase tracking-wider">
                  TIME
                </th>
                <th className="py-3 px-4 text-[10px] font-heading text-gray-400 uppercase tracking-wider">
                  TIMESTAMP
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {isLoading ? (
                <tr>
                  <td
                    colSpan={7}
                    className="py-8 text-center text-xs font-heading text-gray-400 animate-pulse"
                  >
                    SYNCING_RECORDS...
                  </td>
                </tr>
              ) : tasks.length === 0 ? (
                <tr>
                  <td colSpan={7} className="py-8 text-center text-xs font-heading text-gray-400">
                    NO_RECORDS_FOUND
                  </td>
                </tr>
              ) : (
                tasks.map((task) => (
                  <tr key={task.id} className="hover:bg-gray-50/50 transition-colors group">
                    <td className="py-3 px-4 text-xs font-mono font-bold group-hover:text-primary">
                      {task.id}
                    </td>
                    <td className="py-3 px-4 text-xs font-mono text-gray-500">{task.session_id}</td>
                    <td className="py-3 px-4 text-xs font-heading text-gray-600">
                      {task.assigned_agent}
                    </td>
                    <td className="py-3 px-4">
                      <span
                        className={`inline-block px-2 py-0.5 text-[9px] font-heading border ${getStatusClasses(task.status)}`}
                      >
                        {task.status.toUpperCase()}
                      </span>
                    </td>
                    <td className="py-3 px-4 text-xs font-mono font-bold">${task.cost_usd}</td>
                    <td className="py-3 px-4 text-xs font-mono text-gray-500">
                      {task.duration_seconds}s
                    </td>
                    <td className="py-3 px-4 text-[10px] text-gray-400">
                      {new Date(task.created_at).toLocaleString()}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>

        <div className="flex items-center justify-between mt-6 pt-6 border-t border-gray-100">
          <div className="text-[10px] font-heading text-gray-400">
            SHOWING_PAGE <span className="text-gray-900">{page}</span> OF{" "}
            <span className="text-gray-900">{totalPages}</span>
          </div>
          <div className="flex gap-2">
            <button
              type="button"
              disabled={page === 1}
              onClick={() => setPage((p) => p - 1)}
              className="p-1.5 border border-gray-200 hover:bg-gray-50 disabled:opacity-30 disabled:hover:bg-transparent transition-colors"
            >
              <ChevronLeft size={16} />
            </button>
            <button
              type="button"
              disabled={page === totalPages}
              onClick={() => setPage((p) => p + 1)}
              className="p-1.5 border border-gray-200 hover:bg-gray-50 disabled:opacity-30 disabled:hover:bg-transparent transition-colors"
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
      return "border-green-200 text-green-600 bg-green-50";
    case "running":
      return "border-blue-200 text-blue-600 bg-blue-50";
    case "failed":
      return "border-red-200 text-red-600 bg-red-50";
    case "queued":
      return "border-gray-200 text-gray-600 bg-gray-50";
    default:
      return "border-gray-100 text-gray-400 bg-gray-50";
  }
}
