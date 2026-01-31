import {
  Activity,
  Clock,
  CheckCircle,
  AlertCircle,
  ListTodo,
  Bot,
} from 'lucide-react';
import { MetricsCard } from '../components/MetricsCard';
import { TasksTable } from '../components/TasksTable';
import { AgentsGrid } from '../components/AgentsGrid';
import { useTasks, useTaskStats, useQueueLength } from '../hooks/useTasks';
import { useAgents } from '../hooks/useAgents';

export function Dashboard() {
  const { data: tasksData, isLoading: tasksLoading } = useTasks(undefined, 10);
  const { data: stats, isLoading: statsLoading } = useTaskStats();
  const { data: queueData } = useQueueLength();
  const { data: agents, isLoading: agentsLoading } = useAgents();

  const isLoading = tasksLoading || statsLoading || agentsLoading;

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600" />
      </div>
    );
  }

  const activeAgents = agents?.filter((a) => a.status === 'active').length || 0;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Dashboard</h1>
        <p className="text-gray-500">Overview of the agent system</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <MetricsCard
          title="Total Tasks"
          value={stats?.total || 0}
          icon={<ListTodo className="w-5 h-5" />}
        />
        <MetricsCard
          title="Queue Length"
          value={queueData?.queue_length || 0}
          icon={<Clock className="w-5 h-5" />}
        />
        <MetricsCard
          title="Success Rate"
          value={`${Math.round((stats?.success_rate || 0) * 100)}%`}
          icon={<CheckCircle className="w-5 h-5" />}
          trend={{
            value: 5.2,
            isPositive: true,
          }}
        />
        <MetricsCard
          title="Active Agents"
          value={`${activeAgents}/${agents?.length || 0}`}
          icon={<Bot className="w-5 h-5" />}
        />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <MetricsCard
          title="Running Tasks"
          value={stats?.running || 0}
          icon={<Activity className="w-5 h-5" />}
        />
        <MetricsCard
          title="Completed Today"
          value={stats?.completed || 0}
          icon={<CheckCircle className="w-5 h-5" />}
        />
        <MetricsCard
          title="Failed Today"
          value={stats?.failed || 0}
          icon={<AlertCircle className="w-5 h-5" />}
        />
      </div>

      <div>
        <h2 className="text-lg font-semibold text-gray-900 mb-4">
          Agent Status
        </h2>
        <AgentsGrid agents={agents || []} />
      </div>

      <div>
        <h2 className="text-lg font-semibold text-gray-900 mb-4">
          Recent Tasks
        </h2>
        <TasksTable tasks={tasksData?.tasks || []} />
      </div>
    </div>
  );
}
