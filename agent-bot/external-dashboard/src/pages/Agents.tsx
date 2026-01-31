import { AgentsGrid } from '../components/AgentsGrid';
import { useAgents, useAgentsHealth, useAgentsMetrics } from '../hooks/useAgents';
import { CheckCircle, AlertCircle, Clock, Activity } from 'lucide-react';

export function Agents() {
  const { data: agents, isLoading: agentsLoading } = useAgents();
  const { data: health, isLoading: healthLoading } = useAgentsHealth();
  const { data: metrics } = useAgentsMetrics();

  const isLoading = agentsLoading || healthLoading;

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600" />
      </div>
    );
  }

  const healthyCount = health?.filter((h) => h.healthy).length || 0;
  const unhealthyCount = (health?.length || 0) - healthyCount;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Agents</h1>
        <p className="text-gray-500">Monitor and manage agent instances</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-4">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-green-50 rounded-lg">
              <CheckCircle className="w-5 h-5 text-green-600" />
            </div>
            <div>
              <p className="text-sm text-gray-500">Healthy</p>
              <p className="text-xl font-semibold text-gray-900">
                {healthyCount}
              </p>
            </div>
          </div>
        </div>

        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-4">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-red-50 rounded-lg">
              <AlertCircle className="w-5 h-5 text-red-600" />
            </div>
            <div>
              <p className="text-sm text-gray-500">Unhealthy</p>
              <p className="text-xl font-semibold text-gray-900">
                {unhealthyCount}
              </p>
            </div>
          </div>
        </div>

        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-4">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-blue-50 rounded-lg">
              <Activity className="w-5 h-5 text-blue-600" />
            </div>
            <div>
              <p className="text-sm text-gray-500">Active</p>
              <p className="text-xl font-semibold text-gray-900">
                {agents?.filter((a) => a.status === 'active').length || 0}
              </p>
            </div>
          </div>
        </div>

        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-4">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-yellow-50 rounded-lg">
              <Clock className="w-5 h-5 text-yellow-600" />
            </div>
            <div>
              <p className="text-sm text-gray-500">Idle</p>
              <p className="text-xl font-semibold text-gray-900">
                {agents?.filter((a) => a.status === 'idle').length || 0}
              </p>
            </div>
          </div>
        </div>
      </div>

      <div>
        <h2 className="text-lg font-semibold text-gray-900 mb-4">
          All Agents
        </h2>
        <AgentsGrid agents={agents || []} />
      </div>

      {health && health.length > 0 && (
        <div>
          <h2 className="text-lg font-semibold text-gray-900 mb-4">
            Health Status
          </h2>
          <div className="bg-white rounded-lg shadow-sm border border-gray-200 overflow-hidden">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                    Agent
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                    Status
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                    Uptime
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                    Last Check
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200">
                {health.map((h) => (
                  <tr key={h.agent}>
                    <td className="px-6 py-4 text-sm font-medium text-gray-900">
                      {h.agent}
                    </td>
                    <td className="px-6 py-4">
                      <span
                        className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
                          h.healthy
                            ? 'bg-green-100 text-green-800'
                            : 'bg-red-100 text-red-800'
                        }`}
                      >
                        {h.healthy ? 'Healthy' : 'Unhealthy'}
                      </span>
                    </td>
                    <td className="px-6 py-4 text-sm text-gray-500">
                      {Math.round(h.uptime / 60)} min
                    </td>
                    <td className="px-6 py-4 text-sm text-gray-500">
                      {new Date(h.last_check).toLocaleString()}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {metrics && Object.keys(metrics).length > 0 && (
        <div>
          <h2 className="text-lg font-semibold text-gray-900 mb-4">Metrics</h2>
          <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
            <div className="grid grid-cols-2 md:grid-cols-4 gap-6">
              {Object.entries(metrics).map(([key, value]) => (
                <div key={key}>
                  <p className="text-sm text-gray-500">
                    {key.replace(/_/g, ' ')}
                  </p>
                  <p className="text-2xl font-semibold text-gray-900">
                    {typeof value === 'number' ? value.toLocaleString() : value}
                  </p>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
