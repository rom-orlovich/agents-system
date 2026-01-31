import { useRef, useEffect } from "react";
import { X } from "lucide-react";
import { useTaskLogs } from "../features/overview/hooks/useTaskLogs";
import { useTaskModal } from "../hooks/useTaskModal";

export function TaskStatusModal() {
  const { isOpen, taskId, closeTask } = useTaskModal();
  const { data: taskLogs, isLoading: isLogsLoading } = useTaskLogs(taskId);
  const logEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (logEndRef.current) {
      logEndRef.current.scrollIntoView({ behavior: "smooth" });
    }
  }, [taskLogs?.output]);

  if (!isOpen || !taskId) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-[2px] animate-in fade-in duration-200">
      <div className="bg-modal-bg rounded-lg shadow-2xl w-full max-w-2xl mx-4 overflow-hidden border border-modal-border animate-in zoom-in-95 duration-200 ring-1 ring-black/5">
        <div className="flex items-center justify-between p-4 border-b border-modal-border bg-background-app/80">
          <div className="flex items-center gap-2">
            <div className={`w-2 h-2 rounded-full ${getStatusColor(taskLogs?.status || "queued")}`} />
            <h3 className="font-heading font-bold text-xs uppercase tracking-wider text-app-main">
              TASK_DETAILS: {taskId}
            </h3>
          </div>
          <button
            type="button"
            onClick={closeTask}
            className="p-1 hover:bg-gray-200 dark:hover:bg-slate-800 rounded text-gray-400 hover:text-gray-600 dark:hover:text-slate-200 transition-colors"
          >
            <X size={16} />
          </button>
        </div>
        
        <div className="p-6 space-y-6">
          <div className="rounded bg-slate-950 p-4 font-mono text-[10px] text-gray-300 space-y-1 overflow-y-auto max-h-[60vh] border border-slate-800 shadow-inner">
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

        <div className="p-4 bg-background-app/50 border-t border-modal-border flex justify-end gap-2">
          <button
            type="button"
            onClick={closeTask}
            className="px-4 py-2 bg-panel-bg border border-input-border text-[10px] font-heading font-bold hover:bg-background-app text-app-main transition-colors rounded shadow-sm hover:shadow"
          >
            CLOSE_PANEL
          </button>
        </div>
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
