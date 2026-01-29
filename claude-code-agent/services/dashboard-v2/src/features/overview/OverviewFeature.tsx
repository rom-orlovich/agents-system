import { Activity, Cpu, DollarSign, Zap, Eye, X, RefreshCw } from "lucide-react";
import { useMetrics, type Task } from "./hooks/useMetrics";
import { useTaskLogs, useGlobalLogs, type TaskLogResponse } from "./hooks/useTaskLogs";
import { useState, useRef, useEffect } from "react";

export function OverviewFeature() {
  const { metrics, tasks, isLoading, error, refetch } = useMetrics();
  const [selectedTask, setSelectedTask] = useState<Task | null>(null);
  
  const { data: taskLogs, isLoading: isLogsLoading } = useTaskLogs(selectedTask?.id ?? null);
  const { data: globalLogs } = useGlobalLogs();
  
  const logEndRef = useRef<HTMLDivElement>(null);
  const logContainerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (logEndRef.current) {
      logEndRef.current.scrollIntoView({ behavior: "smooth" });
    }
  }, [taskLogs?.output]);

  const scrollToTop = () => {
    if (logContainerRef.current) {
      logContainerRef.current.scrollTop = 0;
    }
  };

  if (isLoading) return <div className="p-8 text-center font-heading">SYNCING_METRICS...</div>;
  if (error)
    return <div className="p-8 text-red-500 font-heading">ERROR: {(error as Error).message}</div>;
  if (!metrics) return null;

  return (
    <div className="space-y-8 animate-in fade-in slide-in-from-bottom-4 duration-700">
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-xl font-heading font-black tracking-tighter">OPERATIONAL_OVERVIEW</h1>
        <button
          type="button"
          onClick={() => refetch()}
          className="flex items-center gap-2 px-3 py-1.5 border border-gray-200 text-[10px] font-heading font-bold hover:bg-white hover:text-primary transition-all uppercase tracking-widest shadow-sm"
        >
          <RefreshCw size={12} className={isLoading ? "animate-spin" : ""} />
          REFRESH
        </button>
      </div>

      <section
        className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4"
        data-label="SYSTEM_STATUS"
      >
        <StatCard label="QUEUE_DEPTH" value={metrics.queue_depth} icon={Cpu} />
        <StatCard label="ACTIVE_SESSIONS" value={metrics.active_sessions} icon={Activity} />
        <StatCard label="WIRES_CONNECTED" value={metrics.wires_connected} icon={Zap} />
        <StatCard
          label="DAILY_BURN"
          value={`$${metrics.daily_burn.toFixed(2)}`}
          icon={DollarSign}
        />
      </section>

      <section
        className="grid grid-cols-1 md:grid-cols-2 gap-4"
        data-label="OAUTH_USAGE"
      >
        <StatCard
          label="OAUTH_SESSION_USAGE"
          value={`${metrics.oauth_session_percentage.toFixed(1)}%`}
          icon={Activity}
        />
        <StatCard
          label="OAUTH_WEEKLY_USAGE"
          value={`${metrics.oauth_weekly_percentage.toFixed(1)}%`}
          icon={Activity}
        />
      </section>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        <section className="lg:col-span-2 panel" data-label="LIVE_PROCESSES">
          <div className="space-y-4">
            {tasks?.map((task: Task) => (
              <div
                key={task.id}
                onClick={() => setSelectedTask(task)}
                className="flex items-center justify-between p-3 border-b border-gray-100 last:border-0 hover:bg-gray-50 transition-colors cursor-pointer group/row"
              >
                <div className="flex items-center gap-4">
                  <div className={`w-2 h-2 rounded-full ${getStatusColor(task.status)}`} />
                  <div>
                    <div className="text-xs font-heading font-bold">{task.name}</div>
                    <div className="text-[10px] text-gray-400 font-mono">{task.id}</div>
                  </div>
                </div>
                <div className="flex items-center gap-4">
                  <div className="text-right">
                    <div className="text-xs font-bold font-mono">${task.cost.toFixed(2)}</div>
                    <div className="text-[10px] text-gray-400">
                      {new Date(task.timestamp).toLocaleTimeString()}
                    </div>
                  </div>
                  <button
                    type="button"
                    onClick={(e) => {
                      e.stopPropagation();
                      setSelectedTask(task);
                    }}
                    className="p-1.5 hover:bg-gray-100 text-gray-400 group-hover/row:text-primary rounded-md transition-colors"
                  >
                    <Eye size={16} />
                  </button>
                </div>
              </div>
            ))}
          </div>
        </section>

        <section className="panel" data-label="AGGREGATE_METRICS">
          <div className="space-y-6">
            <div className="text-center py-4">
              <div className="text-4xl font-heading font-black tracking-tighter text-primary leading-none">
                {metrics.total_jobs}
              </div>
              <div className="text-[10px] text-gray-400 font-heading mt-2 uppercase tracking-wider">
                TOTAL_JOBS_COMPLETED
              </div>
            </div>
            <div className="text-center py-4 border-t border-gray-100">
              <div className="text-4xl font-heading font-black tracking-tighter text-cta leading-none">
                ${metrics.cumulative_cost.toLocaleString()}
              </div>
              <div className="text-[10px] text-gray-400 font-heading mt-2 uppercase tracking-wider">
                CUMULATIVE_COMPUTE_COST
              </div>
            </div>
          </div>
        </section>
      </div>

      <section className="panel" data-label="GLOBAL_CONTAINER_LOGS">
        <div className="flex justify-between items-center mb-4">
          <h2 className="text-xs font-heading font-black tracking-widest uppercase text-gray-400">
            GLOBAL_CONTAINER_LOGS_STREAM
          </h2>
          <div className="flex gap-2">
             <div className="flex items-center gap-1.5 px-2 py-0.5 border border-gray-100 rounded text-[9px] font-mono font-bold text-blue-500 bg-blue-50/50">
              <span className="w-1.5 h-1.5 bg-blue-500 rounded-full animate-pulse" />
              LIVE_STREAM
            </div>
          </div>
        </div>
        <div className="h-64 rounded bg-gray-950 p-4 font-mono text-[10px] text-gray-300 space-y-1 overflow-y-auto border border-gray-800 shadow-inner custom-scrollbar">
          {globalLogs && globalLogs.length > 0 ? (
            globalLogs.map((log: TaskLogResponse) => (
              <div key={log.task_id} className="space-y-1 pb-4 mb-4 border-b border-gray-900 last:border-0 last:pb-0 last:mb-0">
                <div className="text-gray-500 flex items-center gap-2 mb-2">
                  <span className="bg-gray-900 px-1.5 py-0.5 rounded text-[8px] border border-gray-800">
                    TASK_{log.task_id.split("-").pop()}
                  </span>
                  <span className={`text-[8px] uppercase font-bold ${log.status === 'running' ? 'text-blue-400' : 'text-gray-600'}`}>
                    {log.status}
                  </span>
                </div>
                {renderLogs(log.output)}
              </div>
            ))
          ) : (
            <div className="flex items-center justify-center h-full text-gray-600 italic">
              AWAITING_SIGNAL_HANDOFF...
            </div>
          )}
        </div>
      </section>

      {selectedTask && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-[2px] animate-in fade-in duration-200">
          <div className="bg-white rounded-lg shadow-2xl w-full max-w-md mx-4 overflow-hidden border border-gray-100 animate-in zoom-in-95 duration-200 ring-1 ring-black/5">
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
              <div className="space-y-1">
                <div className="text-[10px] text-gray-400 font-heading">TASK_ID</div>
                <div className="font-mono text-sm font-bold text-gray-900 group flex items-center gap-2">
                  {selectedTask.id}
                </div>
              </div>

              <div className="grid grid-cols-2 gap-6">
                <div className="space-y-1">
                  <div className="text-[10px] text-gray-400 font-heading">AGENT_NAME</div>
                  <div className="font-heading text-xs font-bold">{selectedTask.name}</div>
                </div>
                <div className="space-y-1">
                  <div className="text-[10px] text-gray-400 font-heading">STATUS</div>
                  <div className="font-heading text-xs font-bold uppercase">{selectedTask.status}</div>
                </div>
                <div className="space-y-1">
                  <div className="text-[10px] text-gray-400 font-heading">COST</div>
                  <div className="font-mono text-xs font-bold text-cta">
                    ${selectedTask.cost.toFixed(4)}
                  </div>
                </div>
                <div className="space-y-1">
                  <div className="text-[10px] text-gray-400 font-heading">STARTED</div>
                  <div className="font-mono text-xs text-gray-500">
                    {new Date(selectedTask.timestamp).toLocaleString()}
                  </div>
                </div>
              </div>

              <div ref={logContainerRef} className="rounded bg-gray-950 p-4 font-mono text-[10px] text-gray-300 space-y-1 overflow-y-auto max-h-48 md:max-h-96 border border-gray-800 shadow-inner relative">
                <div className="text-gray-500 mb-2 border-b border-gray-800 pb-1 flex justify-between items-center sticky top-0 bg-gray-950/90 backdrop-blur-sm z-10">
                  <span>LIVE_LOGS_STREAM</span>
                  <div className="flex items-center gap-2">
                    <button
                       onClick={scrollToTop}
                       className="text-[9px] px-1.5 py-0.5 border border-gray-700 rounded hover:bg-gray-800 hover:text-white transition-colors cursor-pointer"
                    >
                      SCROLL_TOP
                    </button>
                    {taskLogs?.is_live && (
                      <span className="text-blue-500 animate-pulse text-[8px] font-bold">● LIVE</span>
                    )}
                  </div>
                </div>
                {isLogsLoading ? (
                  <div className="text-gray-600 animate-pulse">CONNECTING_TO_STREAM...</div>
                ) : taskLogs?.output ? (
                  <>
                    {renderLogs(taskLogs.output)}
                    <div ref={logEndRef} />
                  </>
                ) : (
                  <div className="text-gray-600 italic">NO_LOG_DATA_AVAILABLE</div>
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

import type { LucideIcon } from "lucide-react";

function StatCard({
  label,
  value,
  icon: Icon,
}: {
  label: string;
  value: string | number;
  icon: LucideIcon;
}) {
  return (
    <div className="panel flex items-center justify-between group" data-label={label}>
      <div>
        <div className="text-[10px] text-gray-400 font-heading mb-1">{label}</div>
        <div className="text-2xl font-heading font-black tracking-tighter group-hover:text-primary transition-colors">
          {value}
        </div>
      </div>
      <div className="text-gray-200 group-hover:text-primary/10 transition-colors">
        <Icon size={28} strokeWidth={1} />
      </div>
    </div>
  );
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
    
    // Check for common patterns
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
