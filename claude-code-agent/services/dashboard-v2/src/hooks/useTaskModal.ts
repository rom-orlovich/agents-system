import { create } from "zustand";

interface TaskModalStore {
  isOpen: boolean;
  taskId: string | null;
  openTask: (taskId: string) => void;
  closeTask: () => void;
}

export const useTaskModal = create<TaskModalStore>((set) => ({
  isOpen: false,
  taskId: null,
  openTask: (taskId) => set({ isOpen: true, taskId }),
  closeTask: () => set({ isOpen: false, taskId: null }),
}));
