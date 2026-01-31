import { useState } from 'react';
import { TasksTable } from '../components/TasksTable';
import { TaskStatusModal } from '../components/TaskStatusModal';
import { useTasks } from '../hooks/useTasks';
import { useTaskModal } from '../hooks/useTaskModal';
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
  const { data, isLoading } = useTasks(statusFilter, 50);
  const { openTask } = useTaskModal();

  const handleTaskClick = (task: Task) => {
    openTask(task.task_id);
  };

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
          onTaskClick={handleTaskClick}
        />
      )}

      <TaskStatusModal />
    </div>
  );
}
