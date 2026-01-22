import { Activity, Cpu, DollarSign, Zap, Eye, X } from "lucide-react";
import { useMetrics, type Task } from "./hooks/useMetrics";
import { useState } from "react";

export function OverviewFeature() {
  const { metrics, tasks, isLoading, error } = useMetrics();
  const [selectedTask, setSelectedTask] = useState<Task | null>(null);

  if (isLoading) return <div className="p-8 text-center font-heading">SYNCING_METRICS...</div>;
  if (error)
    return <div className="p-8 text-red-500 font-heading">ERROR: {(error as Error).message}</div>;
  if (!metrics) return null;

  return (
    <div className="space-y-8 animate-in fade-in slide-in-from-bottom-4 duration-700">
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

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        <section className="lg:col-span-2 panel" data-label="LIVE_PROCESSES">
          <div className="space-y-4">
            {tasks?.map((task) => (
              <div
                key={task.id}
                className="flex items-center justify-between p-3 border-b border-gray-100 last:border-0 hover:bg-gray-50 transition-colors"
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
                    onClick={() => setSelectedTask(task)}
                    className="p-1.5 hover:bg-gray-100 text-gray-400 hover:text-primary rounded-md transition-colors"
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

              <div className="rounded bg-gray-950 p-4 font-mono text-[10px] text-gray-300 space-y-1 overflow-x-auto border border-gray-800 shadow-inner">
                <div className="text-gray-500 mb-2 border-b border-gray-800 pb-1">LIVE_LOGS_STREAM</div>
                <div className="flex gap-2">
                  <span className="text-blue-400">info</span>
                  <span>Task initialized by system</span>
                </div>
                 <div className="flex gap-2">
                  <span className="text-blue-400">info</span>
                  <span>Agent {selectedTask.name} assigned</span>
                </div>
                 <div className="flex gap-2">
                  <span className="text-yellow-400">exec</span>
                  <span>Running main process loop...</span>
                </div>
                 <div className="flex gap-2">
                  <span className="text-green-400">succ</span>
                  <span>Step completed successfully</span>
                </div>
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
