import { Cpu, Moon, Sun, Terminal, CheckCircle2, XCircle, Loader2, Menu, X } from "lucide-react";
import { useEffect, useState } from "react";
import { useCLIStatus } from "../../hooks/useCLIStatus";
import { useWebSocket } from "../../hooks/useWebSocket";

interface HeaderProps {
  onToggleSidebar?: () => void;
  isSidebarOpen?: boolean;
}

export function Header({ onToggleSidebar, isSidebarOpen }: HeaderProps) {
  const [isDark, setIsDark] = useState(false);
  const { active: cliActive, isLoading: cliLoading } = useCLIStatus();
  
  // Connect to WebSocket for real-time CLI status updates
  useWebSocket("dashboard");

  useEffect(() => {
    // Check local storage or system preference
    const saved = localStorage.getItem("theme");
    const systemDark = window.matchMedia("(prefers-color-scheme: dark)").matches;
    if (saved === "dark" || (!saved && systemDark)) {
      setIsDark(true);
    }
  }, []);

  useEffect(() => {
    if (isDark) {
      document.documentElement.classList.add("dark");
      localStorage.setItem("theme", "dark");
    } else {
      document.documentElement.classList.remove("dark");
      localStorage.setItem("theme", "light");
    }
  }, [isDark]);

  return (
    <header className="h-16 border-b border-gray-200 dark:border-slate-800 bg-white/80 dark:bg-slate-900/80 backdrop-blur-md flex items-center justify-between px-4 md:px-8 z-50 sticky top-0">
      <div className="flex items-center gap-3 group">
        <button
          type="button"
          onClick={onToggleSidebar}
          className="p-2 md:hidden hover:bg-gray-100 dark:hover:bg-slate-800 transition-colors dark:text-gray-400"
          aria-label="Toggle Sidebar"
        >
          {isSidebarOpen ? <X size={20} /> : <Menu size={20} />}
        </button>
        <div className="p-1.5 md:p-2 bg-primary text-white transition-transform group-hover:rotate-12">
          <Terminal size={16} className="md:w-5 md:h-5" />
        </div>
        <div className="flex flex-col">
          <span className="font-heading font-black text-base md:text-lg tracking-tight dark:text-white leading-none">
            CLAUDE_MACHINE
          </span>
          <span className="text-[8px] md:text-[9px] font-heading text-gray-400 dark:text-gray-500 tracking-[0.2em]">
            CORE_SYSTEM_ACCESS
          </span>
        </div>
      </div>

      <div className="flex items-center gap-4">
        <button
          type="button"
          onClick={() => setIsDark(!isDark)}
          className="p-2 hover:bg-gray-100 dark:hover:bg-slate-800 transition-colors rounded-none border border-transparent hover:border-gray-200 dark:hover:border-slate-700 dark:text-gray-400"
          title="TOGGLE_PHASE_MODE"
        >
          {isDark ? <Sun size={18} /> : <Moon size={18} />}
        </button>
        
        {/* CLI Status Indicator */}
        <div className="hidden md:flex items-center gap-2 px-4 py-1.5 border border-gray-200 dark:border-slate-800 text-[10px] font-heading bg-gray-50/50 dark:bg-slate-950/50">
          {cliLoading || cliActive === null ? (
            <>
              <Loader2 size={12} className="animate-spin text-yellow-500" />
              <span className="dark:text-gray-400">CLI: CHECKING...</span>
            </>
          ) : cliActive ? (
            <>
              <CheckCircle2 size={12} className="text-green-500" />
              <span className="dark:text-gray-400">CLI: ACTIVE</span>
            </>
          ) : (
            <>
              <XCircle size={12} className="text-red-500" />
              <span className="dark:text-gray-400">CLI: INACTIVE</span>
            </>
          )}
        </div>
        
        <div className="hidden md:flex items-center gap-4 px-4 py-1.5 border border-gray-200 dark:border-slate-800 text-[10px] font-heading bg-gray-50/50 dark:bg-slate-950/50">
          <div className="flex items-center gap-2">
            <span className="w-1.5 h-1.5 bg-green-500 rounded-full animate-blink" />
            <span className="dark:text-gray-400">CORE_NODE: ONLINE</span>
          </div>
          <div className="w-px h-3 bg-gray-200 dark:bg-slate-800" />
          <div className="flex items-center gap-2 text-gray-400">
            <Cpu size={12} />
            <span>GEN_6_ARC</span>
          </div>
        </div>
      </div>
    </header>
  );
}
