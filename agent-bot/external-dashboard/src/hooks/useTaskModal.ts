import { create } from "zustand";

interface TaskModalState {
  isOpen: boolean;
  taskId: string | null;
  openTask: (taskId: string) => void;
  closeTask: () => void;
}

export const useTaskModal = create<TaskModalState>((set) => ({
  isOpen: false,
  taskId: null,
  openTask: (taskId: string) => set({ isOpen: true, taskId }),
  closeTask: () => set({ isOpen: false, taskId: null }),
}));
