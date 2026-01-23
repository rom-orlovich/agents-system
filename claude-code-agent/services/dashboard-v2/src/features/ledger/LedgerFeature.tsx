import { ChevronLeft, ChevronRight, Filter, RefreshCcw, X } from "lucide-react";
import { useLedger, type LedgerTask } from "./hooks/useLedger";
import { useState, useRef, useEffect } from "react";
import { useTaskLogs } from "../overview/hooks/useTaskLogs";

export function LedgerFeature() {
  const { tasks, agents, isLoading, refetch, filters, setFilters, page, setPage, totalPages } = useLedger();
  const [selectedTask, setSelectedTask] = useState<LedgerTask | null>(null);
  
  const { data: taskLogs, isLoading: isLogsLoading } = useTaskLogs(selectedTask?.id ?? null);
  const logEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (logEndRef.current) {
      logEndRef.current.scrollIntoView({ behavior: "smooth" });
    }
  }, [taskLogs?.output]);

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
            onClick={() => refetch()}
            className="flex items-center gap-2 px-4 py-2 bg-gray-900 hover:bg-gray-800 text-white text-[10px] font-heading font-bold transition-all hover:scale-105 active:scale-95 shadow-sm rounded-sm"
          >
            <RefreshCcw size={14} className={isLoading ? "animate-spin" : "group-hover:rotate-180 transition-transform duration-500"} />
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
                  <tr 
                    key={task.id} 
                    onClick={() => setSelectedTask(task)}
                    className="hover:bg-gray-50/50 transition-colors group cursor-pointer"
                  >
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
                    <td className="py-3 px-4 text-xs font-mono font-bold">${parseFloat(task.cost_usd).toFixed(4)}</td>
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

      {selectedTask && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-[2px] animate-in fade-in duration-200">
          <div className="bg-white rounded-lg shadow-2xl w-full max-w-2xl mx-4 overflow-hidden border border-gray-100 animate-in zoom-in-95 duration-200 ring-1 ring-black/5">
            <div className="flex items-center justify-between p-4 border-b border-gray-100 bg-gray-50/80">
              <div className="flex items-center gap-2">
                <div className={`w-2 h-2 rounded-full ${getStatusColor(selectedTask.status)}`} />
                <h3 className="font-heading font-bold text-xs uppercase tracking-wider">
                  TASK_DETAILS
                </h3>
              </div>
              <button
                type="button"
                onClick={() => setSelectedTask(null)}
                className="p-1 hover:bg-gray-200 rounded text-gray-400 hover:text-gray-600 transition-colors"
              >
                <X size={16} />
              </button>
            </div>
            
            <div className="p-6 space-y-6">
              <div className="grid grid-cols-2 gap-6">
                <div className="space-y-1">
                  <div className="text-[10px] text-gray-400 font-heading">TASK_ID</div>
                  <div className="font-mono text-xs font-bold text-gray-900">{selectedTask.id}</div>
                </div>
                <div className="space-y-1">
                  <div className="text-[10px] text-gray-400 font-heading">SESSION_ID</div>
                  <div className="font-mono text-[10px] text-gray-500 truncate">{selectedTask.session_id}</div>
                </div>
                <div className="space-y-1">
                  <div className="text-[10px] text-gray-400 font-heading">AGENT</div>
                  <div className="font-heading text-xs font-bold">{selectedTask.assigned_agent}</div>
                </div>
                <div className="space-y-1">
                  <div className="text-[10px] text-gray-400 font-heading">STATUS</div>
                  <div className="font-heading text-xs font-bold uppercase">{selectedTask.status}</div>
                </div>
                <div className="space-y-1">
                  <div className="text-[10px] text-gray-400 font-heading">COST</div>
                  <div className="font-mono text-xs font-bold text-cta">
                    ${parseFloat(selectedTask.cost_usd).toFixed(4)}
                  </div>
                </div>
                <div className="space-y-1">
                  <div className="text-[10px] text-gray-400 font-heading">TIMESTAMP</div>
                  <div className="font-mono text-[10px] text-gray-500">
                    {new Date(selectedTask.created_at).toLocaleString()}
                  </div>
                </div>
              </div>

              <div className="rounded bg-gray-950 p-4 font-mono text-[10px] text-gray-300 space-y-1 overflow-y-auto max-h-64 border border-gray-800 shadow-inner">
                <div className="text-gray-500 mb-2 border-b border-gray-800 pb-1 flex justify-between">
                  <span>LIVE_LOGS_STREAM</span>
                  {taskLogs?.is_live && (
                    <span className="text-blue-500 animate-pulse text-[8px] font-bold">● LIVE</span>
                  )}
                </div>
                {isLogsLoading ? (
                  <div className="text-gray-600 animate-pulse">CONNECTING_TO_STREAM...</div>
                ) : taskLogs?.output ? (
                  <>
                    {renderLogs(taskLogs.output)}
                    <div ref={logEndRef} />
                  </>
                ) : (
                  <div className="text-gray-600 italic">No logs available for this task.</div>
                )}
              </div>
            </div>

            <div className="p-4 bg-gray-50 border-t border-gray-100 flex justify-end gap-2">
              <button
                type="button"
                onClick={() => setSelectedTask(null)}
                className="px-4 py-2 bg-white border border-gray-200 text-[10px] font-heading font-bold hover:bg-gray-50 transition-colors rounded shadow-sm hover:shadow"
              >
                CLOSE_PANEL
              </button>
            </div>
          </div>
        </div>
      )}
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

function getStatusColor(status: string) {
  switch (status) {
    case "completed":
      return "bg-green-500";
    case "running":
      return "bg-blue-500 animate-pulse";
    case "failed":
      return "bg-red-500";
    default:
      return "bg-gray-300";
  }
}

function renderLogs(output: string) {
  if (!output) return null;
  
  return output.split("\n").map((line, i) => {
    if (!line.trim()) return null;
    
    let colorClass = "text-gray-300";
    let prefix = "";
    let content = line;
    
    if (line.startsWith("info ")) {
      colorClass = "text-blue-400";
      prefix = "info";
      content = line.substring(5);
    } else if (line.startsWith("exec ")) {
      colorClass = "text-yellow-400";
      prefix = "exec";
      content = line.substring(5);
    } else if (line.startsWith("succ ")) {
      colorClass = "text-green-400";
      prefix = "succ";
      content = line.substring(5);
    } else if (line.startsWith("error ")) {
      colorClass = "text-red-400";
      prefix = "error";
      content = line.substring(6);
    }
    
    return (
      <div key={i} className="flex gap-2">
        {prefix && <span className={`${colorClass} opacity-80 min-w-[32px]`}>{prefix}</span>}
        <span className={prefix ? 'text-gray-300' : colorClass}>{content}</span>
      </div>
    );
  });
}
