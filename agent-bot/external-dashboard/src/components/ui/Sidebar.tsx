import { type ClassValue, clsx } from "clsx";
import {
  Activity,
  BarChart3,
  Database,
  HardDrive,
  LayoutDashboard,
  Link2,
  MessageSquare,
  Package,
  Webhook,
} from "lucide-react";
import { NavLink } from "react-router-dom";
import { twMerge } from "tailwind-merge";

function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

const navItems = [
  { icon: LayoutDashboard, label: "01_OVERVIEW", path: "/" },
  { icon: BarChart3, label: "02_ANALYTICS", path: "/analytics" },
  { icon: Database, label: "03_LEDGER", path: "/ledger" },
  { icon: HardDrive, label: "04_SOURCES", path: "/sources" },
  { icon: Webhook, label: "05_WEBHOOKS", path: "/webhooks" },
  { icon: MessageSquare, label: "06_COMMS", path: "/chat" },
  { icon: Package, label: "07_REGISTRY", path: "/registry" },
  { icon: Link2, label: "08_INTEGRATIONS", path: "/integrations" },
];

interface SidebarProps {
  isOpen?: boolean;
  onClose?: () => void;
}

export function Sidebar({ isOpen, onClose }: SidebarProps) {
  return (
    <>
      {/* Mobile Overlay */}
      <div 
        className={cn(
          "fixed inset-0 bg-black/50 z-40 md:hidden transition-opacity duration-300",
          isOpen ? "opacity-100" : "opacity-0 pointer-events-none"
        )}
        onClick={onClose}
      />
      
      <aside 
        className={cn(
          "fixed md:relative top-0 left-0 h-full w-64 md:w-16 lg:w-64 border-r border-gray-200 dark:border-slate-800 bg-white dark:bg-slate-900 flex flex-col transition-all duration-300 z-40",
          "transform md:transform-none shadow-2xl md:shadow-none",
          isOpen ? "translate-x-0" : "-translate-x-full md:translate-x-0"
        )}
      >
        <nav className="flex-1 py-6">
          {navItems.map((item) => (
            <NavLink
              key={item.path}
              to={item.path}
              onClick={onClose}
              className={({ isActive }) =>
                cn(
                  "flex items-center gap-4 px-6 py-4 text-gray-500 dark:text-gray-400 transition-all duration-300 hover:bg-gray-50 dark:hover:bg-slate-800/50 relative group border-l-4",
                  isActive
                    ? "text-primary dark:text-primary bg-primary/5 dark:bg-primary/10 border-primary"
                    : "border-transparent",
                )
              }
            >
              <item.icon size={18} className="transition-transform group-hover:scale-110" />
              <span className="md:hidden lg:block font-heading text-[11px] font-bold tracking-widest uppercase">
                {item.label}
              </span>
              <div className="absolute left-full ml-2 px-2 py-1 bg-gray-900 dark:bg-slate-800 text-white text-[10px] rounded-none border border-slate-700 opacity-0 group-hover:opacity-100 pointer-events-none md:hidden lg:hidden z-50 whitespace-nowrap shadow-xl">
                {item.label}
              </div>
            </NavLink>
          ))}
        </nav>

        <div className="p-6 border-t border-gray-100 dark:border-slate-800 md:hidden lg:block">
          <div className="bg-gray-50/50 dark:bg-slate-900/50 p-4 border border-gray-100 dark:border-slate-800 relative overflow-hidden group">
            <div className="text-[9px] font-heading text-gray-400 dark:text-gray-500 mb-2 flex justify-between items-center">
              <span>SYSTEM_PULSE</span>
              <span className="text-primary animate-pulse">ACTIVE</span>
            </div>
            <div className="h-1 bg-gray-200 dark:bg-slate-800 overflow-hidden">
              <div className="h-full bg-primary w-2/3 animate-pulse-glow" />
            </div>
            <div className="absolute -right-6 -bottom-6 text-primary/5 dark:text-primary/10 transition-opacity opacity-50 group-hover:opacity-100">
              <Activity size={80} strokeWidth={1} />
            </div>
          </div>
        </div>
      </aside>
    </>
  );
}
