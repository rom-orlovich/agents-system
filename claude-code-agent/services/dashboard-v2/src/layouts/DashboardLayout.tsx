import { type ReactNode, useState, useEffect } from "react";
import { useLocation } from "react-router-dom";
import { Header } from "../components/ui/Header";
import { Sidebar } from "../components/ui/Sidebar";
import { TaskStatusModal } from "../components/TaskStatusModal";
import { clsx } from "clsx";

interface DashboardLayoutProps {
  children: ReactNode;
  headerSlot?: ReactNode;
  sidebarSlot?: ReactNode;
}

export function DashboardLayout({ children, headerSlot, sidebarSlot }: DashboardLayoutProps) {
  const location = useLocation();
  const isChat = location.pathname === "/chat";
  const [sidebarOpen, setSidebarOpen] = useState(false);

  // Close sidebar when location changes on mobile
  useEffect(() => {
    setSidebarOpen(false);
  }, [location.pathname]);

  return (
    <div className="h-screen flex flex-col bg-background-app transition-colors duration-300">
      {headerSlot || (
        <Header 
          onToggleSidebar={() => setSidebarOpen(!sidebarOpen)} 
          isSidebarOpen={sidebarOpen}
        />
      )}
      <div className="flex flex-1 overflow-hidden relative">
        {/* Monitoring Grid Overlay */}
        <div className="monitoring-grid" />

        {sidebarSlot || (
          <Sidebar 
            isOpen={sidebarOpen} 
            onClose={() => setSidebarOpen(false)} 
          />
        )}
        <main
          className={clsx(
            "flex-1 relative z-10 animate-in fade-in slide-in-from-bottom-2 duration-700",
            isChat ? "overflow-hidden p-2 md:p-4" : "overflow-y-auto p-2 md:p-8",
          )}
        >
          <div className={clsx("mx-auto", isChat ? "h-full max-w-full space-y-0" : "max-w-7xl space-y-8")}>
            {children}
          </div>
        </main>
      </div>
      <TaskStatusModal />
    </div>
  );
}
