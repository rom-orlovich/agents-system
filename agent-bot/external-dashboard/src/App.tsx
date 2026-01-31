import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { Layout } from './components/Layout';
import { Dashboard } from './pages/Dashboard';
import { Tasks } from './pages/Tasks';
import { Agents } from './pages/Agents';
import { Analytics } from './pages/Analytics';
import { useWebSocket } from './hooks/useWebSocket';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 1000 * 30,
      retry: 3,
    },
  },
});

function WebSocketProvider({ children }: { children: React.ReactNode }) {
  useWebSocket("dashboard");
  return <>{children}</>;
}

function Settings() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Settings</h1>
        <p className="text-gray-500">Configure the dashboard</p>
      </div>

      <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
        <h2 className="text-lg font-semibold text-gray-900 mb-4">
          CLI Provider Configuration
        </h2>
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700">
              Current Provider
            </label>
            <div className="mt-1 flex items-center gap-4">
              <span className="inline-flex items-center px-3 py-1 rounded-full text-sm font-medium bg-blue-100 text-blue-800">
                {import.meta.env.VITE_CLI_PROVIDER || 'claude'}
              </span>
              <span className="text-sm text-gray-500">
                Set via CLI_PROVIDER environment variable
              </span>
            </div>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700">
              API URL
            </label>
            <input
              type="text"
              className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500"
              defaultValue={import.meta.env.VITE_API_URL || 'http://localhost:5000'}
              readOnly
            />
          </div>
        </div>
      </div>

      <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
        <h2 className="text-lg font-semibold text-gray-900 mb-4">
          Knowledge Graph
        </h2>
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700">
              Knowledge Graph URL
            </label>
            <input
              type="text"
              className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500"
              defaultValue={import.meta.env.VITE_KG_URL || 'http://localhost:4000'}
              readOnly
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700">
              MCP Server
            </label>
            <input
              type="text"
              className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500"
              defaultValue="http://knowledge-graph-mcp:9005"
              readOnly
            />
          </div>
        </div>
      </div>

      <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
        <h2 className="text-lg font-semibold text-gray-900 mb-4">
          Refresh Intervals
        </h2>
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <span className="text-sm text-gray-700">Tasks refresh</span>
            <span className="text-sm text-gray-500">5 seconds</span>
          </div>
          <div className="flex items-center justify-between">
            <span className="text-sm text-gray-700">Agents refresh</span>
            <span className="text-sm text-gray-500">10 seconds</span>
          </div>
          <div className="flex items-center justify-between">
            <span className="text-sm text-gray-700">Metrics refresh</span>
            <span className="text-sm text-gray-500">5 seconds</span>
          </div>
        </div>
      </div>
    </div>
  );
}

export function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <WebSocketProvider>
          <Layout>
            <Routes>
              <Route path="/" element={<Dashboard />} />
              <Route path="/tasks" element={<Tasks />} />
              <Route path="/agents" element={<Agents />} />
              <Route path="/analytics" element={<Analytics />} />
              <Route path="/settings" element={<Settings />} />
            </Routes>
          </Layout>
        </WebSocketProvider>
      </BrowserRouter>
    </QueryClientProvider>
  );
}
