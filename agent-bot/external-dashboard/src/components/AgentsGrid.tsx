import { clsx } from 'clsx';
import { Activity, Pause, AlertTriangle } from 'lucide-react';
import type { Agent } from '../types';

interface AgentsGridProps {
  agents: Agent[];
}

const statusConfig = {
  active: { icon: Activity, className: 'text-green-500', bg: 'bg-green-50' },
  idle: { icon: Pause, className: 'text-yellow-500', bg: 'bg-yellow-50' },
  error: { icon: AlertTriangle, className: 'text-red-500', bg: 'bg-red-50' },
};

function formatTime(dateString: string): string {
  const date = new Date(dateString);
  const now = new Date();
  const diff = now.getTime() - date.getTime();
  const minutes = Math.floor(diff / 60000);
  const hours = Math.floor(minutes / 60);

  if (hours > 0) return `${hours}h ago`;
  if (minutes > 0) return `${minutes}m ago`;
  return 'Just now';
}

export function AgentsGrid({ agents }: AgentsGridProps) {
  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
      {agents.map((agent) => {
        const status = statusConfig[agent.status];
        const StatusIcon = status.icon;

        return (
          <div
            key={agent.name}
            className="bg-white rounded-lg shadow-sm border border-gray-200 p-4"
          >
            <div className="flex items-start justify-between">
              <div className="flex items-center gap-3">
                <div className={clsx('p-2 rounded-lg', status.bg)}>
                  <StatusIcon className={clsx('w-5 h-5', status.className)} />
                </div>
                <div>
                  <h3 className="font-medium text-gray-900">{agent.name}</h3>
                  <p className="text-sm text-gray-500">{agent.type}</p>
                </div>
              </div>
              <span
                className={clsx(
                  'inline-flex items-center px-2 py-1 rounded-full text-xs font-medium',
                  agent.status === 'active' && 'bg-green-100 text-green-800',
                  agent.status === 'idle' && 'bg-yellow-100 text-yellow-800',
                  agent.status === 'error' && 'bg-red-100 text-red-800'
                )}
              >
                {agent.status}
              </span>
            </div>
            <div className="mt-4 grid grid-cols-2 gap-4 text-sm">
              <div>
                <p className="text-gray-500">Tasks Processed</p>
                <p className="font-semibold text-gray-900">
                  {agent.tasks_processed}
                </p>
              </div>
              <div>
                <p className="text-gray-500">Last Activity</p>
                <p className="font-semibold text-gray-900">
                  {formatTime(agent.last_activity)}
                </p>
              </div>
            </div>
          </div>
        );
      })}
    </div>
  );
}
