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
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm">
      <div className="bg-white dark:bg-gray-900 rounded-lg shadow-2xl w-full max-w-3xl mx-4 overflow-hidden border border-gray-200 dark:border-gray-700">
        <div className="flex items-center justify-between p-4 border-b border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800">
          <div className="flex items-center gap-3">
            <div className={`w-2 h-2 rounded-full ${getStatusColor(taskLogs?.status || "queued")}`} />
            <h3 className="font-semibold text-sm text-gray-900 dark:text-white">
              Task: {taskId.slice(0, 8)}...
            </h3>
            {taskLogs?.is_live && (
              <span className="text-xs text-blue-500 animate-pulse font-medium">● LIVE</span>
            )}
          </div>
          <button
            type="button"
            onClick={closeTask}
            className="p-1 hover:bg-gray-200 dark:hover:bg-gray-700 rounded text-gray-400 hover:text-gray-600 dark:hover:text-gray-200 transition-colors"
          >
            <X size={18} />
          </button>
        </div>

        <div className="p-4">
          <div className="rounded-lg bg-gray-950 p-4 font-mono text-xs text-gray-300 space-y-1 overflow-y-auto max-h-[60vh] border border-gray-800">
            <div className="text-gray-500 mb-3 border-b border-gray-800 pb-2 flex justify-between items-center">
              <span className="uppercase text-xs tracking-wide">Live Logs</span>
              <span className="text-xs text-gray-600">
                Status: <span className={getStatusTextColor(taskLogs?.status || "queued")}>{taskLogs?.status || "unknown"}</span>
              </span>
            </div>
            {isLogsLoading ? (
              <div className="text-gray-500 animate-pulse">Connecting to log stream...</div>
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

        <div className="p-4 bg-gray-50 dark:bg-gray-800 border-t border-gray-200 dark:border-gray-700 flex justify-between items-center">
          <div className="text-xs text-gray-500">
            {taskLogs?.started_at && (
              <span>Started: {new Date(taskLogs.started_at).toLocaleString()}</span>
            )}
          </div>
          <button
            type="button"
            onClick={closeTask}
            className="px-4 py-2 bg-gray-200 dark:bg-gray-700 text-sm font-medium hover:bg-gray-300 dark:hover:bg-gray-600 text-gray-700 dark:text-gray-200 transition-colors rounded"
          >
            Close
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
      return "bg-gray-400";
  }
}

function getStatusTextColor(status: string) {
  switch (status) {
    case "completed":
      return "text-green-400";
    case "running":
      return "text-blue-400";
    case "failed":
      return "text-red-400";
    default:
      return "text-gray-400";
  }
}

function renderLogs(output: string) {
  if (!output) return null;

  return output.split("\n").map((line, i) => {
    if (!line.trim()) return null;

    let colorClass = "text-gray-300";
    let prefix = "";
    let content = line;

    if (line.startsWith("[CLI]")) {
      colorClass = "text-cyan-400";
      prefix = "CLI";
      content = line.substring(5).trim();
    } else if (line.startsWith("[TOOL]")) {
      colorClass = "text-yellow-400";
      prefix = "TOOL";
      content = line.substring(6).trim();
    } else if (line.startsWith("[TOOL RESULT]")) {
      colorClass = "text-green-400";
      prefix = "RESULT";
      content = line.substring(13).trim();
    } else if (line.startsWith("[LOG]")) {
      colorClass = "text-gray-500";
      prefix = "LOG";
      content = line.substring(5).trim();
    } else if (line.startsWith("[INIT]")) {
      colorClass = "text-purple-400";
      prefix = "INIT";
      content = line.substring(6).trim();
    } else if (line.includes("error") || line.includes("Error")) {
      colorClass = "text-red-400";
    } else if (line.includes("success") || line.includes("Success")) {
      colorClass = "text-green-400";
    }

    return (
      <div key={i} className="flex gap-2 leading-relaxed">
        {prefix && (
          <span className={`${colorClass} opacity-80 min-w-[50px] text-right`}>[{prefix}]</span>
        )}
        <span className={prefix ? "text-gray-300" : colorClass}>{content}</span>
      </div>
    );
  });
}
