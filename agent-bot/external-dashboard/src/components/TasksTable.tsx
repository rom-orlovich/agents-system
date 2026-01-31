import { clsx } from 'clsx';
import { XCircle, Clock, CheckCircle, AlertCircle, Loader2 } from 'lucide-react';
import type { Task, TaskStatus } from '../types';
import { useCancelTask } from '../hooks/useTasks';

interface TasksTableProps {
  tasks: Task[];
  onTaskClick?: (task: Task) => void;
}

const statusConfig: Record<
  TaskStatus,
  { icon: React.ElementType; className: string; label: string }
> = {
  pending: { icon: Clock, className: 'text-yellow-500', label: 'Pending' },
  running: { icon: Loader2, className: 'text-blue-500 animate-spin', label: 'Running' },
  completed: { icon: CheckCircle, className: 'text-green-500', label: 'Completed' },
  failed: { icon: AlertCircle, className: 'text-red-500', label: 'Failed' },
  cancelled: { icon: XCircle, className: 'text-gray-500', label: 'Cancelled' },
};

const sourceColors: Record<string, string> = {
  github: 'bg-gray-900 text-white',
  jira: 'bg-blue-600 text-white',
  slack: 'bg-purple-600 text-white',
  sentry: 'bg-red-600 text-white',
};

function formatDate(dateString: string): string {
  const date = new Date(dateString);
  return date.toLocaleString();
}

export function TasksTable({ tasks, onTaskClick }: TasksTableProps) {
  const cancelTask = useCancelTask();

  return (
    <div className="bg-white rounded-lg shadow-sm border border-gray-200 overflow-hidden">
      <table className="min-w-full divide-y divide-gray-200">
        <thead className="bg-gray-50">
          <tr>
            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
              Task ID
            </th>
            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
              Source
            </th>
            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
              Event Type
            </th>
            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
              Status
            </th>
            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
              Created
            </th>
            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
              Actions
            </th>
          </tr>
        </thead>
        <tbody className="bg-white divide-y divide-gray-200">
          {tasks.map((task) => {
            const status = statusConfig[task.status];
            const StatusIcon = status.icon;

            return (
              <tr
                key={task.task_id}
                className="hover:bg-gray-50 cursor-pointer"
                onClick={() => onTaskClick?.(task)}
              >
                <td className="px-6 py-4 whitespace-nowrap">
                  <span className="text-sm font-mono text-gray-900">
                    {task.task_id.slice(0, 8)}...
                  </span>
                </td>
                <td className="px-6 py-4 whitespace-nowrap">
                  <span
                    className={clsx(
                      'inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium',
                      sourceColors[task.source] || 'bg-gray-200 text-gray-800'
                    )}
                  >
                    {task.source}
                  </span>
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                  {task.event_type}
                </td>
                <td className="px-6 py-4 whitespace-nowrap">
                  <div className="flex items-center gap-2">
                    <StatusIcon className={clsx('w-4 h-4', status.className)} />
                    <span className="text-sm text-gray-700">{status.label}</span>
                  </div>
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                  {formatDate(task.created_at)}
                </td>
                <td className="px-6 py-4 whitespace-nowrap">
                  {(task.status === 'pending' || task.status === 'running') && (
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        cancelTask.mutate(task.task_id);
                      }}
                      className="text-red-600 hover:text-red-800 text-sm font-medium"
                      disabled={cancelTask.isPending}
                    >
                      Cancel
                    </button>
                  )}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
      {tasks.length === 0 && (
        <div className="text-center py-12 text-gray-500">No tasks found</div>
      )}
    </div>
  );
}
