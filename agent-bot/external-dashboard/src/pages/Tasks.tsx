import { useState } from 'react';
import { TasksTable } from '../components/TasksTable';
import { useTasks } from '../hooks/useTasks';
import type { TaskStatus, Task } from '../types';

const statusFilters: { label: string; value: TaskStatus | undefined }[] = [
  { label: 'All', value: undefined },
  { label: 'Pending', value: 'pending' },
  { label: 'Running', value: 'running' },
  { label: 'Completed', value: 'completed' },
  { label: 'Failed', value: 'failed' },
  { label: 'Cancelled', value: 'cancelled' },
];

export function Tasks() {
  const [statusFilter, setStatusFilter] = useState<TaskStatus | undefined>();
  const [selectedTask, setSelectedTask] = useState<Task | null>(null);
  const { data, isLoading } = useTasks(statusFilter, 50);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Tasks</h1>
          <p className="text-gray-500">Manage and monitor agent tasks</p>
        </div>
        <div className="flex gap-2">
          {statusFilters.map((filter) => (
            <button
              key={filter.label}
              onClick={() => setStatusFilter(filter.value)}
              className={`px-4 py-2 text-sm font-medium rounded-lg transition-colors ${
                statusFilter === filter.value
                  ? 'bg-blue-600 text-white'
                  : 'bg-white text-gray-700 border border-gray-300 hover:bg-gray-50'
              }`}
            >
              {filter.label}
            </button>
          ))}
        </div>
      </div>

      {isLoading ? (
        <div className="flex items-center justify-center h-64">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600" />
        </div>
      ) : (
        <TasksTable
          tasks={data?.tasks || []}
          onTaskClick={(task) => setSelectedTask(task)}
        />
      )}

      {selectedTask && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg shadow-xl max-w-2xl w-full mx-4 max-h-[80vh] overflow-hidden">
            <div className="p-6 border-b border-gray-200">
              <div className="flex items-center justify-between">
                <h2 className="text-lg font-semibold">Task Details</h2>
                <button
                  onClick={() => setSelectedTask(null)}
                  className="text-gray-400 hover:text-gray-600"
                >
                  <svg
                    className="w-6 h-6"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M6 18L18 6M6 6l12 12"
                    />
                  </svg>
                </button>
              </div>
            </div>
            <div className="p-6 overflow-y-auto max-h-[60vh]">
              <dl className="space-y-4">
                <div>
                  <dt className="text-sm font-medium text-gray-500">Task ID</dt>
                  <dd className="mt-1 text-sm text-gray-900 font-mono">
                    {selectedTask.task_id}
                  </dd>
                </div>
                <div>
                  <dt className="text-sm font-medium text-gray-500">Source</dt>
                  <dd className="mt-1 text-sm text-gray-900">
                    {selectedTask.source}
                  </dd>
                </div>
                <div>
                  <dt className="text-sm font-medium text-gray-500">
                    Event Type
                  </dt>
                  <dd className="mt-1 text-sm text-gray-900">
                    {selectedTask.event_type}
                  </dd>
                </div>
                <div>
                  <dt className="text-sm font-medium text-gray-500">Status</dt>
                  <dd className="mt-1 text-sm text-gray-900">
                    {selectedTask.status}
                  </dd>
                </div>
                <div>
                  <dt className="text-sm font-medium text-gray-500">Created</dt>
                  <dd className="mt-1 text-sm text-gray-900">
                    {new Date(selectedTask.created_at).toLocaleString()}
                  </dd>
                </div>
                {selectedTask.output && (
                  <div>
                    <dt className="text-sm font-medium text-gray-500">
                      Output
                    </dt>
                    <dd className="mt-1 text-sm text-gray-900 bg-gray-50 p-4 rounded-lg font-mono whitespace-pre-wrap">
                      {selectedTask.output}
                    </dd>
                  </div>
                )}
                {selectedTask.error && (
                  <div>
                    <dt className="text-sm font-medium text-gray-500">Error</dt>
                    <dd className="mt-1 text-sm text-red-600 bg-red-50 p-4 rounded-lg font-mono">
                      {selectedTask.error}
                    </dd>
                  </div>
                )}
              </dl>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
